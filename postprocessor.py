import re

def postprocess_puml(puml_code: str) -> str:
    """
    Popravlja PlantUML kod:
    1. Uklanja {PK} oznake
    2. Dodaje PK() operacije u dio OPERACIJA (ispod --)
    3. Uklanja naslijeđene PK iz potklasa
    4. Uklanja atribute koji su reference na druge klase
    5. Uklanja duplirane relacije
    """
    
    lines = puml_code.splitlines()
    new_lines = []
    
    inheritance_map = {}
    all_class_names = set()
    
    # Prvi prolaz: pronađi sve klase i nasljeđivanja
    for linija in lines:
        # Nasljeđivanje: Natklasa <|-- Potklasa
        inheritance_match = re.match(r'^\s*(\w+)\s*<\|--\s*(\w+)', linija)
        if inheritance_match:
            natklasa = inheritance_match.group(1)
            potklasa = inheritance_match.group(2)
            inheritance_map[potklasa] = natklasa
        
        # Takođe: Potklasa --|> Natklasa
        inheritance_match2 = re.match(r'^\s*(\w+)\s*--\|>\s*(\w+)', linija)
        if inheritance_match2:
            potklasa = inheritance_match2.group(1)
            natklasa = inheritance_match2.group(2)
            inheritance_map[potklasa] = natklasa
        
        # Ime klase
        class_match = re.match(r'^\s*(class|interface|enum)\s+(\w+)\s*\{', linija)
        if class_match:
            all_class_names.add(class_match.group(2))
    
    # Drugi prolaz: procesuiraj svaku liniju
    inside_class = False
    current_class = None
    class_body = []
    
    for linija in lines:
        class_start = re.match(r'^\s*(class|interface|enum)\s+(\w+)\s*\{', linija)
        if class_start:
            if inside_class and current_class:
                new_lines.extend(_process_class_body(class_body, current_class, inheritance_map, all_class_names))
                class_body = []
            
            current_class = class_start.group(2)
            inside_class = True
            new_lines.append(linija)
            continue
        
        if inside_class and linija.strip() == "}":
            new_lines.extend(_process_class_body(class_body, current_class, inheritance_map, all_class_names))
            new_lines.append(linija)
            class_body = []
            current_class = None
            inside_class = False
            continue
        
        if inside_class:
            class_body.append(linija)
        else:
            new_lines.append(linija)
    
    if inside_class and current_class:
        new_lines.extend(_process_class_body(class_body, current_class, inheritance_map, all_class_names))
        new_lines.append("}")
    
    result = "\n".join(new_lines)
    
    # Ukloni duplirane relacije
    result = _remove_duplicate_relations(result)
    
    return result


def _process_class_body(body_lines, class_name, inheritance_map, all_class_names):
    """Procesuira tijelo jedne klase."""
    
    is_potklasa = class_name in inheritance_map
    body_text = "\n".join(body_lines)
    
    # 1. Ukloni sve {PK} oznake
    body_text = re.sub(r'\{\s*PK\s*\}\s*', '', body_text)
    
    # 2. Ukloni postojeće PK() operacije (biće ponovo dodate na pravo mjesto)
    body_text = re.sub(r'^\s*PK\([^)]+\)\s*$', '', body_text, flags=re.MULTILINE)
    
    # 3. Ukloni postojeće -- linije (biće ponovo dodate)
    body_text = re.sub(r'^\s*--\s*$', '', body_text, flags=re.MULTILINE)
    
    # 4. Pronađi atribute koji su reference na druge klase (npr. Address address)
    attr_pattern = r'^\s*(\w+)\s+(\w+)\s*$'
    for match in re.finditer(attr_pattern, body_text, re.MULTILINE):
        type_name = match.group(1)
        if type_name[0].isupper() and type_name in all_class_names:
            body_text = body_text.replace(match.group(0), "")
    
    # 5. Pronađi atribute koji izgledaju kao PK (id, jmb, sifra, oib, kod, serialNumber...)
    pk_attributes = []
    attr_pattern2 = r'^\s*(\w+)\s*:\s*(\w+)'
    
    for match in re.finditer(attr_pattern2, body_text, re.MULTILINE):
        attr_name = match.group(1)
        attr_type = match.group(2)
        
        if attr_name.lower() in ['id', 'jmb', 'sifra', 'oib', 'maticni_broj', 'broj', 'kod', 'serialnumber', 'uniquecode', 'memberid']:
            pk_attributes.append((attr_name, attr_type))
            body_text = body_text.replace(match.group(0), "")
    
    # 6. Ako je potklasa, ukloni sve atribute koji liče na PK
    if is_potklasa:
        for match in re.finditer(attr_pattern2, body_text, re.MULTILINE):
            attr_name = match.group(1)
            if attr_name.lower() in ['id', 'jmb', 'sifra', 'oib', 'maticni_broj', 'broj', 'kod', 'serialnumber', 'uniquecode', 'memberid']:
                body_text = body_text.replace(match.group(0), "")
    
    # 7. Sastavi rezultat
    result_lines = []
    
    # Prvo dodaj atribute (očišćene)
    atributi_lines = []
    operacije_lines = []
    
    for line in body_text.splitlines():
        stripped = line.strip()
        if stripped:
            # Ako je atribut (ima :), dodaj u atribute
            if ':' in stripped and '(' not in stripped:
                atributi_lines.append(line)
            else:
                operacije_lines.append(line)
    
    # Dodaj atribute
    for line in atributi_lines:
        if line.strip():
            result_lines.append(line)
    
    # Dodaj -- separator i PK operacije (samo ako nije potklasa i ima PK)
    if pk_attributes and not is_potklasa:
        result_lines.append("    --")
        pk_params = ", ".join([f"{name} : {tip}" for name, tip in pk_attributes])
        result_lines.append(f"    PK({pk_params})")
    
    # Dodaj ostale operacije (ako postoje)
    for line in operacije_lines:
        if line.strip():
            result_lines.append(line)
    
    return result_lines


def _remove_duplicate_relations(puml_code: str) -> str:
    """Uklanja duplirane relacije (npr. A--B i B--A)."""
    lines = puml_code.splitlines()
    seen_pairs = set()
    seen_exact = set()
    result = []
    
    for line in lines:
        s = line.strip()
        
        if not s:
            result.append(line)
            continue
        
        # Detektuj da li je linija relacija
        is_relation = False
        if '--' in s or '<|--' in s or '--|>' in s:
            if not re.match(r'^\s*\w+\s*:', s):
                is_relation = True
        
        if not is_relation:
            result.append(line)
            continue
        
        # Normalizuj liniju za poređenje
        normalized = ' '.join(s.split())
        
        if normalized in seen_exact:
            continue
        
        seen_exact.add(normalized)
        
        # Za asocijacije (--), provjeri i obrnuti par
        if '--' in s and '<|--' not in s and '--|>' not in s:
            match = re.match(r'(\w+)\s+"[^"]*"\s+--\s+"[^"]*"\s+(\w+)', s)
            if match:
                ent_a = match.group(1)
                ent_b = match.group(2)
                
                pair = tuple(sorted([ent_a, ent_b]))
                if pair in seen_pairs:
                    continue
                seen_pairs.add(pair)
        
        result.append(line)
    
    return "\n".join(result)


def validate_and_fix_puml(puml_code: str) -> tuple:
    """Validira i ispravlja PlantUML kod. Vraća (kod, upozorenja)."""
    warnings = []
    
    # Provjera {PK} oznaka
    if re.search(r'\{PK\}', puml_code):
        warnings.append("Pronađene {PK} oznake - automatski ispravljeno")
        puml_code = postprocess_puml(puml_code)
    
    # Provjera PK operacija
    if not re.search(r'PK\([^)]+\)', puml_code):
        if re.search(r'class\s+\w+\s*\{[^}]*\w+\s*:\s*\w+', puml_code):
            warnings.append("Nema PK operacija - pokušavam automatski dodati")
            puml_code = postprocess_puml(puml_code)
    
    # Provjera referenci na druge klase unutar atributa
    class_names = set(re.findall(r'class\s+(\w+)\s*\{', puml_code))
    for cls in class_names:
        pattern = rf'^\s*{cls}\s+\w+\s*$'
        if re.search(pattern, puml_code, re.MULTILINE):
            warnings.append(f"Pronađena referenca na klasu {cls} unutar atributa - ispravljeno")
            puml_code = postprocess_puml(puml_code)
            break
    
    # Ukloni duplirane relacije
    puml_before = puml_code
    puml_code = _remove_duplicate_relations(puml_code)
    if puml_before != puml_code:
        warnings.append("Uklonjene duplirane relacije")
    
    return puml_code, warnings
