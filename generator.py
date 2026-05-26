import json

import config
from prompts import PROMPT_TEMPLATE, REPAIR_PROMPT_TEMPLATE
from llm_clients import call_llm
from plantuml_cleaner import sanitize_puml
from renderer import run_plantuml
from evaluation import evaluate_puml


def generate_puml(description: str) -> str:
    """Generise PlantUML iz tekstualnog opisa."""
    prompt = PROMPT_TEMPLATE.format(description=description.strip())
    raw = call_llm(prompt)

    config.RAW_PUML_FILE.write_text(raw, encoding="utf-8")

    return sanitize_puml(raw)


def repair_puml(puml: str, error: str) -> str:
    """Pokusava LLM repair ako PlantUML render ne prodje."""
    prompt = REPAIR_PROMPT_TEMPLATE.format(
        puml=puml,
        error=error[:2000]
    )

    raw = call_llm(prompt)
    return sanitize_puml(raw)


def generate_render_evaluate(description: str) -> tuple[str, dict, str]:
    """
    Kompletan tok:
    opis -> PlantUML -> PNG -> evaluacija.

    Vraca:
    - puml kod
    - evaluation dict
    - putanju do PNG fajla
    """
    puml = generate_puml(description)
    config.PUML_FILE.write_text(puml, encoding="utf-8")

    code, err = run_plantuml(config.PUML_FILE)

    if code != 0:
        fixed = repair_puml(puml, err)
        config.FIXED_PUML_FILE.write_text(fixed, encoding="utf-8")
        config.PUML_FILE.write_text(fixed, encoding="utf-8")

        code, err = run_plantuml(config.PUML_FILE)

        if code != 0:
            evaluation = evaluate_puml(fixed, False)
            raise RuntimeError(
                "PlantUML render nije uspio ni nakon repair.\n\n"
                + err
                + "\n\nEvaluacija:\n"
                + json.dumps(evaluation, indent=2, ensure_ascii=False)
            )

        puml = fixed

    evaluation = evaluate_puml(puml, True)
    png_path = str(config.PUML_FILE.with_suffix(".png"))

    return puml, evaluation, png_path
