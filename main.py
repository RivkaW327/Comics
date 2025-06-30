import sys
import os
import threading
import winsound
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from transformers import DebertaV2Model

# Add project paths to Python path
sys.path.append(os.path.dirname(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "Services", "maverick_coref")))

# Import configuration
from .config.config_loader import config

# Add TextRank service path
sys.path.append(os.path.abspath(config["services"]["textRank"]["path"]))

# Import routers and database
from .API.endpoints import router as auth_router
from .API.story_router import router as story_router
from .Repositories.database import Database


# Patch for DebertaV2Model - fix hidden_size property
def _patched_hidden_size(self):
    """Patch to fix DebertaV2Model hidden_size property"""
    return self.config.hidden_size


DebertaV2Model.hidden_size = property(_patched_hidden_size)


def play_startup_sound():
    """Play startup sound using Windows winsound"""
    try:
        # ביפ כפול לסימון עליית השרת
        winsound.Beep(800, 300)  # Frequency 800Hz for 300ms
        winsound.Beep(1000, 500)  # Frequency 1000Hz for 500ms
    except Exception as e:
        print(f"Failed to play startup sound: {str(e)}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager - handles startup and shutdown events"""
    # Startup: Connect to database
    await Database.connect_db()
    print("Connected to MongoDB!")

    # Play startup sound in a separate thread to avoid blocking the server startup
    threading.Thread(target=play_startup_sound, daemon=True).start()

    yield

    # Shutdown: Close database connection
    await Database.close_db()
    print("Disconnected from MongoDB!")


# Initialize FastAPI application
app = FastAPI(
    title="Story Management API",
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS middleware
origins = config["server"]["origins"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,  # List of allowed domains - use specific domains in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth_router)
app.include_router(story_router)


@app.get("/")
async def root():
    """Root endpoint - API welcome message"""
    return {"message": "Story Management API is running"}


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}

# Run application (uncomment for direct execution)
# if __name__ == "__main__":
#     uvicorn.run("FastAPIProject.__main__:app", host="0.0.0.0", port=8000, reload=True)