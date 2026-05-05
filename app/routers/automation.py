import os
from pathlib import Path
from typing import List

from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

from app.services.project_db import init_db, create_project, add_project_file, add_window_object, list_projects, get_project_objects
from app.services.email_importer import import_recent_emails, preview_emails, import_selected_emails
from app.services.shape_modeler import model_shapes_from_image
from app.services.pdf_image_tools import pdf_to_images
from app.services.project_analyzer import analyze_project_files
from app.services.pdf_page_selector import select_and_render_relevant_pages
from app.services.pdf_page_selector import select_and_render_relevant_pages
from app.services.shape_modeler import analyze_image_shapes

router = APIRouter(prefix='/automation', tags=['automation'])
UPLOAD_DIR = Path('uploads/manual')
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


class SelectedEmailsRequest(BaseModel):
    uids: List[str]
    mailbox: str = 'INBOX'


@router.post('/init-db')
def init_database():
    init_db()
    return {'status': 'ok', 'message': 'DB sukurta / atnaujinta'}


@router.get('/emails/preview')
def emails_preview(limit: int = 50, mailbox: str = 'INBOX', query: str = 'ALL', only_with_attachments: bool = True):
    try:
        init_db()
        return preview_emails(limit=limit, mailbox=mailbox, query=query, only_with_attachments=only_with_attachments)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post('/emails/import-selected')
def emails_import_selected(payload: SelectedEmailsRequest):
    try:
        init_db()
        if not payload.uids:
            raise HTTPException(status_code=400, detail='Nepasirinktas nei vienas laiškas')
        return import_selected_emails(payload.uids, mailbox=payload.mailbox)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post('/import-emails')
def import_emails(limit: int = 100, mailbox: str = 'INBOX', query: str = 'ALL', only_with_attachments: bool = True):
    try:
        init_db()
        return import_recent_emails(limit=limit, mailbox=mailbox, query=query, only_with_attachments=only_with_attachments)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get('/projects')
def projects(limit: int = 50):
    init_db()
    return {'projects': list_projects(limit=limit)}


@router.get('/projects/{project_id}/objects')
def project_objects(project_id: int):
    init_db()
    return {'objects': get_project_objects(project_id)}


@router.post('/model-shapes')
async def model_shapes(file: UploadFile = File(...)):
    init_db()
    project_id = create_project(source='manual_shape_model', subject=file.filename)
    safe_name = (file.filename or 'uploaded_file').replace('/', '_').replace('\\', '_')
    file_path = UPLOAD_DIR / f'{project_id}_{safe_name}'
    file_path.write_bytes(await file.read())
    file_id = add_project_file(project_id, safe_name, file.content_type or '', str(file_path))

    suffix = file_path.suffix.lower()
    if suffix == '.pdf':
        image_paths = pdf_to_images(file_path, max_pages=10)
    elif suffix in {'.png', '.jpg', '.jpeg', '.webp'}:
        image_paths = [str(file_path)]
    else:
        raise HTTPException(status_code=400, detail='Įkelk PDF arba paveikslėlį: png/jpg/jpeg/webp')

    all_results = []
    for image_path in image_paths:
        result = model_shapes_from_image(image_path)
        for obj in result['objects']:
            add_window_object(project_id, file_id, obj)
        all_results.append(result)

    return {
        'status': 'success',
        'project_id': project_id,
        'pages_or_images': len(all_results),
        'results': all_results,
    }


@router.post('/projects/{project_id}/analyze')
def analyze_imported_project(project_id: int, top_pdf_pages: int = 5, max_scan_pages: int = 100):
    """Paleidžia analizę ant jau importuoto email projekto attachmentų.
    Naudok po /emails/import-selected, kai gauni project_id.
    """
    try:
        init_db()
        return analyze_project_files(project_id, top_pdf_pages=top_pdf_pages, max_scan_pages=max_scan_pages)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post('/pdf/select-pages')
async def select_pdf_pages(file: UploadFile = File(...), top_k: int = 5, max_scan_pages: int = 100):
    """Tik atrenka reikalingiausius PDF puslapius.
    Naudinga kai PDF turi 50-100 lapų, o langams aktualūs tik keli.
    """
    safe_name = (file.filename or 'uploaded.pdf').replace('/', '_').replace('\\', '_')
    file_path = UPLOAD_DIR / safe_name
    file_path.write_bytes(await file.read())
    if file_path.suffix.lower() != '.pdf':
        raise HTTPException(status_code=400, detail='Šitas endpointas skirtas tik PDF failams')
    return select_and_render_relevant_pages(file_path, top_k=top_k, max_scan_pages=max_scan_pages)


@router.get('/overlay')
def get_overlay(path: str):
    p = Path(path)
    if not p.exists() or 'uploads' not in p.parts:
        raise HTTPException(status_code=404, detail='Overlay nerastas')
    return FileResponse(str(p))


@router.post("/pdf/analyze-selected-pages")
async def analyze_selected_pdf_pages(file: UploadFile = File(...)):
    os.makedirs("uploads/temp", exist_ok=True)

    file_path = os.path.join("uploads/temp", file.filename)
    with open(file_path, "wb") as f:
        f.write(await file.read())

    selection = select_and_render_relevant_pages(file_path, top_k=5, max_scan_pages=100)

    all_objects = []
    all_table_rows = []
    overlays = []

    for image_path in selection.get("rendered_images", []):
        result = analyze_image_shapes(image_path)

        all_objects.extend(result.get("detected_objects", []))
        all_table_rows.extend(result.get("mbcad_like_table", []))

        if result.get("overlay_image_path"):
            overlays.append(result["overlay_image_path"])

    return {
        "source_pdf": file_path,
        "selected_pages": selection.get("selected_pages", []),
        "rendered_images": selection.get("rendered_images", []),
        "detected_objects": all_objects,
        "mbcad_like_table": all_table_rows,
        "overlay_images": overlays
    }
