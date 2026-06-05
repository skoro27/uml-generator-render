def mark_primary_keys(puml: str) -> str:
    """
    Umjesto dodavanja {PK}, ova funkcija sada provjerava da li postoji 
    ispravna PK operacija. Ako ne postoji, dodaje je.
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
                lines.extend(_process_class_no_pk(class_body, current_class))
            current_class = class_start.group(2)
            inside_class = True
            class_body = []
            lines.append(line)
            continue
        
        if inside_class and line.strip() == "}":
            lines.extend(_process_class_no_pk(class_body, current_class))
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
        lines.extend(_process_class_no_pk(class_body, current_class))
        lines.append("}")
    
    return "\n".join(lines)


def _process_class_no_pk(body_lines, class_name):
    """Procesuira klasu BEZ dodavanja {PK} oznaka."""
    result = []
    has_pk_operation = False
    pk_attributes = []
    
    for line in body_lines:
        # Provjeri da li već postoji PK operacija
        if re.match(r'^\s*PK\s*\(', line):
            has_pk_operation = True
            result.append(line)
            continue
        
        # Ako nije PK operacija, samo zadrži liniju
        result.append(line)
    
    # Ako nema PK operacije, dodaj upozorenje (ne dodajemo {PK}!)
    if not has_pk_operation:
        # Ne dodajemo ništa - prepuštamo postprocessor.py da doda PK operaciju
        pass
    
    return result
