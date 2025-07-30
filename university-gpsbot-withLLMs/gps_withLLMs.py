
import httpx
from fastapi import FastAPI
from pydantic import BaseModel
from datetime import datetime
from math import radians, cos, sin, sqrt, atan2

app = FastAPI()

# === Config ===
GROQ_API_KEY = "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"
GROQ_MODEL = "llama3-8b-8192"
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"

TELEGRAM_TOKEN = "8146080655:AAF7D7ZPc0hSnO1livD6VcChRfaVqFHO0i8"  # Replace with your Bot Token
CHAT_ID = "7297370967"  # Replace with your Telegram user ID or group ID

# University Location
UNIVERSITY_LAT, UNIVERSITY_LON = 24.94557432346588, 67.115382
MAX_DISTANCE_METERS = 150  # Acceptable distance to trigger message

# === Pydantic Model ===
class LocationData(BaseModel):
    latitude: float
    longitude: float
    class_name: str
    arrival_time: str = None

# === Utilities ===
def get_current_time():
    return datetime.now().strftime("%I:%M %p")

def haversine(lat1, lon1, lat2, lon2):
    R = 6371.0  # Earth radius in km
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat/2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon/2)**2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    return R * c * 1000  # in meters

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

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(GROQ_API_URL, headers=headers, json=payload)
            response.raise_for_status()  # 🔒 Add this for safety
            data = response.json()
            return data["choices"][0]["message"]["content"].strip()
    except Exception as e:
        print("LLM Error Response:", e)
        return f"Hey Ammi, just reached uni for {class_name} around {arrival_time}! I'll talk to you later."


async def send_telegram_message(body_text):
    telegram_url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": body_text
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(telegram_url, json=payload)
        print("Telegram API response:", response.json())

# === Main Endpoint ===
@app.post("/location")
async def receive_location(location_data: LocationData):
    print("Received location:", location_data)
    distance = haversine(location_data.latitude, location_data.longitude, UNIVERSITY_LAT, UNIVERSITY_LON)

    if distance > MAX_DISTANCE_METERS:
        return {
            "status": "Not at university",
            "distance_m": round(distance, 2)
        }

    arrival_time = location_data.arrival_time or get_current_time()
    message_text = await generate_message(location_data.class_name, arrival_time)
    await send_telegram_message(message_text)

    return {
        "status": "Message sent",
        "message": message_text,
        "distance_m": round(distance, 2)
    }

