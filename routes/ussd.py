from flask import Blueprint, request, make_response
from legal_data import LEGAL_GUIDANCE
from africastalking_config import send_sms_notification, trigger_voice_guidance

ussd_bp = Blueprint('ussd', __name__)

@ussd_bp.route('/ussd', methods=['POST'])
def ussd_menu():
    session_id = request.values.get("sessionId", None)
    service_code = request.values.get("serviceCode", None)
    phone_number = request.values.get("phoneNumber", None)
    text = request.values.get("text", "").strip()

    response = ""

    if text == "":
        response = "CON Welcome to Bridge Helpline\n"
        response += "Offline Digital Rights & Safety\n"
        response += "1. Mobile Money Fraud\n"
        response += "2. Online Harassment\n"
        response += "3. Data Privacy Rights\n"
        response += "4. Request Audio Voice Guide"

    elif text == "1":
        response = LEGAL_GUIDANCE["1"]["ussd_summary"]

    elif text in ["1*1", "1*2"]:
        response = "END Legal steps and helpline numbers sent via SMS!"
        send_sms_notification(phone_number, LEGAL_GUIDANCE["1"]["sms_details"])

    elif text == "2":
        response = LEGAL_GUIDANCE["2"]["ussd_summary"]

    elif text in ["2*1", "2*2"]:
        response = "END Cybercrime action steps sent via SMS. Preserve all evidence!"
        send_sms_notification(phone_number, LEGAL_GUIDANCE["2"]["sms_details"])

    elif text == "3":
        response = LEGAL_GUIDANCE["3"]["ussd_summary"]

    elif text in ["3*1", "3*2"]:
        response = "END Data privacy summary sent via SMS."
        send_sms_notification(phone_number, LEGAL_GUIDANCE["3"]["sms_details"])

    elif text == "4":
        response = "END Calling your line... Please answer to hear the audio guide."
        trigger_voice_guidance(phone_number)

    elif text == "0":
        response = "CON Welcome back to Bridge Helpline:\n1. Mobile Money Fraud\n2. Harassment\n3. Data Rights\n4. Audio Guide"

    else:
        response = "END Invalid entry. Please dial again."

    resp = make_response(response, 200)
    resp.headers['Content-Type'] = 'text/plain'
    return resp