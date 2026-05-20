#Sistema analizuoja ne tik tekstą, bet ir PDF dokumentus.
import fitz
import base64


def extract_text_from_pdf(pdf_bytes: bytes) -> str:
    if not pdf_bytes:
        return ""

    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    text = ""

    for i, page in enumerate(doc, start=1):
        page_text = page.get_text()
        text += f"\n\n--- PDF PAGE {i} TEXT ---\n{page_text}"

    return text.strip()


def pdf_pages_to_images_base64(pdf_bytes: bytes, max_pages: int = 12) -> list[dict]:
    if not pdf_bytes:
        return []

    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    images = []

    for i, page in enumerate(doc[:max_pages], start=1):
        pix = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
        img_bytes = pix.tobytes("png")
        img_base64 = base64.b64encode(img_bytes).decode("utf-8")

        images.append({
            "page": i,
            "image_base64": img_base64
        })

    return images