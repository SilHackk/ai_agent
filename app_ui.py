# streamlit run streamlit.py

import os
import io
import pandas as pd
import requests
import streamlit as st
from datetime import datetime

# Docker deployment: BASE_URL priklauso nuo aplinkos
BASE_URL = os.getenv("FASTAPI_URL", "http://127.0.0.1:8000")
MANUAL_ANALYZE_URL = f"{BASE_URL}/analyze"
CRM_URL = f"{BASE_URL}/crm"


def _opt_idx(options: list, value) -> int:
    """Returns index of value in options list, or last index (Nenurodyta) if not found."""
    try:
        return options.index(str(value)) if value else len(options) - 1
    except ValueError:
        return len(options) - 1

st.set_page_config(
    page_title="AI langų užklausų asistentas",
    page_icon="🪟",
    layout="wide"
)

# ── LOGIN ─────────────────────────────────────────────────────────────────────
APP_PASSWORD = os.getenv("APP_PASSWORD", "")

def check_login():
    if not APP_PASSWORD:
        # Jei slaptažodis nenustatytas — leidžiame be login (lokalus naudojimas)
        return True
    if st.session_state.get("authenticated"):
        return True
    return False

def show_login():
    st.markdown("""
    <style>
    .login-box {
        max-width: 400px;
        margin: 100px auto;
        padding: 40px;
        border-radius: 12px;
        background: #f8f9fa;
        box-shadow: 0 2px 16px rgba(0,0,0,0.08);
    }
    </style>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("## 🪟 AI langų asistentas")
        st.markdown("---")
        password = st.text_input("Slaptažodis", type="password", key="login_input")
        if st.button("Prisijungti", use_container_width=True, type="primary"):
            if password == APP_PASSWORD:
                st.session_state["authenticated"] = True
                st.rerun()
            else:
                st.error("Neteisingas slaptažodis.")
        st.caption("Kreipkitės į administratorių jei pamiršote slaptažodį.")

if not check_login():
    show_login()
    st.stop()

# ── Po sėkmingo prisijungimo ──────────────────────────────────────────────────

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
        "CRM",
    ]
)

st.sidebar.markdown("---")
st.sidebar.write("Backend:")
st.sidebar.code(BASE_URL)
st.sidebar.markdown("---")


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
        st.subheader("MBcad suvestinė")
        st.caption("Pagal šią lentelę suvedinėk duomenis į MBcad: Orders → New offer → Constructions")

        mbcad_table = (
            analysis.get("mbcad_table")
            or analysis.get("mbcad_like_table")
            or []
        )

        MBCAD_COLUMNS = {
            "nr":                  "Nr.",
            "zymejimas":           "Žymėjimas",
            "element_type":        "Elemento tipas",
            "sistema":             "Sistema",
            "profilio_variantas":  "Profilis (ST/HI)",
            "plotis_mm":           "Plotis (mm)",
            "aukstis_mm":          "Aukštis (mm)",
            "kiekis":              "Kiekis",
            "spalva_isorine":      "Spalva išorinė",
            "spalva_tipas":        "Spalvos tipas",
            "spalva_pavirsius":    "Paviršius",
            "spalva_vidine":       "Spalva vidinė",
            "stiklo_paketas":      "Stiklo paketas",
            "stiklo_storis_mm":    "Stiklo storis (mm)",
            "stiklo_kodas":        "Stiklo kodas",
            "stiklo_ug":           "Ug (W/m²K)",
            "stiklo_g":            "g (SHGC)",
            "varstymas":           "Varstymas",
            "kampų_jungtys":       "Kampų jungtys",
            "montavimo_budas":     "Montavimas",
            "slenkscio_juosta":    "Slenkščio juosta",
            "stiklinimo_juosta":   "Stiklinimo juosta",
            "tarpine_drenazas":    "Tarpinė (drenažas)",
            "tarpine_rebet":       "Tarpinė (rebetas)",
            "tarpine_centrinis":   "Tarpinė (centrinis)",
            "tarpine_slenkscio":   "Tarpinė (slenkstis)",
            "furnitura_rankena":   "Rankena",
            "apsauga_rc":          "RC apsauga",
            "pastabos":            "Pastabos",
        }

        analysis_ts = analysis.get("timestamp", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

        if mbcad_table:
            df = pd.DataFrame(mbcad_table)
            rename_map = {k: v for k, v in MBCAD_COLUMNS.items() if k in df.columns}
            df_display = df.rename(columns=rename_map)
            st.dataframe(df_display, use_container_width=True, hide_index=True)

            import io
            buf = io.BytesIO()
            with pd.ExcelWriter(buf, engine="openpyxl") as writer:
                df_display.to_excel(writer, index=False, sheet_name="MBcad suvestinė")
            st.download_button(
                "⬇️ Atsisiųsti MBcad suvestinę (.xlsx)",
                data=buf.getvalue(),
                file_name="mbcad_suvestine.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )

            # ── Feedback prie kiekvienos eilutės ─────────────────────────────
            st.markdown("---")
            st.markdown("#### ✅ Patikrink AI rezultatus")
            st.caption("Pažymėk kas teisinga. Jei neteisinga — įrašyk komentarą. Tai padeda sistemai tobulėti.")

            from app.services.storage import save_feedback

            for i, row in enumerate(mbcad_table):
                nr = row.get("nr", i + 1)
                zym = row.get("zymejimas") or f"#{nr}"
                sistema = row.get("sistema") or "?"
                plotis = row.get("plotis_mm") or "?"
                aukstis = row.get("aukstis_mm") or "?"
                kiekis = row.get("kiekis") or "?"
                spalva = row.get("spalva_isorine") or "?"
                stiklas = row.get("stiklo_paketas") or "?"

                with st.container(border=True):
                    st.markdown(
                        f"**{zym}** — {sistema} | {plotis}×{aukstis} mm | "
                        f"{kiekis} vnt. | {spalva} | {stiklas}"
                    )

                    fb_cols = st.columns([1, 1, 3])
                    with fb_cols[0]:
                        correct = st.checkbox(
                            "✅ Teisinga",
                            key=f"fb_ok_{i}",
                            value=False
                        )
                    with fb_cols[1]:
                        wrong = st.checkbox(
                            "❌ Neteisinga",
                            key=f"fb_wrong_{i}",
                            value=False
                        )
                    with fb_cols[2]:
                        comment = st.text_input(
                            "Komentaras / pataisymas",
                            key=f"fb_comment_{i}",
                            placeholder="pvz. Sistema turėtų būti MB-86N, spalva RAL 9005"
                        )

                    if correct and not wrong:
                        if st.button("💾 Išsaugoti feedback", key=f"fb_save_{i}"):
                            save_feedback(
                                analysis_timestamp=analysis_ts,
                                field=f"mbcad_row_{nr}_{zym}",
                                ai_value=f"{sistema} {plotis}x{aukstis} {spalva}",
                                is_correct=True,
                                comment=comment,
                                corrected_value="",
                            )
                            st.success("Išsaugota ✅")

                    if wrong:
                        if st.button("💾 Išsaugoti pataisymą", key=f"fb_save_wrong_{i}"):
                            save_feedback(
                                analysis_timestamp=analysis_ts,
                                field=f"mbcad_row_{nr}_{zym}",
                                ai_value=f"{sistema} {plotis}x{aukstis} {spalva}",
                                is_correct=False,
                                comment=comment,
                                corrected_value=comment,
                            )
                            st.success("Pataisymas išsaugotas ✅")

            # ── MBcad redagavimo forma su dropdown'ais ───────────────────────
            st.markdown("---")
            with st.expander("✏️ Redaguoti MBcad lentelę (dropdown'ai kaip MBcad programoje)", expanded=False):
                st.caption("Pataisyk AI sugeneruotus laukus. Paspaudus 'Išsaugoti' — įrašoma į DB ir galima eksportuoti.")

                MBCAD_OPTIONS = {
                    "element_type": [
                        "1) Windows and display windows",
                        "2) Inward opening doors",
                        "3) Outward opening doors",
                        "4) Other doors",
                        "5) Façades",
                        "6) Other",
                    ],
                    "sistema": [
                        "MB-45","MB-59S","MB-60","MB-60US","MB-69V",
                        "MB-70","MB-70US","MB-70HI",
                        "MB-79N","MB-79H","MB-79HI","MB-79N RENO MONO","MB-79N US","MB-79N WW",
                        "MB-80","MB-86","MB-86N","MB-96US",
                        "MB-104","MB-104 Windows",
                        "MB-SR50N","MB-SR50N EFEKT","MB-SR50N HI+",
                        "MB-SLIDE","MB-SLIDER","MB-FOLD LINE","MB-SOFT",
                        "Patikslinti",
                    ],
                    "profilio_variantas": ["ST","HI","N","US","HI+","Nenurodyta"],
                    "spalva_tipas": [
                        "0 raw",
                        "1 C-B - Anodized, natural aluminum",
                        "2 Anodized, colour",
                        "X) RAL - Lacquered, colour",
                        "X) RAL - Lacquered, typical",
                        "X) RAL - Lacquered, untypical",
                        "Y) Bicolour (NRI-E Dial, 3 Inter.)",
                        "Z) Anodized by user - RAL",
                        "Z) Lacquered by user - RAL",
                        "Nenurodyta",
                    ],
                    "spalva_pavirsius": ["MAT","STRUKTURA","SEASIDE","STANDARD","Nenurodyta"],
                    "stiklo_paketas": [
                        "Single glass",
                        "Double glass unit",
                        "Combined two-chamber pane",
                        "Vitrage simple",
                        "Nenurodyta",
                    ],
                    "varstymas": [
                        "Fixed",
                        "Inward opening",
                        "Inward opening tilt-turn",
                        "Outward opening",
                        "Sliding",
                        "Folding",
                        "Nenurodyta",
                    ],
                    "kampų_jungtys": ["Crimped","Pinned","Nenurodyta"],
                    "montavimo_budas": [
                        "No fixing",
                        "Anchors",
                        "Expansion bolts",
                        "Expansion bolts (alternative)",
                        "Concrete screws",
                        "Nenurodyta",
                    ],
                    "slenkscio_juosta": [
                        "Standard strip",
                        "Strips do not require milling",
                        "Nenurodyta",
                    ],
                    "stiklinimo_juosta": [
                        "Standard (rectangular)",
                        "Prestige (rounded)",
                        "Style",
                        "Standard (rectangular, Style gasket)",
                        "Prestige (rounded, Style gaskets)",
                        "Nenurodyta",
                    ],
                    "tarpine_drenazas": ["No drainage","8045501X","8045502X","Nenurodyta"],
                    "tarpine_rebet": ["120454","120523","120523+120524","Nenurodyta"],
                    "tarpine_centrinis": ["120522","120590","Nenurodyta"],
                    "tarpine_slenkscio": ["120757","121592","Nenurodyta"],
                    "furnitura_rankena": [
                        "ALUPROF - Tongue handle CLASSIC",
                        "ALUPROF - Tongue handle PRESTIGE",
                        "ALUPROF - Tongue handle SMART",
                        "ALUPROF - Tongue handle SLIM",
                        "ALUPROF - Push-pull handle",
                        "ALUPROF - Offset handle",
                        "Standard",
                        "Nenurodyta",
                    ],
                    "apsauga_rc": ["No","RC1","RC2","RC3","RC4","Nenurodyta"],
                }

                edited_rows = []
                for i, row in enumerate(mbcad_table):
                    nr = row.get("nr", i + 1)
                    zym = row.get("zymejimas") or f"#{nr}"
                    with st.expander(f"Eilutė {nr}: {zym}", expanded=False):
                        r = dict(row)
                        col_a, col_b = st.columns(2)
                        with col_a:
                            r["zymejimas"] = st.text_input("Žymėjimas", value=str(r.get("zymejimas") or ""), key=f"e_zym_{i}")
                            r["element_type"] = st.selectbox("Elemento tipas", MBCAD_OPTIONS["element_type"],
                                index=_opt_idx(MBCAD_OPTIONS["element_type"], r.get("element_type")), key=f"e_et_{i}")
                            r["sistema"] = st.selectbox("Sistema", MBCAD_OPTIONS["sistema"],
                                index=_opt_idx(MBCAD_OPTIONS["sistema"], r.get("sistema")), key=f"e_sys_{i}")
                            r["profilio_variantas"] = st.selectbox("Profilio variantas", MBCAD_OPTIONS["profilio_variantas"],
                                index=_opt_idx(MBCAD_OPTIONS["profilio_variantas"], r.get("profilio_variantas")), key=f"e_pv_{i}")
                            r["plotis_mm"] = st.number_input("Plotis (mm)", value=int(r.get("plotis_mm") or 0), step=1, key=f"e_w_{i}")
                            r["aukstis_mm"] = st.number_input("Aukštis (mm)", value=int(r.get("aukstis_mm") or 0), step=1, key=f"e_h_{i}")
                            r["kiekis"] = st.number_input("Kiekis", value=int(r.get("kiekis") or 1), step=1, min_value=1, key=f"e_qty_{i}")
                            r["spalva_isorine"] = st.text_input("Spalva išorinė (RAL/kita)", value=str(r.get("spalva_isorine") or ""), key=f"e_co_{i}")
                            r["spalva_tipas"] = st.selectbox("Spalvos tipas", MBCAD_OPTIONS["spalva_tipas"],
                                index=_opt_idx(MBCAD_OPTIONS["spalva_tipas"], r.get("spalva_tipas")), key=f"e_ct_{i}")
                            r["spalva_pavirsius"] = st.selectbox("Paviršius", MBCAD_OPTIONS["spalva_pavirsius"],
                                index=_opt_idx(MBCAD_OPTIONS["spalva_pavirsius"], r.get("spalva_pavirsius")), key=f"e_cp_{i}")
                            r["spalva_vidine"] = st.text_input("Spalva vidinė (RAL/kita)", value=str(r.get("spalva_vidine") or ""), key=f"e_ci_{i}")
                        with col_b:
                            r["stiklo_paketas"] = st.selectbox("Stiklo paketas", MBCAD_OPTIONS["stiklo_paketas"],
                                index=_opt_idx(MBCAD_OPTIONS["stiklo_paketas"], r.get("stiklo_paketas")), key=f"e_gp_{i}")
                            r["stiklo_storis_mm"] = st.number_input("Stiklo storis (mm)", value=int(r.get("stiklo_storis_mm") or 0), step=1, key=f"e_gt_{i}")
                            r["stiklo_kodas"] = st.text_input("Stiklo kodas", value=str(r.get("stiklo_kodas") or ""), key=f"e_gk_{i}")
                            r["stiklo_ug"] = st.number_input("Ug (W/m²K)", value=float(r.get("stiklo_ug") or 0.0), step=0.01, format="%.2f", key=f"e_ug_{i}")
                            r["stiklo_g"] = st.number_input("g (SHGC)", value=float(r.get("stiklo_g") or 0.0), step=0.01, format="%.2f", key=f"e_sg_{i}")
                            r["varstymas"] = st.selectbox("Varstymas", MBCAD_OPTIONS["varstymas"],
                                index=_opt_idx(MBCAD_OPTIONS["varstymas"], r.get("varstymas")), key=f"e_vr_{i}")
                            r["kampų_jungtys"] = st.selectbox("Kampų jungtys", MBCAD_OPTIONS["kampų_jungtys"],
                                index=_opt_idx(MBCAD_OPTIONS["kampų_jungtys"], r.get("kampų_jungtys")), key=f"e_kj_{i}")
                            r["montavimo_budas"] = st.selectbox("Montavimas", MBCAD_OPTIONS["montavimo_budas"],
                                index=_opt_idx(MBCAD_OPTIONS["montavimo_budas"], r.get("montavimo_budas")), key=f"e_mb_{i}")
                            r["slenkscio_juosta"] = st.selectbox("Slenkščio juosta", MBCAD_OPTIONS["slenkscio_juosta"],
                                index=_opt_idx(MBCAD_OPTIONS["slenkscio_juosta"], r.get("slenkscio_juosta")), key=f"e_sj_{i}")
                            r["stiklinimo_juosta"] = st.selectbox("Stiklinimo juosta", MBCAD_OPTIONS["stiklinimo_juosta"],
                                index=_opt_idx(MBCAD_OPTIONS["stiklinimo_juosta"], r.get("stiklinimo_juosta")), key=f"e_stj_{i}")
                            r["tarpine_drenazas"] = st.selectbox("Tarpinė drenažas", MBCAD_OPTIONS["tarpine_drenazas"],
                                index=_opt_idx(MBCAD_OPTIONS["tarpine_drenazas"], r.get("tarpine_drenazas")), key=f"e_td_{i}")
                            r["tarpine_rebet"] = st.selectbox("Tarpinė rebetas", MBCAD_OPTIONS["tarpine_rebet"],
                                index=_opt_idx(MBCAD_OPTIONS["tarpine_rebet"], r.get("tarpine_rebet")), key=f"e_tr_{i}")
                            r["tarpine_centrinis"] = st.selectbox("Tarpinė centrinis", MBCAD_OPTIONS["tarpine_centrinis"],
                                index=_opt_idx(MBCAD_OPTIONS["tarpine_centrinis"], r.get("tarpine_centrinis")), key=f"e_tc_{i}")
                            r["tarpine_slenkscio"] = st.selectbox("Tarpinė slenkstis", MBCAD_OPTIONS["tarpine_slenkscio"],
                                index=_opt_idx(MBCAD_OPTIONS["tarpine_slenkscio"], r.get("tarpine_slenkscio")), key=f"e_ts_{i}")
                            r["furnitura_rankena"] = st.selectbox("Rankena", MBCAD_OPTIONS["furnitura_rankena"],
                                index=_opt_idx(MBCAD_OPTIONS["furnitura_rankena"], r.get("furnitura_rankena")), key=f"e_rk_{i}")
                            r["apsauga_rc"] = st.selectbox("RC apsauga", MBCAD_OPTIONS["apsauga_rc"],
                                index=_opt_idx(MBCAD_OPTIONS["apsauga_rc"], r.get("apsauga_rc")), key=f"e_rc_{i}")
                        r["pastabos"] = st.text_area("Pastabos", value=str(r.get("pastabos") or ""), key=f"e_past_{i}", height=60)
                        edited_rows.append(r)

                if edited_rows and analysis.get("project_id"):
                    if st.button("💾 Išsaugoti pataisytą lentelę į DB", type="primary"):
                        try:
                            resp = requests.put(
                                f"{CRM_URL}/projects/{analysis['project_id']}/mbcad",
                                json={"table": edited_rows},
                                timeout=10,
                            )
                            if resp.ok:
                                st.success("Lentelė išsaugota ✅")
                                st.session_state["analysis"]["mbcad_like_table"] = edited_rows
                            else:
                                st.error(f"Klaida: {resp.text}")
                        except Exception as exc:
                            st.error(str(exc))

                    if analysis.get("project_id"):
                        export_url = f"{CRM_URL}/projects/{analysis['project_id']}/mbcad/export"
                        st.link_button("⬇️ Eksportuoti į Excel (iš DB)", export_url)

        else:
            st.info("MBcad lentelė dar nesugeneruota.")

        # ── Bendras santraukos feedback ───────────────────────────────────────
        st.markdown("---")
        with st.expander("💬 Bendras atsiliepimas apie šią analizę", expanded=False):
            from app.services.storage import save_feedback as _sf
            overall_correct = st.radio(
                "Ar AI santrauka teisinga?",
                ["Taip", "Iš dalies", "Ne"],
                horizontal=True,
                key="overall_fb"
            )
            overall_comment = st.text_area(
                "Komentaras (kas buvo neteisinga, ko trūko)",
                key="overall_fb_comment",
                height=80
            )
            if st.button("💾 Išsaugoti bendrą atsiliepimą", key="overall_fb_save"):
                _sf(
                    analysis_timestamp=analysis_ts,
                    field="summary",
                    ai_value=str(analysis.get("project_summary", ""))[:300],
                    is_correct=(overall_correct == "Taip"),
                    comment=overall_comment,
                    corrected_value="",
                )
                st.success("Ačiū! Atsiliepimas išsaugotas.")

        # MBcad instrukcija
        with st.expander("📋 MBcad įvedimo instrukcija", expanded=False):
            st.markdown("""
**1. Sukurti naują užsakymą**
`Orders → New offer` → įvesti Order name ir Order description

**2. Pridėti konstrukciją**
`Constructions → New construction` → pasirinkti elemento tipą:
- Langai → `1) Windows and display windows`
- Durys į vidų → `2) Inward opening doors`
- Durys į išorę → `3) Outward opening doors`
- Fasadai → `5) Façades`

**3. Pasirinkti sistemą**
Iš sąrašo rinktis pagal projektą, pvz.:
- `MB-79N` — standartiniai langai
- `MB-86N` — langų/durų sistema
- `MB-70` — CASEMENT langai

**4. Construction parameters**
- **Profilio variantas:** ST (standartinis) arba SI
- **Kampų jungtys:** Crimped (standartinis) arba Pined
- **Montavimo būdas:** Anchors / Expansion bolts / Concrete screws
- **Glazing strip:** Standard (rectangular)

**5. Matmenys**
Brėžinių aplinkoje apačioje įvesti: X = plotis (mm), Y = aukštis (mm)

**6. Spalva**
`System → Colours list` — pasirinkti RAL spalvą arba išorinę/vidinę atskirai

**7. Stiklo paketas**
`Fillings` meniu — pasirinkti stiklo paketą pagal šiluminius reikalavimus

**8. Kiekis**
Užsakymo lentelėje stulpelyje `Qua...` įvesti kiekį

**9. Kalkuliacija**
`Calculations → Recalculate the offer` → patikrinti sumą
""")

    # Brėžinių peržiūra
    selected_pages = analysis.get("selected_pages", [])
    rendered_images = analysis.get("rendered_images", [])
    overlay_images = analysis.get("overlay_images", [])

    if rendered_images or overlay_images:
        st.subheader("Brėžinių peržiūra")
        images_to_show = overlay_images if overlay_images else rendered_images
        cols = st.columns(2)
        for index, image_path in enumerate(images_to_show):
            if image_path and os.path.exists(image_path):
                with cols[index % 2]:
                    st.image(image_path, caption=image_path, use_container_width=True)

    if selected_pages:
        with st.expander("Atrinkti PDF puslapiai"):
            st.dataframe(pd.DataFrame(selected_pages), use_container_width=True)

    st.subheader("Atsakymo klientui juodraštis")
    draft = (
        analysis.get("client_reply_draft")
        or analysis.get("reply_draft")
        or ""
    )
    st.text_area("Juodraštis", value=draft, height=180)

    with st.expander("Pilnas JSON rezultatas"):
        st.json(analysis)


# ═════════════════════════════════════════════════════════════════════════════
# REŽIMŲ LOGIKA
# ═════════════════════════════════════════════════════════════════════════════

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
                analysis_obj = data.get("analysis", data)
                if data.get("project_id") and isinstance(analysis_obj, dict):
                    analysis_obj["project_id"] = data["project_id"]
                st.session_state.analysis = analysis_obj
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


elif mode == "Outlook laiškai":
    st.header("Outlook laiškų importas ir analizė")

    st.info(
        "Šis režimas naudoja Microsoft Graph prisijungimą prie Outlook pašto ir leidžia importuoti laiškus su prisegtais failais."
    )

    col1, col2 = st.columns([1, 1])

    with col1:
        limit = st.number_input(
            "Kiek laiškų peržiūrėti",
            min_value=1,
            max_value=100,
            value=20
        )

    with col2:
        only_with_attachments = st.checkbox(
            "Rodyti tik su prisegtais failais",
            value=True
        )

    if st.button("Gauti Outlook laiškus", use_container_width=True):
        with st.spinner("Jungiama prie Outlook ir gaunami laiškai..."):
            response = requests.get(
                f"{BASE_URL}/automation/emails/preview",
                params={
                    "limit": limit,
                    "mailbox": "Inbox",
                    "query": "",
                    "only_with_attachments": only_with_attachments
                },
                timeout=120,
            )

        if response.status_code != 200:
            st.error("Nepavyko gauti Outlook laiškų")
            st.code(response.text)
        else:
            data = response.json()
            st.session_state.outlook_messages = data.get("emails", [])
            st.success(f"Gauta laiškų: {len(st.session_state.outlook_messages)}")

    messages = st.session_state.outlook_messages

    if messages:
        st.subheader("Pasirink laiškus analizei")

        selected_ids = []

        for msg in messages:
            uid = msg.get("uid")
            date = msg.get("date", "")
            sender = msg.get("from", "")
            subject = msg.get("subject", "")
            snippet = msg.get("snippet", "")
            attachments = msg.get("attachments", [])

            label = f"{date} | {sender} | {subject}"

            checked = st.checkbox(label, key=f"msg_{uid}")

            with st.expander(f"Laiško peržiūra: {subject}"):
                st.write("Nuo:", sender)
                st.write("Data:", date)
                st.write("Turi attachmentų:", bool(attachments))
                st.write("Prisegti failai:")

                if attachments:
                    st.dataframe(pd.DataFrame(attachments), use_container_width=True)
                else:
                    st.info("Prisegtų failų nėra.")

                st.write("Laiško tekstas:")
                st.write(snippet)

            if checked:
                selected_ids.append(uid)

        if selected_ids:
            st.success(f"Pasirinkta laiškų: {len(selected_ids)}")

        if st.button("Importuoti pasirinktus laiškus", use_container_width=True):
            with st.spinner("Importuojami laiškai ir attachmentai..."):
                response = requests.post(
                    f"{BASE_URL}/automation/emails/import-selected",
                    json={
                        "uids": selected_ids,
                        "mailbox": "Inbox"
                    },
                    timeout=300,
                )

            if response.status_code != 200:
                st.error("Importo klaida")
                st.code(response.text)
            else:
                data = response.json()
                st.session_state.imported_projects = data.get("projects", [])
                st.success(
                    f"Importuota: {data.get('imported', 0)}, praleista: {data.get('skipped', 0)}"
                )

        if st.session_state.imported_projects:
            st.subheader("Importuoti laiškai / projektai")

            rows = []

            for project in st.session_state.imported_projects:
                files = project.get("files", [])
                rows.append({
                    "project_id": project.get("project_id"),
                    "uid": project.get("uid"),
                    "subject": project.get("subject"),
                    "from": project.get("from"),
                    "files": len(files)
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
                    files = project.get("files", [])

                    for file_info in files:
                        path = file_info.get("path")
                        filename = file_info.get("filename", "attachment.pdf")

                        if not path or not path.lower().endswith(".pdf"):
                            continue

                        if not os.path.exists(path):
                            st.warning(f"Failas nerastas: {path}")
                            continue

                        with open(path, "rb") as f:
                            file_bytes = f.read()

                        with st.spinner(f"Analizuojamas PDF: {filename}"):
                            response = requests.post(
                                f"{BASE_URL}/automation/pdf/analyze-selected-pages",
                                files={
                                    "file": (
                                        filename,
                                        file_bytes,
                                        "application/pdf"
                                    )
                                },
                                timeout=500,
                            )

                        if response.status_code != 200:
                            st.error(f"Klaida analizuojant {filename}")
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
                            "filename": filename,
                            "path": path
                        })

                st.session_state.analysis = combined
                st.session_state.files_processed = processed_files

                st.success("Importuotų laiškų PDF analizė baigta.")

            show_analysis_result(
                st.session_state.analysis,
                st.session_state.files_processed
            )


elif mode == "CRM":
    st.header("CRM — klientų valdymas")

    # ── Migracijos mygtukas ───────────────────────────────────────────────────
    with st.expander("⚙️ Duomenų bazės įrankiai", expanded=False):
        col_m1, col_m2 = st.columns(2)
        with col_m1:
            if st.button("🔗 Susieti senus projektus su klientais", use_container_width=True):
                try:
                    from app.services.project_db import migrate_orphan_projects
                    fixed = migrate_orphan_projects()
                    st.success(f"Pataisyta projektų: {fixed}")
                    st.rerun()
                except Exception as e:
                    st.error(f"Klaida: {e}")
        with col_m2:
            st.caption("Naudok vieną kartą jei matai Klientai = 0 bet projektai egzistuoja.")

    # ── Statistikos juosta ────────────────────────────────────────────────────
    try:
        r = requests.get(f"{CRM_URL}/stats", timeout=10)
        if r.status_code == 200:
            s = r.json()
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("👥 Klientai", s.get("total_clients", 0))
            c2.metric("📋 Projektai", s.get("total_projects", 0))
            c3.metric("🆕 Naujos", s.get("new_projects", 0))
            c4.metric("🔴 Skubūs", s.get("high_urgency_projects", 0))
    except Exception:
        st.warning("Statistikos nepavyko gauti.")

    st.markdown("---")

    # ── Eksportas ─────────────────────────────────────────────────────────────
    with st.expander("📥 Eksportuoti duomenis į Excel / CSV", expanded=False):
        try:
            from app.services.project_db import export_clients_df, export_projects_df
            import io

            ecol1, ecol2 = st.columns(2)

            with ecol1:
                df_clients = export_clients_df()
                if not df_clients.empty:
                    buf = io.BytesIO()
                    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
                        df_clients.to_excel(writer, index=False, sheet_name="Klientai")
                    st.download_button(
                        "⬇️ Klientai (.xlsx)",
                        data=buf.getvalue(),
                        file_name="crm_klientai.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True
                    )
                else:
                    st.info("Klientų dar nėra.")

            with ecol2:
                df_projects = export_projects_df()
                if not df_projects.empty:
                    buf2 = io.BytesIO()
                    with pd.ExcelWriter(buf2, engine="openpyxl") as writer:
                        df_projects.to_excel(writer, index=False, sheet_name="Projektai")
                    st.download_button(
                        "⬇️ Projektai (.xlsx)",
                        data=buf2.getvalue(),
                        file_name="crm_projektai.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True
                    )
                else:
                    st.info("Projektų dar nėra.")
        except Exception as e:
            st.error(f"Eksporto klaida: {e}")

    st.markdown("---")

    # ── Paieška ir filtrai ────────────────────────────────────────────────────
    search_col, filter_col = st.columns([3, 1])
    with search_col:
        crm_search = st.text_input("🔍 Paieška (email, vardas, įmonė, miestas)", key="crm_search_main")
    with filter_col:
        crm_seg_filter = st.selectbox(
            "Segmentas",
            ["— visi —", "reguliarus", "vienkartinis", "naujas", "neaktyvus"],
            key="crm_seg_filter"
        )

    # ── Klientų sąrašas ───────────────────────────────────────────────────────
    SEGMENT_ICONS = {"reguliarus": "🟢", "vienkartinis": "🔵", "naujas": "⚪", "neaktyvus": "🔴"}
    URGENCY_ICONS = {"high": "🔴", "medium": "🟡", "low": "🟢"}
    STATUS_LT = {
        "new": "Nauja", "in_progress": "Vykdoma", "waiting_info": "Laukiama info",
        "offer_sent": "Pasiūlymas išsiųstas", "done": "Atlikta", "cancelled": "Atšaukta"
    }

    try:
        r = requests.get(f"{CRM_URL}/clients", params={"search": crm_search, "limit": 200}, timeout=10)
        all_clients = r.json().get("clients", []) if r.status_code == 200 else []
    except Exception:
        all_clients = []

    if crm_seg_filter != "— visi —":
        all_clients = [c for c in all_clients if c.get("ai_segment") == crm_seg_filter]

    # Session state: pasirinktas klientas
    if "selected_client_id" not in st.session_state:
        st.session_state.selected_client_id = None

    # ── Split layout: kairė = lentelė, dešinė = kortelė ──────────────────────
    left_col, right_col = st.columns([2, 3])

    with left_col:
        st.subheader(f"Klientai ({len(all_clients)})")

        if not all_clients:
            st.info("Klientų nerasta. Importuok laiškus arba pridėk rankiniu būdu.")
        else:
            for c in all_clients:
                seg = c.get("ai_segment") or "naujas"
                icon = SEGMENT_ICONS.get(seg, "⚪")

                # Gauti paskutinį projektą
                last_proj = ""
                proj_count = 0
                try:
                    rp = requests.get(f"{CRM_URL}/clients/{c['id']}/projects", timeout=5)
                    if rp.status_code == 200:
                        projs = rp.json().get("projects", [])
                        proj_count = len(projs)
                        if projs:
                            last_proj = (projs[0].get("created_at") or "")[:10]
                except Exception:
                    pass

                is_selected = st.session_state.selected_client_id == c["id"]
                btn_label = (
                    f"{icon} **{c.get('email')}**\n"
                    f"{c.get('company') or ''} · {proj_count} proj. · {last_proj}"
                )

                if st.button(
                    btn_label,
                    key=f"client_btn_{c['id']}",
                    use_container_width=True,
                    type="primary" if is_selected else "secondary"
                ):
                    st.session_state.selected_client_id = c["id"]
                    st.rerun()

        st.markdown("---")

        # Naujo kliento forma
        with st.expander("➕ Pridėti klientą rankiniu būdu"):
            with st.form("crm_add_client_form"):
                new_email = st.text_input("Email *")
                new_name = st.text_input("Vardas / Pavardė")
                new_company = st.text_input("Įmonė")
                new_phone = st.text_input("Telefonas")
                new_city = st.text_input("Miestas")
                new_notes = st.text_area("Pastabos")
                add_submitted = st.form_submit_button("Sukurti klientą")

            if add_submitted:
                if not new_email:
                    st.error("Email yra privalomas.")
                else:
                    try:
                        r = requests.post(f"{CRM_URL}/clients", json={
                            "email": new_email, "name": new_name,
                            "company": new_company, "phone": new_phone,
                            "city": new_city, "notes": new_notes
                        }, timeout=10)
                        if r.status_code == 200:
                            st.success(f"Sukurta. ID: {r.json().get('client_id')}")
                            st.rerun()
                        elif r.status_code == 409:
                            st.warning(r.json().get("detail"))
                        else:
                            st.error("Klaida kuriant klientą.")
                    except Exception as e:
                        st.error(f"Klaida: {e}")

    # ── Dešinė pusė: kliento kortelė ─────────────────────────────────────────
    with right_col:
        if not st.session_state.selected_client_id:
            st.info("👈 Pasirink klientą iš sąrašo kairėje.")
        else:
            cid = st.session_state.selected_client_id
            try:
                r = requests.get(f"{CRM_URL}/clients/{cid}", timeout=10)
                if r.status_code == 404:
                    st.error("Klientas nerastas.")
                    st.session_state.selected_client_id = None
                elif r.status_code == 200:
                    data = r.json()
                    c = data["client"]
                    projects = data.get("projects", [])
                    interactions = data.get("interactions", [])

                    # Antraštė
                    seg = c.get("ai_segment") or "naujas"
                    seg_icon = SEGMENT_ICONS.get(seg, "⚪")
                    st.subheader(f"{c.get('email')}")

                    info1, info2, info3 = st.columns(3)
                    info1.write(f"**Vardas:** {c.get('name') or '—'}")
                    info2.write(f"**Įmonė:** {c.get('company') or '—'}")
                    info3.write(f"**Miestas:** {c.get('city') or '—'}")

                    seg_col, phone_col, status_col = st.columns(3)
                    seg_col.write(f"**Segmentas:** {seg_icon} {seg}")
                    phone_col.write(f"**Tel.:** {c.get('phone') or '—'}")
                    status_col.write(f"**Statusas:** {c.get('status', 'active')}")

                    if c.get("ai_segment_reason"):
                        st.caption(f"AI: {c['ai_segment_reason']}")

                    if c.get("notes"):
                        st.info(f"📝 {c['notes']}")

                    # Veiksmai
                    act1, act2, act3 = st.columns(3)
                    with act1:
                        if st.button("🤖 Perskaičiuoti segmentą", key="reseg", use_container_width=True):
                            r2 = requests.post(f"{CRM_URL}/clients/{cid}/ai-segment", timeout=30)
                            if r2.status_code == 200:
                                res = r2.json()
                                st.success(f"{res.get('ai_segment')} — {res.get('reason')}")
                                st.rerun()
                    with act2:
                        new_status_val = st.selectbox(
                            "Statusas",
                            ["active", "inactive"],
                            index=0 if c.get("status") == "active" else 1,
                            key="client_status_sel"
                        )
                        if st.button("💾 Išsaugoti", key="save_status", use_container_width=True):
                            requests.put(f"{CRM_URL}/clients/{cid}", json={"status": new_status_val}, timeout=10)
                            st.rerun()
                    with act3:
                        if st.button("🗑️ Ištrinti klientą", key="del_client", use_container_width=True, type="secondary"):
                            st.session_state[f"confirm_delete_{cid}"] = True

                    if st.session_state.get(f"confirm_delete_{cid}"):
                        st.warning("⚠️ Ar tikrai nori ištrinti šį klientą? Visi jo projektai liks DB.")
                        dc1, dc2 = st.columns(2)
                        with dc1:
                            if st.button("✅ Taip, ištrinti", key="confirm_del_yes"):
                                try:
                                    from app.services.project_db import get_conn as _gc, now as _now
                                    with _gc() as conn:
                                        conn.execute("DELETE FROM clients WHERE id=?", (cid,))
                                    st.session_state.selected_client_id = None
                                    st.success("Klientas ištrintas.")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Klaida: {e}")
                        with dc2:
                            if st.button("❌ Atšaukti", key="confirm_del_no"):
                                st.session_state[f"confirm_delete_{cid}"] = False
                                st.rerun()

                    st.markdown("---")

                    # Projektų skirtukas + kontaktų timeline
                    ptab, itab, edittab = st.tabs(["📋 Projektai", "📅 Kontaktų istorija", "✏️ Redaguoti"])

                    with ptab:
                        st.write(f"**Iš viso projektų: {data.get('projects_count', 0)}**")
                        if projects:
                            for p in projects:
                                urgency = p.get("ai_urgency") or "medium"
                                u_icon = URGENCY_ICONS.get(urgency, "🟡")
                                status_lt = STATUS_LT.get(p.get("status", ""), p.get("status", ""))
                                cls = p.get("ai_classification") or "—"

                                with st.container(border=True):
                                    pc1, pc2 = st.columns([3, 1])
                                    with pc1:
                                        st.write(f"**#{p['id']}** {p.get('subject') or '—'}")
                                        st.caption(f"{cls} · {(p.get('created_at') or '')[:10]}")
                                    with pc2:
                                        st.write(f"{u_icon} {urgency}")
                                        st.caption(status_lt)

                                    # Statuso keitimas
                                    ps1, ps2 = st.columns([2, 1])
                                    with ps1:
                                        new_p_status = st.selectbox(
                                            "Statusas",
                                            list(STATUS_LT.keys()),
                                            index=list(STATUS_LT.keys()).index(p.get("status", "new")) if p.get("status") in STATUS_LT else 0,
                                            format_func=lambda x: STATUS_LT.get(x, x),
                                            key=f"pstatus_{p['id']}"
                                        )
                                    with ps2:
                                        if st.button("Išsaugoti", key=f"psave_{p['id']}", use_container_width=True):
                                            requests.put(
                                                f"{CRM_URL}/projects/{p['id']}/status",
                                                json={"status": new_p_status},
                                                timeout=10
                                            )
                                            st.rerun()

                                    if p.get("ai_classification_reason"):
                                        st.caption(f"AI: {p['ai_classification_reason']}")
                        else:
                            st.info("Šis klientas dar neturi projektų.")

                    with itab:
                        st.write(f"**Kontaktų: {data.get('interactions_count', 0)}**")

                        # Naujo kontakto forma
                        with st.expander("➕ Pridėti kontaktą"):
                            with st.form(f"add_inter_{cid}"):
                                inter_type = st.selectbox("Tipas", ["email", "skambutis", "susitikimas", "pastaba", "kita"])
                                inter_dir = st.radio("Kryptis", ["inbound", "outbound"], horizontal=True)
                                inter_summary = st.text_area("Aprašymas")
                                inter_submit = st.form_submit_button("Išsaugoti")
                            if inter_submit:
                                requests.post(
                                    f"{CRM_URL}/clients/{cid}/interactions",
                                    json={"type": inter_type, "summary": inter_summary, "direction": inter_dir},
                                    timeout=10
                                )
                                st.rerun()

                        # Timeline
                        if interactions:
                            for inter in interactions:
                                itype = inter.get("type", "")
                                idir = inter.get("direction", "inbound")
                                idate = (inter.get("created_at") or "")[:16].replace("T", " ")
                                isummary = inter.get("summary") or ""
                                isentiment = inter.get("ai_sentiment") or ""

                                dir_icon = "📨" if idir == "inbound" else "📤"
                                type_icons = {
                                    "email": "✉️", "skambutis": "📞",
                                    "susitikimas": "🤝", "pastaba": "📝",
                                    "ai_classification": "🤖", "kita": "💬"
                                }
                                t_icon = type_icons.get(itype, "💬")

                                with st.container(border=True):
                                    ic1, ic2 = st.columns([4, 1])
                                    with ic1:
                                        st.write(f"{t_icon} {dir_icon} **{itype}** — {idate}")
                                        if isummary:
                                            st.caption(isummary[:200])
                                    with ic2:
                                        if isentiment:
                                            st.caption(isentiment)
                        else:
                            st.info("Kontaktų istorija tuščia.")

                    with edittab:
                        with st.form(f"edit_client_{cid}"):
                            e_name = st.text_input("Vardas", value=c.get("name") or "")
                            e_company = st.text_input("Įmonė", value=c.get("company") or "")
                            e_phone = st.text_input("Telefonas", value=c.get("phone") or "")
                            e_city = st.text_input("Miestas", value=c.get("city") or "")
                            e_notes = st.text_area("Pastabos", value=c.get("notes") or "")
                            edit_submit = st.form_submit_button("💾 Išsaugoti pakeitimus")

                        if edit_submit:
                            requests.put(f"{CRM_URL}/clients/{cid}", json={
                                "name": e_name, "company": e_company,
                                "phone": e_phone, "city": e_city, "notes": e_notes
                            }, timeout=10)
                            st.success("Išsaugota.")
                            st.rerun()

            except Exception as e:
                st.error(f"Klaida kraunant kliento kortelę: {e}")