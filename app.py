import os
import africastalking
from flask import Flask, render_template, request, jsonify
from google import genai
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

# Initialize the official Google GenAI Client
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

# Initialize Africa's Talking for offline SMS follow-ups
AT_USERNAME = os.getenv("AT_USERNAME", "sandbox")
AT_API_KEY = os.getenv("AT_API_KEY", "")

if AT_API_KEY:
    africastalking.initialize(AT_USERNAME, AT_API_KEY)
    sms = africastalking.SMS
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

# ==========================================
# 1. WEB APP ROUTE
# ==========================================
@app.route("/")
def index():
    return render_template("index.html")

# ==========================================
# 2. WEB API ENDPOINT
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
        prompt = f"""You are Bridge, an interactive legal and digital safety assistant based in Uganda.
Provide 3 to 4 direct, actionable steps for the user's issue based strictly on Ugandan law, safety guidelines, and relevant authorities (e.g., Uganda Police Cybercrime Unit, Uganda Law Society Legal Aid, PDPO).

CRITICAL INSTRUCTIONS:
1. Keep the entire response under 100 words.
2. Do NOT use Markdown formatting (no asterisks, hash tags, or bolding).
3. Use plain sentences and simple numbers (1, 2, 3) so it sounds natural when read aloud.
4. Reply strictly in this language: {target_language}.

User Issue (Uganda context): {user_query}"""

        response = client.models.generate_content(
            model=MODEL_ID,
            contents=prompt
        )
        return jsonify({"answer": response.text})
    except Exception as e:
        print(f"Gemini API Error: {e}")
        return jsonify({"error": str(e)}), 500

# ==========================================
# 3. USSD ENDPOINT (Africa's Talking Callback)
# ==========================================
@app.route("/ussd", methods=["POST"])
def ussd_callback():
    session_id = request.values.get("sessionId", "")
    phone_number = request.values.get("phoneNumber", "")
    text = request.values.get("text", "")

    inputs = text.split("*") if text else []

    if text == "":
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
            return "END Invalid choice. Please try again.", 200, {'Content-Type': 'text/plain'}

        sessions[session_id] = LANGUAGES[lang_code]
        response_text = "CON Describe your legal/digital safety issue / Wandika ekizibu kyo:"
        return response_text, 200, {'Content-Type': 'text/plain'}

    if len(inputs) == 2:
        user_query = inputs[1]
        selected_language = sessions.get(session_id, "English")

        try:
            prompt = f"""You are Bridge, a legal and digital safety assistant for Uganda.
The user is accessing via USSD. Keep your answer brief and clear (under 140 characters).
Refer strictly to Ugandan safety steps or contact options if necessary.
Reply strictly in this language: {selected_language}.
User Issue: {user_query}"""

            res = client.models.generate_content(
                model=MODEL_ID,
                contents=prompt
            )
            answer = res.text.strip()
            response_text = f"END {answer}"

            # Send SMS copy for offline reference
            if sms and phone_number:
                try:
                    sms.send(f"Bridge Advice (Uganda): {answer}\nHelplines: Police 999, Legal Aid 0800100150", [phone_number])
                except Exception as sms_err:
                    print(f"SMS Error: {sms_err}")

        except Exception as e:
            print(f"USSD Gemini Error: {e}")
            response_text = "END Sorry, an error occurred. Please try again later."
        finally:
            sessions.pop(session_id, None)

        return response_text, 200, {'Content-Type': 'text/plain'}

if __name__ == "__main__":
    app.run(port=5000, debug=True)