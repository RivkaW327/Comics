import sys
import os
sys.path.append(os.path.dirname(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "Services", "maverick_coref")))
from .config.config_loader import config
sys.path.append(os.path.abspath(config["services"]["textRank"]["path"]))


# main.py - עדכון הקובץ הראשי
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
# from .API.auth_router import router as auth_router
from .API.endpoints import router as auth_router
from .API.story_router import router as story_router

app = FastAPI(title="Story Management API", version="1.0.0")

#
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import API.endpoints
from .API.endpoints import router
from transformers import DebertaV2Model
#
def _patched_hidden_size(self):
    return self.config.hidden_size

DebertaV2Model.hidden_size = property(_patched_hidden_size)

from .Repositories.database import Database
from FastAPIProject.API.endpoints import router
#
#
#
@asynccontextmanager
async def lifespan(app: FastAPI):
    # הפעלת קוד בהתחלה
    await Database.connect_db()
    print("Connected to MongoDB!")
    yield
    # הפעלת קוד בסוף
    await Database.close_db()
    print("Disconnected from MongoDB!")
origins = [
    "0.0.0.0",
    "http://localhost:5173"
]
#
app = FastAPI(lifespan=lifespan)
#
# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=origins,  # רשימת דומיינים מורשים
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )
# # הוספת הראוטר
# app.include_router(router)
#
# # הוספת נקודת קצה שורש באפליקציה הראשית
# @app.get("/")
# async def root():
#     return {"message": "Welcome to FastAPI with MongoDB! The API is running."}
#
# # # הרצת האפליקציה
# # if __name__ == "__main__":
# #     uvicorn.run("FastAPIProject.__main__:app", host="0.0.0.0", port=8000, reload=True)
# # app = FastAPI()
# # # הוספת ה-router לקובץ ה-main
# # app.include_router(router)
#



# הגדרת CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # בפרודקשן צריך להגדיר דומיינים ספציפיים
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# הוספת הרוטרים
app.include_router(auth_router)
app.include_router(story_router)

@app.get("/")
async def root():
    return {"message": "Story Management API is running"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}