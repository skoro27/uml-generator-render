import re


def parse_classes_from_puml(puml_code: str) -> list:
    """Parsira klase i njihove atribute iz PlantUML koda."""
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
    """Parsira relacije iz PlantUML koda."""
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


def _is_spojna_tabela(class_name: str, relations: list, classes: list) -> bool:
    """
    Proverava da li je klasa spojna tabela (many-to-many).
    Spojna tabela ima FK ka dve različite tabele i nema svojih atributa osim id.
    """
    fk_count = 0
    fk_targets = set()
    
    for rel in relations:
        if rel["type"] in ("composition", "association"):
            left = rel["from"]
            right = rel["to"]
            left_card = rel["cardinality_left"]
            right_card = rel["cardinality_right"]
            
            # Ako je klasa na "many" strani i ima FK ka "one" strani
            left_is_one = left_card in ("1", "1..1", "")
            right_is_many = "*" in right_card or "n" in right_card.lower() or "..*" in right_card
            right_is_one = right_card in ("1", "1..1", "")
            left_is_many = "*" in left_card or "n" in left_card.lower() or "..*" in left_card
            
            if left_is_one and right_is_many and right == class_name:
                fk_count += 1
                fk_targets.add(left)
            elif right_is_one and left_is_many and left == class_name:
                fk_count += 1
                fk_targets.add(right)
            elif left_is_one and right_is_one:
                if right == class_name:
                    fk_count += 1
                    fk_targets.add(left)
                elif left == class_name:
                    fk_count += 1
                    fk_targets.add(right)
    
    # Spojna tabela ima FK ka bar 2 različite tabele
    return fk_count >= 2 and len(fk_targets) >= 2


def _get_spojna_fks(class_name: str, relations: list) -> list:
    """Vraća listu FK-ova za spojnu tabelu."""
    fks = []
    
    for rel in relations:
        if rel["type"] in ("composition", "association"):
            left = rel["from"]
            right = rel["to"]
            left_card = rel["cardinality_left"]
            right_card = rel["cardinality_right"]
            
            left_is_one = left_card in ("1", "1..1", "")
            right_is_many = "*" in right_card or "n" in right_card.lower() or "..*" in right_card
            right_is_one = right_card in ("1", "1..1", "")
            left_is_many = "*" in left_card or "n" in left_card.lower() or "..*" in left_card
            
            if left_is_one and right_is_many and right == class_name:
                fks.append(left)
            elif right_is_one and left_is_many and left == class_name:
                fks.append(right)
            elif left_is_one and right_is_one:
                if right == class_name:
                    fks.append(left)
                elif left == class_name:
                    fks.append(right)
    
    return fks


def _add_fk_for_relation(rel: dict, class_name: str, sql_lines: list, added_fks: dict):
    """Dodaje FK u CREATE TABLE."""
    left = rel["from"]
    right = rel["to"]
    left_card = rel["cardinality_left"]
    right_card = rel["cardinality_right"]
    
    left_is_one = left_card in ("1", "1..1", "")
    right_is_many = "*" in right_card or "n" in right_card.lower() or "..*" in right_card
    right_is_one = right_card in ("1", "1..1", "")
    left_is_many = "*" in left_card or "n" in left_card.lower() or "..*" in left_card
    
    # One-to-many: FK na "many" strani
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
    
    # One-to-one: FK na desnu stranu (osim ako je leva klasa roditelj)
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
    """Dodaje ALTER TABLE naredbe."""
    left = rel["from"]
    right = rel["to"]
    left_card = rel["cardinality_left"]
    right_card = rel["cardinality_right"]
    
    left_is_one = left_card in ("1", "1..1", "")
    right_is_many = "*" in right_card or "n" in right_card.lower() or "..*" in right_card
    right_is_one = right_card in ("1", "1..1", "")
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
    """Generiše SQL CREATE TABLE naredbe iz PlantUML koda."""
    classes = parse_classes_from_puml(puml_code)
    relations = parse_relations_from_puml(puml_code)
    
    if not classes:
        return "-- Nema pronađenih klasa u PlantUML kodu"
    
    # Skup klasa koje su spojne tabele
    class_names = [c["name"] for c in classes]
    spojne_tabele = set()
    for cls in classes:
        if _is_spojna_tabela(cls["name"], relations, classes):
            spojne_tabele.add(cls["name"])
    
    sql_lines = ["-- Automatski generisan SQL kod iz UML dijagrama", ""]
    added_fks = {}
    
    for cls in classes:
        table_name = cls["name"].lower()
        class_name = cls["name"]
        added_fks[class_name] = set()
        
        sql_lines.append(f"CREATE TABLE {table_name} (")
        sql_lines.append(f"    id INTEGER PRIMARY KEY AUTOINCREMENT,  -- PK")
        
        # Za spojne tabele, ne dodajemo atribute iz UML-a (oni su FK-ovi)
        if class_name in spojne_tabele:
            spojna_fks = _get_spojna_fks(class_name, relations)
            for fk_target in spojna_fks:
                fk_name = f"{fk_target.lower()}_id"
                if fk_name not in added_fks[class_name]:
                    sql_lines.append(f"    {fk_name} INTEGER,  -- FK -> {fk_target.lower()}")
                    added_fks[class_name].add(fk_name)
        else:
            # Dodaj atribute
            for attr in cls["attributes"]:
                if attr["name"].lower() != "id":
                    sql_type = map_type_to_sql(attr["type"])
                    sql_lines.append(f"    {attr['name'].lower()} {sql_type},")
            
            # Dodaj FK-ove za obične klase
            for rel in relations:
                if rel["type"] == "inheritance":
                    if rel["to"] == class_name:
                        parent_table = rel["from"].lower()
                        fk_name = f"{parent_table}_id"
                        if fk_name not in added_fks[class_name]:
                            sql_lines.append(f"    {fk_name} INTEGER,  -- FK -> {parent_table}")
                            added_fks[class_name].add(fk_name)
                
                elif rel["type"] in ("composition", "association"):
                    # Ne dodaj FK ako je veza ka spojnoj tabeli
                    other = rel["from"] if rel["to"] == class_name else rel["to"]
                    if other not in spojne_tabele:
                        _add_fk_for_relation(rel, class_name, sql_lines, added_fks)
        
        # Ukloni poslednji zarez samo ako postoji
        if sql_lines[-1].endswith(','):
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
            # Preskoči ALTER za spojne tabele (već su u CREATE TABLE)
            left = rel["from"]
            right = rel["to"]
            if left not in spojne_tabele and right not in spojne_tabele:
                _add_alter_table(rel, sql_lines)
    
    return "\n".join(sql_lines)
