import requests
import zlib
import base64
import re
from pathlib import Path
from io import BytesIO


def encode_plantuml(puml_code: str) -> str:
    """
    Enkodira PlantUML kod u format koji očekuje online PlantUML server.
    """
    # Kompresuj kod
    compressed = zlib.compress(puml_code.encode('utf-8'))
    
    # Base64 enkodiranje
    encoded = base64.b64encode(compressed).decode('ascii')
    
    # PlantUML specifično enkodiranje: + -> -, / -> _
    encoded = encoded.replace('+', '-').replace('/', '_')
    
    return encoded


def run_plantuml(puml_file: Path):
    """
    Renderuje PlantUML fajl koristeći online PlantUML server.
    Vraća (return_code, error_message).
    
    Parametri:
    - puml_file: Path objekt koji pokazuje na .puml fajl
    """
    # Pročitaj PlantUML kod
    puml_code = puml_file.read_text(encoding="utf-8")
    
    # Enkoduj za online server
    encoded = encode_plantuml(puml_code)
    
    # PlantUML online server URL
    url = f"https://www.plantuml.com/plantuml/png/{encoded}"
    
    try:
        # Pošalji zahtev
        response = requests.get(url, timeout=30)
        
        # Proveri da li je uspešno
        if response.status_code == 200:
            # Sačuvaj PNG
            png_path = puml_file.with_suffix(".png")
            png_path.write_bytes(response.content)
            return 0, ""  # 0 = uspeh
        
        else:
            # Neuspešno - pokušaj da dobiješ opis greške
            error_url = f"https://www.plantuml.com/plantuml/svg/{encoded}"
            error_response = requests.get(error_url, timeout=30)
            
            # Izvuci tekst greške iz SVG-a ako postoji
            error_text = error_response.text
            
            # Traži <text> element sa greškom
            text_match = re.findall(r'<text[^>]*>(.*?)</text>', error_text, re.DOTALL)
            
            if text_match:
                error_msg = "\n".join(text_match)
            else:
                error_msg = f"HTTP {response.status_code}: Render nije uspeo."
            
            return 1, error_msg  # 1 = greška
            
    except requests.exceptions.Timeout:
        return 1, "Vreme za renderovanje je isteklo. Pokušajte ponovo."
    
    except requests.exceptions.RequestException as e:
        return 1, f"Greška pri povezivanju sa PlantUML serverom: {str(e)}"
    
    except Exception as e:
        return 1, f"Nepoznata greška: {str(e)}"
