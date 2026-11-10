
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.config import settings
from backend.db import Database
from backend.routers import auth, repositories, search


@asynccontextmanager
async def lifespan(app: FastAPI):
    db = Database()
    db.open()

    app.state.db = db

    yield

    db.close()


app = FastAPI(
    title="WhoKnows API",
    description="GitHub developer knowledge search engine",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url.rstrip("/")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(repositories.router)
app.include_router(search.router)


@app.get("/")
def root():
    return {"message": "WhoKnows API is running"}
