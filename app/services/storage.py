import os
import json
import pandas as pd
from datetime import datetime

DATA_PATH = "data/analyses.csv"
FEEDBACK_PATH = "data/feedback.csv"

COLUMNS = [
    "timestamp",
    "source",
    "email_text",
    "pdf_text_preview",
    "ai_analysis",
    "human_reply",
    "human_notes",
    "quality_score"
]

FEEDBACK_COLUMNS = [
    "timestamp",
    "analysis_timestamp",
    "field",
    "ai_value",
    "is_correct",
    "comment",
    "corrected_value",
]


def save_analysis(
    email_text: str,
    pdf_text: str,
    ai_analysis: str,
    source: str = "fastapi",
    human_reply: str = "",
    human_notes: str = "",
    quality_score: str = ""
):
    os.makedirs("data", exist_ok=True)

    new_row = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "source": source,
        "email_text": email_text,
        "pdf_text_preview": pdf_text[:1000],
        "ai_analysis": ai_analysis,
        "human_reply": human_reply,
        "human_notes": human_notes,
        "quality_score": quality_score
    }

    if os.path.exists(DATA_PATH) and os.path.getsize(DATA_PATH) > 0:
        df = pd.read_csv(DATA_PATH)
        for col in COLUMNS:
            if col not in df.columns:
                df[col] = ""
        df = df[COLUMNS]
        df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
    else:
        df = pd.DataFrame([new_row], columns=COLUMNS)

    df.to_csv(DATA_PATH, index=False)


def save_feedback(
    analysis_timestamp: str,
    field: str,
    ai_value: str,
    is_correct: bool,
    comment: str = "",
    corrected_value: str = "",
):
    """
    Išsaugo darbuotojo feedback apie konkretų AI sugeneruotą lauką.
    Naudojama tobulinti prompt'us ateityje.
    """
    os.makedirs("data", exist_ok=True)

    new_row = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "analysis_timestamp": analysis_timestamp,
        "field": field,
        "ai_value": str(ai_value)[:500],
        "is_correct": is_correct,
        "comment": comment,
        "corrected_value": corrected_value,
    }

    if os.path.exists(FEEDBACK_PATH) and os.path.getsize(FEEDBACK_PATH) > 0:
        df = pd.read_csv(FEEDBACK_PATH)
        for col in FEEDBACK_COLUMNS:
            if col not in df.columns:
                df[col] = ""
        df = df[FEEDBACK_COLUMNS]
        df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
    else:
        df = pd.DataFrame([new_row], columns=FEEDBACK_COLUMNS)

    df.to_csv(FEEDBACK_PATH, index=False)


def load_feedback() -> pd.DataFrame:
    if os.path.exists(FEEDBACK_PATH) and os.path.getsize(FEEDBACK_PATH) > 0:
        return pd.read_csv(FEEDBACK_PATH)
    return pd.DataFrame(columns=FEEDBACK_COLUMNS)


def get_feedback_stats() -> dict:
    df = load_feedback()
    if df.empty:
        return {"total": 0, "correct": 0, "incorrect": 0, "accuracy_pct": 0}
    total = len(df)
    correct = int(df["is_correct"].sum())
    incorrect = total - correct
    return {
        "total": total,
        "correct": correct,
        "incorrect": incorrect,
        "accuracy_pct": round(correct / total * 100, 1) if total > 0 else 0,
    }


def load_feedback_for_prompt(max_items: int = 15) -> str:
    """
    Grąžina paskutinių klaidų santrauką kaip tekstą,
    kurį galima įterpti į AI prompt'ą prieš kiekvieną analizę.

    Naudojama ai_agent.py — AI automatiškai mokosi iš darbuotojų pataisymų.
    Įtraukiami tik is_correct == False įrašai su komentaru.
    """
    df = load_feedback()

    if df.empty:
        return ""

    # Pasiimame tik klaidas su komentarais
    errors = df[
        (df["is_correct"] == False) &
        (df["comment"].notna()) &
        (df["comment"].str.strip() != "")
    ].sort_values("timestamp", ascending=False).head(max_items)

    if errors.empty:
        return ""

    lines = ["Ankstesnių analizių pataisymai (darbuotojų feedback):"]

    for _, row in errors.iterrows():
        field = str(row.get("field", "")).replace("mbcad_row_", "Eilutė ")
        ai_val = str(row.get("ai_value", ""))
        comment = str(row.get("comment", ""))
        corrected = str(row.get("corrected_value", ""))

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