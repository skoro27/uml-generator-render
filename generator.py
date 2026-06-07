import os
import re
from groq import Groq
from config import GROQ_API_KEY

client = Groq(api_key=GROQ_API_KEY)

def generate_puml(description: str) -> str:
    """Generiše PlantUML klasni dijagram na osnovu opisa sistema."""
    
    prompt = f"""
Ti si ekspert za UML dijagrame klasa. Generiši PlantUML kod na osnovu sljedećeg opisa sistema.

**OPIS SISTEMA:**
{description}

**PRAVILA KOJA SE MORAJU POŠTOVATI (KRITIČNO VAŽNO!):**

1. **Primarni ključ (PK) se NE piše kao atribut sa oznakom {{PK}}!**
   
   ❌ LOŠE:
   class Osoba {{
     {{PK}} id : Integer
     ime : String
   }}
   
   ✅ DOBRO:
   class Osoba {{
     PK(id : Integer)
     ime : String
   }}
   
   Ako PK ima više atributa:
   class Racun {{
     PK(broj : Integer, godina : Integer)
     stanje : Double
   }}

2. **POTKLASE NE NASLJEĐUJU PK od natklase!**
   
   ❌ LOŠE (Zaposleni ponovo ima id):
   class Osoba {{
     PK(id : Integer)
     ime : String
   }}
   class Zaposleni {{
     PK(id : Integer)  ← OVO JE ZABRANJENO!
     plata : Double
   }}
   Osoba <|-- Zaposleni
   
   ✅ DOBRO (Zaposleni NEMA PK):
   class Osoba {{
     PK(id : Integer)
     ime : String
   }}
   class Zaposleni {{
     plata : Double
     radnoMjesto : String
   }}
   Osoba <|-- Zaposleni

3. **Generalizacija (nasljeđivanje) se piše:** `Natklasa <|-- Potklasa`

4. **Asocijacije sa kardinalnostima:**
   `KlasaA "1" -- "0..*" KlasaB : nazivVeze`

5. **Obavezno koristi @startuml i @enduml.**

6. **Svi atributi i operacije moraju imati tip podatka (String, Integer, Boolean, Date...)**

7. **NE koristi <think> tagove. NE piši objašnjenja. SAMO PlantUML kod!**

**Generiši SAMO PlantUML kod, bez dodatnih objašnjenja.**
"""
    
    try:
        response = client.chat.completions.create(
            model="qwen/qwen3-32b",
            messages=[
                {"role": "system", "content": "Ti si ekspert za UML i PlantUML. Generišeš samo PlantUML kod, bez objašnjenja. Ne koristiš <think> tagove."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,
            max_tokens=4000
        )
        
        puml_code = response.choices[0].message.content
        
        # Ukloni <think> tagove (Qwen model ih ponekad dodaje)
        puml_code = re.sub(r'<think>.*?</think>', '', puml_code, flags=re.DOTALL)
        
        # Očisti kod ako ima markdown formatiranja
        puml_code = re.sub(r'^```plantuml\n?', '', puml_code, flags=re.MULTILINE)
        puml_code = re.sub(r'^```\n?', '', puml_code, flags=re.MULTILINE)
        puml_code = puml_code.strip()
        
        return puml_code
        
    except Exception as e:
        raise Exception(f"Greška pri generisanju PlantUML koda: {str(e)}")
