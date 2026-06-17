import base64
import json
import os
from pathlib import Path
from typing import List, Dict

import fitz
from openai import OpenAI


def _image_to_data_url(image_path: str) -> str:
    with open(image_path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("utf-8")
    return f"data:image/png;base64,{b64}"


def pdf_to_preview_images(pdf_path: str, output_dir: str = "uploads/pdf_previews", zoom: float = 0.55) -> List[Dict]:
    os.makedirs(output_dir, exist_ok=True)
    doc = fitz.open(pdf_path)
    pdf_name = Path(pdf_path).stem
    previews = []
    for page_index in range(len(doc)):
        page = doc[page_index]
        matrix = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=matrix, alpha=False)
        out_path = os.path.join(output_dir, f"{pdf_name}_page_{page_index + 1}_preview.png")
        pix.save(out_path)
        text = page.get_text("text")[:1500]
        previews.append({
            "page_number": page_index,
            "display_page": page_index + 1,
            "image_path": out_path,
            "text_preview": text
        })
    doc.close()
    return previews


def select_relevant_pdf_pages_with_gpt(
    pdf_path: str,
    max_pages: int = 12,
    batch_size: int = 5,
    model: str = "gpt-4o-mini"
) -> List[Dict]:
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    previews = pdf_to_preview_images(pdf_path)
    selected_pages = []
    for start in range(0, len(previews), batch_size):
        batch = previews[start:start + batch_size]
        content = [{
            "type": "text",
            "text": (
                "Tu analizuoji langų/durų įmonės PDF projektą. "
                "Tavo darbas – atrinkti tik tuos puslapius, kuriuos verta analizuoti giliau.\n\n"
                "Ieškok puslapių, kuriuose yra:\n"
                "- langų arba durų brėžiniai;\n"
                "- fasado / pjūvio / langų schemos;\n"
                "- matmenys mm;\n"
                "- varstymo žymėjimai;\n"
                "- mėlynos zonos, raudoni brūkšniai ar kiti projektiniai žymėjimai;\n"
                "- langų/durų specifikacijos lentelės;\n"
                "- profilių, stiklo paketų, spalvų ar kiekių informacija.\n\n"
                "Atmesk puslapius, kurie yra tik viršeliai, bendri tekstai, sutartys, instrukcijos.\n\n"
                "Grąžink TIK validų JSON sąrašą. Be markdown. Be paaiškinimų už JSON ribų.\n\n"
                "Formatas:\n[\n  {\n    \"display_page\": 1,\n    \"page_number\": 0,\n"
                "    \"relevance\": \"high|medium|low\",\n    \"reason\": \"kodėl puslapis aktualus\",\n"
                "    \"expected_content\": [\"window drawing\", \"dimensions\"]\n  }\n]\n\n"
                "Atrink tik high arba medium puslapius."
            )
        }]
        for item in batch:
            content.append({"type": "text", "text": f"Puslapis {item['display_page']} / page_number {item['page_number']}.\nTeksto preview:\n{item['text_preview']}"})
            content.append({"type": "image_url", "image_url": {"url": _image_to_data_url(item["image_path"])}})
        response = client.chat.completions.create(model=model, messages=[{"role": "user", "content": content}])
        raw = response.choices[0].message.content.strip()
        try:
            data = json.loads(raw)
            if isinstance(data, list):
                for page in data:
                    if page.get("relevance") in ["high", "medium"]:
                        selected_pages.append(page)
        except json.JSONDecodeError:
            continue
    selected_pages = sorted(selected_pages, key=lambda x: 0 if x.get("relevance") == "high" else 1)
    return selected_pages[:max_pages]


def select_relevant_pdf_pages(pdf_path: str):
    selected = select_relevant_pdf_pages_with_gpt(pdf_path)
    if not selected:
        return [{"page_number": 0, "display_page": 1, "relevance": "fallback", "reason": "GPT Vision nerado aktualių puslapių.", "expected_content": []}]
    return selected


def pdf_to_images(pdf_path: str, pages: List[int] | None = None, output_dir: str = "uploads/pdf_pages", zoom: float = 2.0) -> List[str]:
    os.makedirs(output_dir, exist_ok=True)
    doc = fitz.open(pdf_path)
    pdf_name = Path(pdf_path).stem
    image_paths = []
    if pages is None:
        pages = list(range(len(doc)))
    for page_index in pages:
        if page_index < 0 or page_index >= len(doc):
            continue
        page = doc[page_index]
        matrix = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=matrix, alpha=False)
        out_path = os.path.join(output_dir, f"{pdf_name}_page_{page_index + 1}.png")
        pix.save(out_path)
        image_paths.append(out_path)
    doc.close()
    return image_paths
