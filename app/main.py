from fastapi import FastAPI

from app import models  # noqa: F401  (imported so Base knows the tables)
from app.database import Base, engine
from app.routers import jobs

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Bulk Certificate Generator")
app.include_router(jobs.router)


@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/")
def root():
    return {"message": "Bulk Certificate Generator API. Docs at /docs"}