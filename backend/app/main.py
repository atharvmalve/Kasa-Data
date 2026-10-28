from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.core.config import settings
from app.core.logging import logger
from app.api.routes import health, datapacks, documents, processing


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting Kasa backend service...")
    yield
    logger.info("Stopping Kasa backend service...")


app = FastAPI(
    title="Kasa Context Engine API",
    description="Local-first context engine - Ingestion and enrichment pipeline",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global safe exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled server error on {request.method} {request.url.path}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "An internal server error occurred. Please consult backend logs."}
    )

# Include API routes under /api
app.include_router(health.router, prefix="/api")
app.include_router(datapacks.router, prefix="/api")
app.include_router(documents.router, prefix="/api")
app.include_router(processing.router, prefix="/api")


@app.get("/")
def root():
    return {
        "name": "Kasa Context Engine API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/api/health"
    }

