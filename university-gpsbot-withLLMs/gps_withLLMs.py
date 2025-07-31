import httpx
from fastapi import FastAPI
from pydantic import BaseModel
from datetime import datetime
from math import radians, cos, sin, sqrt, atan2
from datetime import datetime, timedelta, timezone
from datetime import datetime
import pytz

last_message_sent_time = None

app = FastAPI()

# === Config ===
GROQ_API_KEY = "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"
GROQ_MODEL = "llama3-8b-8192"
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"

TELEGRAM_TOKEN = "8146080655:AAF7D7ZPc0hSnO1livD6VcChRfaVqFHO0i8" 
CHAT_ID = "7297370967"  

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
    pk_tz = pytz.timezone("Asia/Karachi")
    return datetime.now(pk_tz).strftime("%H:%M")

def haversine(lat1, lon1, lat2, lon2):
    R = 6371.0  # Earth radius in km
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat/2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon/2)**2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    return R * c * 1000  # in meters

import httpx

async def generate_message(class_name, arrival_time):
    try:
        GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
        GROQ_API_KEY = "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"  # Replace with environment variable in production

        headers = {
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": "llama3-8b-8192",
            "messages": [
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user",   "content": f"Write a short, sweet message (20 words) as if I am texting my mom, telling her I reached university for {class_name} around {arrival_time}. Start with 'Assalamualaikum'. Only reply with the message. No explanation or intro text."}
           ]
        }

        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(GROQ_API_URL, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"].strip()

    except httpx.HTTPStatusError as e:
        print("❌ HTTP error from GROQ:", e.response.text)
    except Exception as e:
        print("❌ General error from GROQ:", e)

    # Fallback default message
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
from fastapi import Request

@app.post("/location")
async def receive_location(request: Request):
    global last_message_sent_time

    body = await request.json()
    print("Raw incoming data:", body)

    # === Detect Format ===
    if "_type" in body and body["_type"] == "location":
        latitude = body.get("lat")
        longitude = body.get("lon")
        class_name = "AI"         
        timestamp = body.get("tst")
        if timestamp:
            pk_timezone = timezone(timedelta(hours=5))
            dt = datetime.fromtimestamp(timestamp, tz=timezone.utc).astimezone(pk_timezone)
            arrival_time = dt.strftime("%I:%M %p")
        else:
            arrival_time = get_current_time()

    elif "latitude" in body and "longitude" in body:
        latitude = body["latitude"]
        longitude = body["longitude"]
        class_name = body.get("class_name", "AI")
        arrival_time = body.get("arrival_time") or get_current_time()
    else:
        return {"error": "Invalid format"}

    # === Distance Check ===
    distance = haversine(latitude, longitude, UNIVERSITY_LAT, UNIVERSITY_LON)
    if distance > MAX_DISTANCE_METERS:
        return {
            "status": "Not at university",
            "distance_m": round(distance, 2)
        }

    # === Spam Delay Check ===
    now = datetime.now()
    if last_message_sent_time and (now - last_message_sent_time) < timedelta(hours=6):
        time_left = timedelta(hours=6) - (now - last_message_sent_time)
        return {
            "status": "Already notified",
            "next_message_after": str(time_left).split(".")[0],  # remove microseconds
            "distance_m": round(distance, 2)
        }

    # === Send Message ===
    message_text = await generate_message(class_name, arrival_time)
    await send_telegram_message(message_text)
    last_message_sent_time = now

    return {
        "status": "Message sent",
        "message": message_text,
        "distance_m": round(distance, 2)
    }
