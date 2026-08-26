import os
from flask import Flask, render_template, request, jsonify
from google import genai
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

# Initialize the official Google GenAI Client
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

# Model set to gemini-3.6-flash
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
        prompt = f"""You are Bridge, an interactive legal and digital safety assistant.
Provide 3 to 4 direct, actionable steps for the user's issue.

CRITICAL INSTRUCTIONS:
1. Keep the entire response under 100 words.
2. Do NOT use Markdown formatting (no asterisks, hash tags, or bolding).
3. Use plain sentences and simple numbers (1, 2, 3) so it sounds natural when read aloud.
4. Reply strictly in this language: {target_language}.

User Issue: {user_query}"""

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
    text = request.values.get("text", "")

    inputs = text.split("*") if text else []

    if text == "":
        response_text = "CON Welcome to Bridge / Londa Olulimi:\n" \
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
            prompt = f"""You are Bridge, a legal and digital safety assistant.
The user is accessing via USSD. Keep your answer brief and clear (under 140 characters).
Reply strictly in this language: {selected_language}.
User Issue: {user_query}"""

            res = client.models.generate_content(
                model=MODEL_ID,
                contents=prompt
            )
            response_text = f"END {res.text}"
        except Exception as e:
            print(f"USSD Gemini Error: {e}")
            response_text = "END Sorry, an error occurred. Please try again later."
        finally:
            sessions.pop(session_id, None)

        return response_text, 200, {'Content-Type': 'text/plain'}

if __name__ == "__main__":
    app.run(port=5000, debug=True)