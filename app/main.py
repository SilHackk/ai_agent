#python -m uvicorn app.main:app --reload
from fastapi import FastAPI
from app.routers import analyze

app = FastAPI(
    title="AI langų užklausų agentas",
    description="Sistema analizuoja kliento laišką ir PDF projektą langų įmonei.",
    version="1.0.0"
)

app.include_router(analyze.router)


@app.get("/")
def root():
    return {"message": "AI langų užklausų agentas veikia"}