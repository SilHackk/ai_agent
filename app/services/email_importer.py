from __future__ import annotations

import os
import re
import base64
from pathlib import Path
from typing import Any
from dotenv import load_dotenv
import requests
from app.services.token_store import get_graph_token

from app.services.project_db import (
    create_project,
    add_project_file,
    was_email_imported,
    mark_email_imported,
    get_or_create_client,
    update_client,
    add_interaction,
    update_project_ai,
)

load_dotenv(".env.local")
load_dotenv()

ATTACHMENT_DIR = Path("uploads/email_attachments")
ATTACHMENT_DIR.mkdir(parents=True, exist_ok=True)

ALLOWED_ATTACHMENT_EXTENSIONS = {
    ".pdf", ".png", ".jpg", ".jpeg", ".webp", ".xlsx", ".xls", ".csv"
}

GRAPH_BASE_URL = "https://graph.microsoft.com/v1.0"


def _get_access_token() -> str:
    return get_graph_token()


def _clean_html(html: str | None) -> str:
    if not html:
        return ""
    text = re.sub(r"<[^<]+?>", " ", html)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _clean_filename(filename: str) -> str:
    filename = filename.replace("/", "_").replace("\\", "_")
    filename = re.sub(r"[^\w\-. ()\[\]ąčęėįšųūžĄČĘĖĮŠŲŪŽ]", "_", filename)
    return filename[:180] or "attachment"


def _graph_get(url: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
    token = _get_access_token()
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
    }
    response = requests.get(url, headers=headers, params=params)
    if response.status_code >= 400:
        raise RuntimeError(
            f"Graph API klaida {response.status_code}: {response.text}"
        )
    return response.json()


def _extract_name_from_email(from_email: str, display_name: str = "") -> tuple[str, str]:
    """
    Bando išskirti vardą ir įmonę iš siuntėjo informacijos.
    Grąžina (name, company).
    """
    name = display_name.strip() if display_name else ""
    company = ""

    if not name and from_email:
        local = from_email.split("@")[0]
        name = local.replace(".", " ").replace("_", " ").title()

    domain = from_email.split("@")[-1] if "@" in from_email else ""
    if domain and domain not in {
        "gmail.com", "yahoo.com", "outlook.com",
        "hotmail.com", "mail.com", "inbox.lt"
    }:
        company = domain.split(".")[0].title()

    return name, company


def _ai_classify_email(subject: str, body: str) -> dict:
    """
    OpenAI klasifikuoja importuotą laišką.
    Naudoja gpt-4o-mini — greita ir pigi operacija.
    """
    try:
        from openai import OpenAI
        ai = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

        prompt = f"""Tu esi langų gamybos įmonės CRM asistentas.
Klasifikuok šią kliento užklausą.

Tema: {subject}
Tekstas: {body[:1200]}

Grąžink TIK JSON be markdown:
{{
  "classification": "kainos_uzklausas|technine_uzklausas|reklamacija|konsultacija|kita",
  "urgency": "high|medium|low",
  "reason": "trumpas paaiškinimas lietuviškai (max 1 sakinys)"
}}"""

        response = ai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=200
        )

        import json
        text = response.choices[0].message.content.strip()
        text = text.replace("```json", "").replace("```", "").strip()
        return json.loads(text)

    except Exception:
        return {
            "classification": "kita",
            "urgency": "medium",
            "reason": "Automatinis klasifikavimas nepavyko"
        }


def preview_emails(
    limit: int = 50,
    mailbox: str = "Inbox",
    query: str = "",
    only_with_attachments: bool = False,
) -> dict[str, Any]:
    user_email = os.getenv("OUTLOOK_USER_EMAIL")

    if not user_email:
        raise RuntimeError("Trūksta OUTLOOK_USER_EMAIL .env.local faile")

    url = f"{GRAPH_BASE_URL}/users/{user_email}/mailFolders/{mailbox}/messages"

    params = {
        "$top": min(limit, 100),
        "$orderby": "receivedDateTime desc",
        "$select": "id,subject,from,receivedDateTime,body,hasAttachments,internetMessageId",
    }

    data = _graph_get(url, params=params)

    previews = []
    skipped_imported = 0

    for msg in data.get("value", []):
        message_key = msg.get("internetMessageId") or msg.get("id")
        already_imported = was_email_imported(message_key)

        if already_imported:
            skipped_imported += 1

        has_attachments = msg.get("hasAttachments", False)

        if only_with_attachments and not has_attachments:
            continue

        body_html = msg.get("body", {}).get("content", "")
        body_text = _clean_html(body_html)

        sender_obj = msg.get("from", {}).get("emailAddress", {})
        sender_email = sender_obj.get("address", "")
        sender_name = sender_obj.get("name", "")

        previews.append({
            "uid": msg.get("id"),
            "message_key": message_key,
            "already_imported": already_imported,
            "from": sender_email,
            "from_name": sender_name,
            "subject": msg.get("subject", ""),
            "date": msg.get("receivedDateTime", ""),
            "snippet": body_text[:350],
            "has_attachments": has_attachments,
            "recommended": not already_imported,
        })

    return {
        "mailbox": mailbox,
        "query": query,
        "count": len(previews),
        "skipped_already_imported_in_scan": skipped_imported,
        "emails": previews,
    }


def _save_attachments(message_id: str, project_id: int) -> list[dict[str, Any]]:
    user_email = os.getenv("OUTLOOK_USER_EMAIL")

    url = f"{GRAPH_BASE_URL}/users/{user_email}/messages/{message_id}/attachments"
    data = _graph_get(url)

    saved_files = []

    for attachment in data.get("value", []):
        filename = attachment.get("name")
        content_bytes = attachment.get("contentBytes")

        if not filename or not content_bytes:
            continue

        clean = _clean_filename(filename)
        ext = Path(clean).suffix.lower()

        if ext not in ALLOWED_ATTACHMENT_EXTENSIONS:
            continue

        payload = base64.b64decode(content_bytes)

        project_dir = ATTACHMENT_DIR / str(project_id)
        project_dir.mkdir(parents=True, exist_ok=True)

        path = project_dir / clean

        if path.exists():
            stem, suffix = path.stem, path.suffix
            counter = 2
            while path.exists():
                path = project_dir / f"{stem}_{counter}{suffix}"
                counter += 1

        path.write_bytes(payload)

        file_id = add_project_file(
            project_id,
            clean,
            attachment.get("contentType", ""),
            str(path),
        )

        saved_files.append({
            "file_id": file_id,
            "filename": clean,
            "path": str(path),
            "content_type": attachment.get("contentType", ""),
        })

    return saved_files


def import_selected_emails(
    uids: list[str],
    mailbox: str = "Inbox",
) -> dict[str, Any]:
    user_email = os.getenv("OUTLOOK_USER_EMAIL")

    imported = 0
    skipped = 0
    projects = []

    for message_id in uids:
        url = f"{GRAPH_BASE_URL}/users/{user_email}/messages/{message_id}"

        params = {
            "$select": "id,subject,from,receivedDateTime,body,hasAttachments,internetMessageId",
        }

        msg = _graph_get(url, params=params)

        message_key = msg.get("internetMessageId") or msg.get("id")

        if was_email_imported(message_key):
            skipped += 1
            continue

        subject = msg.get("subject", "")

        sender_obj = msg.get("from", {}).get("emailAddress", {})
        from_email = sender_obj.get("address", "")
        display_name = sender_obj.get("name", "")

        body_html = msg.get("body", {}).get("content", "")
        body = _clean_html(body_html)

        # ── CRM: sukurti arba rasti klientą ──────────────────────────────────
        name, company = _extract_name_from_email(from_email, display_name)

        client_id = get_or_create_client(
            email=from_email,
            name=name,
            company=company,
        )

        # ── AI klasifikavimas ─────────────────────────────────────────────────
        ai_result = _ai_classify_email(subject, body)
        classification = ai_result.get("classification", "kita")
        urgency = ai_result.get("urgency", "medium")
        ai_reason = ai_result.get("reason", "")

        # ── Sukurti projektą su client_id ir AI rezultatais ───────────────────
        project_id = create_project(
            source="email",
            client_email=from_email,
            subject=subject,
            email_text=body,
            client_id=client_id,
            ai_classification=classification,
            ai_urgency=urgency,
        )

        # ── Išsaugoti AI klasifikavimo priežastį ──────────────────────────────
        update_project_ai(
            project_id=project_id,
            classification=classification,
            reason=ai_reason,
            urgency=urgency,
        )

        # ── Užfiksuoti kontaktą CRM ───────────────────────────────────────────
        add_interaction(
            client_id=client_id,
            project_id=project_id,
            type="email",
            direction="inbound",
            summary=f"{subject} | {body[:200]}",
            ai_sentiment=f"{classification} / {urgency}",
        )

        # ── Prisegti failai ───────────────────────────────────────────────────
        saved_files = []
        if msg.get("hasAttachments"):
            saved_files = _save_attachments(message_id, project_id)

        mark_email_imported(message_key, from_email, subject)

        imported += 1

        projects.append({
            "project_id": project_id,
            "client_id": client_id,
            "uid": message_id,
            "from": from_email,
            "from_name": name,
            "company": company,
            "subject": subject,
            "text": body[:500],
            "ai_classification": classification,
            "ai_urgency": urgency,
            "ai_reason": ai_reason,
            "files": saved_files,
        })

    return {
        "imported": imported,
        "skipped": skipped,
        "projects": projects,
    }


def import_recent_emails(
    limit: int = 100,
    mailbox: str = "Inbox",
    query: str = "",
    only_with_attachments: bool = False,
) -> dict[str, Any]:
    preview = preview_emails(
        limit=limit,
        mailbox=mailbox,
        query=query,
        only_with_attachments=only_with_attachments,
    )

    uids = [
        item["uid"]
        for item in preview["emails"]
        if item.get("recommended")
    ]

    result = import_selected_emails(uids, mailbox=mailbox)
    result["previewed"] = preview["count"]

    return result