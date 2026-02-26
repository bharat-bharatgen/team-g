import os
import logging
from contextlib import asynccontextmanager

# Set thread caps before any lib that uses OpenMP/ONNX loads (Tesseract, InsightFace)
from app.config import settings
os.environ.setdefault("OMP_NUM_THREADS", str(settings.omp_num_threads))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1.router import api_router
from app.dependencies import connect_to_mongo, close_mongo_connection
from app.services.common.tesseract_ocr import shutdown_ocr_pool

# ─── Logging configuration ──────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)-20s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
# Set DEBUG for our processing modules when needed
logging.getLogger("mer_processor").setLevel(logging.INFO)
logging.getLogger("llm_client").setLevel(logging.INFO)
logging.getLogger("tesseract_ocr").setLevel(logging.INFO)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await connect_to_mongo()
    yield
    # Cleanup on shutdown
    shutdown_ocr_pool(wait=True)
    await close_mongo_connection()


app = FastAPI(
    title="Insurance Underwriting Copilot",
    description="Backend API for automated insurance document processing",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173","https://bharatgen-insurance-copilot.vercel.app"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api/v1")


@app.get("/health")
async def health_check():
    return {"status": "healthy"}
