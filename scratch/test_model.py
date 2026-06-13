import os
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("GEMINI_API_KEY", "")

genai.configure(api_key=api_key)

for model_name in ["gemini-2.0-flash", "gemini-2.5-flash"]:
    try:
        print(f"Testing model: {model_name}...")
        model = genai.GenerativeModel(model_name)
        response = model.generate_content("Say hello in one word.")
        print(f"Success with {model_name}: {response.text.strip()}")
    except Exception as e:
        print(f"Failed with {model_name}: {e}")
