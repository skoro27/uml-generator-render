import re


def parse_classes_from_puml(puml_code: str) -> list:
    classes = []
    current_class = None
    in_class = False

    for line in puml_code.splitlines():
        s = line.strip()

        match = re.match(r"^\s*(class|interface|enum)\s+(\w+)\s*\{", line)
        if match:
            if current_class:
                classes.append(current_class)
            current_class = {
                "name": match.group(2),
                "type": match.group(1),
                "attributes": []
            }
            in_class = True
            continue

        if in_class and s == "}":
            if current_class:
                classes.append(current_class)
            current_class = None
            in_class = False
            continue

        if in_class and current_class is not None:
            attr_match = re.match(r"^\s*(\w+)\s*:\s*(\w+)", s)
            if attr_match:
                current_class["attributes"].append({
                    "name": attr_match.group(1),
                    "type": attr_match.group(2)
                })

    if current_class:
        classes.append(current_class)

    return classes


def parse_relations_from_puml(puml_code: str) -> list:
    relations = []

    for line in puml_code.splitlines():
        inh_match = re.match(r"^\s*(\w+)\s*--\|>\s*(\w+)", line)
        if inh_match:
            relations.append({
                "type": "inheritance",
                "from": inh_match.group(2),
                "to": inh_match.group(1)
            })
            continue

        comp_match = re.match(
            r'^\s*(\w+)\s+"?([^"]*)"?\s*\*--\s*"?([^"]*)"?\s*(\w+)', line
        )
        if comp_match:
            left, left_card, right_card, right = comp_match.groups()
            relations.append({
                "type": "composition",
                "from": left,
                "to": right,
                "cardinality_left": left_card.strip('"') or "1",
                "cardinality_right": right_card.strip('"') or "1"
            })
            continue

        assoc_match = re.match(
            r'^\s*(\w+)\s+"?([^"]*)"?\s*(--|-->)\s*"?([^"]*)"?\s*(\w+)', line
        )
        if assoc_match:
            left, left_card, arrow, right_card, right = assoc_match.groups()
            relations.append({
                "type": "association",
                "from": left,
                "to": right,
                "cardinality_left": left_card.strip('"') or "1",
                "cardinality_right": right_card.strip('"') or "1"
            })

    return relations


def map_type_to_sql(uml_type: str) -> str:
    type_mapping = {
        "String": "VARCHAR(255)",
        "Integer": "INTEGER",
        "Date": "DATE",
        "Boolean": "BOOLEAN",
        "Float": "FLOAT",
        "Double": "DOUBLE PRECISION",
        "Text": "TEXT",
        "Long": "BIGINT",
    }
    return type_mapping.get(uml_type, "VARCHAR(255)")


def generate_sql_from_puml(puml_code: str) -> str:
    classes = parse_classes_from_puml(puml_code)
    relations = parse_relations_from_puml(puml_code)

    if not classes:
        return "-- Nema pronađenih klasa u PlantUML kodu"

    sql_lines = ["-- Automatski generisan SQL kod iz UML dijagrama", ""]
    class_map = {c["name"]: c for c in classes}

    for cls in classes:
        table_name = cls["name"].lower()
        sql_lines.append(f"CREATE TABLE {table_name} (")
        sql_lines.append(f"    id INTEGER PRIMARY KEY AUTOINCREMENT,  -- PK")

        for attr in cls["attributes"]:
            if attr["name"].lower() != "id":
                sql_type = map_type_to_sql(attr["type"])
                sql_lines.append(f"    {attr['name'].lower()} {sql_type},")

        for rel in relations:
            if rel["type"] == "inheritance":
                if rel["to"] == cls["name"]:
                    parent_table = rel["from"].lower()
                    sql_lines.append(f"    {parent_table}_id INTEGER,  -- FK")

            elif rel["type"] == "composition":
                if rel["to"] == cls["name"]:
                    left_card = rel["cardinality_left"].replace('"', '')
                    if left_card in ("1", "1..1"):
                        fk_table = rel["from"].lower()
                        sql_lines.append(f"    {fk_table}_id INTEGER NOT NULL,  -- FK")

                if rel["from"] == cls["name"]:
                    right_card = rel["cardinality_right"].replace('"', '')
                    if right_card in ("1", "1..1"):
                        fk_table = rel["to"].lower()
                        sql_lines.append(f"    {fk_table}_id INTEGER NOT NULL,  -- FK")

        sql_lines[-1] = sql_lines[-1].rstrip(',')
        sql_lines.append(");")
        sql_lines.append("")

    for rel in relations:
        if rel["type"] == "inheritance":
            child_table = rel["to"].lower()
            parent_table = rel["from"].lower()
            sql_lines.append(
                f"ALTER TABLE {child_table} ADD CONSTRAINT "
                f"fk_{child_table}_{parent_table} "
                f"FOREIGN KEY ({parent_table}_id) "
                f"REFERENCES {parent_table}(id);"
            )
            sql_lines.append("")

        elif rel["type"] == "composition":
            left_card = rel["cardinality_left"].replace('"', '')
            right_card = rel["cardinality_right"].replace('"', '')

            if left_card in ("1", "1..1"):
                child_table = rel["to"].lower()
                parent_table = rel["from"].lower()
                sql_lines.append(
                    f"ALTER TABLE {child_table} ADD CONSTRAINT "
                    f"fk_{child_table}_{parent_table} "
                    f"FOREIGN KEY ({parent_table}_id) "
                    f"REFERENCES {parent_table}(id);"
                )
                sql_lines.append("")

            if right_card in ("1", "1..1"):
                child_table = rel["from"].lower()
                parent_table = rel["to"].lower()
                sql_lines.append(
                    f"ALTER TABLE {child_table} ADD CONSTRAINT "
                    f"fk_{child_table}_{parent_table} "
                    f"FOREIGN KEY ({parent_table}_id) "
                    f"REFERENCES {parent_table}(id);"
                )
                sql_lines.append("")

    return "\n".join(sql_lines)