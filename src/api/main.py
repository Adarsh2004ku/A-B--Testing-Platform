from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.utils.logger import get_logger
from src.utils.database import check_db_connection
from src.api.routes.assign import router as assign_router
from src.api.routes.events import router as events_router
from src.api.routes.results import router as results_router

logger = get_logger(__name__)

app = FastAPI(
    title="A/B Testing Platform",
    description="Production-grade experimentation platform",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup():
    logger.info("Starting A/B Testing Platform")
    check_db_connection()

@app.get("/health")
def health():
    return {"status": "ok", "db": check_db_connection()}

@app.get("/")
def root():
    return {"status": "ok", "message": "A/B Testing Platform"}

app.include_router(assign_router, prefix="/api/v1", tags=["assignment"])
app.include_router(events_router, prefix="/api/v1", tags=["events"])
app.include_router(results_router, prefix="/api/v1", tags=["results"])
