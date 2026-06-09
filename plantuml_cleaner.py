# v5.1 - Dvostruko pozivanje remove_pk_from_subclasses + popravljen regex
import re
import config


def strip_diacritics(text: str) -> str:
    mapping = {
        "š": "s", "ć": "c", "č": "c", "ž": "z", "đ": "dj",
        "Š": "S", "Ć": "C", "Č": "C", "Ž": "Z", "Đ": "Dj",
    }
    for k, v in mapping.items():
        text = text.replace(k, v)
    return text


def extract_plantuml(text: str) -> str:
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)
    text = re.sub(r"<think>.*", "", text, flags=re.DOTALL)
    text = text.replace("```plantuml", "").replace("```", "")

    start = text.find("@startuml")
    end = text.rfind("@enduml")

    if start != -1 and end != -1:
        return text[start:end + len("@enduml")].strip()

    config.DEBUG_FILE.write_text(text, encoding="utf-8")
    raise ValueError("Nedostaje @startuml ili @enduml u LLM odgovoru.")


def ensure_header(puml: str) -> str:
    puml = strip_diacritics(puml)
    lines = [line.rstrip() for line in puml.splitlines() if line.strip() != "```"]

    if not lines:
        raise ValueError("Prazan PlantUML kod.")

    if lines[0].strip() != "@startuml":
        lines.insert(0, "@startuml")

    joined = "\n".join(lines)
    insert_at = 1

    if "skinparam defaultFontName" not in joined:
        lines.insert(insert_at, "skinparam defaultFontName Arial")
        insert_at += 1

    if "skinparam classAttributeIconSize" not in joined:
        lines.insert(insert_at, "skinparam classAttributeIconSize 0")
        insert_at += 1

    if "skinparam linetype" not in joined:
        lines.insert(insert_at, "skinparam linetype ortho")

    if "@enduml" not in "\n".join(lines):
        lines.append("@enduml")

    return "\n".join(lines)


def clean_identifier(name: str) -> str:
    name = strip_diacritics(name)
    name = name.strip().strip('"').strip("'")
    name = re.sub(r"[^A-Za-z0-9_]", "", name)

    if not name:
        name = "X"

    if name[0].isdigit():
        name = "X" + name

    return name


def normalize_classes_and_relations(puml: str) -> str:
    output = []

    for line in puml.splitlines():
        s = line.strip()

        class_match = re.match(r"^(\s*)(class|interface|enum)\s+([^\s{]+)\s*(\{)?\s*$", line)
        if class_match:
            indent, kind, name, _ = class_match.groups()
            output.append(f"{indent}{kind} {clean_identifier(name)} {{")
            continue

        inheritance_match = re.match(r"^\s*([^\s]+)\s*<\|--\s*([^\s]+)\s*$", s)
        if inheritance_match:
            parent, child = inheritance_match.groups()
            output.append(f"{clean_identifier(parent)} <|-- {clean_identifier(child)}")
            continue

        inheritance_match2 = re.match(r"^\s*([^\s]+)\s*--\|>\s*([^\s]+)\s*$", s)
        if inheritance_match2:
            child, parent = inheritance_match2.groups()
            output.append(f"{clean_identifier(child)} --|> {clean_identifier(parent)}")
            continue

        output.append(strip_diacritics(line))

    return "\n".join(output)


def move_relations_outside_classes(puml: str) -> str:
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

        if in_class and s != "--" and any(x in s for x in ["<|--", "--|>", "-->", "<--", "*--", "o--"]):
            relations.append(s)
            continue

        output.append(line)

    output.extend(relations)
    return "\n".join(output)


def remove_pk_from_subclasses(puml: str) -> str:
    lines = puml.splitlines()
    subclasses = set()

    for line in lines:
        s = line.strip()

        m = re.match(r"^([A-Za-z_]\w*)\s*<\|--\s*([A-Za-z_]\w*)", s)
        if m:
            subclasses.add(m.group(2))

        m = re.match(r"^([A-Za-z_]\w*)\s*--\|>\s*([A-Za-z_]\w*)", s)
        if m:
            subclasses.add(m.group(1))

    result = []
    in_class = False
    current_class = None
    body = []

    def flush_class(class_name: str, body_lines: list) -> list:
        if class_name not in subclasses:
            return body_lines

        cleaned = []

        for line in body_lines:
            if re.match(r"^\s*PK\s*\(.*\)\s*$", line):
                continue

            line = re.sub(r"\{\s*PK\s*\}", "", line)
            cleaned.append(line)

        final = []

        for i, line in enumerate(cleaned):
            if line.strip() == "--":
                has_operation_after = any(
                    x.strip() and "(" in x and ")" in x
                    for x in cleaned[i + 1:]
                )
                if not has_operation_after:
                    continue

            final.append(line)

        return final

    for line in lines:
        m = re.match(r"^\s*(class|interface|enum)\s+([A-Za-z_]\w*)\s*\{", line)

        if m:
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


def fix_attributes(puml: str) -> str:
    output = []
    in_class = False
    allowed_types = {"String", "Integer", "Date", "Boolean", "Double", "Float", "Long"}

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

            if s == "--":
                output.append(line)
                continue

            if re.match(r"^\s*PK\s*\(.*\)\s*$", line):
                output.append(line)
                continue

            if "(" in s and ")" in s:
                continue

            if "<" in s or ">" in s or "[]" in s:
                continue

            m = re.match(r"^([A-Za-z_]\w*)\s*:\s*([A-Za-z_]\w*)$", s)
            if m:
                attr, typ = m.groups()
                if typ in allowed_types:
                    indent = re.match(r"^(\s*)", line).group(1)
                    output.append(f"{indent}{attr} : {typ}")
                continue

            m = re.match(r"^(String|Integer|Date|Boolean|Double|Float|Long)\s+([A-Za-z_]\w*)$", s)
            if m:
                typ, attr = m.groups()
                indent = re.match(r"^(\s*)", line).group(1)
                output.append(f"{indent}{attr} : {typ}")
                continue

            continue

        output.append(line)

    return "\n".join(output)


def fix_relations(puml: str) -> str:
    lines = []

    for line in puml.splitlines():
        line = strip_diacritics(line)
        line = line.replace('"0.."', '"0..*"')
        lines.append(line)

    return "\n".join(lines)


def rebuild_order(puml: str) -> str:
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

        if any(x in s for x in ["<|--", "--|>", "--", "-->", "<--", "*--", "o--"]):
            relations.append(line)
        elif s:
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
    puml = re.sub(r"(\w+)extends(\w+)", r"\1 --|> \2", puml)

    puml = extract_plantuml(puml)
    puml = ensure_header(puml)

    puml = normalize_classes_and_relations(puml)
    puml = move_relations_outside_classes(puml)

    # Prvo brisanje PK iz potklasa
    puml = remove_pk_from_subclasses(puml)

    puml = fix_attributes(puml)

    # Drugo brisanje PK iz potklasa, za sigurnost
    puml = remove_pk_from_subclasses(puml)

    puml = fix_relations(puml)
    puml = rebuild_order(puml)

    if "class " not in puml:
        raise ValueError("Nema class definicija u PlantUML kodu.")

    return puml.strip()
