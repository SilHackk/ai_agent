from __future__ import annotations

import os
import re
import imaplib
import email
from email.header import decode_header
from pathlib import Path
from typing import Any
from dotenv import load_dotenv

from app.services.project_db import create_project, add_project_file, was_email_imported, mark_email_imported

load_dotenv('.env.local')
load_dotenv()

ATTACHMENT_DIR = Path('uploads/email_attachments')
ATTACHMENT_DIR.mkdir(parents=True, exist_ok=True)

ALLOWED_ATTACHMENT_EXTENSIONS = {
    '.pdf', '.png', '.jpg', '.jpeg', '.webp', '.xlsx', '.xls', '.csv'
}


def _decode(value: str | None) -> str:
    if not value:
        return ''
    parts = decode_header(value)
    out = ''
    for text, enc in parts:
        if isinstance(text, bytes):
            out += text.decode(enc or 'utf-8', errors='ignore')
        else:
            out += text
    return out.strip()


def _clean_filename(filename: str) -> str:
    filename = _decode(filename)
    filename = filename.replace('/', '_').replace('\\', '_')
    filename = re.sub(r'[^\w\-. ()\[\]ąčęėįšųūžĄČĘĖĮŠŲŪŽ]', '_', filename)
    return filename[:180] or 'attachment'


def _connect() -> imaplib.IMAP4_SSL:
    host = os.getenv('EMAIL_IMAP_HOST')
    port = int(os.getenv('EMAIL_IMAP_PORT', '993'))
    address = os.getenv('EMAIL_ADDRESS')
    password = os.getenv('EMAIL_APP_PASSWORD')
    if not all([host, address, password]):
        raise RuntimeError('Trūksta EMAIL_IMAP_HOST, EMAIL_ADDRESS arba EMAIL_APP_PASSWORD .env/.env.local faile')
    imap = imaplib.IMAP4_SSL(host, port)
    imap.login(address, password)
    return imap


def _body_from_message(msg: email.message.Message, max_chars: int | None = None) -> str:
    chunks: list[str] = []
    html_fallback: list[str] = []
    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            disposition = str(part.get('Content-Disposition') or '')
            if 'attachment' in disposition:
                continue
            payload = part.get_payload(decode=True)
            if not payload:
                continue
            text = payload.decode(part.get_content_charset() or 'utf-8', errors='ignore')
            if content_type == 'text/plain':
                chunks.append(text)
            elif content_type == 'text/html':
                html_fallback.append(re.sub('<[^<]+?>', ' ', text))
    else:
        payload = msg.get_payload(decode=True)
        if payload:
            chunks.append(payload.decode(msg.get_content_charset() or 'utf-8', errors='ignore'))
    body = '\n'.join(chunks or html_fallback).strip()
    body = re.sub(r'\n{3,}', '\n\n', body)
    if max_chars and len(body) > max_chars:
        return body[:max_chars] + '...'
    return body


def _attachment_info(msg: email.message.Message) -> list[dict[str, Any]]:
    files: list[dict[str, Any]] = []
    for part in msg.walk():
        filename = part.get_filename()
        if not filename:
            continue
        clean = _clean_filename(filename)
        ext = Path(clean).suffix.lower()
        payload = part.get_payload(decode=True)
        size = len(payload or b'')
        files.append({
            'filename': clean,
            'content_type': part.get_content_type(),
            'size_bytes': size,
            'allowed': ext in ALLOWED_ATTACHMENT_EXTENSIONS,
        })
    return files


def _fetch_message_by_uid(imap: imaplib.IMAP4_SSL, uid: str) -> email.message.Message | None:
    status, raw_data = imap.uid('FETCH', uid, '(RFC822)')
    if status != 'OK' or not raw_data or not raw_data[0]:
        return None
    raw_bytes = raw_data[0][1]
    if not isinstance(raw_bytes, (bytes, bytearray)):
        return None
    return email.message_from_bytes(raw_bytes)


def preview_emails(limit: int = 50, mailbox: str = 'INBOX', query: str = 'ALL', only_with_attachments: bool = True) -> dict[str, Any]:
    """Parodo laiškų sąrašą be importavimo.
    Website/Swagger pusėje gali pažymėti norimus uid ir tik tada importuoti.
    """
    previews: list[dict[str, Any]] = []
    skipped_imported = 0

    with _connect() as imap:
        imap.select(mailbox)
        status, data = imap.uid('SEARCH', None, query)
        if status != 'OK':
            raise RuntimeError(f'IMAP search klaida: {status}')
        uids = data[0].split()[-limit:]
        for uid_b in reversed(uids):
            uid = uid_b.decode()
            msg = _fetch_message_by_uid(imap, uid)
            if msg is None:
                continue
            message_key = msg.get('Message-ID') or uid
            already_imported = was_email_imported(message_key)
            if already_imported:
                skipped_imported += 1
            attachments = _attachment_info(msg)
            if only_with_attachments and not attachments:
                continue
            previews.append({
                'uid': uid,
                'message_key': message_key,
                'already_imported': already_imported,
                'from': _decode(msg.get('From')),
                'subject': _decode(msg.get('Subject')),
                'date': _decode(msg.get('Date')),
                'snippet': _body_from_message(msg, max_chars=350),
                'attachments': attachments,
                'recommended': bool(attachments) and not already_imported,
            })

    return {
        'mailbox': mailbox,
        'query': query,
        'count': len(previews),
        'skipped_already_imported_in_scan': skipped_imported,
        'emails': previews,
    }


def _save_attachments(msg: email.message.Message, project_id: int) -> list[dict[str, Any]]:
    saved_files: list[dict[str, Any]] = []
    for part in msg.walk():
        filename = part.get_filename()
        if not filename:
            continue
        clean = _clean_filename(filename)
        ext = Path(clean).suffix.lower()
        if ext not in ALLOWED_ATTACHMENT_EXTENSIONS:
            continue
        payload = part.get_payload(decode=True)
        if not payload:
            continue
        project_dir = ATTACHMENT_DIR / str(project_id)
        project_dir.mkdir(parents=True, exist_ok=True)
        path = project_dir / clean
        # Kad neperrašytų kelių vienodų attachmentų.
        if path.exists():
            stem, suffix = path.stem, path.suffix
            counter = 2
            while path.exists():
                path = project_dir / f'{stem}_{counter}{suffix}'
                counter += 1
        path.write_bytes(payload)
        file_id = add_project_file(project_id, clean, part.get_content_type(), str(path))
        saved_files.append({'file_id': file_id, 'filename': clean, 'path': str(path), 'content_type': part.get_content_type()})
    return saved_files


def import_selected_emails(uids: list[str], mailbox: str = 'INBOX') -> dict[str, Any]:
    """Importuoja tik vartotojo pasirinktus laiškus pagal UID iš preview_emails rezultato."""
    imported = 0
    skipped = 0
    projects: list[dict[str, Any]] = []

    with _connect() as imap:
        imap.select(mailbox)
        for uid in uids:
            msg = _fetch_message_by_uid(imap, str(uid))
            if msg is None:
                skipped += 1
                continue
            message_key = msg.get('Message-ID') or str(uid)
            if was_email_imported(message_key):
                skipped += 1
                continue
            subject = _decode(msg.get('Subject'))
            from_email = _decode(msg.get('From'))
            body = _body_from_message(msg)
            project_id = create_project(source='email', client_email=from_email, subject=subject, email_text=body)
            saved_files = _save_attachments(msg, project_id)
            mark_email_imported(message_key, from_email, subject)
            imported += 1
            projects.append({
                'project_id': project_id,
                'uid': uid,
                'from': from_email,
                'subject': subject,
                'files': saved_files,
            })

    return {'imported': imported, 'skipped': skipped, 'projects': projects}


def import_recent_emails(limit: int = 100, mailbox: str = 'INBOX', query: str = 'ALL', only_with_attachments: bool = True) -> dict[str, Any]:
    """Senas patogus režimas: automatiškai importuoja naujausius rekomenduojamus laiškus."""
    preview = preview_emails(limit=limit, mailbox=mailbox, query=query, only_with_attachments=only_with_attachments)
    uids = [item['uid'] for item in preview['emails'] if item.get('recommended')]
    result = import_selected_emails(uids, mailbox=mailbox)
    result['previewed'] = preview['count']
    return result
