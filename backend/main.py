import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from database import create_tables
from routes import router
@asynccontextmanager
async def lifespan(app: FastAPI):
    create_tables()
    yield



app = FastAPI(
    title = "YouTube Thumbnail Generator API",
    lifespan=lifespan

)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:5174", "http://localhost:5175", "http://127.0.0.1:5173", "http://127.0.0.1:5174"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(router)