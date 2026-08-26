import os
from flask import Flask, render_template, jsonify, request
from dotenv import load_dotenv
from google import genai
from routes.ussd import ussd_bp

load_dotenv()

# Initialize Google GenAI Client
api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")

if api_key:
    client = genai.Client(api_key=api_key)
else:
    client = None
    print("Warning: GEMINI_API_KEY is missing in your .env file!")

app = Flask(__name__, static_folder='static', template_folder='templates')
app.register_blueprint(ussd_bp)

@app.route('/', methods=['GET'])
def home():
    return render_template('index.html')

# Interactive Inquiry Endpoint
@app.route('/api/ask', methods=['POST'])
def ask_assistant():
    if not client:
        return jsonify({"error": "API Key is missing on the server."}), 500

    data = request.get_json() or {}
    user_query = data.get("question", "").strip()

    if not user_query:
        return jsonify({"error": "Please provide a valid question."}), 400

    prompt = f"""
    You are Bridge AI, an expert digital safety & rights assistant for Uganda.
    Answer the user's issue with clear, practical steps and ground your advice 
    in relevant Ugandan laws (such as the Computer Misuse Act or Data Protection and Privacy Act 2019).
    
    User Inquiry: {user_query}
    """

    try:
        response = client.models.generate_content(
            model='gemini-3.6-flash',
            contents=prompt
        )
        return jsonify({"reply": response.text})
    except Exception as e:
        return jsonify({"error": f"Failed to reach Gemini AI: {str(e)}"}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)