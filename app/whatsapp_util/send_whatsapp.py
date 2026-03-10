import requests
import os
from dotenv import load_dotenv , find_dotenv

load_dotenv(find_dotenv())

ACCESS_TOKEN = os.getenv('ACCESS_TOKEN')
PHONE_NUMBER_ID = os.getenv('PHONE_NUMBER_ID')

async def send_whatsapp_message(recipient_id : str , message : str):
    url = f"https://graph.facebook.com/v22.0/{PHONE_NUMBER_ID}/messages"

    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }

    payload = {
        "messaging_product": "whatsapp",
        "to": recipient_id,
        "type": "text",
        "text": {
            "body": message
        }
    }

    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        print(f"✓ Message sent to {recipient_id}: {response.status_code}")
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"✗ Failed to send message to {recipient_id}: {e}")
        return None