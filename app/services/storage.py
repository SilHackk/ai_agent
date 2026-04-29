import os
import pandas as pd
from datetime import datetime

DATA_PATH = "data/analyses.csv"

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