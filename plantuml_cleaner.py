# v3.1 - Potklase ne brišu atribute, prošireni allowed_types
import re
import config


# ========== POSTPROCESSOR LOGIKA (direktno integrisana) ==========

def _postprocess_puml(puml_code: str) -> str:
    """Popravlja PlantUML kod: uklanja {PK}, dodaje PK() ispod --, uklanja PK iz potklasa."""
    
    lines = puml_code.splitlines()
    new_lines = []
    
    inheritance_map = {}
    all_class_names = set()
    
    for linija in lines:
        inheritance_match = re.match(r'^\s*(\w+)\s*<\|--\s*(\w+)', linija)
        if inheritance_match:
            natklasa = inheritance_match.group(1)
            potklasa = inheritance_match.group(2)
            inheritance_map[potklasa] = natklasa
        
        inheritance_match2 = re.match(r'^\s*(\w+)\s*--\|>\s*(\w+)', linija)
        if inheritance_match2:
            potklasa = inheritance_match2.group(1)
            natklasa = inheritance_match2.group(2)
            inheritance_map[potklasa] = natklasa
        
        class_match = re.match(r'^\s*(class|interface|enum)\s+(\w+)\s*\{', linija)
        if class_match:
            all_class_names.add(class_match.group(2))
    
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
    result = _remove_duplicate_relations(result)
    
    return result


def _process_class_body(body_lines, class_name, inheritance_map, all_class_names):
    """Procesuira tijelo jedne klase. PK ide ispod -- crte, potklase NE dobijaju PK."""
    
    is_potklasa = class_name in inheritance_map
    body_text = "\n".join(body_lines)
    
    # 1. Ukloni sve {PK} oznake
    body_text = re.sub(r'\{\s*PK\s*\}\s*', '', body_text)
    
    # 2. Sačuvaj postojeće PK parametre prije brisanja
    existing_pk = re.findall(r'PK\(([^)]*)\)', body_text)
    
    # Zatim ukloni sve postojeće PK() operacije i -- linije
    body_text = re.sub(r'^\s*PK\([^)]*\)\s*$', '', body_text, flags=re.MULTILINE)
    body_text = re.sub(r'PK\([^)]*\)', '', body_text)
    body_text = re.sub(r'^\s*--\s*$', '', body_text, flags=re.MULTILINE)
    
    # 3. Ukloni reference na druge klase
    attr_pattern = r'^\s*(\w+)\s+(\w+)\s*$'
    for match in re.finditer(attr_pattern, body_text, re.MULTILINE):
        type_name = match.group(1)
        if type_name[0].isupper() and type_name in all_class_names:
            body_text = body_text.replace(match.group(0), "")
    
    # 4. Pronađi PK atribute
    pk_attributes = []
    attr_pattern2 = r'^\s*(\w+)\s*:\s*(\w+)'
    
    if is_potklasa:
        # POTKLASA: NE briši atribute, samo ne dodaj PK
        pass
    else:
        # NATKLASA - pronađi PK atribute za PK operaciju
        for match in re.finditer(attr_pattern2, body_text, re.MULTILINE):
            attr_name = match.group(1)
            attr_type = match.group(2)
            
            if attr_name.lower() in ['id', 'jmb', 'jmbg', 'sifra', 'oib', 'maticni_broj', 'broj', 'kod', 
                                       'serialnumber', 'uniquecode', 'memberid', 'boid', 'mjestoId',
                                       'rednibroj', 'naziv', 'opština', 'adresa', 'oznaka']:
                pk_attributes.append((attr_name, attr_type))
                body_text = body_text.replace(match.group(0), "")
    
    # 5. Sastavi rezultat: prvo atributi, pa --, pa PK (samo za natklase)
    result_lines = []
    
    for line in body_text.splitlines():
        stripped = line.strip()
        if stripped and ':' in stripped:
            result_lines.append(line)
    
    # SAMO za natklase dodaj -- i PK
    if not is_potklasa:
        if pk_attributes:
            result_lines.append("    --")
            pk_params = ", ".join([f"{name} : {tip}" for name, tip in pk_attributes])
            result_lines.append(f"    PK({pk_params})")
        elif existing_pk:
            result_lines.append("    --")
            result_lines.append(f"    PK({existing_pk[0]})")
    # POTKLASE: ne dodaj ništa (ni --, ni PK), atributi ostaju netaknuti
    
    return result_lines


def _remove_duplicate_relations(puml_code: str) -> str:
    """Uklanja duplirane relacije."""
    lines = puml_code.splitlines()
    seen_pairs = set()
    seen_exact = set()
    result = []
    
    for line in lines:
        s = line.strip()
        
        if not s:
            result.append(line)
            continue
        
        is_relation = False
        if '--' in s or '<|--' in s or '--|>' in s:
            if not re.match(r'^\s*\w+\s*:', s):
                is_relation = True
        
        if not is_relation:
            result.append(line)
            continue
        
        normalized = ' '.join(s.split())
        
        if normalized in seen_exact:
            continue
        
        seen_exact.add(normalized)
        
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

# ========== KRAJ POSTPROCESSOR LOGIKE ==========


def extract_plantuml(text: str) -> str:
    """Izdvaja PlantUML kod iz LLM odgovora, uklanjajući <think> tagove i markdown."""
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)
    text = re.sub(r"<think>.*", "", text, flags=re.DOTALL)
    text = text.replace("```plantuml", "").replace("```", "")

    start = text.find("@startuml")
    end = text.rfind("@enduml")

    if start != -1 and end != -1:
        return text[start:end + len("@enduml")].strip()

    plant_lines = []

    for line in text.splitlines():
        s = line.strip()

        if (
            s.startswith("@startuml")
            or s.startswith("@enduml")
            or s.startswith("class ")
            or s.startswith("interface ")
            or s.startswith("enum ")
            or s.startswith("skinparam")
            or s.startswith("hide ")
            or "--" in s
            or s == "{"
            or s == "}"
            or re.match(r"^\w+\s*:\s*(String|Integer|Date)\s*$", s)
        ):
            plant_lines.append(line)

    if plant_lines:
        return (
            "@startuml\n"
            "skinparam defaultFontName Arial\n"
            "skinparam classAttributeIconSize 0\n"
            "skinparam linetype ortho\n\n"
            + "\n".join(plant_lines)
            + "\n@enduml"
        )

    config.DEBUG_FILE.write_text(text, encoding="utf-8")

    raise ValueError(
        "Nedostaje @startuml ili @enduml u LLM odgovoru. "
        "Provjeri debug_llm_output.txt"
    )


def strip_diacritics(text: str) -> str:
    """Uklanja dijakritičke znakove iz teksta."""
    mapping = {
        "š": "s", "ć": "c", "č": "c", "ž": "z", "đ": "dj",
        "Š": "S", "Ć": "C", "Č": "C", "Ž": "Z", "Đ": "Dj",
    }

    for k, v in mapping.items():
        text = text.replace(k, v)

    return text


def ensure_header(puml: str) -> str:
    """Osigurava da PlantUML kod ima ispravan header sa skinparam podešavanjima."""
    puml = strip_diacritics(puml)
    lines = [line.rstrip() for line in puml.splitlines() if line.strip() != "```"]

    if not lines:
        raise ValueError("Prazan PlantUML kod.")

    if lines[0].strip() != "@startuml":
        lines.insert(0, "@startuml")

    text = "\n".join(lines)

    if "skinparam defaultFontName" not in text:
        lines.insert(1, "skinparam defaultFontName Arial")

    if "skinparam classAttributeIconSize" not in text:
        lines.insert(2, "skinparam classAttributeIconSize 0")

    if "skinparam linetype" not in text:
        lines.insert(3, "skinparam linetype ortho")

    if "@enduml" not in text:
        lines.append("@enduml")

    return "\n".join(lines)


def clean_identifier(name: str) -> str:
    """Čisti identifikator od specijalnih znakova i osigurava validan naziv."""
    name = strip_diacritics(name)
    name = re.sub(r"[^A-Za-z0-9_]", "", name)

    if not name:
        name = "X"

    if name[0].isdigit():
        name = "X" + name

    return name


def normalize_classes(puml: str) -> str:
    """Normalizuje definicije klasa, enum-a i interfejsa."""
    output = []

    for line in puml.splitlines():
        match = re.match(r"^(\s*)(class|enum|interface)\s+(.+?)\s*(\{)?\s*$", line)

        if match:
            indent = match.group(1)
            kind = match.group(2)
            name = match.group(3).strip().strip('"').strip("'")
            clean = clean_identifier(name)

            output.append(f"{indent}{kind} {clean} {{")
        else:
            output.append(line)

    return "\n".join(output)


def fix_attributes(puml: str) -> str:
    """Popravlja atribute - čuva -- i PK(), briše metode."""
    output = []
    in_class = False
    allowed_types = {"String", "Integer", "Date", "Boolean", "Double"}

    for line in puml.splitlines():
        s = line.strip()

        if re.match(r"^\s*(class|enum|interface)\s+\w+\s*\{", line):
            in_class = True
            output.append(line)
            continue

        if in_class and s == "}":
            in_class = False
            output.append(line)
            continue

        if in_class:
            if not s:
                continue

            # OBAVEZNO sačuvaj separator operacija
            if s == "--":
                output.append(line)
                continue

            # OBAVEZNO sačuvaj PK operaciju
            if "PK(" in s and ")" in s:
                output.append(line)
                continue

            # Briši ostale metode
            if "(" in s and ")" in s:
                continue

            if "<" in s or ">" in s or "[]" in s:
                continue

            if ":" in s:
                m = re.match(r"^([A-Za-z_]\w*)\s*:\s*([A-Za-z_]\w*)$", s)
                if m:
                    attr = m.group(1)
                    typ = m.group(2)

                    if typ in allowed_types:
                        indent = re.match(r"^(\s*)", line).group(1)
                        output.append(f"{indent}{attr} : {typ}")

                continue

            m = re.match(r"^(String|Integer|Date|Boolean|Double)\s+([A-Za-z_]\w*)$", s)
            if m:
                typ = m.group(1)
                attr = m.group(2)
                indent = re.match(r"^(\s*)", line).group(1)
                output.append(f"{indent}{attr} : {typ}")

            continue

        output.append(line)

    return "\n".join(output)


def move_relations_outside_classes(puml: str) -> str:
    """Premešta relacije koje su greškom unutar klasa na kraj dokumenta."""
    lines = puml.splitlines()
    output = []
    relations = []
    in_class = False

    for line in lines:
        s = line.strip()

        if re.match(r"^\s*(class|enum|interface)\s+\w+\s*\{", line):
            in_class = True
            output.append(line)
            continue

        if in_class and s == "}":
            in_class = False
            output.append(line)
            continue

        if in_class and any(x in s for x in ["--", "-->", "<--", "*--", "o--"]):
            relations.append(s)
            continue

        output.append(line)

    output.extend(relations)
    return "\n".join(output)


def fix_missing_entity_in_relation(puml: str) -> str:
    """Dodatna korekcija za slučajeve gde desni entitet nedostaje u relaciji."""
    lines = []

    for line in puml.splitlines():
        m = re.match(
            r'^\s*(\w+)\s+"([^"]+)"\s+(--|-->|<--|\*--|o--)'
            r'\s+"([^"]+)"\s*:\s*(\w+)\s*$',
            line
        )
        if m:
            left, left_card, arrow, right_card, label = m.groups()
            if label and label[0].isupper():
                line = f'{left} "{left_card}" {arrow} "{right_card}" {label}'

        lines.append(line)

    return "\n".join(lines)


def fix_relations(puml: str) -> str:
    """Popravlja sintaksu relacija u PlantUML kodu."""
    lines = []

    for line in puml.splitlines():
        line = line.replace('"0.."', '"0..*"')
        line = re.sub(r'("\S+")\s+(--|-->)\s+("\S+")\s+(--|-->)\s+', r'\1 \2 \3 ', line)

        m = re.match(
            r'^\s*(\w+)\s+"([^"]+)"\s+(--|-->|<--|\*--|o--)'
            r'\s+"([^"]+)"\s*:\s*(.*?)\s*>\s*(\w+)\s*$',
            line
        )
        if m:
            left, left_card, arrow, right_card, label, right = m.groups()
            line = f'{left} "{left_card}" {arrow} "{right_card}" {right} : {label}'
            lines.append(line)
            continue

        m = re.match(
            r'^\s*(\w+)\s+"([^"]+)"\s+(--|-->|<--|\*--|o--)'
            r'\s+"([^"]+)"\s*:\s*(\w+)\s*(?::\s*(.*))?$',
            line
        )
        if m:
            left, left_card, arrow, right_card, right, label = m.groups()
            if label:
                line = f'{left} "{left_card}" {arrow} "{right_card}" {right} : {label}'
            else:
                line = f'{left} "{left_card}" {arrow} "{right_card}" {right}'
            lines.append(line)
            continue

        m = re.match(
            r'^\s*(\w+)\s+"([^"]+)"\s+(--|-->|<--|\*--|o--)'
            r'\s+(\w+)\s+"([^"]+)"\s*(?::\s*(.*))?$',
            line
        )
        if m:
            left, left_card, arrow, right, right_card, label = m.groups()
            if label:
                line = f'{left} "{left_card}" {arrow} "{right_card}" {right} : {label}'
            else:
                line = f'{left} "{left_card}" {arrow} "{right_card}" {right}'
            lines.append(line)
            continue

        m = re.match(
            r'^\s*(\w+)\s+"([^"]+)"\s+(--|-->|<--|\*--|o--)'
            r'\s+"([^"]+)"\s+(\w+)\s*(?::\s*(.*))?$',
            line
        )
        if m:
            left, left_card, arrow, right_card, right, label = m.groups()
            if label:
                line = f'{left} "{left_card}" {arrow} "{right_card}" {right} : {label}'
            else:
                line = f'{left} "{left_card}" {arrow} "{right_card}" {right}'
            lines.append(line)
            continue

        lines.append(line)

    return "\n".join(lines)


def rebuild_order(puml: str) -> str:
    """Reorganizuje PlantUML kod u pravilan redosled."""
    blocks = []
    relations = []
    others = []
    in_block = False
    current = []

    for line in puml.splitlines():
        s = line.strip()

        if s in ["@startuml", "@enduml"]:
            continue

        if s.startswith("skinparam"):
            continue

        if re.match(r"^\s*(class|enum|interface)\s+\w+\s*\{", line):
            in_block = True
            current = [line]
            continue

        if in_block:
            current.append(line)

            if s == "}":
                blocks.append("\n".join(current))
                in_block = False

            continue

        if any(x in s for x in ["--", "-->", "<--", "*--", "o--"]):
            relations.append(line)
        else:
            if s:
                others.append(line)

    final = [
        "@startuml",
        "skinparam defaultFontName Arial",
        "skinparam classAttributeIconSize 0",
        "skinparam linetype ortho",
        ""
    ]

    final.extend(blocks)

    if relations:
        final.append("")
        final.extend(relations)

    if others:
        final.append("")
        final.extend(others)

    final.append("@enduml")

    return "\n".join(final)


def sanitize_puml(puml: str) -> str:
    """Glavna funkcija za sanitizaciju PlantUML koda."""
    puml = re.sub(r"(\w+)extends(\w+)", r"\1 --|> \2", puml)

    puml = extract_plantuml(puml)
    puml = ensure_header(puml)

    puml = normalize_classes(puml)
    puml = move_relations_outside_classes(puml)

    # v3.1: Postprocessor direktno integrisan - briše PK iz potklasa, NE diraj atribute
    puml = _postprocess_puml(puml)

    # TEST: privremeno bez fix_attributes
    # puml = fix_attributes(puml)
    puml = fix_missing_entity_in_relation(puml)
    puml = fix_relations(puml)

    puml = rebuild_order(puml)

    if "class " not in puml:
        raise ValueError("Nema class definicija u PlantUML kodu.")

    return puml.strip()
