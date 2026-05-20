from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api.routes import (
    alerts,
    calibration,
    feedback,
    portfolio,
    regime,
    signals,
    simulation,
    stocks,
    watchlist,
)
from backend.api.schemas import StatusOut
from backend.core.config import get_settings


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.app_name)
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

    @app.get("/health", response_model=StatusOut, tags=["health"])
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
