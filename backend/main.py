
from contextlib import asynccontextmanager

from fastapi import FastAPI

from backend.db import Database
from backend.routers import repositories, search


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

app.include_router(repositories.router)
app.include_router(search.router)


@app.get("/")
def root():
    return {"message": "WhoKnows API is running"}
