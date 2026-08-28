import os
import africastalking
from flask import Flask, render_template, request, jsonify
from google import genai
from dotenv import load_dotenv
from scamdb import check_number, normalize_number, report_number

load_dotenv()

app = Flask(__name__)

# Initialize Google GenAI Client
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

# Initialize Africa's Talking SMS
AT_USERNAME = os.getenv("AT_USERNAME", "sandbox")
AT_API_KEY = os.getenv("AT_API_KEY", "")

if AT_API_KEY:
    try:
        africastalking.initialize(AT_USERNAME, AT_API_KEY)
        sms = africastalking.SMS
    except Exception as e:
        print(f"Africa's Talking Init Error: {e}")
        sms = None
else:
    sms = None

MODEL_ID = "gemini-3.6-flash"

LANGUAGES = {
    "en": "English",
    "lg": "Luganda",
    "sw": "Swahili",
    "nyn": "Runyankole / Rukiga",
    "lgg": "Lugbara",
    "ach": "Acholi (Luo)"
}

USSD_LANG_MAP = {
    "1": "en",
    "2": "lg",
    "3": "sw",
    "4": "nyn",
    "5": "lgg",
    "6": "ach"
}

sessions = {}

def get_bridge_ai_response(user_query, target_language):
    """Unified AI helper function so both Web and USSD receive identical advice."""
    prompt = f"""You are Bridge, an interactive legal and digital safety assistant based in Uganda.
Provide 3 direct, actionable steps for the user's issue based strictly on Ugandan law, safety guidelines, and relevant authorities (e.g., Uganda Police Cybercrime Unit, Uganda Law Society Legal Aid, PDPO).

CRITICAL INSTRUCTIONS:
1. Keep the response concise (around 80 words) so it fits comfortably on screen.
2. Do NOT use Markdown formatting (no asterisks, hash tags, or bolding).
3. Use plain sentences and simple numbers (1, 2, 3) so it displays clearly on all screens.
4. Reply strictly in this language: {target_language}.

User Issue (Uganda context): {user_query}"""

    response = client.models.generate_content(
        model=MODEL_ID,
        contents=prompt
    )
    return response.text.strip()

@app.after_request
def add_localtunnel_bypass_header(response):
    response.headers["Bypass-Tunnel-Reminder"] = "true"
    return response

# ==========================================
# 1. WEB APP ROUTE
# ==========================================
@app.route("/")
def index():
    return render_template("index.html")

# ==========================================
# 2. WEB API ENDPOINTS
# ==========================================
@app.route("/api/query", methods=["POST"])
def web_query():
    data = request.get_json() or {}
    user_query = data.get("query", "")
    lang_code = data.get("language", "en")
    target_language = LANGUAGES.get(lang_code, "English")

    if not user_query.strip():
        return jsonify({"error": "Query cannot be empty"}), 400

    try:
        answer = get_bridge_ai_response(user_query, target_language)
        return jsonify({"answer": answer})
    except Exception as e:
        print(f"Gemini API Error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/api/scams/check", methods=["POST"])
def check_scam_number():
    data = request.get_json() or {}
    number = normalize_number(data.get("number", ""))
    if not number:
        return jsonify({"error": "A phone number is required"}), 400
    return jsonify(check_number(number))

@app.route("/api/scams/report", methods=["POST"])
def report_scam_number():
    data = request.get_json() or {}
    number = normalize_number(data.get("number", ""))
    reason = (data.get("reason") or "").strip()
    if not number or not reason:
        return jsonify({"error": "A phone number and reason are required"}), 400
    return jsonify(report_number(number, reason, (data.get("reporter") or "").strip() or None)), 201

# ==========================================
# 3. USSD ENDPOINT (Basic Phone Interface)
# ==========================================
@app.route("/ussd", methods=["POST"])
def ussd_callback():
    session_id = request.values.get("sessionId", "")
    phone_number = request.values.get("phoneNumber", "")
    text = request.values.get("text", "")

    inputs = [i.strip() for i in text.split("*")] if text else []

    if text == "" or not inputs:
        response_text = "CON Welcome to Bridge Uganda / Londa Olulimi:\n" \
                        "1. English\n" \
                        "2. Luganda\n" \
                        "3. Swahili\n" \
                        "4. Runyankole\n" \
                        "5. Lugbara\n" \
                        "6. Acholi"
        return response_text, 200, {'Content-Type': 'text/plain'}

    if len(inputs) == 1:
        lang_choice = inputs[0]
        lang_code = USSD_LANG_MAP.get(lang_choice)

        if not lang_code:
            return "END Invalid choice. Please dial again and select a number from 1 to 6.", 200, {'Content-Type': 'text/plain'}

        sessions[session_id] = LANGUAGES[lang_code]
        response_text = "CON Describe your legal/digital safety issue / Wandika ekizibu kyo:"
        return response_text, 200, {'Content-Type': 'text/plain'}

    if len(inputs) >= 2:
        user_query = "*".join(inputs[1:])
        selected_language = sessions.get(session_id, "English")
        sessions.pop(session_id, None)

        try:
            ai_advice = get_bridge_ai_response(user_query, selected_language)
            response_text = f"END {ai_advice}\nHelplines: Police 999, Legal Aid 0800100150"

            if sms and phone_number:
                try:
                    sms.send(
                        message=f"Bridge Advice:\n{ai_advice}\nHelplines: Police 999",
                        recipients=[phone_number]
                    )
                except Exception as sms_err:
                    print(f"SMS Copy Warning: {sms_err}")

        except Exception as e:
            print(f"USSD Gemini Error: {e}")
            response_text = "END Service unavailable. Please call Police 999 or Legal Aid 0800100150."

        return response_text, 200, {'Content-Type': 'text/plain'}

if __name__ == "__main__":
    app.run(port=5000, debug=True)