# model.py
import os
import requests
from dotenv import load_dotenv

# Load .env file
load_dotenv()  

# Get API key
api_key = os.getenv("API_KEY")

if not api_key:
    raise ValueError("GROQ_API_KEY not found. Make sure it's in your .env file.")


api_key = api_key.strip()

# URL to get models
url = "https://api.groq.com/openai/v1/models"

# Headers
headers = {
    "Authorization": f"Bearer {api_key}",
    "Content-Type": "application/json"
}

# Make request
response = requests.get(url, headers=headers)

# Check response
if response.status_code == 200:
    models = response.json()
    print("Available Groq models:")
    for model in models.get("data", []):
        print("-", model.get("id"))
else:
    print("Error fetching models!")
    print("Status code:", response.status_code)
    print("Response:", response.json())


