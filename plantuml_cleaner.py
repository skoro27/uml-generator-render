# v4.0 - Univerzalno rješenje - briše SAMO PK() iz potklasa, ne dira atribute
import re
import config


def remove_pk_from_subclasses(puml: str) -> str:
    """Uklanja PK() operacije i prazan -- samo iz potklasa. Atribute ne dira."""
    lines = puml.splitlines()

    subclasses = set()

    # Pronađi sve potklase
    for line in lines:
        m = re.match(r"^\s*(\w+)\s*<\|--\s*(\w+)", line)
        if m:
            subclasses.add(m.group(2))

        m = re.match(r"^\s*(\w+)\s*--\|>\s*(\w+)", line)
        if m:
            subclasses.add(m.group(1))

    result = []
    in_class = False
    current_class = None
    body = []

    def flush_class(class_name, body_lines):
        if class_name not in subclasses:
            return body_lines

        cleaned = []

        for line in body_lines:
            s = line.strip()

            # Izbaci PK operaciju
            if re.match(r"^PK\s*\(.*\)\s*$", s):
                continue

            # Izbaci {PK} ako se negdje pojavi
            line = re.sub(r"\{\s*PK\s*\}", "", line)

            cleaned.append(line)

        # Ukloni -- ako poslije njega nema nijedne operacije
        final = []
        for i, line in enumerate(cleaned):
            if line.strip() == "--":
                has_after = any(x.strip() for x in cleaned[i + 1:])
                if not has_after:
                    continue
            final.append(line)

        return final

    for line in lines:
        m = re.match(r"^\s*(class|interface|enum)\s+(\w+)\s*\{", line)

        if m:
            if in_class and current_class:
                result.extend(flush_class(current_class, body))
            in_class = True
            current_class = m.group(2)
            body = []
            result.append(line)
            continue

        if in_class and line.strip() == "}":
            result.extend(flush_class(current_class, body))
            result.append(line)
            in_class = False
            current_class = None
            body = []
            continue

        if in_class:
            body.append(line)
        else:
            result.append(line)

    return "\n".join(result)


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

    # v4.0: Univerzalno - briše SAMO PK() iz potklasa, atribute ne dira
    puml = remove_pk_from_subclasses(puml)

    puml = fix_attributes(puml)
    puml = fix_missing_entity_in_relation(puml)
    puml = fix_relations(puml)

    puml = rebuild_order(puml)

    if "class " not in puml:
        raise ValueError("Nema class definicija u PlantUML kodu.")

    return puml.strip()
