def mark_primary_keys(puml: str) -> str:
    """
    Provjerava da li postoji ispravna PK operacija.
    Ako ne postoji, ali postoje id atributi, ostavlja postprocessoru da to riješi.
    """
    import re
    
    lines = []
    inside_class = False
    class_body = []
    current_class = None
    
    for line in puml.splitlines():
        class_start = re.match(r'^\s*(class|interface|enum)\s+(\w+)\s*\{', line)
        if class_start:
            # Završi prethodnu klasu
            if inside_class and current_class:
                lines.extend(_process_class_body(class_body))
            current_class = class_start.group(2)
            inside_class = True
            class_body = []
            lines.append(line)
            continue
        
        if inside_class and line.strip() == "}":
            lines.extend(_process_class_body(class_body))
            lines.append(line)
            current_class = None
            inside_class = False
            continue
        
        if inside_class:
            class_body.append(line)
        else:
            lines.append(line)
    
    # Zadnja klasa
    if inside_class and current_class:
        lines.extend(_process_class_body(class_body))
        lines.append("}")
    
    return "\n".join(lines)


def _process_class_body(body_lines):
    """
    Procesuira tijelo klase.
    Samo uklanja {PK} oznake ako postoje, ali NE dodaje nove.
    """
    result = []
    
    for line in body_lines:
        # Ukloni {PK} oznake ako postoje (ne dodajemo nove)
        if '{PK}' in line:
            line = re.sub(r'\{\s*PK\s*\}\s*', '', line)
        
        # Zadrži sve ostale linije (uključujući PK operacije ako postoje)
        result.append(line)
    
    return result
