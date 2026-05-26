from groq import Groq
from config import GROQ_API_KEY, GROQ_MODEL


def call_groq(prompt: str) -> str:

    try:
        client = Groq(api_key=GROQ_API_KEY)

        final_prompt = f"""
VRATI SAMO PLANTUML.

NE OBJASNJAVAJ.
NE ANALIZIRAJ.
NE KORISTI THINKING.
NE PISI TEKST.

OBAVEZNO:
- odgovor mora poceti sa @startuml
- odgovor mora zavrsiti sa @enduml
- koristi najmanje jednu class definiciju

{prompt}
"""

        response = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {
                    "role": "user",
                    "content": final_prompt
                }
            ],
            temperature=0,
            max_tokens=2500
        )

        text = response.choices[0].message.content

        if "@startuml" not in text and "class " in text:
            text = "@startuml\n" + text + "\n@enduml"

        return text

    except Exception as e:
        raise RuntimeError(f"Groq greska: {e}")


def call_llm(prompt: str) -> str:
    return call_groq(prompt)