from app.services.pdf_image_tools import (
    select_relevant_pdf_pages,
    pdf_to_images
)


def select_and_render_relevant_pages(
    pdf_path: str,
    top_k: int = 5,
    max_scan_pages: int = 100
) -> dict:
    """
    Atrenka aktualius PDF puslapius ir paverčia juos į PNG analizavimui.
    top_k ir max_scan_pages kol kas priimami tam, kad endpointas nelūžtų.
    """

    selected_pages = select_relevant_pdf_pages(pdf_path)

    selected_pages = selected_pages[:top_k]

    page_numbers = [
        page["page_number"]
        for page in selected_pages
        if "page_number" in page
    ]

    image_paths = pdf_to_images(
        pdf_path,
        pages=page_numbers
    )

    return {
        "pdf_path": pdf_path,
        "selected_pages": selected_pages,
        "rendered_images": image_paths,
        "top_k": top_k,
        "max_scan_pages": max_scan_pages
    }