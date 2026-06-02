import streamlit as st
import os
import time
import re
from io import BytesIO
from fpdf import FPDF
import pandas as pd

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

# ========== SIDEBAR: Rečnik pojmova ==========
with st.sidebar:
    st.markdown("## 📚 Rečnik pojmova")
    with st.expander("📦 Klasa (Class)"):
        st.write("Entitet u sistemu. U bazi postaje **tabela**.")
    with st.expander("🔑 PK (Primarni ključ)"):
        st.write("Jedinstveni identifikator. Označava se sa `{PK}`.")
    with st.expander("🧬 Generalizacija"):
        st.write("Nasleđivanje: `Dete --|> Roditelj`")
    with st.expander("🔗 Asocijacija"):
        st.write("Veza između klasa: `KlasaA -- KlasaB`")
    with st.expander("🔢 Multiplikativnost"):
        st.write("""
        - `1` = tačno jedan
        - `0..*` = nula ili više
        - `1..*` = bar jedan
        """)
    with st.expander("🟢🟡🔴 Semafor"):
        st.write("Vizuelna ocena: zeleno = dobro, žuto = prosečno, crveno = loše")
    st.divider()
    st.caption("📌 v2.0 | Groq API | Qwen3-32B")

description = st.text_area(
    "Unesite opis sistema:",
    height=260,
    placeholder="Npr: Sistem za upravljanje bibliotekom ima klase Knjiga, Član, Pozajmica..."
)


def parsiraj_klase_i_atribute(puml_kod):
    """Izvlači imena klasa i njihove atribute iz PlantUML koda."""
    klase_atributi = []
    current_class = None
    in_class = False
    nasledjivanja = {}
    
    for line in puml_kod.splitlines():
        inh_match = re.match(r'^\s*(\w+)\s*--\|>\s*(\w+)', line)
        if inh_match:
            nasledjivanja[inh_match.group(1)] = inh_match.group(2)
    
    for line in puml_kod.splitlines():
        s = line.strip()
        match = re.match(r'^\s*(class|interface|enum)\s+(\w+)\s*\{', line)
        if match:
            if current_class:
                klase_atributi.append(current_class)
            current_class = {
                "name": match.group(2),
                "parent": nasledjivanja.get(match.group(2)),
                "attributes": []
            }
            in_class = True
            continue
        if in_class and s == "}":
            if current_class:
                klase_atributi.append(current_class)
            current_class = None
            in_class = False
            continue
        if in_class and current_class is not None:
            attr_match = re.match(r'^\s*(\{PK\}\s*)?(\w+)\s*:\s*(\w+)', s)
            if attr_match:
                current_class["attributes"].append({
                    "name": attr_match.group(2),
                    "type": attr_match.group(3),
                    "is_pk": attr_match.group(1) is not None
                })
    
    if current_class:
        klase_atributi.append(current_class)
    
    return klase_atributi


def parsiraj_relacije(puml_kod):
    """Izvlači sve relacije iz PlantUML koda."""
    relacije_lista = []
    for line in puml_kod.splitlines():
        s = line.strip()
        if "--|>" in s:
            relacije_lista.append({"tip": "Generalizacija", "tekst": s})
        elif "--" in s and "--|>" not in s:
            relacije_lista.append({"tip": "Asocijacija", "tekst": s})
    return relacije_lista


def generisi_pdf(opis, puml_kod, sql_kod, evaluacija, png_path):
    """Generiše PDF izveštaj sa svim rezultatima."""
    pdf = FPDF()
    pdf.add_page()
    pdf.add_font("DejaVu", "", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", uni=True)
    pdf.add_font("DejaVu", "B", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", uni=True)

    pdf.set_font("DejaVu", "B", 14)
    pdf.cell(0, 10, "UML Class Diagram Generator - Izvestaj", ln=True, align="C")
    pdf.ln(5)

    pdf.set_font("DejaVu", "B", 11)
    pdf.cell(0, 8, "1. Opis sistema", ln=True)
    pdf.set_font("DejaVu", "", 9)
    pdf.multi_cell(0, 5, opis)
    pdf.ln(5)

    if png_path and png_path.exists():
        pdf.set_font("DejaVu", "B", 11)
        pdf.cell(0, 8, "2. UML Class dijagram", ln=True)
        pdf.image(str(png_path), x=10, w=190)
        pdf.ln(5)

    pdf.set_font("DejaVu", "B", 11)
    pdf.cell(0, 8, "3. PlantUML kod", ln=True)
    pdf.set_font("Courier", "", 7)
    for line in puml_kod.split('\n'):
        clean_line = line.encode('ascii', 'ignore').decode('ascii')
        pdf.cell(0, 4, clean_line[:120], ln=True)
    pdf.ln(5)

    pdf.set_font("DejaVu", "B", 11)
    pdf.cell(0, 8, "4. SQL kod za kreiranje baze", ln=True)
    pdf.set_font("Courier", "", 7)
    for line in sql_kod.split('\n'):
        clean_line = line.encode('ascii', 'ignore').decode('ascii')
        pdf.cell(0, 4, clean_line[:120], ln=True)
    pdf.ln(5)

    pdf.set_font("DejaVu", "B", 11)
    pdf.cell(0, 8, "5. Evaluacija modela", ln=True)
    pdf.set_font("DejaVu", "", 9)
    for key, value in evaluacija.items():
        clean_key = str(key).encode('ascii', 'ignore').decode('ascii')
        clean_value = str(value).encode('ascii', 'ignore').decode('ascii')
        pdf.cell(0, 6, f"{clean_key}: {clean_value}", ln=True)

    return pdf.output(dest='S').encode('latin-1')


# Brojač generisanja
if "visits" not in st.session_state:
    st.session_state.visits = 1
else:
    st.session_state.visits += 1


if st.button("✨ Generiši dijagram", type="primary"):

    if not description.strip():
        st.warning("⚠️ Unesite opis sistema.")
        st.stop()

    try:
        start_time = time.time()
        
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        status_text.text("🧠 Generisanje PlantUML koda...")
        for i in range(1, 6): progress_bar.progress(i * 4); time.sleep(0.1)
        
        puml = generate_puml(description)
        progress_bar.progress(30)
        
        status_text.text("🔧 Sanitizacija PlantUML koda...")
        for i in range(6, 9): progress_bar.progress(i * 5); time.sleep(0.1)
        
        PUML_FILE.write_text(puml, encoding="utf-8")
        progress_bar.progress(40)
        
        status_text.text("🎨 Renderovanje dijagrama...")
        for i in range(8, 13): progress_bar.progress(i * 5); time.sleep(0.1)
        
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
        
        status_text.text("🗄️ Generisanje SQL koda...")
        for i in range(14, 17): progress_bar.progress(i * 5); time.sleep(0.1)
        
        sql_code = generate_sql_from_puml(puml)
        progress_bar.progress(85)
        
        status_text.text("📊 Evaluacija modela...")
        for i in range(17, 21): progress_bar.progress(i * 5); time.sleep(0.1)
        
        evaluation = evaluate_puml(puml, True)
        progress_bar.progress(100)
        status_text.text("✅ Generisanje završeno!")
        time.sleep(0.3)
        
        elapsed = time.time() - start_time
        progress_bar.empty()
        status_text.empty()

        col1, col2 = st.columns([2, 1])

        with col1:
            st.subheader("📊 Generisani dijagram")
            if png_path.exists():
                st.image(str(png_path), use_container_width=True)
            else:
                st.error("PNG fajl nije kreiran.")

        with col2:
            st.subheader("📈 Evaluacija")
            
            def semafor(vrednost, dobro, lose):
                if vrednost >= dobro: return "🟢"
                elif vrednost >= lose: return "🟡"
                else: return "🔴"
            
            klase = evaluation.get("class_count", 0)
            relacije = evaluation.get("relation_count", 0)
            nasledjivanje = evaluation.get("inheritance_count", 0)
            jedan_jedan = evaluation.get("one_to_one_count", 0)
            jedan_vise = evaluation.get("one_to_many_count", 0)
            vise_vise = evaluation.get("many_to_many_count", 0)
            nazivi = evaluation.get("association_with_name", 0)
            atributi = evaluation.get("attribute_count", 0)
            
            klase_atributi = parsiraj_klase_i_atribute(puml)
            relacije_lista = parsiraj_relacije(puml)
            
            st.markdown("### 📊 Metrike modela")
            st.markdown(f"""
            <table style="width:100%; font-size:13px;">
                <tr><td>🏗️ Broj klasa</td><td><b>{klase}</b></td><td>{semafor(klase,5,2)}</td></tr>
                <tr><td>📋 Broj atributa</td><td><b>{atributi}</b></td><td>{semafor(atributi,15,5)}</td></tr>
                <tr><td>🔗 Ukupno relacija</td><td><b>{relacije}</b></td><td>{semafor(relacije,5,2)}</td></tr>
                <tr><td>🧬 Generalizacija</td><td><b>{nasledjivanje}</b></td><td>{semafor(nasledjivanje,3,1)}</td></tr>
            </table>
            """, unsafe_allow_html=True)
            
            st.markdown("### 🔗 Multiplikativnost (kardinalnosti)")
            st.markdown(f"""
            <table style="width:100%; font-size:13px; border-collapse:collapse;">
                <tr style="background-color:#f0f0f0;">
                    <th style="text-align:left; padding:5px;">Oznaka</th>
                    <th style="text-align:left; padding:5px;">Naziv</th>
                    <th style="text-align:center; padding:5px;">Značenje</th>
                    <th style="text-align:center; padding:5px;">Broj</th>
                    <th style="text-align:center; padding:5px;">Status</th>
                </tr>
                <tr>
                    <td><b>1 : 1</b></td>
                    <td>One-to-One</td>
                    <td>Jedan vezan za tačno jedan</td>
                    <td align="center"><b>{jedan_jedan}</b></td>
                    <td align="center">{'🟢' if jedan_jedan > 0 else '⚪'}</td>
                </tr>
                <tr>
                    <td><b>1 : N</b></td>
                    <td>One-to-Many</td>
                    <td>Jedan vezan za više</td>
                    <td align="center"><b>{jedan_vise}</b></td>
                    <td align="center">{semafor(jedan_vise, 3, 1)}</td>
                </tr>
                <tr>
                    <td><b>M : N</b></td>
                    <td>Many-to-Many</td>
                    <td>Više vezano za više</td>
                    <td align="center"><b>{vise_vise}</b></td>
                    <td align="center">{'🟢' if vise_vise > 0 else '⚪'}</td>
                </tr>
            </table>
            """, unsafe_allow_html=True)
            
            with st.expander(f"📦 Detaljna analiza klasa ({klase} klasa, {atributi} atributa)"):
                st.markdown("**Prikaz: Naziv tabele, PK operacija, Generalizacija A→B i B→A**")
                st.markdown("---")
                
                for cls in klase_atributi:
                    class_name = cls['name']
                    parent = cls['parent']
                    
                    pk_attr = next((a for a in cls['attributes'] if a['is_pk']), None)
                    pk_text = f"🔑 `{pk_attr['name']}` : {pk_attr['type']}" if pk_attr else "⚠️ Nema PK"
                    
                    attr_list = ", ".join([f"`{a['name']}` : {a['type']}" for a in cls['attributes']])
                    
                    st.markdown(f"### 📦 {class_name}")
                    
                    col_a, col_b = st.columns([1, 1])
                    with col_a:
                        st.markdown(f"**PK operacija:** {pk_text}")
                        st.markdown(f"**Atributi:** {attr_list}")
                    with col_b:
                        if parent:
                            st.markdown(f"**Generalizacija A→B:** `{class_name} --|> {parent}`")
                            st.markdown(f"**Generalizacija B→A:** `{parent} <|-- {class_name}`")
                        else:
                            st.markdown("**Generalizacija:** ❌ Nema")
                    
                    st.markdown("---")
            
            with st.expander(f"🔗 Detaljna analiza relacija ({relacije} relacija)"):
                st.markdown("**Prikaz: Naziv asocijacije, Multiplikativnost A, Multiplikativnost B**")
                st.markdown("---")
                
                gen_relacije = [r for r in relacije_lista if r['tip'] == 'Generalizacija']
                
                relacija_data = []
                
                for rel in relacije_lista:
                    tekst = rel['tekst']
                    tip = rel['tip']
                    
                    if tip == "Generalizacija":
                        match = re.match(r'(\w+)\s*--\|>\s*(\w+)', tekst)
                        if match:
                            dete = match.group(1)
                            roditelj = match.group(2)
                            relacija_data.append({
                                "Tip": "🧬",
                                "Entitet A": dete,
                                "Mult. A": "—",
                                "Entitet B": roditelj,
                                "Mult. B": "—",
                                "Naziv asocijacije": f"Generalizacija ({dete} je {roditelj})"
                            })
                    
                    elif tip == "Asocijacija":
                        match = re.match(r'(\w+)\s+"([^"]*)"\s+(--|-->)\s+"([^"]*)"\s+(\w+)\s*(?::\s*(.*))?', tekst)
                        if match:
                            ent_a = match.group(1)
                            mult_a = match.group(2)
                            ent_b = match.group(5)
                            mult_b = match.group(4)
                            naziv = match.group(6) if match.group(6) else "—"
                            relacija_data.append({
                                "Tip": "🔗",
                                "Entitet A": ent_a,
                                "Mult. A": f'"{mult_a}"',
                                "Entitet B": ent_b,
                                "Mult. B": f'"{mult_b}"',
                                "Naziv asocijacije": naziv
                            })
                        else:
                            relacija_data.append({
                                "Tip": "🔗",
                                "Entitet A": "—",
                                "Mult. A": "1",
                                "Entitet B": "—",
                                "Mult. B": "1",
                                "Naziv asocijacije": tekst
                            })
                
                if relacija_data:
                    df = pd.DataFrame(relacija_data)
                    st.dataframe(df, use_container_width=True, hide_index=True)
                
                if gen_relacije:
                    st.markdown("### 🧬 Generalizacija (poseban prikaz)")
                    for rel in gen_relacije:
                        match = re.match(r'(\w+)\s*--\|>\s*(\w+)', rel['tekst'])
                        if match:
                            dete = match.group(1)
                            roditelj = match.group(2)
                            st.markdown(f"- **A→B:** `{dete} --|> {roditelj}`")
                            st.markdown(f"- **B→A:** `{roditelj} <|-- {dete}`")
                            st.markdown(f"  *(čita se: {dete} je {roditelj})*")
            
            st.markdown("### ✅ Validacija")
            st.markdown(f"""
            <table style="width:100%; font-size:13px;">
                <tr><td>🏷️ Nazivi asocijacija</td><td><b>{nazivi}</b></td><td>{semafor(nazivi,5,2)}</td></tr>
                <tr><td>📌 @startuml</td><td>{'🟢' if evaluation.get('has_startuml') else '🔴'}</td></tr>
                <tr><td>📌 @enduml</td><td>{'🟢' if evaluation.get('has_enduml') else '🔴'}</td></tr>
                <tr><td>🖼️ Render OK</td><td>{'🟢' if evaluation.get('rendered_ok') else '🔴'}</td></tr>
            </table>
            """, unsafe_allow_html=True)

        st.divider()
        col_code1, col_code2 = st.columns(2)
        with col_code1:
            st.subheader("📝 PlantUML kod")
            st.code(puml, language="text")
        with col_code2:
            st.subheader("🗄️ SQL kod")
            st.code(sql_code, language="sql")

        st.divider()
        col_dl1, col_dl2, col_dl3, col_dl4 = st.columns(4)
        with col_dl1:
            if png_path.exists():
                with open(png_path, "rb") as f:
                    st.download_button("🖼️ PNG", f, "model.png", "image/png", use_container_width=True)
        with col_dl2:
            st.download_button("📄 PlantUML", puml, "model.puml", "text/plain", use_container_width=True)
        with col_dl3:
            st.download_button("📥 SQL", sql_code, "schema.sql", "text/plain", use_container_width=True)
        with col_dl4:
            pdf_file = generisi_pdf(description, puml, sql_code, evaluation, png_path)
            st.download_button("📕 PDF Izveštaj", pdf_file, "uml_izvestaj.pdf", "application/pdf", use_container_width=True)

        # Statusna traka
        st.divider()
        col_s1, col_s2 = st.columns(2)
        with col_s1:
            st.caption(f"👁️ Generisanja u sesiji: {st.session_state.visits}")
        with col_s2:
            st.caption(f"⏱️ Vreme: {elapsed:.1f}s | 📌 v2.0 | Groq API")

    except Exception as e:
        st.error(f"💥 Došlo je do greške: {str(e)}")
        with st.expander("🔧 Detalji greške"):
            import traceback
            st.code(traceback.format_exc(), language="text")
