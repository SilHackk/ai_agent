from fastapi import FastAPI, UploadFile, File, Form
from app.services.pdf_reader import extract_text_from_pdf
from app.services.ai_agent import analyze_request
from services.save_results import save_analysis

app = FastAPI(
    title="AI langų užklausų agentas",
    description="Sistema analizuoja kliento laišką ir PDF projektą langų įmonei.",
    version="1.0.0"
)


@app.get("/")
def root():
    return {
        "message": "AI langų užklausų agentas veikia"
    }


@app.post("/analyze")
async def analyze(
    email_text: str = Form(...),
    pdf_file: UploadFile = File(None)
):
    pdf_text = ""

    if pdf_file:
        pdf_bytes = await pdf_file.read()
        pdf_text = extract_text_from_pdf(pdf_bytes)

    result = analyze_request(email_text, pdf_text)

    save_analysis(email_text, pdf_text, result)

    return {
        "status": "success",
        "email_text": email_text,
        "pdf_text_preview": pdf_text[:500],
        "analysis": result
    }