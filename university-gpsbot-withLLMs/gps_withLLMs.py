# from fastapi import FastAPI, Request
# from geopy.distance import geodesic
# import requests
# import os
# from datetime import datetime, timedelta
# import httpx

# app = FastAPI()

# HEADERS = {
#     "Authorization": f"Bearer {os.environ.get('WHATSAPP_TOKEN')}",
#     "Content-Type": "application/json"
# }

# # UBIT Coordinates
# UNI_LAT, UNI_LON = 24.94557432346588, 67.115382

# # WhatsApp Cloud API credentials
# WHATSAPP_API_URL = "https://graph.facebook.com/v22.0/715095305022325/messages"
# MOM_PHONE = "whatsapp:+923403553839"

# # Track last message sent time
# last_sent_time = None
# SEND_INTERVAL_HOURS = 5  # Don't send again within 5 hours

# # Groq + LLaMA 3 API details
# GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
# GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"

# # Generate dynamic message using LLaMA 3
# async def generate_message(class_name: str, transport: str, time: str) -> str:
#     prompt = f"""
#     Write a short WhatsApp message in a warm, caring tone from a university student to their mom, saying they just reached university. The message should include:
#     - Mention of the class name: {class_name}
#     - How they got there (e.g., via {transport})
#     - Mention the time: {time}
#     Make the message informal and natural.
#     """

#     async with httpx.AsyncClient() as client:
#         response = await client.post(
#             GROQ_API_URL,
#             headers={
#                 "Authorization": f"Bearer {GROQ_API_KEY}",
#                 "Content-Type": "application/json"
#             },
#             json={
#                 "model": "llama3-8b-8192",
#                 "messages": [
#                     {"role": "user", "content": prompt}
#                 ],
#                 "temperature": 0.8
#             }
#         )
#         data = response.json()
#         return data["choices"][0]["message"]["content"].strip()



# @app.post("/location")
# async def receive_location(request: Request):
#     global last_sent_time

#     data = await request.json()
#     lat = data.get("lat")
#     lon = data.get("lon")
#     class_name = data.get("class")
#     transport = data.get("transport")

#     if not lat or not lon:
#         return {"error": "Missing lat/lon"}

#     user_coords = (lat, lon)
#     campus_coords = (UNI_LAT, UNI_LON)
#     distance = geodesic(user_coords, campus_coords).meters
#     print(f"Distance to university: {distance}m")

#     # Check if already sent in the last 5 hours
#     now = datetime.now()
#     if last_sent_time and now - last_sent_time < timedelta(hours=SEND_INTERVAL_HOURS):
#         print("Message already sent in last 5 hours. Skipping.")
#         return {"status": "Message recently sent. Skipped."}

#     if distance < 300:
#         # Generate message
#         arrival_time = now.strftime("%I:%M %p")
#         message_text = await generate_message(class_name, transport, arrival_time)

#         message_payload = {
#             "messaging_product": "whatsapp",
#             "to": MOM_PHONE,
#             "type": "text",
#             "text": {"body": message_text}
#         }

#         response = requests.post(WHATSAPP_API_URL, json=message_payload, headers=HEADERS)
#         print("Message response:", response.status_code, response.text)

#         # Update last sent time
#         last_sent_time = now

#         return {
#             "status": "Personalized message sent to mom",
#             "message_text": message_text,
#             "response": response.json()
#         }

#     return {"status": f"Distance is {distance:.2f} meters"}
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

    async with httpx.AsyncClient() as client:
        response = await client.post(GROQ_API_URL, headers=headers, json=payload)
        data = response.json()

    try:
        return data["choices"][0]["message"]["content"].strip()
    except KeyError:
        print("LLM Error Response:", data)
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

