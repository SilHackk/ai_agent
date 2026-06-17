"""
CRM router — app/routers/crm.py

Endpoints:
    GET  /crm/clients                  — klientų sąrašas su paieška
    GET  /crm/clients/{id}             — vieno kliento kortelė
    POST /crm/clients                  — sukurti klientą rankiniu būdu
    PUT  /crm/clients/{id}             — atnaujinti kliento duomenis
    GET  /crm/clients/{id}/projects    — kliento projektų istorija
    GET  /crm/clients/{id}/interactions — kliento kontaktų istorija
    POST /crm/clients/{id}/interactions — pridėti kontaktą rankiniu būdu
    POST /crm/clients/{id}/ai-segment  — AI perskaičiuoja kliento segmentą
    GET  /crm/projects                 — visi projektai su filtru
    POST /crm/projects/{id}/classify   — AI klasifikuoja projektą
    GET  /crm/stats                    — greita CRM suvestinė
"""

import os
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional
from openai import OpenAI

from app.services.project_db import (
    get_client, get_client_by_email, list_clients, update_client,
    get_or_create_client, update_client_ai_segment,
    get_client_projects, get_client_interactions, add_interaction,
    list_projects, get_project, update_project_ai, update_project_status,
    init_db, get_conn, now
)

router = APIRouter(prefix="/crm", tags=["crm"])

client_ai = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


# ── Pydantic schemas ──────────────────────────────────────────────────────────

class ClientCreate(BaseModel):
    email: str
    name: Optional[str] = None
    company: Optional[str] = None
    phone: Optional[str] = None
    city: Optional[str] = None
    notes: Optional[str] = None


class ClientUpdate(BaseModel):
    name: Optional[str] = None
    company: Optional[str] = None
    phone: Optional[str] = None
    city: Optional[str] = None
    notes: Optional[str] = None
    status: Optional[str] = None


class InteractionCreate(BaseModel):
    type: str
    summary: str = ""
    project_id: Optional[int] = None
    direction: str = "inbound"


class ProjectStatusUpdate(BaseModel):
    status: str


# ── Helpers ───────────────────────────────────────────────────────────────────

def _ai_classify_project(subject: str, email_text: str) -> dict:
    """OpenAI klasifikuoja užklausos tipą ir skubumą."""
    prompt = f"""Tu esi langų gamybos įmonės CRM asistentas.
Klasifikuok šią kliento užklausą.

Tema: {subject}
Tekstas: {email_text[:1500]}

Grąžink TIK JSON be markdown:
{{
  "classification": "kainos_uzklausas|technine_uzklausas|reklamacija|konsultacija|kita",
  "urgency": "high|medium|low",
  "reason": "trumpas paaiškinimas lietuviškai (max 1 sakinys)"
}}"""

    response = client_ai.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1,
        max_tokens=200
    )

    import json
    try:
        text = response.choices[0].message.content.strip()
        text = text.replace("```json", "").replace("```", "").strip()
        return json.loads(text)
    except Exception:
        return {"classification": "kita", "urgency": "medium", "reason": "Nepavyko klasifikuoti"}


def _ai_segment_client(client_id: int) -> dict:
    """OpenAI nustato kliento segmentą pagal projektų istoriją."""
    projects = get_client_projects(client_id)
    client = get_client(client_id)

    if not projects:
        return {"segment": "naujas", "reason": "Dar nėra projektų istorijos"}

    subjects = [p.get("subject", "") for p in projects[:10]]
    classifications = [p.get("ai_classification", "") for p in projects[:10] if p.get("ai_classification")]
    count = len(projects)

    prompt = f"""Tu esi langų gamybos įmonės CRM asistentas.
Klientas: {client.get('email')}
Projektų skaičius: {count}
Temų pavyzdžiai: {subjects}
Klasifikacijos: {classifications}

Nustatyk kliento segmentą. Grąžink TIK JSON be markdown:
{{
  "segment": "reguliarus|vienkartinis|naujas|neaktyvus",
  "reason": "trumpas paaiškinimas lietuviškai (max 1 sakinys)"
}}"""

    response = client_ai.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1,
        max_tokens=150
    )

    import json
    try:
        text = response.choices[0].message.content.strip()
        text = text.replace("```json", "").replace("```", "").strip()
        return json.loads(text)
    except Exception:
        return {"segment": "naujas", "reason": "Nepavyko nustatyti segmento"}


# ── Clients ───────────────────────────────────────────────────────────────────

@router.get("/clients")
def clients_list(
    search: str = Query("", description="Paieška pagal email, vardą, įmonę, miestą"),
    limit: int = Query(100, le=500)
):
    """Klientų sąrašas su paieška."""
    init_db()
    return {"clients": list_clients(limit=limit, search=search)}


@router.get("/clients/{client_id}")
def client_detail(client_id: int):
    """Vieno kliento kortelė."""
    init_db()
    c = get_client(client_id)
    if not c:
        raise HTTPException(status_code=404, detail="Klientas nerastas")
    projects = get_client_projects(client_id)
    interactions = get_client_interactions(client_id)
    return {
        "client": c,
        "projects_count": len(projects),
        "projects": projects[:10],
        "interactions_count": len(interactions),
        "interactions": interactions[:10]
    }


@router.post("/clients")
def client_create(payload: ClientCreate):
    """Sukurti klientą rankiniu būdu."""
    init_db()
    existing = get_client_by_email(payload.email)
    if existing:
        raise HTTPException(status_code=409, detail=f"Klientas su šiuo email jau egzistuoja (id={existing['id']})")
    client_id = get_or_create_client(
        email=payload.email,
        name=payload.name,
        company=payload.company,
        phone=payload.phone,
        city=payload.city
    )
    if payload.notes:
        update_client(client_id, notes=payload.notes)
    return {"status": "created", "client_id": client_id}


@router.put("/clients/{client_id}")
def client_update(client_id: int, payload: ClientUpdate):
    """Atnaujinti kliento duomenis."""
    init_db()
    if not get_client(client_id):
        raise HTTPException(status_code=404, detail="Klientas nerastas")
    update_client(client_id, **payload.model_dump(exclude_none=True))
    return {"status": "updated", "client_id": client_id}


@router.get("/clients/{client_id}/projects")
def client_projects(client_id: int):
    """Kliento projektų istorija."""
    init_db()
    if not get_client(client_id):
        raise HTTPException(status_code=404, detail="Klientas nerastas")
    return {"projects": get_client_projects(client_id)}


@router.get("/clients/{client_id}/interactions")
def client_interactions(client_id: int):
    """Kliento kontaktų istorija."""
    init_db()
    if not get_client(client_id):
        raise HTTPException(status_code=404, detail="Klientas nerastas")
    return {"interactions": get_client_interactions(client_id)}


@router.post("/clients/{client_id}/interactions")
def interaction_add(client_id: int, payload: InteractionCreate):
    """Pridėti kontaktą rankiniu būdu (pvz. skambutis, susitikimas)."""
    init_db()
    if not get_client(client_id):
        raise HTTPException(status_code=404, detail="Klientas nerastas")
    interaction_id = add_interaction(
        client_id=client_id,
        type=payload.type,
        summary=payload.summary,
        project_id=payload.project_id,
        direction=payload.direction
    )
    return {"status": "added", "interaction_id": interaction_id}


@router.post("/clients/{client_id}/ai-segment")
def client_ai_segment(client_id: int):
    """AI perskaičiuoja kliento segmentą pagal projektų istoriją."""
    init_db()
    if not get_client(client_id):
        raise HTTPException(status_code=404, detail="Klientas nerastas")
    result = _ai_segment_client(client_id)
    update_client_ai_segment(
        client_id=client_id,
        segment=result.get("segment", "naujas"),
        reason=result.get("reason", "")
    )
    return {
        "status": "updated",
        "client_id": client_id,
        "ai_segment": result.get("segment"),
        "reason": result.get("reason")
    }


# ── Projects ──────────────────────────────────────────────────────────────────

@router.get("/projects")
def projects_list(
    status: Optional[str] = Query(None, description="Filtras pagal statusą: new, in_progress, done"),
    classification: Optional[str] = Query(None, description="Filtras pagal AI klasifikaciją"),
    urgency: Optional[str] = Query(None, description="Filtras: high|medium|low"),
    limit: int = Query(50, le=200)
):
    """Visi projektai su filtrais."""
    init_db()
    all_projects = list_projects(limit=500)

    if status:
        all_projects = [p for p in all_projects if p.get("status") == status]
    if classification:
        all_projects = [p for p in all_projects if p.get("ai_classification") == classification]
    if urgency:
        all_projects = [p for p in all_projects if p.get("ai_urgency") == urgency]

    return {
        "count": len(all_projects[:limit]),
        "projects": all_projects[:limit]
    }


@router.post("/projects/{project_id}/classify")
def project_classify(project_id: int):
    """AI klasifikuoja projekto užklausą ir nustato skubumą."""
    init_db()
    project = get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Projektas nerastas")

    result = _ai_classify_project(
        subject=project.get("subject", ""),
        email_text=project.get("email_text", "")
    )

    update_project_ai(
        project_id=project_id,
        classification=result.get("classification", "kita"),
        reason=result.get("reason", ""),
        urgency=result.get("urgency", "medium")
    )

    # Jei yra klientas — pridedame interaction
    client_id = project.get("client_id")
    if client_id:
        add_interaction(
            client_id=client_id,
            project_id=project_id,
            type="ai_classification",
            summary=f"AI klasifikacija: {result.get('classification')} | {result.get('reason')}",
            direction="inbound"
        )

    return {
        "status": "classified",
        "project_id": project_id,
        "classification": result.get("classification"),
        "urgency": result.get("urgency"),
        "reason": result.get("reason")
    }


@router.put("/projects/{project_id}/status")
def project_status_update(project_id: int, payload: ProjectStatusUpdate):
    """Atnaujinti projekto statusą."""
    init_db()
    if not get_project(project_id):
        raise HTTPException(status_code=404, detail="Projektas nerastas")
    allowed = {"new", "in_progress", "waiting_info", "offer_sent", "done", "cancelled"}
    if payload.status not in allowed:
        raise HTTPException(status_code=400, detail=f"Leistini statusai: {allowed}")
    update_project_status(project_id, payload.status)
    return {"status": "updated", "project_id": project_id, "new_status": payload.status}


# ── Stats ─────────────────────────────────────────────────────────────────────

@router.get("/stats")
def crm_stats():
    """Greita CRM suvestinė darbuotojui."""
    init_db()
    with get_conn() as conn:
        total_clients = conn.execute("SELECT COUNT(*) FROM clients").fetchone()[0]
        total_projects = conn.execute("SELECT COUNT(*) FROM projects").fetchone()[0]
        new_projects = conn.execute("SELECT COUNT(*) FROM projects WHERE status='new'").fetchone()[0]
        high_urgency = conn.execute("SELECT COUNT(*) FROM projects WHERE ai_urgency='high'").fetchone()[0]

        segments = conn.execute(
            "SELECT ai_segment, COUNT(*) as cnt FROM clients WHERE ai_segment IS NOT NULL GROUP BY ai_segment"
        ).fetchall()

        classifications = conn.execute(
            "SELECT ai_classification, COUNT(*) as cnt FROM projects WHERE ai_classification IS NOT NULL GROUP BY ai_classification"
        ).fetchall()

    return {
        "total_clients": total_clients,
        "total_projects": total_projects,
        "new_projects": new_projects,
        "high_urgency_projects": high_urgency,
        "client_segments": {row[0]: row[1] for row in segments},
        "project_classifications": {row[0]: row[1] for row in classifications}
    }