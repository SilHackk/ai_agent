from fastapi import APIRouter, UploadFile, File, Form
from app.services.ai_agent import analyze_request
from app.services.pdf_reader import extract_text_from_pdf
from app.services.save_results import save_analysis

router = APIRouter()


@router.post("/analyze")
async def analyze(
    email_text: str = Form(...),
    pdf_file: UploadFile = File(None)
):
    pdf_text = ""

    if pdf_file:
        content = await pdf_file.read()
        pdf_text = extract_text_from_pdf(content)

    result = analyze_request(email_text, pdf_text)

    save_analysis(email_text, pdf_text, result)

    return {
        "status": "success",
        "analysis": result
    }