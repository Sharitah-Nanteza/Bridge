Bridge
An offline digital safety and legal helpline for Uganda powered by Africa's Talking USSD, Voice, and SMS APIs.. It helps people spot mobile money scams and understand their rights, on any phone, with or without internet.

2nd runner-up Africa's Talking Women in Tech Hackathon (Legal & Policy), August 2026.


Features

Ask for Help: plain-language legal guidance, available as audio.
Check or report a number: a community scam-number database that returns a risk level.
Call screening: known scam numbers are blocked; unfamiliar callers connect with a quiet SMS alert.
Trusted contacts: managed by web, USSD or SMS, limited to the verified line owner.
Six languages through Sunbird AI translation, on one shared backend for web, USSD, SMS and voice.

 Tech stack

Python, Flask, Google Gemini, Sunbird AI, Africa's Talking (USSD, SMS, Voice), SQLite, Gunicorn

Run locally


git clone https://github.com/Sharitah-Nanteza/Bridge.git
cd Bridge
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env            # then add your own keys
python app.py

To test USSD, SMS and voice, expose the app with a tunnel such as ngrok and set the callback URLs in your Africa's Talking sandbox.

 Environment variables

Team

Najjuma Phionah, Sharitah Nanteza with Joan Atimango.
[GitHub](https://github.com/Aribe-24) · [LinkedIn](https://www.linkedin.com/in/atimango-joan-826575270)
