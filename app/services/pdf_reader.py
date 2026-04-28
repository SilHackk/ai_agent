import fitz


def extract_text_from_pdf(uploaded_file) -> str:
    if uploaded_file is None:
        return ""

    pdf_bytes = uploaded_file.read()
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")

    text = ""
    for page in doc:
        text += page.get_text() + "\n"

    return text.strip()