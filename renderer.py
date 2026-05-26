import requests
import zlib
import base64
import re
from pathlib import Path


def encode_plantuml(puml_code: str) -> str:
    """
    Enkodira PlantUML kod u format koji očekuje online PlantUML server.
    """
    # Kompresuj kod
    compressed = zlib.compress(puml_code.encode('utf-8'))
    
    # Ukloni prva 2 bajta (DEFLATE header) i poslednja 4 bajta (checksum)
    # Ovo je potrebno za PlantUML server
    compressed = compressed[2:-4]
    
    # Base64 enkodiranje
    encoded = base64.b64encode(compressed).decode('ascii')
    
    # PlantUML specifično enkodiranje: + -> -, / -> _
    encoded = encoded.replace('+', '-').replace('/', '_')
    
    return encoded


def run_plantuml(puml_file: Path):
    """
    Renderuje PlantUML fajl koristeći online PlantUML server.
    Vraća (return_code, error_message).
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
            # Proveri da li je stvarno PNG (a ne HTML sa greškom)
            content_type = response.headers.get('content-type', '')
            
            if 'image' in content_type or response.content[:4] == b'\x89PNG':
                # Sačuvaj PNG
                png_path = puml_file.with_suffix(".png")
                png_path.write_bytes(response.content)
                return 0, ""
            else:
                # Možda je greška u HTML formatu
                error_text = response.text
                
                # Probaj da izvučeš tekst greške
                text_match = re.findall(r'<text[^>]*>(.*?)</text>', error_text, re.DOTALL)
                if text_match:
                    return 1, "\n".join(text_match)
                else:
                    return 1, "PlantUML server nije vratio validan PNG."
        
        else:
            return 1, f"HTTP greška {response.status_code}"
            
    except requests.exceptions.Timeout:
        return 1, "Vreme za renderovanje je isteklo. Pokušajte ponovo."
    
    except requests.exceptions.RequestException as e:
        return 1, f"Greška pri povezivanju sa PlantUML serverom: {str(e)}"
    
    except Exception as e:
        return 1, f"Nepoznata greška: {str(e)}"