from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from backend.db.repository import SupabaseRepository


def explain_signal(
    audit_id: str,
    *,
    repository: SupabaseRepository | None = None,
) -> dict[str, Any] | None:
    repository = repository or SupabaseRepository()
    audit = repository.get_signal_audit_log(audit_id)
    if not audit:
        return None

    stock = audit.get("stocks") or {}
    models_involved = audit.get("models_involved") or []
    meta_output = audit.get("final_meta_model_output") or {}
    guardrails = audit.get("guardrail_decision") or {}

    chain = [
        {
            "step": "model_outputs",
            "detail": models_involved,
        },
        {
            "step": "calibration",
            "detail": audit.get("calibration_values") or {},
        },
        {
            "step": "regime",
            "detail": audit.get("regime"),
        },
        {
            "step": "meta_model",
            "detail": meta_output,
        },
        {
            "step": "guardrails",
            "detail": guardrails,
        },
        {
            "step": "final_decision",
            "detail": {
                "allowed": guardrails.get("allowed", True),
                "signal_type": meta_output.get("signal_type") or guardrails.get("adjusted_signal_type"),
            },
        },
    ]

    return {
        "audit_id": audit_id,
        "ticker": stock.get("ticker"),
        "timestamp": audit.get("timestamp"),
        "reasoning_chain": chain,
        "portfolio_state": meta_output.get("portfolio_state"),
        "raw": audit,
    }


def build_audit_center_payload(
    repository: SupabaseRepository | None = None,
    *,
    limit: int = 100,
) -> dict[str, Any]:
    repository = repository or SupabaseRepository()
    audits = repository.list_signal_audit_logs(limit=limit)
    enriched = []
    for audit in audits:
        stock = audit.get("stocks") if isinstance(audit.get("stocks"), dict) else {}
        enriched.append(
            {
                "id": audit.get("id"),
                "ticker": stock.get("ticker") if stock else None,
                "timestamp": audit.get("timestamp"),
                "regime": audit.get("regime"),
                "blocked": not (audit.get("guardrail_decision") or {}).get("allowed", True),
            }
        )

    return {
        "recent_audits": enriched,
        "total": len(enriched),
        "updated_at": datetime.now(tz=UTC).isoformat(),
    }
