export type HealthStatus = "HEALTHY" | "DEGRADED" | "CRITICAL";

export interface SignalFeedItem {
  id?: string;
  ticker: string;
  signal_type: string;
  probability: number;
  expected_return: number;
  risk_score: number;
  regime: string;
  confidence: number;
  model_agreement: number;
  timestamp?: string;
}

export interface OverviewPayload {
  kpis: {
    active_signals: number;
    current_regime: string | null;
    models_tracked: number;
    calibration_error: number;
    drift_warnings: number;
    system_status: HealthStatus;
  };
  signals: Record<string, unknown>;
  models: Record<string, unknown>;
  calibration: Record<string, unknown>;
  regimes: Record<string, unknown>;
  drift: Record<string, unknown>;
  infra: Record<string, unknown>;
  updated_at: string;
}
