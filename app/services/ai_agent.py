import os
import re
from openai import OpenAI
from app.core.config import OPENAI_API_KEY
from services.text_processing import preprocess_text, tokenize, remove_stopwords
from services.pdf_table_extractor import extract_window_tables_from_text

client = OpenAI(api_key=OPENAI_API_KEY)


def load_prompt() -> str:
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    prompt_path = os.path.join(base_dir, "prompts", "email_analysis_prompt.txt")

    with open(prompt_path, "r", encoding="utf-8") as file:
        return file.read()


def analyze_request(
    email_text: str,
    pdf_text: str = "",
    pdf_images: list[dict] | None = None
) -> str:

    # 1. Sujungiame laiško ir PDF tekstą
    full_text = email_text + " " + pdf_text

    # 2. Klasikinis NLP preprocessing
    clean_text = preprocess_text(full_text)

    # 3. Tokenizacija
    words, sentences = tokenize(clean_text)

    # 4. Stop words šalinimas
    filtered_words = remove_stopwords(words)

    # 5. Regex informacijos ištraukimas
    dimensions = re.findall(r"\d+\s*[xX×]\s*\d+", full_text)
    numbers = re.findall(r"\d+", full_text)

    # 6. Klasikiniais metodais ištraukti faktai
    classic_features = {
        "clean_text_preview": clean_text[:1000],
        "word_count": len(words),
        "sentence_count": len(sentences),
        "filtered_keywords": filtered_words[:50],
        "dimensions": dimensions,
        "numbers": numbers,
        "pdf_window_tables": pdf_window_tables
    }

    # 7. Ištraukti langų lentelės informaciją iš PDF teksto
    pdf_window_tables = extract_window_tables_from_text(pdf_text)

    base_prompt = load_prompt()

    content = [
        {
            "type": "input_text",
            "text": f"""
{base_prompt}

Klasikiniais NLP metodais ištraukti faktai:
{classic_features}

Naudok šiuos faktus kaip pagalbinį pagrindą. Jeigu LLM analizė nesutampa su klasikiniais faktais, pažymėk neaiškumą, bet neišsigalvok.

Kliento laiškas:
{email_text}

PDF tekstinis sluoksnis:
{pdf_text}

Labai svarbu:
Jeigu PDF puslapiuose matosi brėžiniai, fasadai, langų žiniaraščiai, lentelės ar gaminių schemos, analizuok ir vaizdus.
Iš vaizdų ištrauk langų žymėjimus, matmenis, kiekius, spalvą, stiklo / šiluminius reikalavimus ir paruošk MBcad / Klaes suvestinę.
Jeigu informacijos nematai aiškiai, rašyk „neaiškiai matoma“, bet neišsigalvok.
"""
        }
    ]

    if pdf_images:
        for item in pdf_images:
            content.append({
                "type": "input_text",
                "image_url": f"data:image/png;base64,{item['image_base64']}",
                "detail": "high"
            })
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