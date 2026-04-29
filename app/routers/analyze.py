from fastapi import APIRouter, UploadFile, File, Form
from app.services.ai_agent import analyze_request
from app.services.pdf_reader import extract_text_from_pdf, pdf_pages_to_images_base64
from app.services.storage import save_analysis
from app.services.classic_extractor import extract_classic_features

router = APIRouter()


@router.post("/analyze")
async def analyze(
    email_text: str = Form(...),
    pdf_file: UploadFile = File(None)
):
    pdf_text = ""
    pdf_images = []
    classic_features = extract_classic_features(email_text + "\n" + pdf_text)
    if pdf_file:
        content = await pdf_file.read()
        pdf_text = extract_text_from_pdf(content)
        pdf_images = pdf_pages_to_images_base64(content, max_pages=12)

    result = analyze_request(email_text, pdf_text, pdf_images, classic_features)

    save_analysis(email_text, pdf_text, result, source="fastapi")

    return {
        "status": "success",
        "classic_features": classic_features,
        "analysis": result,
        "pdf_text_preview": pdf_text[:1000],
        "pages_sent_to_vision": len(pdf_images)
    }