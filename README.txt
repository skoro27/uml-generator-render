UML PROJECT - modularna verzija

Fajlovi:
- config.py              podesavanja modela, putanje i API key
- prompts.py             promptovi za generisanje i repair
- llm_clients.py         Groq i Ollama pozivi
- plantuml_cleaner.py    ciscenje i sanitizacija PlantUML koda
- renderer.py            poziv plantuml.jar
- evaluation.py          osnovna evaluacija modela
- generator.py           glavni tok generisanja
- app.py                 Streamlit web aplikacija
- main.py                CMD verzija aplikacije

Pokretanje web aplikacije:
cd "C:\Users\Public\Documents\UML_PROJECT"
py -m streamlit run app.py

Pokretanje kroz CMD:
py main.py

VAZNO:
- U config.py upisi svoj Groq API key.
- plantuml.jar mora biti u tools/plantuml.jar
