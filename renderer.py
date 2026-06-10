import requests
from pathlib import Path


def run_plantuml(puml_file: Path):
    """
    Renderuje PlantUML fajl koristeći k8s PlantUML server.
    Vraća (return_code, error_message).
    """
    puml_code = puml_file.read_text(encoding="utf-8")
    
    try:
        response = requests.post(
            "https://k8s.plantuml.com/plantuml/form",
            data={"text": puml_code},
            timeout=60
        )
        
        if response.status_code == 200 and len(response.content) > 100:
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
