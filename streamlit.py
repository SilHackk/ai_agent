#streamlit run streamlit.py
import streamlit as st
import requests

API_URL = "http://127.0.0.1:8000/analyze"

st.set_page_config(
    page_title="AI langų užklausų asistentas",
    page_icon="🪟",
    layout="wide"
)

st.title("AI langų užklausų asistentas")

email_text = st.text_area(
    "Įklijuok kliento email tekstą:",
    height=220
)

uploaded_pdf = st.file_uploader(
    "Įkelk PDF projektą",
    type=["pdf"]
)

if st.button("Analizuoti užklausą"):
    if not email_text and uploaded_pdf is None:
        st.warning("Įkelk bent email tekstą arba PDF failą.")
    else:
        with st.spinner("Analizuojama per FastAPI backendą..."):
            files = None

            if uploaded_pdf:
                files = {
                    "pdf_file": (
                        uploaded_pdf.name,
                        uploaded_pdf.getvalue(),
                        "application/pdf"
                    )
                }

            data = {
                "email_text": email_text
            }

            response = requests.post(API_URL, data=data, files=files)

        if response.status_code == 200:
            result = response.json()

            st.success("Analizė baigta")

            st.subheader("AI analizės rezultatas")
            st.markdown(result["analysis"])

            if "pdf_text_preview" in result:
                with st.expander("PDF teksto peržiūra"):
                    st.write(result["pdf_text_preview"])
        else:
            st.error("Įvyko klaida FastAPI backend'e")
            st.code(response.text)

            st.subheader("Žmogaus įvertinimas")

quality_score = st.slider("AI atsakymo kokybė", 1, 5, 3)

human_reply = st.text_area(
    "Tikras darbuotojo atsakymas klientui",
    height=160
)

human_notes = st.text_area(
    "Ką AI praleido arba suklydo?",
    height=160
)

approved = st.checkbox("AI atsakymas tinkamas naudoti")
save_analysis(
    email_text=email_text,
    pdf_text="",
    ai_analysis=st.session_state.analysis_result,
    source="streamlit",
    human_reply=human_reply,
    human_notes=human_notes,
    quality_score=quality_score
)