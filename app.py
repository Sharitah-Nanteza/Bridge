import os
import threading
import africastalking
from flask import Flask, render_template, request, jsonify
from google import genai
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

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

def process_ai_and_sms(phone_number, selected_language, user_query):
    """Background task to query Gemini and send SMS without blocking USSD."""
    try:
        prompt = f"""You are Bridge, a legal and digital safety assistant for Uganda.
Keep your answer brief and clear (under 140 characters).
Refer strictly to Ugandan safety steps or contact options if necessary.
Reply strictly in this language: {selected_language}.
User Issue: {user_query}"""

        res = client.models.generate_content(
            model=MODEL_ID,
            contents=prompt
        )
        answer = res.text.strip()

        if sms and phone_number:
            sms.send(
                message=f"Bridge Advice: {answer}\nHelplines: Police 999, Legal Aid 0800100150",
                recipients=[phone_number]
            )
            print(f"[SUCCESS] SMS sent to {phone_number}")
    except Exception as e:
        print(f"[BACKGROUND ERROR] {e}")

@app.route("/")
def index():
    return render_template("index.html")

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
Provide 3 to 4 direct, actionable steps for the user's issue based strictly on Ugandan law, safety guidelines, and relevant authorities.

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

        # Dispatch AI & SMS tasks to a background thread for zero-latency USSD completion
        threading.Thread(
            target=process_ai_and_sms,
            args=(phone_number, selected_language, user_query)
        ).start()

        response_text = "END Request received! Your safety advice is being processed and will arrive via SMS shortly."
        return response_text, 200, {'Content-Type': 'text/plain'}

if __name__ == "__main__":
    app.run(port=5000, debug=True)