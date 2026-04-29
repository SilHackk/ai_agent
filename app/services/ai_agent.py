import os
from openai import OpenAI
from app.core.config import OPENAI_API_KEY

client = OpenAI(api_key=OPENAI_API_KEY)


def load_prompt() -> str:
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    prompt_path = os.path.join(base_dir, "prompts", "email_analysis_prompt.txt")

    with open(prompt_path, "r", encoding="utf-8") as file:
        return file.read()


def analyze_request(email_text: str, pdf_text: str = "", pdf_images: list[dict] | None = None, classic_features: dict | None = None) -> str:
    base_prompt = load_prompt()

    content = [
        {
            "type": "input_text",
            "text": f"""
{base_prompt}

Klasikiniais metodais ištraukti faktai:
{classic_features}

Naudok šiuos faktus kaip pagrindą. Jeigu LLM analizė nesutampa su klasikiniais faktais, pažymėk neaiškumą, bet neišsigalvok.
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
                "text": f"PDF puslapis {item['page']} kaip vaizdas:"
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