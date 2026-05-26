import streamlit as st

from config import PUML_FILE
from generator import generate_puml
from renderer import run_plantuml
from evaluation import evaluate_puml

st.set_page_config(
    page_title="LLM PlantUML Generator",
    layout="wide"
)

st.title("LLM PlantUML Generator")
st.write("BAZE PODATAKA II ciklus")
st.write("Generisanje PlantUML dijagrama klasa pomocu Groq API-ja.")

description = st.text_area(
    "Unesite opis sistema:",
    height=260
)

if st.button("Generisi dijagram"):

    if not description.strip():
        st.warning("Unesite opis sistema.")
        st.stop()

    try:
        with st.spinner("Generisem PlantUML model..."):
            puml = generate_puml(description)

            PUML_FILE.write_text(puml, encoding="utf-8")

            code, err = run_plantuml(PUML_FILE)

            if code != 0:
                st.error("PlantUML render nije uspio.")
                st.code(err)
                st.stop()

            png_path = PUML_FILE.with_suffix(".png")
            evaluation = evaluate_puml(puml, True)

        col1, col2 = st.columns([2, 1])

        with col1:
            st.subheader("Generisani dijagram")
            st.image(str(png_path))

        with col2:
            st.subheader("Evaluacija")
            st.json(evaluation)

        st.subheader("PlantUML kod")
        st.code(puml, language="text")

        with open(png_path, "rb") as f:
            st.download_button(
                label="Preuzmi PNG dijagram",
                data=f,
                file_name="model.png",
                mime="image/png"
            )

        st.download_button(
            label="Preuzmi PlantUML kod",
            data=puml,
            file_name="model.puml",
            mime="text/plain"
        )

    except Exception as e:
        st.error(str(e))