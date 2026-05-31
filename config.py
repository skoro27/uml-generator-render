import os
from pathlib import Path

# Put do fajlova
BASE_DIR = Path(__file__).resolve().parent
DEBUG_FILE = BASE_DIR / "debug_llm_output.txt"
PUML_FILE = BASE_DIR / "model.puml"

# Alias za backward kompatibilnost
RAW_PUML_FILE = PUML_FILE

# Groq API podešavanja
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
GROQ_MODEL = "qwen/qwen3-32b"
GROQ_MAX_TOKENS = 2048
GROQ_TEMPERATURE = 0.3

# LLM Provider (za backward kompatibilnost)
LLM_PROVIDER = "groq"