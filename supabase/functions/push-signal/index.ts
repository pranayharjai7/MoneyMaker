import { createClient } from 'https://esm.sh/@supabase/supabase-js@2.48.1';

type NotificationEvent = {
  id: string;
  user_id: string;
  title: string;
  body: string;
  data: Record<string, unknown>;
  attempts: number;
};

type Device = {
  push_token: string;
  platform: 'ios' | 'android';
};

const supabaseUrl = Deno.env.get('SUPABASE_URL') ?? '';
const serviceRoleKey = Deno.env.get('SUPABASE_SERVICE_ROLE_KEY') ?? '';
const firebaseProjectId = Deno.env.get('FIREBASE_PROJECT_ID') ?? '';

const supabase = createClient(supabaseUrl, serviceRoleKey, {
  auth: { persistSession: false },
});

Deno.serve(async (request) => {
  if (request.method !== 'POST') {
    return new Response('Method not allowed', { status: 405 });
  }

  const payload = await request.json().catch(() => ({}));
  const event = parseNotificationEvent(payload);
  if (!event) {
    return new Response('Missing notification event record', { status: 400 });
  }

  const { data: devices, error: devicesError } = await supabase
    .from('user_devices')
    .select('push_token, platform')
    .eq('user_id', event.user_id)
    .eq('is_active', true);

  if (devicesError) {
    await markFailed(event, devicesError.message);
    return Response.json({ ok: false, error: devicesError.message }, { status: 500 });
  }

  const tokens = ((devices ?? []) as Device[])
    .map((device) => device.push_token)
    .filter(Boolean);

  if (tokens.length === 0) {
    await markFailed(event, 'No active device tokens');
    return Response.json({ ok: true, sent: 0 });
  }

  const accessToken = await firebaseAccessToken();
  const results = await Promise.allSettled(
    tokens.map((token) => sendFcm(accessToken, token, event)),
  );
  const failures = results.filter((result) => result.status === 'rejected');

  if (failures.length > 0) {
    await markFailed(event, `${failures.length} FCM sends failed`);
    return Response.json({ ok: false, sent: tokens.length - failures.length });
  }

  await supabase
    .from('notification_events')
    .update({
      status: 'sent',
      attempts: event.attempts + 1,
      sent_at: new Date().toISOString(),
      last_error: null,
    })
    .eq('id', event.id);

  return Response.json({ ok: true, sent: tokens.length });
});

function parseNotificationEvent(payload: Record<string, unknown>): NotificationEvent | null {
  const record = (payload.record ?? payload) as Record<string, unknown>;
  if (!record.id || !record.user_id) {
    return null;
  }
  return {
    id: String(record.id),
    user_id: String(record.user_id),
    title: String(record.title ?? 'MoneyMaker AI'),
    body: String(record.body ?? ''),
    data: (record.data ?? {}) as Record<string, unknown>,
    attempts: Number(record.attempts ?? 0),
  };
}

async function markFailed(event: NotificationEvent, error: string) {
  await supabase
    .from('notification_events')
    .update({
      status: 'failed',
      attempts: event.attempts + 1,
      last_error: error,
    })
    .eq('id', event.id);
}

async function sendFcm(
  accessToken: string,
  token: string,
  event: NotificationEvent,
) {
  const response = await fetch(
    `https://fcm.googleapis.com/v1/projects/${firebaseProjectId}/messages:send`,
    {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${accessToken}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        message: {
          token,
          notification: {
            title: event.title,
            body: event.body,
          },
          data: stringifyData(event.data),
          android: {
            priority: 'HIGH',
            notification: { channel_id: 'trading_signals' },
          },
          apns: {
            payload: {
              aps: {
                sound: 'default',
                badge: 1,
              },
            },
          },
        },
      }),
    },
  );

  if (!response.ok) {
    throw new Error(await response.text());
  }
}

function stringifyData(data: Record<string, unknown>) {
  return Object.fromEntries(
    Object.entries(data).map(([key, value]) => [key, String(value ?? '')]),
  );
}

async function firebaseAccessToken() {
  const serviceAccount = serviceAccountConfig();
  const now = Math.floor(Date.now() / 1000);
  const jwt = await signJwt(
    {
      alg: 'RS256',
      typ: 'JWT',
    },
    {
      iss: serviceAccount.clientEmail,
      scope: 'https://www.googleapis.com/auth/firebase.messaging',
      aud: 'https://oauth2.googleapis.com/token',
      iat: now,
      exp: now + 3600,
    },
    serviceAccount.privateKey,
  );

  const response = await fetch('https://oauth2.googleapis.com/token', {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: new URLSearchParams({
      grant_type: 'urn:ietf:params:oauth:grant-type:jwt-bearer',
      assertion: jwt,
    }),
  });

  if (!response.ok) {
    throw new Error(await response.text());
  }
  const json = await response.json();
  return String(json.access_token);
}

function serviceAccountConfig() {
  const raw = Deno.env.get('FIREBASE_SERVICE_ACCOUNT_JSON');
  if (raw) {
    const parsed = JSON.parse(raw);
    return {
      clientEmail: String(parsed.client_email),
      privateKey: String(parsed.private_key),
    };
  }
  return {
    clientEmail: Deno.env.get('FIREBASE_CLIENT_EMAIL') ?? '',
    privateKey: (Deno.env.get('FIREBASE_PRIVATE_KEY') ?? '').replace(/\\n/g, '\n'),
  };
}

async function signJwt(
  header: Record<string, unknown>,
  payload: Record<string, unknown>,
  privateKeyPem: string,
) {
  const encodedHeader = base64UrlEncode(JSON.stringify(header));
  const encodedPayload = base64UrlEncode(JSON.stringify(payload));
  const unsigned = `${encodedHeader}.${encodedPayload}`;
  const key = await crypto.subtle.importKey(
    'pkcs8',
    pemToArrayBuffer(privateKeyPem),
    { name: 'RSASSA-PKCS1-v1_5', hash: 'SHA-256' },
    false,
    ['sign'],
  );
  const signature = await crypto.subtle.sign(
    'RSASSA-PKCS1-v1_5',
    key,
    new TextEncoder().encode(unsigned),
  );
  return `${unsigned}.${base64UrlEncode(signature)}`;
}

function pemToArrayBuffer(pem: string) {
  const base64 = pem
    .replace('-----BEGIN PRIVATE KEY-----', '')
    .replace('-----END PRIVATE KEY-----', '')
    .replace(/\s/g, '');
  const binary = atob(base64);
  const bytes = new Uint8Array(binary.length);
  for (let index = 0; index < binary.length; index += 1) {
    bytes[index] = binary.charCodeAt(index);
  }
  return bytes.buffer;
}

function base64UrlEncode(input: string | ArrayBuffer) {
  const bytes = typeof input === 'string' ? new TextEncoder().encode(input) : new Uint8Array(input);
  let binary = '';
  for (const byte of bytes) {
    binary += String.fromCharCode(byte);
  }
  return btoa(binary).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/g, '');
}
