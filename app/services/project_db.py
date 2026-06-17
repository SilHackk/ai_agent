import json
import sqlite3
from pathlib import Path
from datetime import datetime
from typing import Any

DB_PATH = Path('data/ai_agent.db')
DB_PATH.parent.mkdir(exist_ok=True)


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_conn() as conn:
        conn.execute('''
        CREATE TABLE IF NOT EXISTS clients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            name TEXT,
            company TEXT,
            phone TEXT,
            city TEXT,
            language TEXT DEFAULT 'lt',
            ai_segment TEXT,
            ai_segment_reason TEXT,
            ai_segment_updated_at TEXT,
            notes TEXT,
            status TEXT DEFAULT 'active',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        ''')
        conn.execute('''
        CREATE TABLE IF NOT EXISTS projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_id INTEGER,
            source TEXT DEFAULT 'manual',
            client_email TEXT,
            subject TEXT,
            email_text TEXT,
            status TEXT DEFAULT 'new',
            ai_classification TEXT,
            ai_classification_reason TEXT,
            ai_urgency TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY(client_id) REFERENCES clients(id)
        )
        ''')
        conn.execute('''
        CREATE TABLE IF NOT EXISTS project_files (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL,
            filename TEXT NOT NULL,
            content_type TEXT,
            saved_path TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY(project_id) REFERENCES projects(id)
        )
        ''')
        conn.execute('''
        CREATE TABLE IF NOT EXISTS window_objects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL,
            file_id INTEGER,
            object_type TEXT,
            shape TEXT,
            width_px REAL,
            height_px REAL,
            bbox_json TEXT,
            opening_type TEXT,
            color_zone TEXT,
            profile TEXT,
            confidence REAL,
            source TEXT,
            needs_review INTEGER DEFAULT 1,
            created_at TEXT NOT NULL,
            FOREIGN KEY(project_id) REFERENCES projects(id),
            FOREIGN KEY(file_id) REFERENCES project_files(id)
        )
        ''')
        conn.execute('''
        CREATE TABLE IF NOT EXISTS email_import_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email_uid TEXT UNIQUE,
            from_email TEXT,
            subject TEXT,
            imported_at TEXT NOT NULL
        )
        ''')
        conn.execute('''
        CREATE TABLE IF NOT EXISTS crm_interactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_id INTEGER NOT NULL,
            project_id INTEGER,
            type TEXT NOT NULL,
            direction TEXT DEFAULT 'inbound',
            summary TEXT,
            ai_sentiment TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY(client_id) REFERENCES clients(id),
            FOREIGN KEY(project_id) REFERENCES projects(id)
        )
        ''')

        # Migracijos: prideda stulpelius, jei jų dar nėra (seniems DB)
        _run_migrations(conn)


def _run_migrations(conn):
    existing = {
        row[1]
        for row in conn.execute("PRAGMA table_info(projects)").fetchall()
    }
    for col, definition in [
        ("client_id", "INTEGER"),
        ("ai_classification", "TEXT"),
        ("ai_classification_reason", "TEXT"),
        ("ai_urgency", "TEXT"),
    ]:
        if col not in existing:
            conn.execute(f"ALTER TABLE projects ADD COLUMN {col} {definition}")


def migrate_orphan_projects() -> int:
    """
    Seni projektai su client_email bet be client_id automatiškai
    susiejami su klientu (arba sukuriamas naujas).
    Grąžina pataisytų projektų skaičių.
    """
    init_db()
    fixed = 0
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT id, client_email FROM projects WHERE client_id IS NULL AND client_email IS NOT NULL AND client_email != ''"
        ).fetchall()
        for row in rows:
            project_id = row["id"]
            email = row["client_email"]
            client_row = conn.execute("SELECT id FROM clients WHERE email=?", (email,)).fetchone()
            if client_row:
                client_id = client_row["id"]
            else:
                cur = conn.execute(
                    "INSERT INTO clients(email, created_at, updated_at) VALUES (?,?,?)",
                    (email, now(), now())
                )
                client_id = cur.lastrowid
            conn.execute("UPDATE projects SET client_id=? WHERE id=?", (client_id, project_id))
            fixed += 1
    return fixed


def export_clients_df():
    """Grąžina visų klientų DataFrame eksportui."""
    import pandas as pd
    init_db()
    with get_conn() as conn:
        rows = conn.execute("""
            SELECT
                c.id, c.email, c.name, c.company, c.phone, c.city,
                c.ai_segment, c.status, c.notes, c.created_at,
                COUNT(DISTINCT p.id) as projects_count,
                MAX(p.created_at) as last_project_at
            FROM clients c
            LEFT JOIN projects p ON p.client_id = c.id
            GROUP BY c.id
            ORDER BY c.id DESC
        """).fetchall()
    return pd.DataFrame([dict(r) for r in rows])


def export_projects_df():
    """Grąžina visų projektų DataFrame eksportui."""
    import pandas as pd
    init_db()
    with get_conn() as conn:
        rows = conn.execute("""
            SELECT
                p.id, p.subject, p.client_email,
                c.name as client_name, c.company,
                p.ai_classification, p.ai_urgency, p.ai_classification_reason,
                p.status, p.source, p.created_at
            FROM projects p
            LEFT JOIN clients c ON c.id = p.client_id
            ORDER BY p.id DESC
        """).fetchall()
    return pd.DataFrame([dict(r) for r in rows])


def now() -> str:
    return datetime.utcnow().isoformat(timespec='seconds')


# ── CLIENTS ──────────────────────────────────────────────────────────────────

def get_or_create_client(email: str, name: str = None, company: str = None, phone: str = None, city: str = None) -> int:
    """Grąžina esamo kliento id arba sukuria naują pagal email."""
    init_db()
    with get_conn() as conn:
        row = conn.execute('SELECT id FROM clients WHERE email=?', (email,)).fetchone()
        if row:
            if name or company or phone or city:
                conn.execute(
                    '''UPDATE clients SET
                        name=COALESCE(NULLIF(?,\'\'), name),
                        company=COALESCE(NULLIF(?,\'\'), company),
                        phone=COALESCE(NULLIF(?,\'\'), phone),
                        city=COALESCE(NULLIF(?,\'\'), city),
                        updated_at=?
                       WHERE id=?''',
                    (name, company, phone, city, now(), row['id'])
                )
            return int(row['id'])
        cur = conn.execute(
            'INSERT INTO clients(email, name, company, phone, city, created_at, updated_at) VALUES (?,?,?,?,?,?,?)',
            (email, name, company, phone, city, now(), now())
        )
        return int(cur.lastrowid)


def update_client_ai_segment(client_id: int, segment: str, reason: str = ''):
    init_db()
    with get_conn() as conn:
        conn.execute(
            'UPDATE clients SET ai_segment=?, ai_segment_reason=?, ai_segment_updated_at=?, updated_at=? WHERE id=?',
            (segment, reason, now(), now(), client_id)
        )


def get_client(client_id: int) -> dict | None:
    init_db()
    with get_conn() as conn:
        row = conn.execute('SELECT * FROM clients WHERE id=?', (client_id,)).fetchone()
        return dict(row) if row else None


def get_client_by_email(email: str) -> dict | None:
    init_db()
    with get_conn() as conn:
        row = conn.execute('SELECT * FROM clients WHERE email=?', (email,)).fetchone()
        return dict(row) if row else None


def list_clients(limit: int = 100, search: str = '') -> list[dict]:
    init_db()
    with get_conn() as conn:
        if search:
            pattern = f'%{search}%'
            rows = conn.execute(
                '''SELECT * FROM clients
                   WHERE email LIKE ? OR name LIKE ? OR company LIKE ? OR city LIKE ?
                   ORDER BY id DESC LIMIT ?''',
                (pattern, pattern, pattern, pattern, limit)
            ).fetchall()
        else:
            rows = conn.execute('SELECT * FROM clients ORDER BY id DESC LIMIT ?', (limit,)).fetchall()
        return [dict(r) for r in rows]


def update_client(client_id: int, **fields) -> None:
    init_db()
    allowed = {'name', 'company', 'phone', 'city', 'notes', 'status', 'language'}
    updates = {k: v for k, v in fields.items() if k in allowed}
    if not updates:
        return
    updates['updated_at'] = now()
    set_clause = ', '.join(f'{k}=?' for k in updates)
    values = list(updates.values()) + [client_id]
    with get_conn() as conn:
        conn.execute(f'UPDATE clients SET {set_clause} WHERE id=?', values)


def get_client_projects(client_id: int) -> list[dict]:
    init_db()
    with get_conn() as conn:
        rows = conn.execute(
            'SELECT * FROM projects WHERE client_id=? ORDER BY id DESC',
            (client_id,)
        ).fetchall()
        return [dict(r) for r in rows]


# ── INTERACTIONS ──────────────────────────────────────────────────────────────

def add_interaction(client_id: int, type: str, summary: str = '', project_id: int = None,
                    direction: str = 'inbound', ai_sentiment: str = '') -> int:
    init_db()
    with get_conn() as conn:
        cur = conn.execute(
            '''INSERT INTO crm_interactions(client_id, project_id, type, direction, summary, ai_sentiment, created_at)
               VALUES (?,?,?,?,?,?,?)''',
            (client_id, project_id, type, direction, summary, ai_sentiment, now())
        )
        return int(cur.lastrowid)


def get_client_interactions(client_id: int) -> list[dict]:
    init_db()
    with get_conn() as conn:
        rows = conn.execute(
            'SELECT * FROM crm_interactions WHERE client_id=? ORDER BY id DESC',
            (client_id,)
        ).fetchall()
        return [dict(r) for r in rows]


# ── PROJECTS ──────────────────────────────────────────────────────────────────

def create_project(source='manual', client_email=None, subject=None, email_text='',
                   client_id: int = None, ai_classification: str = None,
                   ai_urgency: str = None) -> int:
    init_db()
    if client_email and not client_id:
        client_id = get_or_create_client(client_email)
    with get_conn() as conn:
        cur = conn.execute(
            '''INSERT INTO projects(client_id, source, client_email, subject, email_text,
               ai_classification, ai_urgency, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
            (client_id, source, client_email, subject, email_text,
             ai_classification, ai_urgency, now())
        )
        return int(cur.lastrowid)


def update_project_ai(project_id: int, classification: str, reason: str = '', urgency: str = ''):
    init_db()
    with get_conn() as conn:
        conn.execute(
            '''UPDATE projects SET ai_classification=?, ai_classification_reason=?, ai_urgency=?
               WHERE id=?''',
            (classification, reason, urgency, project_id)
        )


def add_project_file(project_id: int, filename: str, content_type: str, saved_path: str) -> int:
    init_db()
    with get_conn() as conn:
        cur = conn.execute(
            'INSERT INTO project_files(project_id, filename, content_type, saved_path, created_at) VALUES (?, ?, ?, ?, ?)',
            (project_id, filename, content_type, saved_path, now())
        )
        return int(cur.lastrowid)


def add_window_object(project_id: int, file_id: int | None, obj: dict[str, Any]) -> int:
    init_db()
    with get_conn() as conn:
        cur = conn.execute('''
            INSERT INTO window_objects(
                project_id, file_id, object_type, shape, width_px, height_px, bbox_json,
                opening_type, color_zone, profile, confidence, source, needs_review, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            project_id, file_id,
            obj.get('object_type'), obj.get('shape'),
            obj.get('width_px'), obj.get('height_px'),
            json.dumps(obj.get('bbox'), ensure_ascii=False),
            obj.get('opening_type'), obj.get('color_zone'),
            obj.get('profile'), obj.get('confidence'),
            obj.get('source'),
            1 if obj.get('needs_review', True) else 0,
            now(),
        ))
        return int(cur.lastrowid)


def list_projects(limit: int = 50) -> list[dict[str, Any]]:
    init_db()
    with get_conn() as conn:
        rows = conn.execute('SELECT * FROM projects ORDER BY id DESC LIMIT ?', (limit,)).fetchall()
        return [dict(r) for r in rows]


def get_project_objects(project_id: int) -> list[dict[str, Any]]:
    init_db()
    with get_conn() as conn:
        rows = conn.execute('SELECT * FROM window_objects WHERE project_id=? ORDER BY id', (project_id,)).fetchall()
    out = []
    for r in rows:
        d = dict(r)
        try:
            d['bbox'] = json.loads(d.get('bbox_json') or 'null')
        except Exception:
            d['bbox'] = None
        out.append(d)
    return out


def was_email_imported(uid: str) -> bool:
    init_db()
    with get_conn() as conn:
        row = conn.execute('SELECT id FROM email_import_log WHERE email_uid=?', (uid,)).fetchone()
        return row is not None


def mark_email_imported(uid: str, from_email: str, subject: str):
    init_db()
    with get_conn() as conn:
        conn.execute(
            'INSERT OR IGNORE INTO email_import_log(email_uid, from_email, subject, imported_at) VALUES (?, ?, ?, ?)',
            (uid, from_email, subject, now())
        )


def get_project_files(project_id: int) -> list[dict[str, Any]]:
    init_db()
    with get_conn() as conn:
        rows = conn.execute('SELECT * FROM project_files WHERE project_id=? ORDER BY id', (project_id,)).fetchall()
        return [dict(r) for r in rows]


def update_project_status(project_id: int, status: str) -> None:
    init_db()
    with get_conn() as conn:
        conn.execute('UPDATE projects SET status=? WHERE id=?', (status, project_id))


def get_project(project_id: int) -> dict[str, Any] | None:
    init_db()
    with get_conn() as conn:
        row = conn.execute('SELECT * FROM projects WHERE id=?', (project_id,)).fetchone()
        return dict(row) if row else None