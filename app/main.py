#python -m uvicorn app.main:app --reload
from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse, HTMLResponse
from app.services.ms_graph_auth import _build_msal_app, build_auth_url
import os
from app.routers import analyze, automation, crm
from app.services.token_store import save_access_token

app = FastAPI(
    title="AI langų užklausų agentas",
    description="Sistema analizuoja kliento laišką ir PDF projektą langų įmonei.",
    version="1.0.0"
)
AUTH_FLOW = {}

app.include_router(analyze.router)
app.include_router(automation.router)
app.include_router(crm.router)

@app.get("/")
def root():
    return {"message": "AI langų užklausų agentas veikia"}

@app.get("/auth/login")
def auth_login():
    global AUTH_FLOW

    AUTH_FLOW = build_auth_url()

    return RedirectResponse(AUTH_FLOW["auth_uri"])


@app.get("/auth/callback")
def auth_callback(request: Request):
    app_msal = _build_msal_app()

    result = app_msal.acquire_token_by_auth_code_flow(
        AUTH_FLOW,
        dict(request.query_params),
    )

    if "access_token" not in result:
        return HTMLResponse(f"<h3>Login nepavyko</h3><pre>{result}</pre>")

    save_access_token(result["access_token"])

    return HTMLResponse("""
        <h2>Prisijungimas pavyko ✅</h2>
        <p>Dabar gali grįžti į Streamlit ir spausti email preview.</p>
    """)
