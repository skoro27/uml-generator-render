import requests
import zlib
import base64
from pathlib import Path


def encode_plantuml(puml_code: str) -> str:
    """Enkodira PlantUML kod za PlantUML online server."""
    compressed = zlib.compress(puml_code.encode('utf-8'), level=9)
    b64 = base64.b64encode(compressed).decode('ascii')
    b64 = b64.replace('+', '-').replace('/', '_')
    return b64


def run_plantuml(puml_file: Path):
    """
    Renderuje PlantUML fajl koristeći PlantUML online server.
    Vraća (return_code, error_message).
    """
    puml_code = puml_file.read_text(encoding="utf-8")
    
    encoded = encode_plantuml(puml_code)
    url = f"https://www.plantuml.com/plantuml/png/{encoded}"
    
    try:
        response = requests.get(url, timeout=60)
        
        if response.status_code == 200 and response.content[:4] == b'\x89PNG':
            png_path = puml_file.with_suffix(".png")
            png_path.write_bytes(response.content)
            return 0, ""
        else:
            return 1, f"PlantUML server greška: HTTP {response.status_code}"
            
    except requests.exceptions.Timeout:
        return 1, "Vreme za renderovanje je isteklo."
    
    except requests.exceptions.RequestException as e:
        return 1, f"Greška pri povezivanju: {str(e)}"
    
    except Exception as e:
        return 1, f"Nepoznata greška: {str(e)}"
