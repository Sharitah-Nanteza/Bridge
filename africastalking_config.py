import os
import africastalking
from dotenv import load_dotenv

load_dotenv()

username = os.getenv("AT_USERNAME", "sandbox")
api_key = os.getenv("AT_API_KEY", "")

# Initialize Africa's Talking SDK
africastalking.initialize(username, api_key)

# Initialize Services
sms = africastalking.SMS
voice = africastalking.Voice

def send_sms_notification(phone_number, message):
    """Triggers an SMS summary via Africa's Talking API."""
    try:
        response = sms.send(message, [phone_number])
        print(f"SMS Sent: {response}")
        return True
    except Exception as e:
        print(f"Error sending SMS: {e}")
        return False

def trigger_voice_guidance(phone_number):
    """Triggers an IVR Voice call to explain safety steps in audio format."""
    try:
        call_from = os.getenv("AT_VIRTUAL_NUMBER", "+256700000000")
        response = voice.call(call_from, [phone_number])
        print(f"Voice Call Initiated: {response}")
        return True
    except Exception as e:
        print(f"Error initiating voice call: {e}")
        return False