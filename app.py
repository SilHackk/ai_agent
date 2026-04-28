#bash : streamlit run app.py
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

from app.services.pdf_reader import extract_text_from_pdf
from app.services.ai_agent import analyze_request
from app.services.storage import save_analysis

st.set_page_config(
    page_title="AI langų užklausų asistentas",
    page_icon="🪟",
    layout="wide"
)

st.title("AI langų užklausų asistentas")
st.write("Sistema analizuoja kliento laišką ir PDF projektą, tada paruošia informaciją darbuotojui prieš darbą su MBcad / Klaes.")

email_text = st.text_area(
    "Įklijuok kliento email tekstą:",
    height=220,
    placeholder="Pvz. Sveiki, siunčiu namo projektą, norėčiau preliminarios langų kainos..."
)

uploaded_pdf = st.file_uploader("Įkelk PDF projektą arba MBcad eksportą", type=["pdf"])

if "analysis_result" not in st.session_state:
    st.session_state.analysis_result = None

if "last_email_text" not in st.session_state:
    st.session_state.last_email_text = ""

if st.button("Analizuoti užklausą"):
    if not email_text and uploaded_pdf is None:
        st.warning("Įkelk bent email tekstą arba PDF failą.")
    else:
        with st.spinner("AI analizuoja užklausą..."):
            pdf_text = extract_text_from_pdf(uploaded_pdf) if uploaded_pdf else ""
            result = analyze_request(email_text, pdf_text)

        st.session_state.analysis_result = result
        st.session_state.last_email_text = email_text

if st.session_state.analysis_result:
    st.subheader("AI analizės rezultatas")

    sections = st.session_state.analysis_result.split("##")

    for section in sections:
        if section.strip():
            lines = section.strip().split("\n", 1)
            title = lines[0]
            content = lines[1] if len(lines) > 1 else ""

            st.markdown(f"### {title}")
            st.write(content)

    if st.button("💾 Išsaugoti analizę", key="save_button_main"):
        save_analysis(
            st.session_state.last_email_text,
            st.session_state.analysis_result
        )
        st.success("Išsaugota!")