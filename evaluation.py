import re
import config


def evaluate_puml(puml: str, rendered_ok: bool) -> dict:
    """Osnovna evaluacija generisanog modela."""
    class_count = len(re.findall(r"^\s*class\s+", puml, flags=re.MULTILINE))
    relation_count = len(re.findall(r'".*?"\s+--\s+".*?"', puml))
    inheritance_count = len(re.findall(r"--\|>", puml))
    attribute_count = len(
        re.findall(
            r"^\s*\w+\s*:\s*(String|Integer|Date)\s*$",
            puml,
            flags=re.MULTILINE
        )
    )

    return {
        "provider": config.LLM_PROVIDER,
        "class_count": class_count,
        "relation_count": relation_count,
        "inheritance_count": inheritance_count,
        "attribute_count": attribute_count,
        "has_startuml": "@startuml" in puml,
        "has_enduml": "@enduml" in puml,
        "rendered_ok": rendered_ok
    }
