# ---------------- PROMPTI ----------------

PROMPT_TEMPLATE = """Ti si ekspert za konceptualno modelovanje baza podataka i UML class dijagrame.
Generisi DETALJAN PlantUML dijagram KLASA koji predstavlja konceptualni/relacioni model baze podataka.

VRATI ISKLJUCIVO PlantUML kod izmedju @startuml i @enduml.

OBAVEZNO:
- Identifikuj sve vazne entitete iz opisa.
- Broj klasa odredi prema opisu sistema; ne izmisljaj nepotrebne klase.
- Ne svodi model samo na glavne 3-4 klase.
- Ukljuci sve bitne klase koje se pojavljuju u opisu.
- Atributi moraju biti prosti tipovi: String, Integer, Date.
- Dodaj atribut id : Integer u svaku klasu.
- Dodaj osnovne atribute kao naziv, datum, tip, broj, opis gdje imaju smisla.
- Ne koristi metode.
- Ne koristi liste.
- Ne koristi dijakritiku.
- Koristi ASCII slova.

NASLJEDJIVANJE:
- Koristi nasljedjivanje kada u opisu postoje tipovi/podtipovi.
- Nasljedjivanje pisi iskljucivo PlantUML sintaksom:
  Dijete --|> Roditelj.
- Nikada ne koristi rijec extends u nazivima klasa.
- Nazivi klasa moraju biti kratki i cisti.

RELACIJE:
- Relacije pisi VAN klasa.
- Obavezno koristi kardinalnosti "1", "0..*", "1..*" u svim relacijama.
- Ako postoji veza vise-na-vise, napravi veznu klasu.
- Ako postoji hijerarhija istih elemenata, koristi rekurzivnu relaciju.
- Ne ubacuj relacije unutar class blokova.

PRIMJER ISPRAVNOG FORMATA:
@startuml
skinparam defaultFontName Arial
skinparam classAttributeIconSize 0
skinparam linetype ortho

class EntitetA {{
  id : Integer
  naziv : String
}}

class EntitetB {{
  id : Integer
  datum : Date
}}

class EntitetC {{
  id : Integer
  tip : String
}}

EntitetB --|> EntitetA
EntitetA "1" -- "0..*" EntitetC : sadrzi
EntitetB "1" -- "1..*" EntitetC : koristi

@enduml

OPIS:
{description}
"""

REPAIR_PROMPT_TEMPLATE = """Popravi PlantUML da bude validan.
Ne mijenjaj domenu, samo ispravi sintaksu.
Vrati samo @startuml ... @enduml.

ORIGINAL:
{puml}

PLANTUML ERROR:
{error}
"""
