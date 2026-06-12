from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

import models
from database import engine
from app.routers.reviews import router as reviews_router

load_dotenv()
models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="AI Code Reviewer API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(reviews_router)

@app.get("/api/health")
async def health():
    return {"status": "ok"}