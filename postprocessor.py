import re

def postprocess_puml(puml_code: str) -> str:
    """
    Popravlja PlantUML kod:
    1. Uklanja {PK} iz atributa
    2. Dodaje PK() operaciju
    3. Uklanja naslijeđene PK atribute iz potklasa
    """
    
    lines = puml_code.splitlines()
    new_lines = []
    
    class_names = []
    inheritance_map = {}  # potklasa -> natklasa
    
    # Prvi prolaz: pronađi sve klase i nasljeđivanja
    for linija in lines:
        # Nasljeđivanje
        inheritance_match = re.match(r'^\s*(\w+)\s*<\|--\s*(\w+)', linija)
        if inheritance_match:
            potklasa = inheritance_match.group(1)
            natklasa = inheritance_match.group(2)
            inheritance_map[potklasa] = natklasa
        
        # Ime klase
        class_match = re.match(r'^\s*(class|interface|enum)\s+(\w+)\s*\{', linija)
        if class_match:
            class_names.append(class_match.group(2))
    
    # Drugi prolaz: procesuiraj svaku liniju
    inside_class = False
    current_class = None
    class_body = []
    has_invalid_pk = False
    
    for linija in lines:
        # Početak klase
        class_start = re.match(r'^\s*(class|interface|enum)\s+(\w+)\s*\{', linija)
        if class_start:
            # Završi prethodnu klasu ako postoji
            if inside_class and current_class:
                new_lines.extend(_process_class_body(class_body, current_class, inheritance_map))
                class_body = []
            
            current_class = class_start.group(2)
            inside_class = True
            new_lines.append(linija)
            continue
        
        # Kraj klase
        if inside_class and linija.strip() == "}":
            new_lines.extend(_process_class_body(class_body, current_class, inheritance_map))
            new_lines.append(linija)
            class_body = []
            current_class = None
            inside_class = False
            continue
        
        # Unutar klase
        if inside_class:
            class_body.append(linija)
        else:
            new_lines.append(linija)
    
    # Zadnja klasa
    if inside_class and current_class:
        new_lines.extend(_process_class_body(class_body, current_class, inheritance_map))
        new_lines.append("}")
    
    return "\n".join(new_lines)


def _process_class_body(body_lines, class_name, inheritance_map):
    """Procesuira tijelo jedne klase."""
    
    is_potklasa = class_name in inheritance_map
    body_text = "\n".join(body_lines)
    
    # 1. Ukloni sve {PK} oznake
    body_text = re.sub(r'\{\s*PK\s*\}\s*', '', body_text)
    
    # 2. Pronađi atribute koji izgledaju kao PK (id, sifra, jmb...)
    # i pretvori ih u PK() operaciju
    pk_attributes = []
    
    # Pokupi sve atribute koji bi mogli biti PK
    attr_pattern = r'^\s*(\w+)\s*:\s*(\w+)'
    for match in re.finditer(attr_pattern, body_text, re.MULTILINE):
        attr_name = match.group(1)
        attr_type = match.group(2)
        
        # Ako atribut izgleda kao potencijalni PK (po imenu)
        if attr_name.lower() in ['id', 'sifra', 'jmb', 'oib', 'matični_broj', 'broj']:
            pk_attributes.append((attr_name, attr_type))
            # Ukloni ovaj atribut iz body-ja (biće dodat kao operacija)
            body_text = body_text.replace(match.group(0), "")
    
    # 3. Ako je potklasa, ukloni sve atribute koji se zovu 'id'
    # (jer se nasljeđuju od natklase)
    if is_potklasa:
        for match in re.finditer(attr_pattern, body_text, re.MULTILINE):
            attr_name = match.group(1)
            if attr_name.lower() == 'id':
                body_text = body_text.replace(match.group(0), "")
    
    # 4. Dodaj PK operacije na početak body-ja (samo ako nije potklasa)
    result_lines = []
    
    if pk_attributes and not is_potklasa:
        # Dodaj PK operaciju
        pk_params = ", ".join([f"{name} : {tip}" for name, tip in pk_attributes])
        result_lines.append(f"    PK({pk_params})")
    
    # Dodaj ostatak body-ja (očišćen od praznih linija)
    for line in body_text.splitlines():
        if line.strip():
            result_lines.append(line)
    
    return result_lines


def validate_and_fix_puml(puml_code: str) -> tuple[str, list]:
    """
    Validira PlantUML kod i vraća ispravljeni kod + listu upozorenja.
    """
    warnings = []
    
    # Provjera: ima li {PK} oznaka?
    if re.search(r'\{PK\}', puml_code):
        warnings.append("Pronađene {PK} oznake - automatski ispravljeno")
        puml_code = postprocess_puml(puml_code)
    
    # Provjera: ima li potklasa sa 'id' atributom?
    # Ovo se rješava u postprocessu
    
    # Provjera: ima li PK operacija?
    if not re.search(r'PK\([^)]+\)', puml_code):
        # Ako nema PK operacija, pokušaj popraviti
        if re.search(r'class\s+\w+\s*\{[^}]*id\s*:', puml_code, re.IGNORECASE):
            warnings.append("Nema PK operacija, ali postoje 'id' atributi - pokušavam popraviti")
            puml_code = postprocess_puml(puml_code)
    
    return puml_code, warnings
