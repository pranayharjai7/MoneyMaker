import { createClient } from 'https://esm.sh/@supabase/supabase-js@2.48.1';

const supabaseUrl = Deno.env.get('SUPABASE_URL') ?? '';
const serviceRoleKey = Deno.env.get('SUPABASE_SERVICE_ROLE_KEY') ?? '';
const webhookSecret = Deno.env.get('REVENUECAT_WEBHOOK_SECRET') ?? '';

const supabase = createClient(supabaseUrl, serviceRoleKey, {
  auth: { persistSession: false },
});

Deno.serve(async (request) => {
  if (request.method !== 'POST') {
    return new Response('Method not allowed', { status: 405 });
  }

  if (webhookSecret) {
    const authorization = request.headers.get('authorization') ?? '';
    const provided = authorization.replace(/^Bearer\s+/i, '');
    if (provided !== webhookSecret) {
      return new Response('Unauthorized', { status: 401 });
    }
  }

  const body = await request.json();
  const event = body.event ?? body;
  const userId = String(event.app_user_id ?? '');
  if (!userId) {
    return new Response('Missing app_user_id', { status: 400 });
  }

  const productId = String(event.product_id ?? '');
  const entitlementIds = normalizeEntitlements(event.entitlement_ids ?? event.entitlement_id);
  const type = String(event.type ?? '').toUpperCase();
  const expiresAt = event.expiration_at_ms
    ? new Date(Number(event.expiration_at_ms)).toISOString()
    : null;
  const accessLevel = type.includes('EXPIRATION') || type.includes('CANCELLATION')
    ? 'free'
    : accessLevelFor(entitlementIds, productId);

  const { error } = await supabase
    .from('user_entitlements')
    .upsert(
      {
        user_id: userId,
        revenuecat_app_user_id: userId,
        access_level: accessLevel,
        active_entitlements: accessLevel === 'free' ? [] : entitlementIds,
        product_id: productId || null,
        expires_at: expiresAt,
        source: 'revenuecat',
        updated_at: new Date().toISOString(),
      },
      { onConflict: 'user_id' },
    );

  if (error) {
    return Response.json({ ok: false, error: error.message }, { status: 500 });
  }

  return Response.json({ ok: true, access_level: accessLevel });
});

function normalizeEntitlements(value: unknown): string[] {
  if (Array.isArray(value)) {
    return value.map((item) => String(item).toLowerCase());
  }
  if (typeof value === 'string' && value.length > 0) {
    return [value.toLowerCase()];
  }
  return [];
}

function accessLevelFor(entitlements: string[], productId: string) {
  const haystack = `${entitlements.join(' ')} ${productId}`.toLowerCase();
  if (haystack.includes('elite')) {
    return 'elite';
  }
  if (haystack.includes('pro')) {
    return 'pro';
  }
  return 'free';
}
