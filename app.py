with kolona2:
    st.subheader("📈 Evaluacija")
    
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
        <tr><td>🏗️ Broj klasa</td><td><b>{broj_klasa}</b></td><td>{'OK' if broj_klasa >= 5 else 'UPOZORENJE'}</td></tr>
        <tr><td>📋 Broj atributa</td><td><b>{broj_atributa}</b></td><td>{'OK' if broj_atributa >= 15 else 'UPOZORENJE'}</td></tr>
        <tr><td>🔑 PK operacija</td><td><b>{broj_pk}</b></td><td>{'OK' if broj_pk >= 3 else 'UPOZORENJE'}</td></tr>
        <tr><td>⚠️ Neispravni PK</td><td><b>{neispravni_pk}</b></td><td>{'Da' if neispravni_pk == 0 else 'Ne'}</td></tr>
        <tr><td>🧬 Naslijeđeni PK</td><td><b>{naslijedjeni_pk}</b></td><td>{'Da' if naslijedjeni_pk == 0 else 'Ne'}</td></tr>
        <tr><td>🔗 Ukupno relacija</td><td><b>{broj_relacija}</b></td><td>{'OK' if broj_relacija >= 5 else 'UPOZORENJE'}</td></tr>
        <tr><td>🧬 Generalizacija</td><td><b>{broj_nasljeđivanja}</b></td><td>{'OK' if broj_nasljeđivanja >= 3 else 'UPOZORENJE'}</td></tr>
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
            <td align="center">{'Postoji' if jedan_jedan > 0 else 'Nema'}</td>
        </tr>
        <tr>
            <td><b>1 : N</b></td>
            <td>One-to-Many</td>
            <td>Jedan vezan za više</td>
            <td align="center"><b>{jedan_vise}</b></td>
            <td align="center">{'OK' if jedan_vise >= 3 else 'UPOZORENJE'}</td>
        </tr>
        <tr>
            <td><b>M : N</b></td>
            <td>Many-to-Many</td>
            <td>Više vezano za više</td>
            <td align="center"><b>{vise_vise}</b></td>
            <td align="center">{'Postoji' if vise_vise > 0 else 'Nema'}</td>
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
        <tr><td>🏷️ Nazivi asocijacija</td><td><b>{broj_naziva}</b></td><td>{'OK' if broj_naziva >= 5 else 'UPOZORENJE'}</td></tr>
        <tr><td>📌 @startuml</td><td>{'Da' if evaluacija.get('has_startuml') else 'Ne'}</td></tr>
        <tr><td>📌 @enduml</td><td>{'Da' if evaluacija.get('has_enduml') else 'Ne'}</td></tr>
        <tr><td>🖼️ Render OK</td><td>{'Da' if evaluacija.get('rendered_ok') else 'Ne'}</td></tr>
    </table>
    """, unsafe_allow_html=True)
