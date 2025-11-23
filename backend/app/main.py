from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from .database import db
from .routers import recipes, history, profiles, settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle startup and shutdown events"""
    # Startup
    await db.init_db()
    print("🌶️  Elzar backend started! BAM!")
    print(f"📊 Database initialized at: {db.db_path}")
    yield
    # Shutdown
    print("👋 Elzar backend shutting down...")


app = FastAPI(
    title="Elzar - Grocy Recipe Generator",
    description="BAM! Generate amazing recipes from your Grocy inventory! 🌶️",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(recipes.router)
app.include_router(history.router)
app.include_router(profiles.router)
app.include_router(settings.router)


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "name": "Elzar - Grocy Recipe Generator",
        "version": "1.0.0",
        "message": "BAM! Welcome to Elzar! 🌶️",
        "docs": "/docs"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "message": "BAM! Everything's cooking! 🌶️"}


if __name__ == "__main__":
    import uvicorn
    from .config import settings
    
    uvicorn.run(
        "app.main:app",
        host=settings.backend_host,
        port=settings.backend_port,
        reload=True
    )

