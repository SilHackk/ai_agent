import os
from dotenv import load_dotenv

load_dotenv(".env.local")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")