PROMPT_TEMPLATE = """Ti si ekspert za konceptualno modelovanje baza podataka i UML class dijagrame.
Generisi DETALJAN PlantUML dijagram KLASA koji predstavlja konceptualni/relacioni model baze podataka.

VRATI ISKLJUCIVO PlantUML kod izmedju @startuml i @enduml. NIKAKVA objasnjenja, NIKAKAV markdown, NIKAKVE napomene pre ili posle koda.

PRAVILA KOJA MORAS POSTOVATI:

1. KLASE:
- Identifikuj SVE entitete iz opisa (ne samo 3-4 glavne).
- Svaka klasa MORA imati id : Integer.
- Atributi samo prosti tipovi: String, Integer, Date.
- Imena klasa: veliko pocetno slovo, bez dijakritike, bez razmaka (npr. IzbornaKomisija, ne "Izborna komisija").
- Ne koristi metode, liste, niti slozene tipove.

2. NASLJEDJIVANJE (OBAVEZNO ako opis spominje tipove/podtipove):
- SINTAKSA: Dijete --|> Roditelj
- Primer: Ako opis kaze "Centralna izborna komisija je izborna komisija", pisi: CentralnaIzbornaKomisija --|> IzbornaKomisija
- Primer: Ako opis kaze "biracki odbori (BO) i izborne komisije (IK) su organi", pisi:
  BirackiOdbor --|> Organ
  IzbornaKomisija --|> Organ
- NIKADA ne koristi rec "extends" u imenima klasa.
- Klase koje nasledjuju NE ponavljaju atribute roditelja (oni su nasledjeni).

3. RELACIJE (VAN klasa, POSLE svih definicija klasa):
- SVAKA relacija MORA imati kardinalnost: "1", "0..*", "1..*", "0..1"
- Format: KlasaA "kard1" -- "kard2" KlasaB : opis
- Primer: Organ "1" -- "1..*" Clan : ima
- Ako opis kaze "X ima Y", to je relacija: X "1" -- "0..*" Y : ima
- Ako opis kaze "X imenuje Y", to je relacija: X "1" -- "0..*" Y : imenuje
- Za many-to-many, kreiraj posebnu veznu klasu (npr. Clanstvo).

4. KONZISTENTNOST (NAJVAZNIJE):
- Svaka klasa koja se pojavljuje u relaciji MORA biti prethodno definisana.
- Proveri da li sve klase iz relacija postoje u definicijama.
- Ne koristi skracenice u relacijama ako klasa ima puno ime.

PRIMER ISPRAVNOG UML-a:

@startuml
skinparam defaultFontName Arial
skinparam classAttributeIconSize 0
skinparam linetype ortho
hide methods
hide circle

class Osoba {
  id : Integer
  ime : String
  prezime : String
}
class Student {
  id : Integer
  indeks : String
}
class Profesor {
  id : Integer
  zvanje : String
}
class Predmet {
  id : Integer
  naziv : String
  espb : Integer
}
class Ispit {
  id : Integer
  datum : Date
  ocena : Integer
}

Student --|> Osoba
Profesor --|> Osoba
Student "1" -- "0..*" Ispit : polaze
Predmet "1" -- "0..*" Ispit : ima
Profesor "1" -- "0..*" Predmet : predaje

@enduml

OPIS SISTEMA ZA MODELOVANJE:
{description}
"""

REPAIR_PROMPT_TEMPLATE = """Popravi PlantUML dijagram da bude validan PlantUML kod.

PRAVILA:
- Ne menjaj koncepte, klase i atribute iz originala.
- Samo ispravi sintaksne greske.
- OBAVEZNO dodaj @startuml na pocetak i @enduml na kraj.
- Ako fale relacije ili nasledjivanje koje je ocigledno iz imena klasa, dodaj ih.
- Ako se u relacijama koriste klase koje nisu definisane, ili ih definisi ili prepravi relacije.
- Imena klasa pisi bez razmaka (npr. IzbornaKomisija, ne Izborna komisija).
- Vrati SAMO PlantUML kod, bez ikakvih objasnjenja.

ORIGINAL (sa greskom):
{puml}

PLANTUML GRESKA:
{error}
"""
