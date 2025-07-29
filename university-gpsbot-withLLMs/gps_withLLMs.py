import httpx
from fastapi import FastAPI, Request
from pydantic import BaseModel
from datetime import datetime

app = FastAPI()

# API Keys and Config (Hardcoded)
GROQ_API_KEY = "your_groq_api_key_here"
GROQ_MODEL = "llama3-8b-8192"
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"

WHATSAPP_API_URL = "https://graph.facebook.com/v22.0/715095305022325/messages"
WHATSAPP_TOKEN = "your_whatsapp_token_here"
RECIPIENT_PHONE = "whatsapp:+923403553839" 

class LocationData(BaseModel):
    latitude: float
    longitude: float
    class_name: str
    arrival_time: str

def get_current_time():
    return datetime.now().strftime("%I:%M %p")

async def generate_message(class_name, arrival_time):
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }

    prompt = (
        f"Just tell my mom in a warm and informal tone that I've reached the university for my {class_name} class around {arrival_time}. "
        f"Make it a short, sweet WhatsApp-style message under 280 characters."
    )

    payload = {
        "model": GROQ_MODEL,
        "messages": [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.7
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(GROQ_API_URL, headers=headers, json=payload)
        data = response.json()

    try:
        return data["choices"][0]["message"]["content"].strip()
    except KeyError:
        print("LLM Error Response:", data)
        return f"Hey Ammi, just reached uni for {class_name} around {arrival_time}! I'll talk to you later."  

async def send_whatsapp_message(body_text):
    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json"
    }

    payload = {
        "messaging_product": "whatsapp",
        "to": RECIPIENT_PHONE,
        "type": "text",
        "text": {
            "preview_url": False,
            "body": body_text
        }
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(WHATSAPP_API_URL, headers=headers, json=payload)
        print("WhatsApp API response:", response.json())

@app.post("/location")
async def receive_location(location_data: LocationData):
    arrival_time = location_data.arrival_time or get_current_time()

    message_text = await generate_message(
        location_data.class_name,
        arrival_time
    )

    await send_whatsapp_message(message_text)
    return {"status": "Message sent", "message": message_text}
