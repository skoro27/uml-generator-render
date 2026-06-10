import requests
import zlib
from pathlib import Path


PLANTUML_ALPHABET = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz-_"


def plantuml_encode(text: str) -> str:
    data = text.encode("utf-8")
    compressor = zlib.compressobj(level=9, wbits=-15)
    compressed = compressor.compress(data) + compressor.flush()

    def encode3bytes(b1, b2, b3):
        c1 = b1 >> 2
        c2 = ((b1 & 0x3) << 4) | (b2 >> 4)
        c3 = ((b2 & 0xF) << 2) | (b3 >> 6)
        c4 = b3 & 0x3F
        return (
            PLANTUML_ALPHABET[c1]
            + PLANTUML_ALPHABET[c2]
            + PLANTUML_ALPHABET[c3]
            + PLANTUML_ALPHABET[c4]
        )

    result = ""
    i = 0
    while i < len(compressed):
        b1 = compressed[i]
        b2 = compressed[i + 1] if i + 1 < len(compressed) else 0
        b3 = compressed[i + 2] if i + 2 < len(compressed) else 0
        result += encode3bytes(b1, b2, b3)
        i += 3

    return result


def try_kroki(puml_code: str):
    response = requests.post(
        "https://kroki.io/plantuml/png",
        data=puml_code.encode("utf-8"),
        headers={
            "Content-Type": "text/plain",
            "Accept": "image/png"
        },
        timeout=30
    )

    if response.status_code == 200 and response.content[:4] == b"\x89PNG":
        return response.content, ""

    return None, f"Kroki HTTP {response.status_code}: {response.text[:500]}"


def try_plantuml_server(puml_code: str):
    encoded = plantuml_encode(puml_code)
    url = f"https://www.plantuml.com/plantuml/png/{encoded}"

    response = requests.get(url, timeout=30)

    if response.status_code == 200 and response.content[:4] == b"\x89PNG":
        return response.content, ""

    return None, f"PlantUML HTTP {response.status_code}: {response.text[:500]}"


def run_plantuml(puml_file: Path):
    puml_code = puml_file.read_text(encoding="utf-8")

    errors = []

    try:
        png_data, err = try_kroki(puml_code)
        if png_data:
            puml_file.with_suffix(".png").write_bytes(png_data)
            return 0, ""
        errors.append(err)
    except Exception as e:
        errors.append(f"Kroki greška: {str(e)}")

    try:
        png_data, err = try_plantuml_server(puml_code)
        if png_data:
            puml_file.with_suffix(".png").write_bytes(png_data)
            return 0, ""
        errors.append(err)
    except Exception as e:
        errors.append(f"PlantUML server greška: {str(e)}")

    return 1, "\n".join(errors)
