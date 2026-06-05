import re

def validate_and_fix_puml(puml_code: str) -> tuple[str, list]:
    """
    Validira PlantUML kod i vraća ispravljeni kod + listu upozorenja.
    """
    warnings = []
    original_code = puml_code
    
    # Provjera: ima li {PK} oznaka?
    if re.search(r'\{PK\}', puml_code):
        warnings.append("Pronađene {PK} oznake - automatski ispravljeno")
        puml_code = _fix_pk_annotations(puml_code)
    
    # Provjera: ima li potklasa sa 'id' atributom?
    puml_code, id_warnings = _remove_inherited_ids(puml_code)
    warnings.extend(id_warnings)
    
    # Provjera: ima li PK operacija?
    if not re.search(r'PK\([^)]+\)', puml_code):
        if re.search(r'class\s+\w+\s*\{[^}]*id\s*:', puml_code, re.IGNORECASE):
            warnings.append("Nema PK operacija, ali postoje 'id' atributi - pokušavam popraviti")
            puml_code = _convert_id_to_pk(puml_code)
    
    # Provjera: da li je format nasljeđivanja ispravan?
    puml_code = _fix_inheritance_format(puml_code)
    
    return puml_code, warnings


def _fix_pk_annotations(puml_code: str) -> str:
    """Uklanja {PK} oznake i pretvara ih u PK() operacije."""
    lines = puml_code.splitlines()
    new_lines = []
    inside_class = False
    class_body = []
    current_class = None
    
    for linija in lines:
        class_start = re.match(r'^\s*(class|interface|enum)\s+(\w+)\s*\{', linija)
        if class_start:
            if inside_class and current_class:
                new_lines.extend(_process_class_for_pk(class_body, current_class))
            current_class = class_start.group(2)
            inside_class = True
            class_body = []
            new_lines.append(linija)
            continue
        
        if inside_class and linija.strip() == "}":
            new_lines.extend(_process_class_for_pk(class_body, current_class))
            new_lines.append(linija)
            current_class = None
            inside_class = False
            continue
        
        if inside_class:
            class_body.append(linija)
        else:
            new_lines.append(linija)
    
    if inside_class and current_class:
        new_lines.extend(_process_class_for_pk(class_body, current_class))
        new_lines.append("}")
    
    return "\n".join(new_lines)


def _process_class_for_pk(body_lines, class_name):
    """Procesuira tijelo klase i pretvara {PK} u PK() operaciju."""
    result = []
    pk_attributes = []
    
    for line in body_lines:
        # Pronađi {PK} oznaku
        pk_match = re.match(r'^\s*\{PK\}\s*(\w+)\s*:\s*(\w+)', line)
        if pk_match:
            attr_name = pk_match.group(1)
            attr_type = pk_match.group(2)
            pk_attributes.append((attr_name, attr_type))
        else:
            # Ukloni prazne {PK} ako ih ima
            cleaned_line = re.sub(r'\{\s*PK\s*\}\s*', '', line)
            if cleaned_line.strip():
                result.append(cleaned_line)
    
    # Dodaj PK operaciju na početak ako ima PK atributa
    if pk_attributes:
        pk_params = ", ".join([f"{name} : {typ}" for name, typ in pk_attributes])
        result.insert(0, f"    PK({pk_params})")
    
    return result


def _remove_inherited_ids(puml_code: str) -> tuple[str, list]:
    """Uklanja id atribute iz potklasa (naslijeđene od natklase)."""
    warnings = []
    
    # Pronađi sve klase i nasljeđivanja
    class_names = set()
    inheritance_map = {}
    
    for linija in puml_code.splitlines():
        class_match = re.match(r'^\s*(class|interface|enum)\s+(\w+)\s*\{', linija)
        if class_match:
            class_names.add(class_match.group(2))
        
        inh_match = re.match(r'^\s*(\w+)\s*(?:<\|--|--\|>)\s*(\w+)', linija)
        if inh_match:
            # Ako je format Potklasa --|> Natklasa
            if "--|>" in linija:
                inheritance_map[inh_match.group(1)] = inh_match.group(2)
            # Ako je format Natklasa <|-- Potklasa
            elif "<|--" in linija:
                inheritance_map[inh_match.group(2)] = inh_match.group(1)
    
    # Procesuiraj svaku klasu
    lines = puml_code.splitlines()
    new_lines = []
    inside_class = False
    current_class = None
    class_body = []
    
    for linija in lines:
        class_start = re.match(r'^\s*(class|interface|enum)\s+(\w+)\s*\{', linija)
        if class_start:
            if inside_class and current_class:
                new_lines.extend(_clean_class_body(class_body, current_class, inheritance_map, warnings))
            current_class = class_start.group(2)
            inside_class = True
            class_body = []
            new_lines.append(linija)
            continue
        
        if inside_class and linija.strip() == "}":
            new_lines.extend(_clean_class_body(class_body, current_class, inheritance_map, warnings))
            new_lines.append(linija)
            current_class = None
            inside_class = False
            continue
        
        if inside_class:
            class_body.append(linija)
        else:
            new_lines.append(linija)
    
    if inside_class and current_class:
        new_lines.extend(_clean_class_body(class_body, current_class, inheritance_map, warnings))
        new_lines.append("}")
    
    return "\n".join(new_lines), warnings


def _clean_class_body(body_lines, class_name, inheritance_map, warnings):
    """Čisti tijelo klase - uklanja naslijeđene PK atribute."""
    result = []
    is_subclass = class_name in inheritance_map
    
    for line in body_lines:
        # Provjeri da li je atribut 'id'
        id_match = re.match(r'^\s*id\s*:\s*\w+', line, re.IGNORECASE)
        if id_match and is_subclass:
            warnings.append(f"U klasi '{class_name}' uklonjen naslijeđeni atribut 'id' (nasljeđuje se od {inheritance_map[class_name]})")
            continue
        
        # Provjeri PK operaciju - ako je potklasa, ukloni je
        if is_subclass and re.match(r'^\s*PK\s*\(', line):
            warnings.append(f"U klasi '{class_name}' uklonjena PK operacija (nasljeđuje se od {inheritance_map[class_name]})")
            continue
        
        result.append(line)
    
    return result


def _convert_id_to_pk(puml_code: str) -> str:
    """Pretvara obične 'id' atribute u PK operacije."""
    lines = puml_code.splitlines()
    new_lines = []
    inside_class = False
    class_body = []
    current_class = None
    
    for linija in lines:
        class_start = re.match(r'^\s*(class|interface|enum)\s+(\w+)\s*\{', linija)
        if class_start:
            if inside_class and current_class:
                new_lines.extend(_convert_class_ids_to_pk(class_body, current_class))
            current_class = class_start.group(2)
            inside_class = True
            class_body = []
            new_lines.append(linija)
            continue
        
        if inside_class and linija.strip() == "}":
            new_lines.extend(_convert_class_ids_to_pk(class_body, current_class))
            new_lines.append(linija)
            current_class = None
            inside_class = False
            continue
        
        if inside_class:
            class_body.append(linija)
        else:
            new_lines.append(linija)
    
    if inside_class and current_class:
        new_lines.extend(_convert_class_ids_to_pk(class_body, current_class))
        new_lines.append("}")
    
    return "\n".join(new_lines)


def _convert_class_ids_to_pk(body_lines, class_name):
    """Pretvara 'id' atribut u PK operaciju."""
    result = []
    id_attribute = None
    other_lines = []
    
    for line in body_lines:
        id_match = re.match(r'^\s*id\s*:\s*(\w+)', line, re.IGNORECASE)
        if id_match and not id_attribute:
            id_attribute = id_match.group(1)
        else:
            other_lines.append(line)
    
    if id_attribute:
        result.append(f"    PK(id : {id_attribute})")
    
    result.extend(other_lines)
    return result


def _fix_inheritance_format(puml_code: str) -> str:
    """Popravlja format nasljeđivanja u ispravan PlantUML format."""
    # Zamijeni Dijete --|> Roditelj u Roditelj <|-- Dijete
    pattern = r'(\w+)\s*--\|>\s*(\w+)'
    
    def replace_inheritance(match):
        dijete = match.group(1)
        roditelj = match.group(2)
        return f"{roditelj} <|-- {dijete}"
    
    return re.sub(pattern, replace_inheritance, puml_code)
