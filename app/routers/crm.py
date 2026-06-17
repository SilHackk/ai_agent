"""
CRM router — app/routers/crm.py
"""

import io
import json
import os
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, List
from openai import OpenAI

from app.services.project_db import (
    get_client, get_client_by_email, list_clients, update_client,
    get_or_create_client, update_client_ai_segment,
    get_client_projects, get_client_interactions, add_interaction,
    list_projects, get_project, update_project_ai, update_project_status,
    save_mbcad_table, get_mbcad_table,
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


class MBcadTableUpdate(BaseModel):
    table: List[dict]


# ── Helpers ───────────────────────────────────────────────────────────────────

def _ai_classify_project(subject: str, email_text: str) -> dict:
    prompt = f"""Tu esi langų gamybos įmonės CRM asistentas.
Klasifikuok šią kliento užklausą.

Tema: {subject}
tekstas: {email_text[:1500]}

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

    try:
        text = response.choices[0].message.content.strip()
        text = text.replace("```json", "").replace("```", "").strip()
        return json.loads(text)
    except Exception:
        return {"classification": "kita", "urgency": "medium", "reason": "Nepavyko klasifikuoti"}


def _ai_segment_client(client_id: int) -> dict:
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
    init_db()
    return {"clients": list_clients(limit=limit, search=search)}


@router.get("/clients/{client_id}")
def client_detail(client_id: int):
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
    init_db()
    if not get_client(client_id):
        raise HTTPException(status_code=404, detail="Klientas nerastas")
    update_client(client_id, **payload.model_dump(exclude_none=True))
    return {"status": "updated", "client_id": client_id}


@router.get("/clients/{client_id}/projects")
def client_projects(client_id: int):
    init_db()
    if not get_client(client_id):
        raise HTTPException(status_code=404, detail="Klientas nerastas")
    return {"projects": get_client_projects(client_id)}


@router.get("/clients/{client_id}/interactions")
def client_interactions(client_id: int):
    init_db()
    if not get_client(client_id):
        raise HTTPException(status_code=404, detail="Klientas nerastas")
    return {"interactions": get_client_interactions(client_id)}


@router.post("/clients/{client_id}/interactions")
def interaction_add(client_id: int, payload: InteractionCreate):
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
    status: Optional[str] = Query(None),
    classification: Optional[str] = Query(None),
    urgency: Optional[str] = Query(None),
    limit: int = Query(50, le=200)
):
    init_db()
    all_projects = list_projects(limit=500)
    if status:
        all_projects = [p for p in all_projects if p.get("status") == status]
    if classification:
        all_projects = [p for p in all_projects if p.get("ai_classification") == classification]
    if urgency:
        all_projects = [p for p in all_projects if p.get("ai_urgency") == urgency]
    return {"count": len(all_projects[:limit]), "projects": all_projects[:limit]}


@router.post("/projects/{project_id}/classify")
def project_classify(project_id: int):
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
    init_db()
    if not get_project(project_id):
        raise HTTPException(status_code=404, detail="Projektas nerastas")
    allowed = {"new", "in_progress", "waiting_info", "offer_sent", "done", "cancelled"}
    if payload.status not in allowed:
        raise HTTPException(status_code=400, detail=f"Leistini statusai: {allowed}")
    update_project_status(project_id, payload.status)
    return {"status": "updated", "project_id": project_id, "new_status": payload.status}


# ── MBcad lentelė ─────────────────────────────────────────────────────────────

@router.get("/projects/{project_id}/mbcad")
def project_mbcad_get(project_id: int):
    """Grąžina projekto MBcad lentelę."""
    init_db()
    if not get_project(project_id):
        raise HTTPException(status_code=404, detail="Projektas nerastas")
    table = get_mbcad_table(project_id)
    return {"project_id": project_id, "rows": len(table), "mbcad_table": table}


@router.put("/projects/{project_id}/mbcad")
def project_mbcad_update(project_id: int, payload: MBcadTableUpdate):
    """Atnaujina projekto MBcad lentelę (darbuotojas gali pataisyti rankiniu būdu)."""
    init_db()
    if not get_project(project_id):
        raise HTTPException(status_code=404, detail="Projektas nerastas")
    save_mbcad_table(project_id, payload.table)
    return {"status": "updated", "project_id": project_id, "rows": len(payload.table)}


@router.get("/projects/{project_id}/mbcad/export")
def project_mbcad_export(project_id: int):
    """Eksportuoja MBcad lentelę kaip Excel (.xlsx) failą."""
    init_db()
    if not get_project(project_id):
        raise HTTPException(status_code=404, detail="Projektas nerastas")
    table = get_mbcad_table(project_id)
    if not table:
        raise HTTPException(status_code=404, detail="MBcad lentelė tuščia arba dar neišanalizuota")

    try:
        import pandas as pd
        df = pd.DataFrame(table)

        column_labels = {
            "nr": "Nr.",
            "zymejimas": "Žymėjimas",
            "element_type": "Elemento tipas",
            "sistema": "Sistema",
            "profilio_variantas": "Profilio var.",
            "plotis_mm": "Plotis (mm)",
            "aukstis_mm": "Aukštis (mm)",
            "kiekis": "Kiekis",
            "spalva_isorine": "Spalva išorinė",
            "spalva_tipas": "Spalvos tipas",
            "spalva_pavirsius": "Paviršius",
            "spalva_vidine": "Spalva vidinė",
            "stiklo_paketas": "Stiklo paketas",
            "stiklo_storis_mm": "Stiklo storis",
            "stiklo_kodas": "Stiklo kodas",
            "stiklo_ug": "Ug",
            "stiklo_g": "g",
            "varstymas": "Varstymas",
            "kampų_jungtys": "Kampų jungtys",
            "montavimo_budas": "Montavimas",
            "slenkscio_juosta": "Slenksčio juosta",
            "stiklinimo_juosta": "Stiklinimo juosta",
            "tarpine_drenazas": "Tarpinė drenažas",
            "tarpine_rebet": "Tarpinė rebetas",
            "tarpine_centrinis": "Tarpinė centrinis",
            "tarpine_slenkscio": "Tarpinė slenksčio",
            "furnitura_rankena": "Rankena",
            "apsauga_rc": "RC klasė",
            "pastabos": "Pastabos",
        }
        df.rename(columns={k: v for k, v in column_labels.items() if k in df.columns}, inplace=True)

        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='MBcad')
            ws = writer.sheets['MBcad']
            for col in ws.columns:
                max_len = max(len(str(cell.value or '')) for cell in col)
                ws.column_dimensions[col[0].column_letter].width = min(max_len + 4, 40)
        output.seek(0)

        project = get_project(project_id)
        filename = f"mbcad_projektas_{project_id}.xlsx"

        return StreamingResponse(
            output,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'}
        )
    except ImportError:
        raise HTTPException(status_code=500, detail="openpyxl neįdiegtas. Paleisk: pip install openpyxl")


# ── Stats ─────────────────────────────────────────────────────────────────────

@router.get("/stats")
def crm_stats():
    init_db()
    with get_conn() as conn:
        total_clients = conn.execute("SELECT COUNT(*) FROM clients").fetchone()[0]
        total_projects = conn.execute("SELECT COUNT(*) FROM projects").fetchone()[0]
        new_projects = conn.execute("SELECT COUNT(*) FROM projects WHERE status='new'").fetchone()[0]
        high_urgency = conn.execute("SELECT COUNT(*) FROM projects WHERE ai_urgency='high'").fetchone()[0]
        with_mbcad = conn.execute("SELECT COUNT(*) FROM projects WHERE mbcad_table_json IS NOT NULL AND mbcad_table_json != '[]'").fetchone()[0]

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
        "projects_with_mbcad_table": with_mbcad,
        "client_segments": {row[0]: row[1] for row in segments},
        "project_classifications": {row[0]: row[1] for row in classifications}
    }
