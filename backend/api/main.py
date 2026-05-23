from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.analytics_api import routes as analytics_routes
from backend.historical_api import router as historical_router
from backend.quant_dashboard_api import router as quant_dashboard_router
from backend.api.routes import (
    alerts,
    calibration,
    feedback,
    health as health_routes,
    portfolio,
    regime,
    signals,
    simulation,
    stocks,
    watchlist,
    trade_planning,
)
from backend.api.schemas import StatusOut
from backend.core.config import get_settings
from backend.observability.logging import CorrelationIdMiddleware, configure_json_logging


def create_app() -> FastAPI:
    settings = get_settings()
    configure_json_logging()
    app = FastAPI(title=settings.app_name)
    app.add_middleware(CorrelationIdMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(stocks.router, prefix=settings.api_prefix)
    app.include_router(signals.router, prefix=settings.api_prefix)
    app.include_router(watchlist.router, prefix=settings.api_prefix)
    app.include_router(portfolio.router, prefix=settings.api_prefix)
    app.include_router(alerts.router, prefix=settings.api_prefix)
    app.include_router(feedback.router, prefix=settings.api_prefix)
    app.include_router(calibration.router, prefix=settings.api_prefix)
    app.include_router(regime.router, prefix=settings.api_prefix)
    app.include_router(simulation.router, prefix=settings.api_prefix)
    app.include_router(health_routes.router, prefix=settings.api_prefix)
    app.include_router(analytics_routes.router, prefix=settings.api_prefix)
    app.include_router(historical_router, prefix=settings.api_prefix)
    app.include_router(quant_dashboard_router, prefix=settings.api_prefix)
    app.include_router(trade_planning.router, prefix=settings.api_prefix)


    @app.get("/health", response_model=StatusOut, tags=["health"])
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
