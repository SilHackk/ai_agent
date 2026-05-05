# streamlit run streamlit.py

import os
import pandas as pd
import requests
import streamlit as st

BASE_URL = "http://127.0.0.1:8000"
MANUAL_ANALYZE_URL = f"{BASE_URL}/analyze"

st.set_page_config(
    page_title="AI langų užklausų asistentas",
    page_icon="🪟",
    layout="wide"
)

st.title("AI langų užklausų asistentas")
st.write("Sistema analizuoja klientų laiškus, PDF brėžinius ir failus, atrenka svarbius puslapius ir formuoja MBcad/Klaes tipo suvestinę.")

if "analysis" not in st.session_state:
    st.session_state.analysis = None

if "files_processed" not in st.session_state:
    st.session_state.files_processed = []

if "outlook_messages" not in st.session_state:
    st.session_state.outlook_messages = []

if "imported_projects" not in st.session_state:
    st.session_state.imported_projects = []

mode = st.sidebar.radio(
    "Darbo režimas",
    [
        "Rankinis įkėlimas",
        "Outlook laiškai",
    ]
)

st.sidebar.markdown("---")
st.sidebar.write("Backend:")
st.sidebar.code(BASE_URL)

def show_analysis_result(analysis, files_processed=None):
    if isinstance(analysis, str):
        try:
            import json
            analysis = json.loads(analysis)
        except Exception:
            analysis = {
                "project_summary": analysis,
                "missing_information": [],
                "warnings": [],
                "mbcad_like_table": [],
                "detected_objects": [],
                "client_reply_draft": ""
            }
    if files_processed:
        st.subheader("Apdoroti failai")
        st.dataframe(pd.DataFrame(files_processed), use_container_width=True)

    if not analysis:
        st.info("Analizės rezultato dar nėra.")
        return

    left, right = st.columns([1, 1])

    with left:
        st.subheader("AI santrauka")
        st.write(
            analysis.get("project_summary")
            or analysis.get("summary")
            or "Santrauka dar nesugeneruota."
        )

        st.subheader("Trūkstama informacija")
        missing = (
            analysis.get("missing_information")
            or analysis.get("missing_fields")
            or []
        )

        if missing:
            for item in missing:
                st.warning(str(item))
        else:
            st.success("AI nerado kritiškai trūkstamos informacijos.")

        st.subheader("Perspėjimai")
        warnings = analysis.get("warnings", [])

        if warnings:
            for warning in warnings:
                st.error(str(warning))
        else:
            st.info("Perspėjimų nėra.")

    with right:
        st.subheader("MBcad / Klaes suvestinė")

        mbcad_table = (
            analysis.get("mbcad_table")
            or analysis.get("mbcad_like_table")
            or []
        )

        if mbcad_table:
            df = pd.DataFrame(mbcad_table)
            st.dataframe(df, use_container_width=True)

            csv = df.to_csv(index=False).encode("utf-8-sig")
            st.download_button(
                "Atsisiųsti MBcad lentelę CSV",
                data=csv,
                file_name="mbcad_suvestine.csv",
                mime="text/csv",
            )
        else:
            st.info("MBcad lentelė dar nesugeneruota.")

    st.subheader("Aptikti objektai")

    detected_items = (
        analysis.get("detected_items")
        or analysis.get("detected_objects")
        or []
    )

    if detected_items:
        st.dataframe(pd.DataFrame(detected_items), use_container_width=True)
    else:
        st.info("Objektų nerasta arba reikia aiškesnio brėžinio.")

    st.subheader("Atrinkti PDF puslapiai")

    selected_pages = analysis.get("selected_pages", [])
    rendered_images = analysis.get("rendered_images", [])
    overlay_images = analysis.get("overlay_images", [])

    if selected_pages:
        st.dataframe(pd.DataFrame(selected_pages), use_container_width=True)
    else:
        st.info("Atrinktų PDF puslapių nėra arba šis failas ne PDF.")

    if rendered_images or overlay_images:
        st.subheader("Brėžinių peržiūra")

        images_to_show = overlay_images if overlay_images else rendered_images

        cols = st.columns(2)
        for index, image_path in enumerate(images_to_show):
            if image_path and os.path.exists(image_path):
                with cols[index % 2]:
                    st.image(image_path, caption=image_path, use_container_width=True)

    st.subheader("Atsakymo klientui juodraštis")

    draft = (
        analysis.get("client_reply_draft")
        or analysis.get("reply_draft")
        or ""
    )

    st.text_area("Juodraštis", value=draft, height=180)

    with st.expander("Pilnas JSON rezultatas"):
        st.json(analysis)


if mode == "Rankinis įkėlimas":
    st.header("Rankinis projekto įkėlimas")

    email_text = st.text_area("Kliento email tekstas", height=200)

    uploaded_files = st.file_uploader(
        "Įkelk projekto failus",
        type=["pdf", "xlsx", "xls", "csv", "png", "jpg", "jpeg", "webp"],
        accept_multiple_files=True,
    )

    col1, col2 = st.columns([1, 1])

    with col1:
        analyze_normal = st.button("Analizuoti per pagrindinį /analyze", use_container_width=True)

    with col2:
        analyze_pdf_deep = st.button("PDF analizė su GPT puslapių atranka", use_container_width=True)

    if analyze_normal:
        if not email_text and not uploaded_files:
            st.warning("Įkelk bent email tekstą arba failą.")
        else:
            multipart_files = []

            for file in uploaded_files:
                multipart_files.append((
                    "files",
                    (file.name, file.getvalue(), file.type or "application/octet-stream")
                ))

            with st.spinner("Analizuojama: tekstas + lentelės + PDF/paveikslėliai..."):
                response = requests.post(
                    MANUAL_ANALYZE_URL,
                    data={"email_text": email_text},
                    files=multipart_files,
                    timeout=300,
                )

            if response.status_code != 200:
                st.error("Backend klaida")
                st.code(response.text)
            else:
                data = response.json()
                st.session_state.analysis = data.get("analysis", data)
                st.session_state.files_processed = data.get("files_processed", [])
                st.success(f"Analizė baigta. Project ID: {data.get('project_id')}")

    if analyze_pdf_deep:
        if not uploaded_files:
            st.warning("Įkelk bent vieną PDF failą.")
        else:
            final_results = []

            for file in uploaded_files:
                if not file.name.lower().endswith(".pdf"):
                    continue

                with st.spinner(f"GPT Vision atrenka ir analizuoja PDF: {file.name}"):
                    response = requests.post(
                        f"{BASE_URL}/automation/pdf/analyze-selected-pages",
                        files={
                            "file": (
                                file.name,
                                file.getvalue(),
                                file.type or "application/pdf"
                            )
                        },
                        timeout=500,
                    )

                if response.status_code != 200:
                    st.error(f"Klaida analizuojant {file.name}")
                    st.code(response.text)
                else:
                    result = response.json()
                    result["file_name"] = file.name
                    final_results.append(result)

            if final_results:
                combined = {
                    "project_summary": "PDF failai išanalizuoti su GPT Vision puslapių atranka.",
                    "selected_pages": [],
                    "rendered_images": [],
                    "overlay_images": [],
                    "detected_objects": [],
                    "mbcad_like_table": [],
                    "warnings": [],
                    "missing_information": [],
                    "client_reply_draft": ""
                }

                for result in final_results:
                    combined["selected_pages"].extend(result.get("selected_pages", []))
                    combined["rendered_images"].extend(result.get("rendered_images", []))
                    combined["overlay_images"].extend(result.get("overlay_images", []))
                    combined["detected_objects"].extend(result.get("detected_objects", []))
                    combined["mbcad_like_table"].extend(result.get("mbcad_like_table", []))

                st.session_state.analysis = combined
                st.session_state.files_processed = [
                    {"file_name": r.get("file_name"), "source_pdf": r.get("source_pdf")}
                    for r in final_results
                ]

                st.success("PDF analizė baigta.")

    show_analysis_result(st.session_state.analysis, st.session_state.files_processed)


if mode == "Outlook laiškai":
    st.header("Outlook laiškų importas ir analizė")

    st.info(
        "Šis režimas naudoja Microsoft Graph API. Pirmą kartą terminale gali atsirasti prisijungimo kodas."
    )

    col1, col2 = st.columns([1, 1])

    with col1:
        limit = st.number_input("Kiek laiškų peržiūrėti", min_value=1, max_value=100, value=20)

    with col2:
        only_with_attachments = st.checkbox("Rodyti tik su prisegtais failais", value=True)

    if st.button("Gauti Outlook laiškus", use_container_width=True):
        with st.spinner("Jungiama prie Outlook ir gaunami laiškai..."):
            response = requests.get(
                f"{BASE_URL}/automation/outlook/preview",
                params={
                    "limit": limit,
                    "only_with_attachments": only_with_attachments
                },
                timeout=120,
            )

        if response.status_code != 200:
            st.error("Nepavyko gauti Outlook laiškų")
            st.code(response.text)
        else:
            data = response.json()
            st.session_state.outlook_messages = data.get("messages", [])
            st.success(f"Gauta laiškų: {len(st.session_state.outlook_messages)}")

    messages = st.session_state.outlook_messages

    if messages:
        st.subheader("Pasirink laiškus analizei")

        selected_ids = []

        for msg in messages:
            label = f"{msg.get('received', '')} | {msg.get('from_email', '')} | {msg.get('subject', '')}"

            checked = st.checkbox(
                label,
                key=f"msg_{msg.get('id')}"
            )

            with st.expander(f"Laiško peržiūra: {msg.get('subject', '')}"):
                st.write("Nuo:", msg.get("from_email"))
                st.write("Data:", msg.get("received"))
                st.write("Turi attachmentų:", msg.get("has_attachments"))
                st.write(msg.get("body_preview", ""))

            if checked:
                selected_ids.append(msg.get("id"))

        if selected_ids:
            st.success(f"Pasirinkta laiškų: {len(selected_ids)}")

        if st.button("Importuoti pasirinktus laiškus", use_container_width=True):
            with st.spinner("Importuojami laiškai ir attachmentai..."):
                response = requests.post(
                    f"{BASE_URL}/automation/outlook/import-selected",
                    json={"message_ids": selected_ids},
                    timeout=300,
                )

            if response.status_code != 200:
                st.error("Importo klaida")
                st.code(response.text)
            else:
                data = response.json()
                st.session_state.imported_projects = data.get("imported", [])
                st.success(f"Importuota: {data.get('imported_count')}")

        if st.session_state.imported_projects:
            st.subheader("Importuoti laiškai / projektai")

            rows = []
            for project in st.session_state.imported_projects:
                rows.append({
                    "project_id": project.get("project_id"),
                    "subject": project.get("subject"),
                    "from_email": project.get("from_email"),
                    "attachments": len(project.get("attachments", []))
                })

            st.dataframe(pd.DataFrame(rows), use_container_width=True)

            if st.button("Analizuoti importuotų laiškų PDF failus", use_container_width=True):
                combined = {
                    "project_summary": "Importuoti Outlook laiškai išanalizuoti.",
                    "selected_pages": [],
                    "rendered_images": [],
                    "overlay_images": [],
                    "detected_objects": [],
                    "mbcad_like_table": [],
                    "warnings": [],
                    "missing_information": [],
                    "client_reply_draft": ""
                }

                processed_files = []

                for project in st.session_state.imported_projects:
                    attachments = project.get("attachments", [])

                    for attachment in attachments:
                        path = attachment.get("path")

                        if not path or not path.lower().endswith(".pdf"):
                            continue

                        if not os.path.exists(path):
                            st.warning(f"Failas nerastas: {path}")
                            continue

                        with open(path, "rb") as f:
                            file_bytes = f.read()

                        with st.spinner(f"Analizuojamas PDF: {attachment.get('filename')}"):
                            response = requests.post(
                                f"{BASE_URL}/automation/pdf/analyze-selected-pages",
                                files={
                                    "file": (
                                        attachment.get("filename", "attachment.pdf"),
                                        file_bytes,
                                        "application/pdf"
                                    )
                                },
                                timeout=500,
                            )

                        if response.status_code != 200:
                            st.error(f"Klaida analizuojant {attachment.get('filename')}")
                            st.code(response.text)
                            continue

                        result = response.json()

                        combined["selected_pages"].extend(result.get("selected_pages", []))
                        combined["rendered_images"].extend(result.get("rendered_images", []))
                        combined["overlay_images"].extend(result.get("overlay_images", []))
                        combined["detected_objects"].extend(result.get("detected_objects", []))
                        combined["mbcad_like_table"].extend(result.get("mbcad_like_table", []))

                        processed_files.append({
                            "project_id": project.get("project_id"),
                            "filename": attachment.get("filename"),
                            "path": path
                        })

                st.session_state.analysis = combined
                st.session_state.files_processed = processed_files

                st.success("Importuotų laiškų PDF analizė baigta.")

            show_analysis_result(st.session_state.analysis, st.session_state.files_processed)