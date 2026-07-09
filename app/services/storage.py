import json
from datetime import datetime

from app.services.project_db import get_conn, init_db, now


def save_analysis(
    email_text: str,
    pdf_text: str,
    ai_analysis: str,
    source: str = "fastapi",
    human_reply: str = "",
    human_notes: str = "",
    quality_score: str = ""
):
    init_db()
    with get_conn() as conn:
        conn.execute(
            """INSERT INTO analyses
               (timestamp, source, email_text, pdf_text_preview, ai_analysis, human_reply, human_notes, quality_score)
               VALUES (?,?,?,?,?,?,?,?)""",
            (now(), source, email_text, pdf_text[:1000], ai_analysis, human_reply, human_notes, quality_score)
        )


def save_feedback(
    analysis_timestamp: str,
    field: str,
    ai_value: str,
    is_correct: bool,
    comment: str = "",
    corrected_value: str = "",
):
    init_db()
    with get_conn() as conn:
        conn.execute(
            """INSERT INTO feedback
               (timestamp, analysis_timestamp, field, ai_value, is_correct, comment, corrected_value)
               VALUES (?,?,?,?,?,?,?)""",
            (now(), analysis_timestamp, field, str(ai_value)[:500], 1 if is_correct else 0, comment, corrected_value)
        )


def load_feedback() -> list:
    init_db()
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM feedback ORDER BY timestamp DESC").fetchall()
    return [dict(r) for r in rows]


def get_feedback_stats() -> dict:
    init_db()
    with get_conn() as conn:
        total = conn.execute("SELECT COUNT(*) FROM feedback").fetchone()[0]
        correct = conn.execute("SELECT COUNT(*) FROM feedback WHERE is_correct=1").fetchone()[0]
    incorrect = total - correct
    return {
        "total": total,
        "correct": correct,
        "incorrect": incorrect,
        "accuracy_pct": round(correct / total * 100, 1) if total > 0 else 0,
    }


def load_feedback_for_prompt(max_items: int = 15) -> str:
    init_db()
    with get_conn() as conn:
        rows = conn.execute(
            """SELECT field, ai_value, comment, corrected_value FROM feedback
               WHERE is_correct=0 AND comment IS NOT NULL AND comment != ''
               ORDER BY timestamp DESC LIMIT ?""",
            (max_items,)
        ).fetchall()

    if not rows:
        return ""

    lines = ["Ankstesnių analizių pataisymai (darbuotojų feedback):"]
    for row in rows:
        field = str(row["field"] or "").replace("mbcad_row_", "Eilutė ")
        ai_val = str(row["ai_value"] or "")
        comment = str(row["comment"] or "")
        corrected = str(row["corrected_value"] or "")

        line = f"- {field}: AI nurodė [{ai_val}]"
        if corrected and corrected != comment:
            line += f" → teisingai turėtų būti [{corrected}]"
        if comment:
            line += f". Pastaba: {comment}"
        lines.append(line)

    lines.append(
        "\nRemkis šiais pataisymais analizuodamas naują užklausą. "
        "Jei matai panašias sąlygas — taikyk išmoktas taisykles."
    )
    return "\n".join(lines)
