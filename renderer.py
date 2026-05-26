import requests
from pathlib import Path
from io import BytesIO


def encode_plantuml(puml_code: str) -> str:
    """
    Enkodira PlantUML kod koristeći standardni PlantUML text encoding.
    Ovo je najjednostavniji i najpouzdaniji način.
    """
    import base64
    import zlib
    
    # Kompresuj
    compressed = zlib.compress(puml_code.encode('utf-8'), level=9)
    
    # Base64 enkodiranje
    b64 = base64.b64encode(compressed).decode('ascii')
    
    # PlantUML specijalno enkodiranje
    b64 = b64.replace('+', '-').replace('/', '_')
    
    return b64


def run_plantuml(puml_file: Path):
    """
    Renderuje PlantUML fajl koristeći online PlantUML server.
    Vraća (return_code, error_message).
    """
    puml_code = puml_file.read_text(encoding="utf-8")
    
    # Probaj prvo sa plantuml.com/plantuml/png/ (bez ~1)
    encoded = encode_plantuml(puml_code)
    
    urls_to_try = [
        f"https://www.plantuml.com/plantuml/png/{encoded}",
        f"https://www.plantuml.com/plantuml/png/~1{encoded}",
        f"https://www.plantuml.com/plantuml/svg/{encoded}",
        f"https://www.plantuml.com/plantuml/svg/~1{encoded}",
    ]
    
    last_error = ""
    
    for url in urls_to_try:
        try:
            response = requests.get(url, timeout=30)
            
            if response.status_code == 200:
                content = response.content
                
                # Proveri da li je PNG
                if content[:4] == b'\x89PNG':
                    png_path = puml_file.with_suffix(".png")
                    png_path.write_bytes(content)
                    return 0, ""
                
                # Proveri da li je SVG (konvertuj u PNG ne možemo lako, ali možemo SVG sačuvati)
                if content.startswith(b'<?xml') or content.startswith(b'<svg'):
                    # Pokušaj da konvertuješ SVG u PNG preko drugog endpointa
                    svg_url = f"https://www.plantuml.com/plantuml/png/{encoded}"
                    svg_response = requests.get(svg_url, timeout=30)
                    if svg_response.status_code == 200 and svg_response.content[:4] == b'\x89PNG':
                        png_path = puml_file.with_suffix(".png")
                        png_path.write_bytes(svg_response.content)
                        return 0, ""
                    
                    last_error = "Server je vratio SVG umesto PNG-a"
                    continue
                
                # Ako je HTML sa greškom
                if b'<html>' in content or b'<text>' in content:
                    last_error = "PlantUML server je vratio grešku"
                    continue
                    
        except Exception as e:
            last_error = str(e)
            continue
    
    return 1, f"Render nije uspeo: {last_error}"