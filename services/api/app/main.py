from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from services.api.app.api import (
    berths,
    countries,
    locations,
    port_intelligence,
    ports,
    regions,
    terminals,
)
from services.api.app.config.settings import get_settings
from services.api.app.repositories.health_repository import HealthRepository


settings = get_settings()
health_repository = HealthRepository()

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(countries.router)
app.include_router(regions.router)
app.include_router(locations.router)
app.include_router(ports.router)
app.include_router(terminals.router)
app.include_router(berths.router)
app.include_router(port_intelligence.router)


@app.get("/")
def root():
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "status": "running",
    }


@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "api",
        "environment": settings.environment,
    }


@app.get("/health/database")
def database_health():
    return health_repository.check_database()
