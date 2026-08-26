import os
import google.generativeai as genai
from flask import Flask, render_template, jsonify, request
from dotenv import load_dotenv
from routes.ussd import ussd_bp

load_dotenv()

# Configure Gemini AI
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel('gemini-1.5-flash')

app = Flask(__name__, static_folder='static', template_folder='templates')
app.register_blueprint(ussd_bp)

@app.route('/', methods=['GET'])
def home():
    return render_template('index.html')

# Interactive Inquiry Endpoint (Haki-style Help)
@app.route('/api/ask', methods=['POST'])
def ask_assistant():
    data = request.get_json()
    user_query = data.get("question", "").strip()

    if not user_query:
        return jsonify({"error": "Please ask a question."}), 400

    prompt = f"""
    You are Bridge AI, an expert digital safety & rights assistant for Uganda.
    Answer the user's issue with actionable steps, grounding your advice in relevant laws 
    such as the Computer Misuse Act or Data Protection and Privacy Act 2019.
    
    User Inquiry: {user_query}
    """

    try:
        response = model.generate_content(prompt)
        return jsonify({"reply": response.text})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)