import re


def parse_classes_from_puml(puml_code: str) -> list:
    """
    Parsira klase i njihove atribute iz PlantUML koda.
    Vraća listu rečnika sa nazivom klase i atributima.
    """
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
    """
    Parsira relacije iz PlantUML koda.
    Podržava formate:
    - KlasaA --|> KlasaB (nasleđivanje)
    - KlasaA "1" -- "1..*" KlasaB : labela
    - KlasaA "1" -- "1..*" KlasaB
    - KlasaA -- KlasaB
    """
    relations = []
    
    for line in puml_code.splitlines():
        s = line.strip()
        
        if not s:
            continue
        
        # Nasleđivanje: KlasaA --|> KlasaB
        inh_match = re.match(r"^\s*(\w+)\s*--\|>\s*(\w+)", s)
        if inh_match:
            relations.append({
                "type": "inheritance",
                "from": inh_match.group(2),
                "to": inh_match.group(1)
            })
            continue
        
        # Kompozicija: KlasaA "1" *-- "0..*" KlasaB : labela
        comp_match = re.match(
            r'^\s*(\w+)\s+"?([^"]*)"?\s+\*--\s+"?([^"]*)"?\s+(\w+)\s*(?::\s*(.*))?$',
            s
        )
        if comp_match:
            left, left_card, right_card, right, label = comp_match.groups()
            relations.append({
                "type": "composition",
                "from": left,
                "to": right,
                "cardinality_left": left_card.strip('"') or "1",
                "cardinality_right": right_card.strip('"') or "1",
                "label": label.strip() if label else ""
            })
            continue
        
        # Asocijacija: KlasaA "1" -- "0..*" KlasaB : labela
        assoc_match = re.match(
            r'^\s*(\w+)\s+"?([^"]*)"?\s+(--|-->)\s+"?([^"]*)"?\s+(\w+)\s*(?::\s*(.*))?$',
            s
        )
        if assoc_match:
            left, left_card, arrow, right_card, right, label = assoc_match.groups()
            relations.append({
                "type": "association",
                "from": left,
                "to": right,
                "cardinality_left": left_card.strip('"') or "1",
                "cardinality_right": right_card.strip('"') or "1",
                "label": label.strip() if label else ""
            })
            continue
        
        # Jednostavna: KlasaA -- KlasaB
        simple_match = re.match(r'^\s*(\w+)\s+(--|-->)\s+(\w+)\s*$', s)
        if simple_match:
            left, arrow, right = simple_match.groups()
            relations.append({
                "type": "association",
                "from": left,
                "to": right,
                "cardinality_left": "1",
                "cardinality_right": "1",
                "label": ""
            })
    
    return relations


def map_type_to_sql(uml_type: str) -> str:
    """Mapira UML tip u SQL tip."""
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


def _add_fk_for_relation(rel: dict, class_name: str, sql_lines: list, added_fks: dict):
    """
    Pomoćna funkcija za dodavanje FK u CREATE TABLE.
    """
    left = rel["from"]
    right = rel["to"]
    left_card = rel["cardinality_left"]
    right_card = rel["cardinality_right"]
    
    left_is_one = left_card in ("1", "1..1", "")
    right_is_many = "*" in right_card or "n" in right_card.lower() or "..*" in right_card
    right_is_one = right_card in ("1", "1..1", "")
    left_is_many = "*" in left_card or "n" in left_card.lower() or "..*" in left_card
    
    if left_is_one and right_is_many:
        if class_name == right:
            fk_table = left.lower()
            fk_name = f"{fk_table}_id"
            if fk_name not in added_fks.get(class_name, set()):
                sql_lines.append(f"    {fk_name} INTEGER,  -- FK -> {fk_table}")
                if class_name not in added_fks:
                    added_fks[class_name] = set()
                added_fks[class_name].add(fk_name)
    
    elif right_is_one and left_is_many:
        if class_name == left:
            fk_table = right.lower()
            fk_name = f"{fk_table}_id"
            if fk_name not in added_fks.get(class_name, set()):
                sql_lines.append(f"    {fk_name} INTEGER,  -- FK -> {fk_table}")
                if class_name not in added_fks:
                    added_fks[class_name] = set()
                added_fks[class_name].add(fk_name)
    
    elif left_is_one and right_is_one:
        if class_name == right:
            fk_table = left.lower()
            fk_name = f"{fk_table}_id"
            if fk_name not in added_fks.get(class_name, set()):
                sql_lines.append(f"    {fk_name} INTEGER,  -- FK -> {fk_table}")
                if class_name not in added_fks:
                    added_fks[class_name] = set()
                added_fks[class_name].add(fk_name)


def _add_alter_table(rel: dict, sql_lines: list):
    """
    Pomoćna funkcija za dodavanje ALTER TABLE naredbi.
    """
    left = rel["from"]
    right = rel["to"]
    left_card = rel["cardinality_left"]
    right_card = rel["cardinality_right"]
    
    left_is_one = left_card in ("1", "1..1", "")
    right_is_one = right_card in ("1", "1..1", "")
    right_is_many = "*" in right_card or "n" in right_card.lower() or "..*" in right_card
    left_is_many = "*" in left_card or "n" in left_card.lower() or "..*" in left_card
    
    child_table = None
    parent_table = None
    
    if left_is_one and right_is_many:
        child_table = right.lower()
        parent_table = left.lower()
    elif right_is_one and left_is_many:
        child_table = left.lower()
        parent_table = right.lower()
    elif left_is_one and right_is_one:
        child_table = right.lower()
        parent_table = left.lower()
    
    if child_table and parent_table:
        sql_lines.append(
            f"ALTER TABLE {child_table} ADD CONSTRAINT "
            f"fk_{child_table}_{parent_table} "
            f"FOREIGN KEY ({parent_table}_id) "
            f"REFERENCES {parent_table}(id);"
        )
        sql_lines.append("")


def generate_sql_from_puml(puml_code: str) -> str:
    """
    Generiše SQL CREATE TABLE naredbe iz PlantUML koda.
    """
    classes = parse_classes_from_puml(puml_code)
    relations = parse_relations_from_puml(puml_code)
    
    if not classes:
        return "-- Nema pronađenih klasa u PlantUML kodu"
    
    sql_lines = ["-- Automatski generisan SQL kod iz UML dijagrama", ""]
    
    added_fks = {}
    
    for cls in classes:
        table_name = cls["name"].lower()
        class_name = cls["name"]
        added_fks[class_name] = set()
        
        sql_lines.append(f"CREATE TABLE {table_name} (")
        sql_lines.append(f"    id INTEGER PRIMARY KEY AUTOINCREMENT,  -- PK")
        
        for attr in cls["attributes"]:
            if attr["name"].lower() != "id":
                sql_type = map_type_to_sql(attr["type"])
                sql_lines.append(f"    {attr['name'].lower()} {sql_type},")
        
        for rel in relations:
            if rel["type"] == "inheritance":
                if rel["to"] == class_name:
                    parent_table = rel["from"].lower()
                    fk_name = f"{parent_table}_id"
                    if fk_name not in added_fks[class_name]:
                        sql_lines.append(f"    {fk_name} INTEGER,  -- FK -> {parent_table}")
                        added_fks[class_name].add(fk_name)
            
            elif rel["type"] in ("composition", "association"):
                _add_fk_for_relation(rel, class_name, sql_lines, added_fks)
        
        sql_lines[-1] = sql_lines[-1].rstrip(',')
        sql_lines.append(");")
        sql_lines.append("")
    
    sql_lines.append("-- Strani ključevi (ALTER TABLE naredbe)")
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
        
        elif rel["type"] in ("composition", "association"):
            _add_alter_table(rel, sql_lines)
    
    return "\n".join(sql_lines)
