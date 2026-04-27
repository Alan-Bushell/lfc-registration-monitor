from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import os
from app.api import auth, stripe
from app.db.session import engine, Base
from app.services.worker import check_lfc_site
from app.core.config import settings
import logging

# Create tables on startup (simplification for dev)
import asyncio

app = FastAPI(title="LFC Monitor API")

origins = []
if settings.FRONTEND_URL:
    origins.append(settings.FRONTEND_URL)

for dev_origin in ("http://localhost:5173", "http://127.0.0.1:5173"):
    if dev_origin not in origins:
        origins.append(dev_origin)

# Allow frontend to access API
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

logger = logging.getLogger(__name__)

async def run_worker_loop():
    while True:
        try:
            logger.info("Starting scheduled scrape job...")
            await check_lfc_site()
            logger.info("Scrape job finished. Sleeping for 1 hour.")
        except Exception as e:
            logger.error(f"Worker crashed: {e}")
        
        await asyncio.sleep(3600) # Run every hour

@app.on_event("startup")
async def startup():
    # Database Init
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        # We continue starting up so the container doesn't crash on deploy
        # and we can see the logs.
    
    # In production (Cloud Run), persistent background tasks are unreliable.
    # Use Cloud Scheduler to hit the /cron/scrape endpoint instead.
    # asyncio.create_task(run_worker_loop())

@app.post("/cron/scrape", tags=["Worker"])
async def trigger_scrape():
    """Endpoint for Cloud Scheduler or manual trigger"""
    logger.info("Manual/Scheduled scrape trigger received")
    try:
        await check_lfc_site()
        return {"status": "success", "message": "Scrape completed"}
    except Exception as e:
        logger.error(f"Scrape failed: {e}")
        return {"status": "error", "message": str(e)}

app.include_router(auth.router, prefix="/auth", tags=["Auth"])
app.include_router(stripe.router, prefix="/stripe", tags=["Payments"])

from fastapi.responses import FileResponse

# ... (imports)

# Mount static files for frontend (Production only)
# IMPORTANT: This must be the LAST route defined
if os.path.exists("app/static"):
    app.mount("/assets", StaticFiles(directory="app/static/assets"), name="assets")
    
    # Catch-all route to serve index.html for SPA routing
    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        # Allow API calls to pass through (should be caught by routers above if they exist)
        # However, we must allow /auth/callback to serve index.html (so remove startswith checking for auth)
        if full_path.startswith("api/") or full_path.startswith("stripe/") or full_path.startswith("cron/"):
             # If it wasn't caught by a specific router above, it's a 404 API call
             from fastapi import HTTPException
             raise HTTPException(status_code=404, detail="API endpoint not found")
        
        # Otherwise, serve index.html
        return FileResponse("app/static/index.html")

@app.get("/api/health") # Changed from root to specific health endpoint
def health_check():
    return {"status": "ok"}
