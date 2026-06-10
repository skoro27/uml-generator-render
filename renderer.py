import requests
from pathlib import Path


def run_plantuml(puml_file: Path):
    """
    Renderuje PlantUML fajl koristeći Kroki.io server.
    Vraća (return_code, error_message).
    """
    puml_code = puml_file.read_text(encoding="utf-8")
    
    url = "https://kroki.io/plantuml/png"
    
    try:
        response = requests.post(
            url,
            data=puml_code.encode('utf-8'),
            headers={'Content-Type': 'text/plain'},
            timeout=60
        )
        
        if response.status_code == 200:
            png_path = puml_file.with_suffix(".png")
            png_path.write_bytes(response.content)
            return 0, ""
        else:
            return 1, f"Kroki server greška: HTTP {response.status_code}"
            
    except requests.exceptions.Timeout:
        return 1, "Vreme za renderovanje je isteklo."
    
    except requests.exceptions.RequestException as e:
        return 1, f"Greška pri povezivanju: {str(e)}"
    
    except Exception as e:
        return 1, f"Nepoznata greška: {str(e)}"
