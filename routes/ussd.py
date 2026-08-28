from flask import Blueprint, request, make_response
from legal_data import LEGAL_GUIDANCE
from africastalking_config import send_sms_notification, trigger_voice_guidance
from scamdb import report_number, check_number

ussd_bp = Blueprint('ussd', __name__)


@ussd_bp.route('/ussd', methods=['POST'])
def ussd_menu():
    session_id = request.values.get("sessionId", None)
    service_code = request.values.get("serviceCode", None)
    phone_number = request.values.get("phoneNumber", None)
    text = request.values.get("text", "").strip()

    response = ""
    parts = text.split("*") if text else []

    # Main menu
    if text == "":
        response = "CON Welcome to Bridge Helpline\n"
        response += "1. Legal & Safety Assistance\n"
        response += "2. Report Fraud / Scam\n"
        response += "3. Explore Digital World\n"
        response += "4. Request Audio Voice Guide"

    # Legal & Safety Assistance flow
    elif parts[0] == "1":
        # Show legal topic list
        if len(parts) == 1:
            response = "CON Legal & Safety Assistance:\n1. Mobile Money Fraud\n2. Online Harassment\n3. Data Privacy Rights\n0. Back"
        # Show selected topic summary
        elif len(parts) == 2:
            topic = parts[1]
            if topic in LEGAL_GUIDANCE:
                response = LEGAL_GUIDANCE[topic]["ussd_summary"]
            elif topic == "0":
                response = "CON Welcome back to Bridge Helpline:\n1. Legal & Safety Assistance\n2. Report Fraud / Scam\n3. Explore Digital World\n4. Audio Guide"
            else:
                response = "END Invalid legal topic."
        # Handle actions inside a topic (e.g., send SMS)
        elif len(parts) >= 3:
            topic = parts[1]
            action = parts[2]
            if topic in LEGAL_GUIDANCE and action == "2":
                send_sms_notification(phone_number, LEGAL_GUIDANCE[topic]["sms_details"])
                response = "END Legal steps sent via SMS. Check your messages."
            else:
                response = "END Action not recognised."

    # Report Fraud / Scam flow
    elif parts[0] == "2":
        # Ask for number to report
        if len(parts) == 1:
            response = "CON Enter the phone number you want to report (local or +256):"
        # Got number, ask for short reason
        elif len(parts) == 2:
            number = parts[1]
            response = "CON Enter a short reason (e.g., 'momo scam', 'impersonation'):\n0. Cancel"
        # Got reason, submit the report
        else:
            number = parts[1]
            reason = parts[2]
            report = report_number(number, reason, reporter=phone_number)
            # Prepare SMS confirmation with a brief risk check
            risk = check_number(number)
            sms_msg = (
                f"BRIDGE: Thanks. Report ID {report['id']} received for {report['number']}.\n"
                f"Risk: {risk['risk_level']}. Reports: {risk['report_count']}.\n"
                "If urgent, contact your telco and file a police report."
            )
            send_sms_notification(phone_number, sms_msg)
            response = "END Thank you — your report has been recorded and a confirmation SMS was sent."

    # Explore Digital World resources
    elif parts[0] == "3":
        if len(parts) == 1:
            response = (
                "CON Explore Digital World:\n"
                "1. Safe mobile money tips\n"
                "2. Common scams explained\n"
                "3. Get rights & resources via SMS\n"
                "0. Back"
            )
        elif len(parts) == 2:
            choice = parts[1]
            if choice == "1":
                msg = (
                    "SAFE TIPS: Never share PINs or OTPs. Verify callers before sending money. "
                    "Report suspicious activity to your telco immediately."
                )
                send_sms_notification(phone_number, msg)
                response = "END Safe mobile money tips sent via SMS."
            elif choice == "2":
                msg = (
                    "COMMON SCAMS: Prize, impersonation, SIM swap, and fake agents. "
                    "Keep transaction receipts and report suspicious numbers."
                )
                send_sms_notification(phone_number, msg)
                response = "END Common scams summary sent via SMS."
            elif choice == "3":
                # Send short rights & resources
                msg = (
                    "RESOURCES: You have rights under the Data Protection & Privacy Act. "
                    "For help, visit CERT-UG, PDPO or call the Police Cybercrime Unit."
                )
                send_sms_notification(phone_number, msg)
                response = "END Rights and resources sent via SMS."
            elif choice == "0":
                response = "CON Welcome back to Bridge Helpline:\n1. Legal & Safety Assistance\n2. Report Fraud / Scam\n3. Explore Digital World\n4. Audio Guide"
            else:
                response = "END Invalid selection."

    # Voice guide
    elif text == "4":
        response = "END Calling your line... Please answer to hear the audio guide."
        trigger_voice_guidance(phone_number)

    # Fallback
    else:
        response = "END Invalid entry. Please dial again."

    resp = make_response(response, 200)
    resp.headers['Content-Type'] = 'text/plain'
    return resp