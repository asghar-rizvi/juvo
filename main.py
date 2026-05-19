"""
Juvo Service Orchestrator - Main Application
Phase 4: Complete API with Chat, HTL, Bookings, Provider Dashboard
"""
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import time

from src.core.config import settings
from src.utils.logger import setup_logging, get_logger

# Setup logging first
setup_logging(log_level=settings.LOG_LEVEL)
logger = get_logger(__name__)

# Rate limiter
limiter = Limiter(key_func=get_remote_address)

# ============================================
# FastAPI Application
# ============================================

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="""
    ## Juvo Service Orchestrator API

    AI-powered service matching for Pakistan's informal economy.

    ### Features
    - 🤖 **AI Chat Agent** - Multi-lingual service matching (Urdu, Roman Urdu, English)
    - 🔒 **HTL System** - 5-minute slot reservation hold
    - 📅 **Bookings** - Complete lifecycle management
    - 🏪 **Provider Dashboard** - Slot management & analytics
    - 🔐 **JWT Auth** - Secure role-based access

    ### Authentication
    1. Register: `POST /api/v1/auth/register/user`
    2. Login: `POST /api/v1/auth/login/user`
    3. Use token: `Authorization: Bearer <access_token>`

    ### Roles
    - **User** (Customer): Chat, HTL, Bookings
    - **Provider**: Dashboard, Slots, Analytics
    """,
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
    openapi_tags=[
        {
            "name": "Authentication",
            "description": "User and Provider registration, login, token management"
        },
        {
            "name": "Chat & AI Agent",
            "description": "AI-powered service matching conversation"
        },
        {
            "name": "HTL Reservations",
            "description": "Hold-to-Lock: 5-minute slot reservations"
        },
        {
            "name": "Bookings",
            "description": "Complete booking lifecycle for users"
        },
        {
            "name": "Provider Dashboard",
            "description": "Slot management and analytics for providers"
        },
        {
            "name": "System",
            "description": "Health checks and system info"
        }
    ]
)

# ============================================
# Middleware
# ============================================

# Rate limiter
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all requests with timing"""
    start_time = time.time()

    logger.info(f"→ {request.method} {request.url.path}")

    response = await call_next(request)

    duration = time.time() - start_time

    logger.info(
        f"← {request.method} {request.url.path} "
        f"| {response.status_code} "
        f"| {duration:.3f}s"
    )

    response.headers["X-Process-Time"] = str(round(duration, 3))
    response.headers["X-API-Version"] = settings.APP_VERSION

    return response


# ============================================
# Exception Handlers
# ============================================

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request,
    exc: RequestValidationError
):
    """Handle Pydantic validation errors"""
    errors = []
    for error in exc.errors():
        field = " -> ".join([str(loc) for loc in error["loc"]])
        errors.append({
            "field": field,
            "message": error["msg"],
            "type": error["type"]
        })

    logger.warning(f"Validation error on {request.url.path}: {errors}")

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "detail": "Validation error",
            "errors": errors,
            "path": str(request.url.path)
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle unexpected errors"""
    logger.error(
        f"Unhandled error on {request.url.path}: {str(exc)}",
        exc_info=True
    )

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": "Internal server error",
            "message": str(exc) if settings.DEBUG else "An unexpected error occurred",
            "path": str(request.url.path)
        }
    )


# ============================================
# API Routes - Include ALL Routers
# ============================================

from src.api.v1 import auth, chat, htl, bookings, providers

app.include_router(auth.router, prefix=settings.API_V1_PREFIX)
app.include_router(chat.router, prefix=settings.API_V1_PREFIX)
app.include_router(htl.router, prefix=settings.API_V1_PREFIX)
app.include_router(bookings.router, prefix=settings.API_V1_PREFIX)
app.include_router(providers.router, prefix=settings.API_V1_PREFIX)


# ============================================
# Root & Health Endpoints
# ============================================

@app.get("/", tags=["System"])
def root():
    """API root - service info"""
    return {
        "service": "Juvo Service Orchestrator",
        "version": settings.APP_VERSION,
        "environment": settings.APP_ENV,
        "docs": "/docs",
        "health": "/health",
        "status": "operational"
    }


@app.get("/health", tags=["System"])
def health_check():
    """Health check with DB and background task status"""
    from src.database.connection import test_connection
    from src.core.background_tasks import get_task_status

    db_healthy = test_connection()
    task_status = get_task_status()

    overall = "healthy" if db_healthy else "degraded"

    return {
        "status": overall,
        "timestamp": time.time(),
        "environment": settings.APP_ENV,
        "database": "connected" if db_healthy else "disconnected",
        "background_tasks": task_status,
        "version": settings.APP_VERSION
    }


@app.get("/api/v1", tags=["System"])
def api_info():
    """API v1 endpoint overview"""
    return {
        "version": "1.0.0",
        "prefix": settings.API_V1_PREFIX,
        "endpoints": {
            "auth": {
                "register_user":    f"{settings.API_V1_PREFIX}/auth/register/user",
                "login_user":       f"{settings.API_V1_PREFIX}/auth/login/user",
                "register_provider":f"{settings.API_V1_PREFIX}/auth/register/provider",
                "login_provider":   f"{settings.API_V1_PREFIX}/auth/login/provider",
                "refresh":          f"{settings.API_V1_PREFIX}/auth/refresh",
                "logout":           f"{settings.API_V1_PREFIX}/auth/logout",
                "me_user":          f"{settings.API_V1_PREFIX}/auth/me/user",
                "me_provider":      f"{settings.API_V1_PREFIX}/auth/me/provider",
            },
            "chat": {
                "start":    f"{settings.API_V1_PREFIX}/chat/start",
                "message":  f"{settings.API_V1_PREFIX}/chat/message",
                "history":  f"{settings.API_V1_PREFIX}/chat/history/{{session_id}}",
                "end":      f"{settings.API_V1_PREFIX}/chat/end/{{session_id}}",
            },
            "htl": {
                "reserve":  f"{settings.API_V1_PREFIX}/htl/reserve",
                "confirm":  f"{settings.API_V1_PREFIX}/htl/confirm",
                "cancel":   f"{settings.API_V1_PREFIX}/htl/cancel/{{id}}",
                "active":   f"{settings.API_V1_PREFIX}/htl/active",
            },
            "bookings": {
                "create":   f"{settings.API_V1_PREFIX}/bookings",
                "list":     f"{settings.API_V1_PREFIX}/bookings",
                "detail":   f"{settings.API_V1_PREFIX}/bookings/{{id}}",
                "cancel":   f"{settings.API_V1_PREFIX}/bookings/{{id}}/cancel",
                "review":   f"{settings.API_V1_PREFIX}/bookings/{{id}}/review",
            },
            "providers": {
                "bookings":         f"{settings.API_V1_PREFIX}/providers/bookings",
                "booking_status":   f"{settings.API_V1_PREFIX}/providers/bookings/{{id}}/status",
                "slots":            f"{settings.API_V1_PREFIX}/providers/slots",
                "create_slots":     f"{settings.API_V1_PREFIX}/providers/slots",
                "delete_slot":      f"{settings.API_V1_PREFIX}/providers/slots/{{id}}",
                "profile":          f"{settings.API_V1_PREFIX}/providers/profile",
                "analytics":        f"{settings.API_V1_PREFIX}/providers/analytics",
            }
        }
    }


# ============================================
# Startup & Shutdown Events
# ============================================

@app.on_event("startup")
async def startup_event():
    """Application startup"""
    logger.info("=" * 60)
    logger.info(f"  Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    logger.info(f"  Environment : {settings.APP_ENV}")
    logger.info(f"  Debug Mode  : {settings.DEBUG}")
    logger.info(f"  API Prefix  : {settings.API_V1_PREFIX}")
    logger.info("=" * 60)

    # Test database
    from src.database.connection import test_connection, verify_postgis
    if test_connection():
        logger.info("✓ PostgreSQL connected")
    else:
        logger.error("✗ PostgreSQL connection FAILED")

    if verify_postgis():
        logger.info("✓ PostGIS extension verified")
    else:
        logger.warning("⚠ PostGIS not available")

    # Start background tasks
    from src.core.background_tasks import start_background_tasks
    start_background_tasks()

    logger.info("✓ All systems operational")
    logger.info(f"  Docs available at: http://localhost:{settings.PORT}/docs")
    logger.info("=" * 60)


@app.on_event("shutdown")
async def shutdown_event():
    """Application shutdown"""
    logger.info("Shutting down Juvo API...")

    # Stop background tasks
    from src.core.background_tasks import stop_background_tasks
    stop_background_tasks()

    logger.info("✓ Shutdown complete")


# ============================================
# Run directly
# ============================================

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload= False,
        log_level=settings.LOG_LEVEL.lower()
    )