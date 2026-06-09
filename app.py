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

# ========== SIDEBAR: Rječnik pojmova ==========
with st.sidebar:
    st.markdown("## 📚 Rječnik pojmova")
    with st.expander("📦 Klasa (Class)"):
        st.write("Entitet u sistemu. U bazi postaje **tabela**.")
    with st.expander("🔑 PK (Primarni ključ)"):
        st.write("Jedinstveni identifikator. Označava se kao `PK(id : Integer)`.")
    with st.expander("🧬 Generalizacija"):
        st.write("Nasljeđivanje: `Natklasa <|-- Potklasa`")
    with st.expander("🔗 Asocijacija"):
        st.write("Veza između klasa: `KlasaA -- KlasaB`")
    with st.expander("🔢 Multiplikativnost"):
        st.write("""
        - `1` = tačno jedan
        - `0..*` = nula ili više
        - `1..*` = bar jedan
        """)
    with st.expander("🟢🟡🔴 Semafor"):
        st.write("Vizuelna ocjena: zeleno = dobro, žuto = osrednje, crveno = loše")
    st.divider()
    st.caption("📌 v2.0 | Groq API | Qwen3-32B")

opis_sistema = st.text_area(
    "Unesite opis sistema:",
    height=260,
    placeholder="Npr: Sistem za upravljanje bibliotekom ima klase Knjiga, Član, Pozajmica..."
)


def parsiraj_klase_i_atribute(puml_kod):
    """Izvlači imena klasa i njihove atribute iz PlantUML koda."""
    klase_atributi = []
    trenutna_klasa = None
    unutar_klase = False
    nasljeđivanja = {}
    
    for linija in puml_kod.splitlines():
        naslj_match = re.match(r'^\s*(\w+)\s*<\|--\s*(\w+)', linija)
        if naslj_match:
            potklasa = naslj_match.group(1)
            natklasa = naslj_match.group(2)
            nasljeđivanja[potklasa] = natklasa
    
    for linija in puml_kod.splitlines():
        s = linija.strip()
        match = re.match(r'^\s*(class|interface|enum)\s+(\w+)\s*\{', linija)
        if match:
            if trenutna_klasa:
                klase_atributi.append(trenutna_klasa)
            trenutna_klasa = {
                "naziv": match.group(2),
                "roditelj": nasljeđivanja.get(match.group(2)),
                "atributi": []
            }
            unutar_klase = True
            continue
        if unutar_klase and s == "}":
            if trenutna_klasa:
                klase_atributi.append(trenutna_klasa)
            trenutna_klasa = None
            unutar_klase = False
            continue
        if unutar_klase and trenutna_klasa is not None:
            # Preskoči PK operacije
            if re.match(r'^\s*PK\s*\(', s):
                continue
            attr_match = re.match(r'^\s*(\w+)\s*:\s*(\w+)', s)
            if attr_match:
                trenutna_klasa["atributi"].append({
                    "naziv": attr_match.group(1),
                    "tip": attr_match.group(2)
                })
    
    if trenutna_klasa:
        klase_atributi.append(trenutna_klasa)
    
    return klase_atributi


def parsiraj_relacije(puml_kod):
    """Izvlači sve relacije iz PlantUML koda."""
    relacije_lista = []
    for linija in puml_kod.splitlines():
        s = linija.strip()
        if "<|--" in s or "--|>" in s:
            relacije_lista.append({"tip": "Generalizacija", "tekst": s})
        elif "--" in s and "<|--" not in s and "--|>" not in s:
            relacije_lista.append({"tip": "Asocijacija", "tekst": s})
    return relacije_lista


def generisi_pdf(opis, puml_kod, sql_kod, evaluacija, putanja_png):
    """Generiše PDF izvještaj sa svim rezultatima."""
    pdf = FPDF()
    pdf.add_page()
    pdf.add_font("DejaVu", "", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", uni=True)
    pdf.add_font("DejaVu", "B", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", uni=True)

    pdf.set_font("DejaVu", "B", 14)
    pdf.cell(0, 10, "UML Class Diagram Generator - Izvještaj", ln=True, align="C")
    pdf.ln(5)

    pdf.set_font("DejaVu", "B", 11)
    pdf.cell(0, 8, "1. Opis sistema", ln=True)
    pdf.set_font("DejaVu", "", 9)
    pdf.multi_cell(0, 5, opis)
    pdf.ln(5)

    if putanja_png and putanja_png.exists():
        pdf.set_font("DejaVu", "B", 11)
        pdf.cell(0, 8, "2. UML Class dijagram", ln=True)
        pdf.image(str(putanja_png), x=10, w=190)
        pdf.ln(5)

    pdf.set_font("DejaVu", "B", 11)
    pdf.cell(0, 8, "3. PlantUML kod", ln=True)
    pdf.set_font("Courier", "", 7)
    for linija in puml_kod.split('\n'):
        cista_linija = linija.encode('ascii', 'ignore').decode('ascii')
        pdf.cell(0, 4, cista_linija[:120], ln=True)
    pdf.ln(5)

    pdf.set_font("DejaVu", "B", 11)
    pdf.cell(0, 8, "4. SQL kod za kreiranje baze", ln=True)
    pdf.set_font("Courier", "", 7)
    for linija in sql_kod.split('\n'):
        cista_linija = linija.encode('ascii', 'ignore').decode('ascii')
        pdf.cell(0, 4, cista_linija[:120], ln=True)
    pdf.ln(5)

    pdf.set_font("DejaVu", "B", 11)
    pdf.cell(0, 8, "5. Evaluacija modela", ln=True)
    pdf.set_font("DejaVu", "", 9)
    for kljuc, vrijednost in evaluacija.items():
        cist_kljuc = str(kljuc).encode('ascii', 'ignore').decode('ascii')
        cista_vrijednost = str(vrijednost).encode('ascii', 'ignore').decode('ascii')
        pdf.cell(0, 6, f"{cist_kljuc}: {cista_vrijednost}", ln=True)

    return pdf.output(dest='S').encode('latin-1')


# Brojač generisanja
if "broj_posjeta" not in st.session_state:
    st.session_state.broj_posjeta = 1
else:
    st.session_state.broj_posjeta += 1


if st.button("✨ Generiši dijagram", type="primary"):

    if not opis_sistema.strip():
        st.warning("⚠️ Unesite opis sistema.")
        st.stop()

    try:
        pocetno_vrijeme = time.time()
        
        progress_bar = st.progress(0)
        status_tekst = st.empty()
        
        status_tekst.text("🧠 Generisanje PlantUML koda...")
        for i in range(1, 6): progress_bar.progress(i * 4); time.sleep(0.1)
        
        puml = generate_puml(opis_sistema)
        progress_bar.progress(30)
        
        status_tekst.text("🔧 Sanitizacija PlantUML koda...")
        for i in range(6, 9): progress_bar.progress(i * 5); time.sleep(0.1)
        
        PUML_FILE.write_text(puml, encoding="utf-8")
        progress_bar.progress(40)
        
        status_tekst.text("🎨 Renderovanje dijagrama...")
        for i in range(8, 13): progress_bar.progress(i * 5); time.sleep(0.1)
        
        code, err = run_plantuml(PUML_FILE)
        progress_bar.progress(70)

        if code != 0:
            progress_bar.empty()
            status_tekst.empty()
            st.error("❌ PlantUML render nije uspio.")
            st.code(err, language="text")
            with st.expander("🔍 Generisani PlantUML kod (sadrži greške)"):
                st.code(puml, language="text")
            st.stop()

        putanja_png = PUML_FILE.with_suffix(".png")
        
        status_tekst.text("🗄️ Generisanje SQL koda...")
        for i in range(14, 17): progress_bar.progress(i * 5); time.sleep(0.1)
        
        sql_kod = generate_sql_from_puml(puml)
        progress_bar.progress(85)
        
        status_tekst.text("📊 Evaluacija modela...")
        for i in range(17, 21): progress_bar.progress(i * 5); time.sleep(0.1)
        
        evaluacija = evaluate_puml(puml, True)
        progress_bar.progress(100)
        status_tekst.text("✅ Generisanje završeno!")
        time.sleep(0.3)
        
        proteklo_vrijeme = time.time() - pocetno_vrijeme
        progress_bar.empty()
        status_tekst.empty()

        kolona1, kolona2 = st.columns([2, 1])

        with kolona1:
            st.subheader("📊 Generisani dijagram")
            if putanja_png.exists():
                st.image(str(putanja_png), use_container_width=True)
            else:
                st.error("PNG fajl nije kreiran.")

        with kolona2:
            st.subheader("📈 Evaluacija")
            
            def semafor(vrijednost, dobro, lose):
                if vrijednost >= dobro: return "🟢"
                elif vrijednost >= lose: return "🟡"
                else: return "🔴"
            
            broj_klasa = evaluacija.get("class_count", 0)
            broj_relacija = evaluacija.get("relation_count", 0)
            broj_nasljeđivanja = evaluacija.get("inheritance_count", 0)
            jedan_jedan = evaluacija.get("one_to_one_count", 0)
            jedan_vise = evaluacija.get("one_to_many_count", 0)
            vise_vise = evaluacija.get("many_to_many_count", 0)
            broj_naziva = evaluacija.get("association_with_name", 0)
            broj_atributa = evaluacija.get("attribute_count", 0)
            broj_pk = evaluacija.get("pk_operation_count", 0)
            neispravni_pk = evaluacija.get("invalid_pk_count", 0)
            naslijedjeni_pk = evaluacija.get("inherited_pk_count", 0)
            
            klase_atributi = parsiraj_klase_i_atribute(puml)
            relacije_lista = parsiraj_relacije(puml)
            
            st.markdown("### 📊 Metrike modela")
            st.markdown(f"""
            <table style="width:100%; font-size:13px;">
                <tr><td>🏗️ Broj klasa</td><td><b>{broj_klasa}</b></td><td>{semafor(broj_klasa,5,2)}</td></tr>
                <tr><td>📋 Broj atributa</td><td><b>{broj_atributa}</b></td><td>{semafor(broj_atributa,15,5)}</td></tr>
                <tr><td>🔑 PK operacija</td><td><b>{broj_pk}</b></td><td>{semafor(broj_pk,3,1)}</td></tr>
                <tr><td>⚠️ Neispravni PK</td><td><b>{neispravni_pk}</b></td><td>{'🟢' if neispravni_pk == 0 else '🔴'}</td></tr>
                <tr><td>🧬 Naslijeđeni PK</td><td><b>{naslijedjeni_pk}</b></td><td>{'🟢' if naslijedjeni_pk == 0 else '🔴'}</td></tr>
                <tr><td>🔗 Ukupno relacija</td><td><b>{broj_relacija}</b></td><td>{semafor(broj_relacija,5,2)}</td></tr>
                <tr><td>🧬 Generalizacija</td><td><b>{broj_nasljeđivanja}</b></td><td>{semafor(broj_nasljeđivanja,3,1)}</td></tr>
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
            
            with st.expander(f"📦 Detaljna analiza klasa ({broj_klasa} klasa, {broj_atributa} atributa)"):
                st.markdown("**Prikaz: Naziv tabele, PK operacija, Generalizacija A→B i B→A**")
                st.markdown("---")
                
                for klasa in klase_atributi:
                    naziv_klase = klasa['naziv']
                    roditelj = klasa['roditelj']
                    
                    lista_atributa = ", ".join([f"`{a['naziv']}` : {a['tip']}" for a in klasa['atributi']])
                    
                    st.markdown(f"### 📦 {naziv_klase}")
                    
                    kol_a, kol_b = st.columns([1, 1])
                    with kol_a:
                        st.markdown(f"**Atributi:** {lista_atributa if lista_atributa else 'Nema (naslijeđeni od natklase)'}")
                    with kol_b:
                        if roditelj:
                            st.markdown(f"**Generalizacija A→B:** `{naziv_klase} <|-- {roditelj}`")
                            st.markdown(f"**Generalizacija B→A:** `{roditelj} --|> {naziv_klase}`")
                        else:
                            st.markdown("**Generalizacija:** ❌ Nema")
                    
                    st.markdown("---")
            
            with st.expander(f"🔗 Detaljna analiza relacija ({broj_relacija} relacija)"):
                st.markdown("**Prikaz: Naziv asocijacije, Multiplikativnost A, Multiplikativnost B**")
                st.markdown("---")
                
                gen_relacije = [r for r in relacije_lista if r['tip'] == 'Generalizacija']
                
                podaci_relacija = []
                
                for rel in relacije_lista:
                    tekst = rel['tekst']
                    tip = rel['tip']
                    
                    if tip == "Generalizacija":
                        match = re.match(r'(\w+)\s*<\|--\s*(\w+)', tekst)
                        if not match:
                            match = re.match(r'(\w+)\s*--\|>\s*(\w+)', tekst)
                        if match:
                            if "<|--" in tekst:
                                potklasa = match.group(1)
                                natklasa = match.group(2)
                            else:
                                natklasa = match.group(1)
                                potklasa = match.group(2)
                            podaci_relacija.append({
                                "Tip": "🧬",
                                "Entitet A": potklasa,
                                "Mult. A": "—",
                                "Entitet B": natklasa,
                                "Mult. B": "—",
                                "Naziv asocijacije": f"Generalizacija ({potklasa} je {natklasa})"
                            })
                    
                    elif tip == "Asocijacija":
                        match = re.match(r'(\w+)\s+"([^"]*)"\s+(--|-->)\s+"([^"]*)"\s+(\w+)\s*(?::\s*(.*))?', tekst)
                        if match:
                            ent_a = match.group(1)
                            mult_a = match.group(2)
                            ent_b = match.group(5)
                            mult_b = match.group(4)
                            naziv = match.group(6) if match.group(6) else "—"
                            podaci_relacija.append({
                                "Tip": "🔗",
                                "Entitet A": ent_a,
                                "Mult. A": f'"{mult_a}"',
                                "Entitet B": ent_b,
                                "Mult. B": f'"{mult_b}"',
                                "Naziv asocijacije": naziv
                            })
                
                if podaci_relacija:
                    df = pd.DataFrame(podaci_relacija)
                    st.dataframe(df, use_container_width=True, hide_index=True)
                
                if gen_relacije:
                    st.markdown("### 🧬 Generalizacija (poseban prikaz)")
                    for rel in gen_relacije:
                        tekst = rel['tekst']
                        if "<|--" in tekst:
                            match = re.match(r'(\w+)\s*<\|--\s*(\w+)', tekst)
                            if match:
                                potklasa = match.group(1)
                                natklasa = match.group(2)
                        else:
                            match = re.match(r'(\w+)\s*--\|>\s*(\w+)', tekst)
                            if match:
                                natklasa = match.group(1)
                                potklasa = match.group(2)
                        if match:
                            st.markdown(f"- **A→B:** `{potklasa} <|-- {natklasa}`")
                            st.markdown(f"- **B→A:** `{natklasa} --|> {potklasa}`")
                            st.markdown(f"  *(čita se: {potklasa} je {natklasa})*")
            
            st.markdown("### ✅ Validacija")
            st.markdown(f"""
            <table style="width:100%; font-size:13px;">
                <tr><td>🏷️ Nazivi asocijacija</td><td><b>{broj_naziva}</b></td><td>{semafor(broj_naziva,5,2)}</td></tr>
                <tr><td>📌 @startuml</td><td>{'🟢' if evaluacija.get('has_startuml') else '🔴'}</td></tr>
                <tr><td>📌 @enduml</td><td>{'🟢' if evaluacija.get('has_enduml') else '🔴'}</td></tr>
                <tr><td>🖼️ Render OK</td><td>{'🟢' if evaluacija.get('rendered_ok') else '🔴'}</td></tr>
            </table>
            """, unsafe_allow_html=True)

        st.divider()
        kol_kod1, kol_kod2 = st.columns(2)
        with kol_kod1:
            st.subheader("📝 PlantUML kod")
            st.code(puml, language="text")
        with kol_kod2:
            st.subheader("🗄️ SQL kod")
            st.code(sql_kod, language="sql")

        st.divider()
        kol_dug1, kol_dug2, kol_dug3, kol_dug4 = st.columns(4)
        with kol_dug1:
            if putanja_png.exists():
                with open(putanja_png, "rb") as f:
                    st.download_button("🖼️ PNG", f, "model.png", "image/png", use_container_width=True)
        with kol_dug2:
            st.download_button("📄 PlantUML", puml, "model.puml", "text/plain", use_container_width=True)
        with kol_dug3:
            st.download_button("📥 SQL", sql_kod, "schema.sql", "text/plain", use_container_width=True)
        with kol_dug4:
            pdf_fajl = generisi_pdf(opis_sistema, puml, sql_kod, evaluacija, putanja_png)
            st.download_button("📕 PDF Izvještaj", pdf_fajl, "uml_izvjestaj.pdf", "application/pdf", use_container_width=True)

        # Statusna traka
        st.divider()
        kol_s1, kol_s2 = st.columns(2)
        with kol_s1:
            st.caption(f"👁️ Generisanja u sesiji: {st.session_state.broj_posjeta}")
        with kol_s2:
            st.caption(f"⏱️ Vrijeme: {proteklo_vrijeme:.1f}s | 📌 v2.0 | Groq API")

    except Exception as e:
        st.error(f"💥 Došlo je do greške: {str(e)}")
        with st.expander("🔧 Detalji greške"):
            import traceback
            st.code(traceback.format_exc(), language="text")
