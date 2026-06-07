def _process_class_body(body_lines, class_name, inheritance_map, all_class_names):
    """Procesuira tijelo jedne klase. PK ide ispod -- crte, potklase NE dobijaju PK."""
    
    is_potklasa = class_name in inheritance_map
    body_text = "\n".join(body_lines)
    
    # 1. Ukloni sve {PK} oznake
    body_text = re.sub(r'\{\s*PK\s*\}\s*', '', body_text)
    
    # 2. Ukloni sve postojeće PK() operacije i -- linije
    body_text = re.sub(r'PK\([^)]*\)', '', body_text)
    body_text = re.sub(r'^\s*--\s*$', '', body_text, flags=re.MULTILINE)
    
    # 3. Ukloni reference na druge klase
    attr_pattern = r'^\s*(\w+)\s+(\w+)\s*$'
    for match in re.finditer(attr_pattern, body_text, re.MULTILINE):
        type_name = match.group(1)
        if type_name[0].isupper() and type_name in all_class_names:
            body_text = body_text.replace(match.group(0), "")
    
    # 4. Pronađi PK atribute (samo za natklase)
    pk_attributes = []
    attr_pattern2 = r'^\s*(\w+)\s*:\s*(\w+)'
    
    # AKO JE POTKLASA - ukloni SVE atribute koji liče na PK
    if is_potklasa:
        for match in re.finditer(attr_pattern2, body_text, re.MULTILINE):
            attr_name = match.group(1)
            if attr_name.lower() in ['id', 'jmb', 'sifra', 'oib', 'maticni_broj', 'broj', 'kod', 
                                       'serialnumber', 'uniquecode', 'memberid', 'boid', 'mjestoId',
                                       'rednibroj', 'naziv']:
                body_text = body_text.replace(match.group(0), "")
    else:
        # Samo za natklase - pronađi PK atribute
        for match in re.finditer(attr_pattern2, body_text, re.MULTILINE):
            attr_name = match.group(1)
            attr_type = match.group(2)
            
            if attr_name.lower() in ['id', 'jmb', 'sifra', 'oib', 'maticni_broj', 'broj', 'kod', 
                                       'serialnumber', 'uniquecode', 'memberid', 'boid', 'mjestoId',
                                       'rednibroj', 'naziv']:
                pk_attributes.append((attr_name, attr_type))
                body_text = body_text.replace(match.group(0), "")
    
    # 5. Sastavi rezultat: prvo atributi, pa --, pa PK (samo za natklase)
    result_lines = []
    
    for line in body_text.splitlines():
        stripped = line.strip()
        if stripped and ':' in stripped:
            result_lines.append(line)
    
    # Dodaj -- i PK samo ako nije potklasa i ima PK atribute
    if pk_attributes and not is_potklasa:
        result_lines.append("    --")
        pk_params = ", ".join([f"{name} : {tip}" for name, tip in pk_attributes])
        result_lines.append(f"    PK({pk_params})")
    
    return result_lines
