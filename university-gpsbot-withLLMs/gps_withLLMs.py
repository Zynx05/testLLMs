from fastapi import FastAPI, Request
from geopy.distance import geodesic
import requests
import os
from datetime import datetime, timedelta
import httpx

app = FastAPI()

HEADERS = {
    "Authorization": f"Bearer {os.environ.get('WHATSAPP_TOKEN')}",
    "Content-Type": "application/json"
}

# UBIT Coordinates
UNI_LAT, UNI_LON = 24.94557432346588, 67.115382

# WhatsApp Cloud API credentials
WHATSAPP_API_URL = "https://graph.facebook.com/v22.0/715095305022325/messages"
MOM_PHONE = "whatsapp:+923403553839"

# Track last message sent time
last_sent_time = None
SEND_INTERVAL_HOURS = 5  # Don't send again within 5 hours

# Groq + LLaMA 3 API details
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"

# Generate dynamic message using LLaMA 3
async def generate_message(class_name: str, transport: str, time: str) -> str:
    prompt = f"""
    Write a short WhatsApp message in a warm, caring tone from a university student to their mom, saying they just reached university. The message should include:
    - Mention of the class name: {class_name}
    - How they got there (e.g., via {transport})
    - Mention the time: {time}
    Make the message informal and natural.
    """

    async with httpx.AsyncClient() as client:
        response = await client.post(
            GROQ_API_URL,
            headers={
                "Authorization": f"Bearer {GROQ_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": "llama3-8b-8192",
                "messages": [
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.8
            }
        )
        data = response.json()
        return data["choices"][0]["message"]["content"].strip()



@app.post("/location")
async def receive_location(request: Request):
    global last_sent_time

    data = await request.json()
    lat = data.get("lat")
    lon = data.get("lon")
    class_name = data.get("class")
    transport = data.get("transport")

    if not lat or not lon:
        return {"error": "Missing lat/lon"}

    user_coords = (lat, lon)
    campus_coords = (UNI_LAT, UNI_LON)
    distance = geodesic(user_coords, campus_coords).meters
    print(f"Distance to university: {distance}m")

    # Check if already sent in the last 5 hours
    now = datetime.now()
    if last_sent_time and now - last_sent_time < timedelta(hours=SEND_INTERVAL_HOURS):
        print("Message already sent in last 5 hours. Skipping.")
        return {"status": "Message recently sent. Skipped."}

    if distance < 300:
        # Generate message
        arrival_time = now.strftime("%I:%M %p")
        message_text = await generate_message(class_name, transport, arrival_time)

        message_payload = {
            "messaging_product": "whatsapp",
            "to": MOM_PHONE,
            "type": "text",
            "text": {"body": message_text}
        }

        response = requests.post(WHATSAPP_API_URL, json=message_payload, headers=HEADERS)
        print("Message response:", response.status_code, response.text)

        # Update last sent time
        last_sent_time = now

        return {
            "status": "Personalized message sent to mom",
            "message_text": message_text,
            "response": response.json()
        }

    return {"status": f"Distance is {distance:.2f} meters"}
