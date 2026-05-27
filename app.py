import streamlit as st
import os

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
        with st.spinner("🧠 Generišem PlantUML model... Ovo može potrajati 10-20 sekundi."):
            # Generiši PlantUML kod
            puml = generate_puml(description)

            # Sačuvaj u fajl (potrebno za renderer)
            PUML_FILE.write_text(puml, encoding="utf-8")

            # Renderuj u PNG
            code, err = run_plantuml(PUML_FILE)

            if code != 0:
                st.error("❌ PlantUML render nije uspio.")
                st.code(err, language="text")
                
                with st.expander("🔍 Generisani PlantUML kod (sadrži greške)"):
                    st.code(puml, language="text")
                st.stop()

            # Putanja do PNG fajla
            png_path = PUML_FILE.with_suffix(".png")
            
            # Evaluacija
            evaluation = evaluate_puml(puml, True)
            
            # Generiši SQL
            sql_code = generate_sql_from_puml(puml)

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