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

1. **Primarni ključ (PK) se piše KAO OPERACIJA, ne kao atribut!**
   
   ✅ DOBRO:
   class Osoba {{
     PK(jmb : String)
     ime : String
     prezime : String
   }}
   
   ✅ DOBRO za složeni PK:
   class Račun {{
     PK(broj : Integer, godina : Integer)
     stanje : Double
   }}

2. **POTKLASE NE PONAVLJAJU PK od natklase!**
   
   ✅ DOBRO:
   class Osoba {{
     PK(jmb : String)
     ime : String
   }}
   class Zaposleni {{
     plata : Double
   }}
   Osoba <|-- Zaposleni

3. **NE stavljaj objekte drugih klasa kao atribute!**
   Koristi relacije za povezivanje klasa.
   
   ❌ LOŠE:
   class BiračkoMjesto {{
     Adresa adresa
   }}
   
   ✅ DOBRO:
   class BiračkoMjesto {{
     PK(redniBroj : Integer)
   }}
   Adresa "1" -- "0..*" BiračkoMjesto : nalaziSeNa

4. **Generalizacija (nasljeđivanje) se piše:** `Natklasa <|-- Potklasa`

5. **Asocijacije sa kardinalnostima:**
   `KlasaA "1" -- "0..*" KlasaB : nazivVeze`

6. **Ako više entiteta može dijeliti isti resurs, koristi "0..*" na toj strani.**
   Npr: Adresa "1" -- "0..*" BiračkoMjesto (više mjesta na istoj adresi)

7. **Obavezno koristi @startuml i @enduml.**

8. **Svi atributi moraju imati tip (String, Integer, Date, Boolean...)**

9. **NE koristi <think> tagove. NE piši objašnjenja. SAMO PlantUML kod!**

10. **SVE nazive klasa, atributa i relacija piši NA SRPSKOM JEZIKU (ijekavica)!**
    - Imena klasa: Organ, BiračkiOdbor, IzbornaKomisija, Osoba, Adresa, Opština...
    - Atributi: ime, prezime, datumRođenja, naziv, adresa, broj...
    - Nazivi veza: ima, sadrži, pripada, imenuje, nalaziSe...
    - NE koristi engleske riječi (name, address, id, member...)

**Generiši SAMO PlantUML kod, bez dodatnih objašnjenja.**
"""
    
    try:
        response = client.chat.completions.create(
            model="qwen/qwen3-32b",
            messages=[
                {"role": "system", "content": "Ti si ekspert za UML i PlantUML. Generišeš SAMO PlantUML kod bez objašnjenja i bez <think> tagova. SVE pišeš na srpskom jeziku (ijekavica)."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,
            max_tokens=4000
        )
        
        puml_code = response.choices[0].message.content
        
        # Ukloni <think> tagove (i sa i bez zatvarajućeg taga)
        puml_code = re.sub(r'<think>.*?</think>', '', puml_code, flags=re.DOTALL)
        puml_code = re.sub(r'<think>.*', '', puml_code, flags=re.DOTALL)
        
        # Očisti markdown formatiranje
        puml_code = re.sub(r'^```plantuml\n?', '', puml_code, flags=re.MULTILINE)
        puml_code = re.sub(r'^```\n?', '', puml_code, flags=re.MULTILINE)
        puml_code = puml_code.strip()
        
        return puml_code
        
    except Exception as e:
        raise Exception(f"Greška pri generisanju PlantUML koda: {str(e)}")
