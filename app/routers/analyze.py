import os
import re
import json
from fastapi import APIRouter, UploadFile, File, Form
from typing import List

from app.services.ai_agent import analyze_request
from app.services.pdf_reader import extract_text_from_pdf, pdf_pages_to_images_base64
from app.services.storage import save_analysis
from app.services.classic_extractor import extract_classic_features
from app.services.text_processing import preprocess_text, tokenize, remove_stopwords

router = APIRouter()


def build_nlp_debug(full_text: str, classic_features: dict) -> dict:
    clean_text = preprocess_text(full_text)
    words, sentences = tokenize(clean_text)
    filtered_words = remove_stopwords(words)

    extracted_parameters = {
        "dimensions": classic_features.get("dimensions", []),
        "quantities": classic_features.get("quantities", []),
        "emails": classic_features.get("emails", []),
        "phones": classic_features.get("phones", []),
        "cities": classic_features.get("cities", []),
        "product_types": classic_features.get("product_types", []),
        "services": classic_features.get("services", []),
        "urgency": classic_features.get("urgency", []),
        "materials": classic_features.get("materials", []),
        "colors": classic_features.get("colors", []),
    }

    return {
        "original_text": full_text[:3000],
        "clean_text": clean_text[:3000],
        "word_count": len(words),
        "sentence_count": len(sentences),
        "tokens_preview": words[:80],
        "filtered_words_preview": filtered_words[:80],
        "extracted_parameters": extracted_parameters,
        "missing_fields": classic_features.get("missing_info", [])
    }


def _extract_json_from_text(text: str):
    """
    Bando ištraukti JSON iš AI teksto atsakymo.
    Veikia net jei AI apgaubia JSON markdown blokais arba
    rašo tekstą prieš/po JSON.
    """
    # 1. Bandome tiesiogiai
    try:
        return json.loads(text.strip())
    except Exception:
        pass

    # 2. Ištraukiam iš ```json ... ``` bloko
    match = re.search(r"```json\s*(.*?)```", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1).strip())
        except Exception:
            pass

    # 3. Ištraukiam iš ``` ... ``` bloko
    match = re.search(r"```\s*(.*?)```", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1).strip())
        except Exception:
            pass

    # 4. Ieškome pirmo { arba [ simbolio
    for start_char, end_char in [('{', '}'), ('[', ']')]:
        start = text.find(start_char)
        end = text.rfind(end_char)
        if start != -1 and end != -1 and end > start:
            try:
                return json.loads(text[start:end + 1])
            except Exception:
                pass

    return None


def _extract_mbcad_table_from_text(text: str) -> list:
    """
    Specialiai ieško MBcad lentelės JSON masyvo AI atsakyme.
    AI dažnai grąžina lentelę atskirame JSON bloke teksto pabaigoje.
    """
    # Ieškome JSON masyvo su mbcad požymiais
    matches = re.findall(r'\[\s*\{[^[\]]*"sistema"[^[\]]*\}\s*\]', text, re.DOTALL)
    for match in matches:
        try:
            data = json.loads(match)
            if isinstance(data, list) and len(data) > 0:
                return data
        except Exception:
            pass

    # Ieškome bet kokio JSON masyvo
    matches = re.findall(r'\[\s*\{.*?\}\s*\]', text, re.DOTALL)
    for match in matches:
        try:
            data = json.loads(match)
            if isinstance(data, list) and len(data) > 0:
                if any(k in str(data[0]) for k in ['sistema', 'plotis_mm', 'zymejimas', 'nr']):
                    return data
        except Exception:
            pass

    return []


def normalize_ai_result(result, nlp_debug: dict) -> dict:
    """
    Paverčia AI atsakymą į struktūrizuotą dict su visais laukais.
    Tvarko tiek dict, tiek teksto atsakymus.
    """
    if isinstance(result, dict):
        analysis = result
    else:
        text = str(result).strip()

        # Bandome ištraukti JSON
        parsed = _extract_json_from_text(text)

        if parsed and isinstance(parsed, dict):
            analysis = parsed
        else:
            # AI grąžino tekstą — skaidome į sekcijas
            analysis = _parse_text_response(text)

    # Užtikriname kad mbcad_like_table visada egzistuoja
    if not analysis.get("mbcad_like_table") and not analysis.get("mbcad_table"):
        # Bandome ištraukti iš teksto jei yra
        raw_text = str(result)
        table = _extract_mbcad_table_from_text(raw_text)
        if table:
            analysis["mbcad_like_table"] = table

    # Normalizuojame laukų pavadinimus
    if analysis.get("mbcad_table") and not analysis.get("mbcad_like_table"):
        analysis["mbcad_like_table"] = analysis["mbcad_table"]

    analysis["nlp_debug"] = nlp_debug
    return analysis


def _parse_text_response(text: str) -> dict:
    """
    Kai AI grąžina struktūrizuotą tekstą (ne JSON),
    bandome išskirti sekcijas pagal antraštes.
    """
    analysis = {
        "project_summary": "",
        "missing_information": [],
        "warnings": [],
        "mbcad_like_table": [],
        "detected_objects": [],
        "client_reply_draft": ""
    }

    # Santrauka
    summary_match = re.search(
        r"##\s*Santrauka\s*\n(.*?)(?=##|\Z)",
        text, re.DOTALL | re.IGNORECASE
    )
    if summary_match:
        analysis["project_summary"] = summary_match.group(1).strip()
    else:
        # Pirmą paragrafą naudojame kaip santrauką
        lines = [l.strip() for l in text.split('\n') if l.strip()]
        if lines:
            analysis["project_summary"] = lines[0]

    # Trūkstama informacija
    missing_match = re.search(
        r"##\s*Tr[ūu]kstama informacija\s*\n(.*?)(?=##|\Z)",
        text, re.DOTALL | re.IGNORECASE
    )
    if missing_match:
        missing_text = missing_match.group(1).strip()
        items = re.findall(r"[-*•]\s*(.+)", missing_text)
        analysis["missing_information"] = items if items else [missing_text]

    # Rekomendacija
    rec_match = re.search(
        r"##\s*Rekomendacija.*?\n(.*?)(?=##|\Z)",
        text, re.DOTALL | re.IGNORECASE
    )
    if rec_match:
        analysis["warnings"] = [rec_match.group(1).strip()]

    # Atsakymo juodraštis
    draft_match = re.search(
        r"##\s*Atsakymo.*?juodra[šs]tis\s*\n(.*?)(?=##|\Z)",
        text, re.DOTALL | re.IGNORECASE
    )
    if draft_match:
        analysis["client_reply_draft"] = draft_match.group(1).strip()

    # MBcad lentelė — ieškome JSON bloko
    mbcad_table = _extract_mbcad_table_from_text(text)
    if mbcad_table:
        analysis["mbcad_like_table"] = mbcad_table

    # Jei santrauka tuščia — naudojame visą tekstą
    if not analysis["project_summary"]:
        analysis["project_summary"] = text[:800]

    return analysis


@router.post("/analyze")
async def analyze(
    email_text: str = Form(""),
    files: List[UploadFile] = File(None),
    pdf_file: UploadFile = File(None)
):
    pdf_text = ""
    pdf_images = []
    files_processed = []
    uploaded_files = []

    if files:
        uploaded_files.extend(files)
    if pdf_file:
        uploaded_files.append(pdf_file)

    for uploaded_file in uploaded_files:
        filename = uploaded_file.filename or "unknown_file"
        content = await uploaded_file.read()

        file_info = {
            "file_name": filename,
            "content_type": uploaded_file.content_type,
            "processed_as": "not_processed"
        }

        if filename.lower().endswith(".pdf"):
            extracted_text = extract_text_from_pdf(content)
            pdf_text += "\n" + extracted_text
            images = pdf_pages_to_images_base64(content, max_pages=12)
            pdf_images.extend(images)
            file_info["processed_as"] = "pdf"
            file_info["text_preview"] = extracted_text[:300]

        files_processed.append(file_info)

    full_text = email_text + "\n" + pdf_text
    classic_features = extract_classic_features(full_text)
    nlp_debug = build_nlp_debug(full_text=full_text, classic_features=classic_features)

    result = analyze_request(
        email_text=email_text,
        pdf_text=pdf_text,
        pdf_images=pdf_images,
        classic_features=classic_features
    )

    analysis = normalize_ai_result(result, nlp_debug)

    save_analysis(
        email_text=email_text,
        pdf_text=pdf_text,
        ai_analysis=str(analysis),
        source="fastapi"
    )

    return {
        "status": "success",
        "classic_features": classic_features,
        "analysis": analysis,
        "files_processed": files_processed,
        "pdf_text_preview": pdf_text[:1000],
        "pages_sent_to_vision": len(pdf_images)
    }