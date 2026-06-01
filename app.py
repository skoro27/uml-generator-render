import streamlit as st
import os
import time

from config import PUML_FILE, GROQ_API_KEY
from generator import generate_puml
from renderer import run_plantuml
from evaluation import evaluate_puml
from sql_generator import generate_sql_from_puml

# Provjera API ključa na samom početku
if not GROQ_API_KEY:
    st.error("🚨 **GROQ_API_KEY nije podešen!**")
    st.info("""
    Da bi aplikacija radila, potrebno je dodati API ključ:
    
    1. Idite na **Settings** tab
    2. Skrolujte do **Repository Secrets**
    3. Dodajte `GROQ_API_KEY` sa vrednošću vašeg Groq API ključa
    4. Restartujte aplikaciju
    """)
    st.stop()

st.set_page_config(
    page_title="LLM PlantUML Generator",
    layout="wide",
    page_icon="📊"
)

st.title("📊 LLM PlantUML Generator")
st.caption("BAZE PODATAKA II ciklus [Slaviša Škorić]")
st.write("Generisanje PlantUML dijagrama klasa pomoću Groq API-ja (Qwen3-32B).")

description = st.text_area(
    "Unesite opis sistema:",
    height=260,
    placeholder="Npr: Sistem za upravljanje bibliotekom ima klase Knjiga, Član, Pozajmica..."
)

if st.button("✨ Generiši dijagram", type="primary"):

    if not description.strip():
        st.warning("⚠️ Unesite opis sistema.")
        st.stop()

    try:
        # Kreiraj placeholdere za progress
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        # Korak 1: Generisanje PlantUML koda (0-40%)
        status_text.text("🧠 Generisanje PlantUML koda...")
        for i in range(1, 6):
            progress_bar.progress(i * 4)
            time.sleep(0.1)
        
        puml = generate_puml(description)
        progress_bar.progress(30)
        
        # Korak 2: Sanitizacija (30-40%)
        status_text.text("🔧 Sanitizacija i optimizacija PlantUML koda...")
        for i in range(6, 9):
            progress_bar.progress(i * 5)
            time.sleep(0.1)
        
        PUML_FILE.write_text(puml, encoding="utf-8")
        progress_bar.progress(40)
        
        # Korak 3: Renderovanje (40-70%)
        status_text.text("🎨 Renderovanje dijagrama u PNG...")
        for i in range(8, 13):
            progress_bar.progress(i * 5)
            time.sleep(0.1)
        
        code, err = run_plantuml(PUML_FILE)
        progress_bar.progress(70)

        if code != 0:
            progress_bar.empty()
            status_text.empty()
            st.error("❌ PlantUML render nije uspio.")
            st.code(err, language="text")
            
            with st.expander("🔍 Generisani PlantUML kod (sadrži greške)"):
                st.code(puml, language="text")
            st.stop()

        png_path = PUML_FILE.with_suffix(".png")
        
        # Korak 4: SQL generisanje (70-85%)
        status_text.text("🗄️ Generisanje SQL koda za kreiranje baze...")
        for i in range(14, 17):
            progress_bar.progress(i * 5)
            time.sleep(0.1)
        
        sql_code = generate_sql_from_puml(puml)
        progress_bar.progress(85)
        
        # Korak 5: Evaluacija (85-100%)
        status_text.text("📊 Evaluacija generisanog modela...")
        for i in range(17, 21):
            progress_bar.progress(i * 5)
            time.sleep(0.1)
        
        evaluation = evaluate_puml(puml, True)
        progress_bar.progress(100)
        status_text.text("✅ Generisanje završeno!")
        time.sleep(0.5)
        
        # Očisti progress
        progress_bar.empty()
        status_text.empty()

        # Dijagram i evaluacija
        col1, col2 = st.columns([2, 1])

        with col1:
            st.subheader("📊 Generisani dijagram")
            if png_path.exists():
                st.image(str(png_path), use_column_width=True)
            else:
                st.error("PNG fajl nije kreiran.")

        with col2:
            st.subheader("📈 Evaluacija")
            st.json(evaluation)

        st.divider()

        # PlantUML i SQL kod jedan pored drugog
        col_code1, col_code2 = st.columns(2)

        with col_code1:
            st.subheader("📝 PlantUML kod")
            st.code(puml, language="text")

        with col_code2:
            st.subheader("🗄️ SQL kod")
            st.code(sql_code, language="sql")

        # Download dugmići
        st.divider()
        col_dl1, col_dl2, col_dl3 = st.columns(3)
        
        with col_dl1:
            if png_path.exists():
                with open(png_path, "rb") as f:
                    st.download_button(
                        label="🖼️ Preuzmi PNG",
                        data=f,
                        file_name="model.png",
                        mime="image/png",
                        use_container_width=True
                    )

        with col_dl2:
            st.download_button(
                label="📄 Preuzmi PlantUML",
                data=puml,
                file_name="model.puml",
                mime="text/plain",
                use_container_width=True
            )

        with col_dl3:
            st.download_button(
                label="📥 Preuzmi SQL",
                data=sql_code,
                file_name="schema.sql",
                mime="text/plain",
                use_container_width=True
            )

    except Exception as e:
        st.error(f"💥 Došlo je do greške: {str(e)}")
        
        with st.expander("🔧 Detalji greške (za debagovanje)"):
            import traceback
            st.code(traceback.format_exc(), language="text")
