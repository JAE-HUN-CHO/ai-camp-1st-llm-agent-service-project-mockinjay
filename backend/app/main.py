import os
import sys
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

# Load environment variables from .env file
load_dotenv()

# Add backend directory to path
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

from app.db.connection import Database, check_connection, init_legacy_collections
from app.db.indexes import create_indexes
from app.features.chat.runtime import StreamRegistry
from app.services.agent_runtime import AgentRuntime
from app.core.context_system import ContextSystem
from app.features.research.runtime import ResearchRuntime
from app.api.chat import close_parlant_server
from app.api.careguide import router as careguide_router
from app.api.clinical_trials import router as clinical_trials_router
from app.api.terms import router as terms_router
from app.api.diet_care import router as diet_care_router
from app.api.news import router as news_router
from app.api.error_handlers import (
    not_found_handler,
    internal_server_error_handler,
    validation_error_handler
)
from app.middleware.auth import AuthenticationMiddleware

# Setup logging
from app.logging_config import setup_logging

logger = setup_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    logger.info("Application starting up...")
    app.state.stream_registry = StreamRegistry()
    app.state.agent_runtime = AgentRuntime()
    app.state.context_system = ContextSystem()
    app.state.research_runtime = ResearchRuntime()
    # Initialize MongoDB connection
    await Database.connect()
    # Initialize legacy collection variables for backward compatibility
    init_legacy_collections()
    # Create database indexes
    await create_indexes(Database.db)
    logger.info("Database initialized with indexes")

    yield

    # Cleanup on shutdown
    await close_parlant_server(app.state.agent_runtime)
    await app.state.research_runtime.close()
    await Database.disconnect()
    logger.info("Application shutting down...")


app = FastAPI(
    title="CareGuide API",
    version="1.0.0",
    lifespan=lifespan
)

# Mount static files directory
uploads_dir = backend_path / "uploads"
uploads_dir.mkdir(exist_ok=True)
app.mount("/uploads", StaticFiles(directory=str(uploads_dir)), name="uploads")

# CORS 설정 - 환경변수 기반
from app.config import settings

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,  # 환경변수에서 읽어옴
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=[
        "Content-Type",
        "Authorization",
        "Accept",
        "Origin",
        "X-Requested-With",
        "X-CSRF-Token",
    ],
    expose_headers=["Content-Length", "X-Request-ID"],
    max_age=600,  # Preflight 요청 캐시 시간 (초)
)

# Authentication Middleware
# Note: Add this after CORS middleware
app.add_middleware(AuthenticationMiddleware)


# Include routers
# Include CareGuide Master Router (contains all main API routes)
app.include_router(careguide_router)

# Include additional routers from PR #25
app.include_router(clinical_trials_router)
app.include_router(terms_router)
app.include_router(diet_care_router)
app.include_router(news_router)


# Error handlers (UTI-005)
# app.add_exception_handler(StarletteHTTPException, not_found_handler)  # Removed: This converts all HTTP errors to 404
app.add_exception_handler(Exception, internal_server_error_handler)
app.add_exception_handler(RequestValidationError, validation_error_handler)


@app.get("/")
def root():
    return {"message": "CareGuide API", "version": "1.0.0"}


@app.get("/health")
def health_check():
    return {"status": "healthy"}


@app.get("/db-check")
async def database_check():
    """MongoDB 연결 상태 확인"""
    return await check_connection()


@app.get("/test/error/500")
def test_server_error():
    """500 에러 테스트용 엔드포인트"""
    raise Exception("의도적인 500 에러 테스트")


# Note: /api/session/create and /api/nutrition/analyze are registered via
# app.api.session.router and app.api.nutrition.router (included by careguide_router).
# Legacy inline definitions removed to avoid duplicate route registration.
