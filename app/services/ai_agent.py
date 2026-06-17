import os
from openai import OpenAI

from app.core.config import OPENAI_API_KEY
from app.services.text_processing import preprocess_text, tokenize, remove_stopwords
from app.services.pdf_table_extractor import extract_window_tables_from_text
from app.services.sentiment_service import analyze_sentiment
from app.services.storage import load_feedback_for_prompt

client = OpenAI(api_key=OPENAI_API_KEY)


def load_prompt() -> str:
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    prompt_path = os.path.join(base_dir, "prompts", "email_analysis_prompt.txt")
    with open(prompt_path, "r", encoding="utf-8") as file:
        return file.read()


def analyze_request(
    email_text: str,
    pdf_text: str = "",
    pdf_images: list[dict] | None = None,
    classic_features: dict | None = None
) -> str:

    sentiment = analyze_sentiment(email_text)
    full_text = email_text + " " + pdf_text
    pdf_window_tables = extract_window_tables_from_text(pdf_text)

    if classic_features is None:
        clean_text = preprocess_text(full_text)
        words, sentences = tokenize(clean_text)
        filtered_words = remove_stopwords(words)
        classic_features = {
            "clean_text_preview": clean_text[:1000],
            "word_count": len(words),
            "sentence_count": len(sentences),
            "filtered_keywords": filtered_words[:50],
            "pdf_window_tables": pdf_window_tables,
            "sentiment_analysis": sentiment
        }
    else:
        classic_features["pdf_window_tables"] = pdf_window_tables
        classic_features["sentiment_analysis"] = sentiment

    base_prompt = load_prompt()

    # ── Feedback loop: darbuotojų pataisymai automatiškai į prompt'ą ──────────
    feedback_context = load_feedback_for_prompt(max_items=15)

    feedback_section = ""
    if feedback_context:
        feedback_section = f"""
---
SVARBU — ANKSTESNIŲ ANALIZIŲ PATAISYMAI:
{feedback_context}

Prieš generuodamas MBcad suvestinę — peržiūrėk šiuos pataisymus.
Jei dabartinė situacija panaši į aprašytą klaidą — taikyk išmoktą taisyklę.
---
"""

    content = [
        {
            "type": "input_text",
            "text": f"""
{base_prompt}
{feedback_section}

Klasikiniais NLP metodais ištraukti faktai:
{classic_features}

Naudok šiuos faktus kaip pagalbinį pagrindą. Jeigu LLM analizė nesutampa su klasikiniais faktais, pažymėk neaiškumą, bet neišsigalvok.

Kliento laiškas:
{email_text}

PDF tekstinis sluoksnis:
{pdf_text}

Labai svarbu:
Jeigu PDF puslapiuose matosi brėžiniai, fasadai, langų žiniaraščiai, lentelės ar gaminių schemos, analizuok ir vaizdus.
Iš vaizdų ištrauk langų žymėjimus, matmenis, kiekius, spalvą, stiklo / šiluminius reikalavimus ir paruošk MBcad suvestinę.
Jeigu informacijos nematai aiškiai, rašyk „neaiškiai matoma", bet neišsigalvok.
"""
        }
    ]

    if pdf_images:
        for item in pdf_images:
            content.append({
                "type": "input_image",
                "image_url": f"data:image/png;base64,{item['image_base64']}",
                "detail": "high"
            })

    response = client.responses.create(
        model="gpt-4.1-mini",
        input=[
            {
                "role": "user",
                "content": content
            }
        ],
        temperature=0.2
    )

    return response.output_text