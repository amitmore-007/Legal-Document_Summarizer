import os
from dotenv import load_dotenv

load_dotenv(override=True)  # Force reload the environment variables

API_KEY = os.getenv("GROQ_API_KEY")
print(API_KEY)
