import logging
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from app.config import settings
from app.modules.users import routes as users_routes
from app.modules.auth import routes as auth_routes
from app.modules.templates import routes as templates_routes
from app.modules.workshops import routes as workshops_routes
from app.modules.deployments import routes as deployments_routes
from app.modules.groups import routes as groups_routes
from app.modules.environments import routes as environments_routes
from app.modules.roles import routes as roles_routes
from app.modules.template_groups import routes as template_groups_routes

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%SZ",
)
logger = logging.getLogger(__name__)

limiter = Limiter(key_func=get_remote_address, default_limits=[settings.rate_limit])
app = FastAPI(
    title=settings.app_name,
    debug=settings.debug,
    redirect_slashes=False,
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled exception: %s", exc)
    if settings.is_production:
        return JSONResponse(status_code=500, content={"detail": "Internal server error"})
    return JSONResponse(status_code=500, content={"detail": str(exc)})


class SecurityHeadersMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        async def send_with_headers(message):
            if message["type"] == "http.response.start":
                message.setdefault("headers", [])
                message["headers"].extend([
                    (b"X-Content-Type-Options", b"nosniff"),
                    (b"X-Frame-Options", b"DENY"),
                    (b"X-XSS-Protection", b"1; mode=block"),
                ])
            await send(message)

        await self.app(scope, receive, send_with_headers)


app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.get_cors_origins_list(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include module routes
app.include_router(users_routes.router, prefix="/api/v1")
app.include_router(auth_routes.router, prefix="/api/v1")
app.include_router(templates_routes.router, prefix="/api/v1")
app.include_router(workshops_routes.router, prefix="/api/v1")
app.include_router(deployments_routes.router, prefix="/api/v1")
app.include_router(groups_routes.router, prefix="/api/v1")
app.include_router(environments_routes.router, prefix="/api/v1")
app.include_router(roles_routes.router, prefix="/api/v1")
app.include_router(template_groups_routes.router, prefix="/api/v1")


@app.on_event("startup")
async def startup_event():
    logger.info("Application startup")
    
    # # Start TTL scheduler for automatic workshop destruction
    # from app.modules.workshops.ttl_scheduler import ttl_scheduler_loop
    # import asyncio
    # asyncio.create_task(ttl_scheduler_loop())
    # logger.info("TTL scheduler started - will check for expired workshops every 5 minutes")


@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Application shutdown")


@app.get("/")
async def root():
    return {"message": "Welcome to elaas-backend", "status": "healthy"}


@app.get("/health")
@limiter.exempt
async def health():
    return {"status": "healthy"}


@app.get("/ready")
@limiter.exempt
async def ready():
    """Readiness probe: extend here with DB/Kafka checks if needed."""
    return {"status": "ready"}
