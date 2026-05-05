import os
from pathlib import Path

from app.services.project_db import get_project_files
from app.services.pdf_image_tools import pdf_to_images, select_relevant_pdf_pages
from app.services.shape_modeler import analyze_image_shapes


def analyze_project_files(project_id: int) -> dict:
    files = get_project_files(project_id)

    results = {
        "project_id": project_id,
        "analyzed_files": [],
        "detected_objects": [],
        "mbcad_like_table": [],
    }

    for file in files:
        file_path = file.get("path") or file.get("file_path")
        if not file_path or not os.path.exists(file_path):
            continue

        suffix = Path(file_path).suffix.lower()

        if suffix == ".pdf":
            selected_pages = select_relevant_pdf_pages(file_path)

            page_images = pdf_to_images(
                file_path,
                pages=[p["page_number"] for p in selected_pages]
            )

            for image_path in page_images:
                analysis = analyze_image_shapes(image_path)

                results["analyzed_files"].append({
                    "source_file": file_path,
                    "analyzed_image": image_path,
                    "type": "pdf_page"
                })

                results["detected_objects"].extend(
                    analysis.get("detected_objects", [])
                )

                results["mbcad_like_table"].extend(
                    analysis.get("mbcad_like_table", [])
                )

        elif suffix in [".png", ".jpg", ".jpeg", ".webp"]:
            analysis = analyze_image_shapes(file_path)

            results["analyzed_files"].append({
                "source_file": file_path,
                "type": "image"
            })

            results["detected_objects"].extend(
                analysis.get("detected_objects", [])
            )

            results["mbcad_like_table"].extend(
                analysis.get("mbcad_like_table", [])
            )

        else:
            results["analyzed_files"].append({
                "source_file": file_path,
                "type": "unsupported",
                "note": "Šis failo tipas kol kas neanalizuojamas per shape modeler."
            })


    return results