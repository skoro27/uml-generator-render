import json

import config
from generator import generate_render_evaluate


def main():
    print("========================================")
    print(" LLM PlantUML generator")
    print(" Provider:", config.LLM_PROVIDER)
    print("========================================")
    print("Unesi opis sistema. Prazna linija za kraj:")

    lines = []

    while True:
        line = input()
        if not line.strip():
            break
        lines.append(line)

    description = "\n".join(lines).strip()

    if not description:
        print("Nisi unio opis.")
        return

    print("\n--- Generisem PlantUML ---\n")

    try:
        puml, evaluation, png_path = generate_render_evaluate(description)

        print("\nUspjeh!")
        print("Generisano:")
        print("- raw_model.puml")
        print("- model.puml")
        print("- model.png")
        print("\nEvaluacija:")
        print(json.dumps(evaluation, indent=2, ensure_ascii=False))

    except Exception as e:
        print("\n[GRESKA]")
        print(e)


if __name__ == "__main__":
    main()
