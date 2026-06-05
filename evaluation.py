import re
from pathlib import Path

def evaluate_puml(puml_code: str, check_rendering: bool = False) -> dict:
    """Evaluacija PlantUML koda sa novim pravilima za PK operacije."""
    
    results = {
        "has_startuml": "@startuml" in puml_code,
        "has_enduml": "@enduml" in puml_code,
        "class_count": 0,
        "attribute_count": 0,
        "pk_operation_count": 0,
        "invalid_pk_count": 0,
        "inherited_pk_count": 0,
        "relation_count": 0,
        "inheritance_count": 0,
        "one_to_one_count": 0,
        "one_to_many_count": 0,
        "many_to_many_count": 0,
        "association_with_name": 0,
        "rendered_ok": None
    }
    
    class_names = []
    inheritance_map = {}  # potklasa -> natklasa
    
    # 1. Pronađi sve klase
    class_pattern = r'^\s*(class|interface|enum)\s+(\w+)\s*\{'
    classes = re.findall(class_pattern, puml_code, re.MULTILINE)
    results["class_count"] = len(classes)
    class_names = [cls[1] for cls in classes]
    
    # 2. Pronađi nasljeđivanja
    inheritance_pattern = r'(\w+)\s*<\|--\s*(\w+)'
    for match in re.findall(inheritance_pattern, puml_code):
        natklasa, potklasa = match
        inheritance_map[potklasa] = natklasa
        results["inheritance_count"] += 1
    
    # 3. Parsiranje svake klase
    current_class = None
    inside_class = False
    
    for linija in puml_code.splitlines():
        # Početak klase
        class_start = re.match(r'^\s*(class|interface|enum)\s+(\w+)\s*\{', linija)
        if class_start:
            if current_class:
                results = _process_class(current_class, results, inheritance_map)
            current_class = {"name": class_start.group(2), "body": [], "is_potklasa": class_start.group(2) in inheritance_map}
            inside_class = True
            continue
        
        # Kraj klase
        if inside_class and linija.strip() == "}":
            if current_class:
                results = _process_class(current_class, results, inheritance_map)
            current_class = None
            inside_class = False
            continue
        
        # Sadržaj klase
        if inside_class and current_class:
            current_class["body"].append(linija)
    
    # Zadnja klasa
    if current_class:
        results = _process_class(current_class, results, inheritance_map)
    
    # 4. Pronađi relacije
    relation_pattern = r'(\w+)\s+(?:"[^"]*")?\s*(?:--|\.\.)\s*(?:[<>]*)\s*(?:"[^"]*")?\s*(\w+)'
    for linija in puml_code.splitlines():
        if "--" in linija and "<|--" not in linija:
            results["relation_count"] += 1
            
            # Korektan format asocijacije sa nazivom
            if ':"' in linija or '":' in linija:
                results["association_with_name"] += 1
            
            # Kardinalnosti
            if '"1"' in linija and not '"*"' in linija and not '"n"' in linija:
                results["one_to_one_count"] += 1
            elif '"1"' in linija and ('"*"' in linija or '"n"' in linija):
                results["one_to_many_count"] += 1
            elif ('"*"' in linija or '"n"' in linija) and ('"*"' in linija or '"n"' in linija):
                results["many_to_many_count"] += 1
    
    return results


def _process_class(class_data, results, inheritance_map):
    """Procesuira jednu klasu i ažurira rezultate."""
    
    class_name = class_data["name"]
    is_potklasa = class_name in inheritance_map
    
    class_body = "".join(class_data["body"])
    
    # 1. Pronađi PK operacije (ispravan format)
    pk_ops = re.findall(r'^\s*PK\s*\(([^)]+)\)', class_body, re.MULTILINE)
    results["pk_operation_count"] += len(pk_ops)
    
    # 2. Pronađi neispravne {PK} oznake (treba da bude 0)
    invalid_pk = re.findall(r'\{PK\}', class_body)
    results["invalid_pk_count"] += len(invalid_pk)
    
    # 3. Pronađi atribute (ne računajući one unutar PK operacije)
    # Prvo ukloni PK operacije iz body-ja za brojanje atributa
    body_without_pk = re.sub(r'PK\([^)]+\)', '', class_body)
    attributes = re.findall(r'^\s*(\w+)\s*:\s*(\w+)', body_without_pk, re.MULTILINE)
    results["attribute_count"] += len(attributes)
    
    # 4. Provjera: potklasa ne smije imati atribut 'id' (naslijeđeni PK)
    if is_potklasa:
        for attr in attributes:
            if attr[0].lower() == 'id':
                results["inherited_pk_count"] += 1
    
    return results
