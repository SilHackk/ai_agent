from fastapi import APIRouter, UploadFile, File, Form
from typing import List
import json

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


def normalize_ai_result(result, nlp_debug: dict):
    if isinstance(result, dict):
        analysis = result
    else:
        text = str(result).strip()

        if text.startswith("```json"):
            text = text.replace("```json", "").replace("```", "").strip()
        elif text.startswith("```"):
            text = text.replace("```", "").strip()

        try:
            analysis = json.loads(text)
        except Exception:
            analysis = {
                "project_summary": text,
                "missing_information": [],
                "warnings": [],
                "mbcad_like_table": [],
                "detected_objects": [],
                "client_reply_draft": ""
            }

    analysis["nlp_debug"] = nlp_debug
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

    nlp_debug = build_nlp_debug(
        full_text=full_text,
        classic_features=classic_features
    )

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
        ai_analysis=analysis,
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