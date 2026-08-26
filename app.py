import os
from flask import Flask, render_template, jsonify
from dotenv import load_dotenv
from routes.ussd import ussd_bp
from legal_data import LEGAL_GUIDANCE

load_dotenv()

app = Flask(__name__, static_folder='static', template_folder='templates')

# Register USSD route
app.register_blueprint(ussd_bp)

# Web Browser Routes
@app.route('/', methods=['GET'])
def home():
    return render_template('index.html')

# JSON API for JavaScript Frontend
@app.route('/api/guides', methods=['GET'])
def get_guides():
    return jsonify(LEGAL_GUIDANCE)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)