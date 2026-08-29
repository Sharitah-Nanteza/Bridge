import os
import africastalking
from flask import Flask, render_template, request, jsonify
from google import genai
from dotenv import load_dotenv
from scamdb import check_number, normalize_number, report_number, get_stats, recent_reports, check_duplicate_report
import calldb
import call_screening
from security import require_auth, rate_limit, get_client_ip, AUTH_TOKEN

load_dotenv()

app = Flask(__name__)

# Print auth token on startup (for documentation purposes)
print(f"🔐 Bridge Auth Token: {AUTH_TOKEN}")
print("   Include this in Authorization header: 'Bearer {token}' for trusted-number/call-log API endpoints")

# Initialize Google GenAI Client
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

# Initialize Africa's Talking SMS
AT_USERNAME = os.getenv("AT_USERNAME", "sandbox")
AT_API_KEY = os.getenv("AT_API_KEY", "")

if AT_API_KEY:
    try:
        africastalking.initialize(AT_USERNAME, AT_API_KEY)
        sms = africastalking.SMS
        voice = africastalking.Voice
    except Exception as e:
        print(f"Africa's Talking Init Error: {e}")
        sms = None
        voice = None
else:
    sms = None
    voice = None

# The real phone number calls get connected to (yours).
OWNER_PHONE_NUMBER = os.getenv("OWNER_PHONE_NUMBER", "")

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
@rate_limit(max_requests=10, window_seconds=60, key_func=get_client_ip)
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
        # Don't leak raw exception message to client
        return jsonify({"error": "Failed to process query. Please try again later."}), 500


@app.route("/api/scams/check", methods=["POST"])
def check_scam_number():
    data = request.get_json() or {}
    number = normalize_number(data.get("number", ""))
    if not number:
        return jsonify({"error": "A phone number is required"}), 400
    return jsonify(check_number(number))


@app.route("/api/scams/report", methods=["POST"])
@rate_limit(max_requests=5, window_seconds=3600, key_func=get_client_ip)
def report_scam_number():
    data = request.get_json() or {}
    number = normalize_number(data.get("number", ""))
    reason = (data.get("reason") or "").strip()
    reporter = (data.get("reporter") or "").strip() or None
    
    if not number or not reason:
        return jsonify({"error": "A phone number and reason are required"}), 400
    
    # Detect duplicate reports to prevent spam
    if check_duplicate_report(number, reporter, window_hours=24):
        return jsonify({
            "error": "This number was recently reported from your device. To prevent spam, "
                     "duplicate reports are limited to once per 24 hours.",
            "duplicate": True
        }), 429
    
    return jsonify(report_number(number, reason, reporter)), 201


@app.route("/api/scams/stats", methods=["GET"])
def scam_stats():
    return jsonify(get_stats())


@app.route("/api/scams/recent", methods=["GET"])
def scam_recent():
    limit = request.args.get("limit", 10, type=int)
    limit = max(1, min(limit, 50))
    return jsonify(recent_reports(limit))


# ==========================================
# 4. SMS COMMANDS (Trusted-number management)
# ==========================================
@app.route("/sms", methods=["POST"])
def sms_inbound():
    """Africa's Talking posts here whenever someone texts your Bridge number.
    Only commands from OWNER_PHONE_NUMBER are honored -- anyone else gets a
    short rejection so the trusted list can't be tampered with remotely."""
    sender = request.values.get("from", "")
    text = (request.values.get("text", "") or "").strip()

    def reply(message: str):
        if sms and sender:
            try:
                sms.send(message=message, recipients=[sender])
            except Exception as sms_err:
                print(f"SMS Reply Warning: {sms_err}")

    if not OWNER_PHONE_NUMBER or normalize_number(sender) != normalize_number(OWNER_PHONE_NUMBER):
        reply("This command is only available to the registered Bridge line owner.")
        return "", 200, {"Content-Type": "text/plain"}

    parts = text.split(maxsplit=2)
    command = parts[0].upper() if parts else ""

    if command == "TRUST" and len(parts) >= 2:
        number = parts[1]
        label = parts[2] if len(parts) > 2 else ""
        saved = calldb.add_trusted(number, label)
        label_note = f" ({label})" if label else ""
        reply(f"Bridge: {saved['number']}{label_note} added to trusted numbers.")

    elif command == "UNTRUST" and len(parts) >= 2:
        number = parts[1]
        removed = calldb.remove_trusted(number)
        reply(f"Bridge: {normalize_number(number)} removed from trusted numbers." if removed
              else f"Bridge: {normalize_number(number)} was not in your trusted list.")

    elif command == "LIST":
        contacts = calldb.list_trusted()
        if not contacts:
            reply("Bridge: No trusted numbers yet. Text TRUST <number> [name] to add one.")
        else:
            lines = [f"{c['number']} - {c['label']}" if c['label'] else c['number'] for c in contacts[:10]]
            reply("Bridge trusted numbers:\n" + "\n".join(lines))

    else:
        reply(
            "Bridge commands:\n"
            "TRUST <number> [name] - add a trusted number\n"
            "UNTRUST <number> - remove one\n"
            "LIST - show trusted numbers"
        )

    return "", 200, {"Content-Type": "text/plain"}


# ==========================================
# 5. CALL SCREENING (Africa's Talking Voice)
# ==========================================
@app.route("/voice", methods=["POST"])
def voice_inbound():
    """Entry point for every inbound call to your Africa's Talking number.
    Calls always connect immediately -- nothing here ever puts a caller on
    hold or makes them wait through a menu. The only two things that
    happen automatically: known scam numbers get silently rejected before
    they ring, and unverified numbers trigger a parallel SMS alert to the
    owner that doesn't delay the call at all."""
    session_id = request.values.get("sessionId", "")
    is_active = request.values.get("isActive", "0")
    caller_number = request.values.get("callerNumber", "")

    if is_active != "1":
        # Call has ended; AT sends a final notification with cost/duration.
        return "", 200, {"Content-Type": "text/plain"}

    normalized_caller = normalize_number(caller_number)

    if not OWNER_PHONE_NUMBER:
        xml = call_screening.xml_response(
            call_screening.say("This line is not fully configured yet. Goodbye."),
            call_screening.reject(),
        )
        return xml, 200, {"Content-Type": "text/plain"}

    # Trusted contact -- connect instantly, no alert needed.
    if calldb.is_trusted(normalized_caller):
        calldb.log_call(normalized_caller, "connected_trusted", session_id=session_id)
        xml = call_screening.xml_response(call_screening.dial(OWNER_PHONE_NUMBER))
        return xml, 200, {"Content-Type": "text/plain"}

    reputation = check_number(normalized_caller)

    # Known scammer -- the one case that actually blocks, since the call
    # was never going to be a real conversation the owner needed to have.
    if reputation["risk_level"] == "high":
        calldb.log_call(normalized_caller, "blocked_known_scammer", session_id=session_id, risk_level="high")
        if sms and OWNER_PHONE_NUMBER:
            try:
                sms.send(message=call_screening.build_block_sms(normalized_caller, reputation), recipients=[OWNER_PHONE_NUMBER])
            except Exception as sms_err:
                print(f"SMS Warning: {sms_err}")
        xml = call_screening.xml_response(
            call_screening.say("This number is unavailable."),
            call_screening.reject(),
        )
        return xml, 200, {"Content-Type": "text/plain"}

    # Everything else (unverified, not previously flagged) -- connect
    # immediately, exactly like a normal call. Only alert the FIRST time
    # this number calls; once the owner has seen it, repeat calls from
    # the same unverified number connect quietly.
    is_new_number = not calldb.has_called_before(normalized_caller)
    action = "connected_alerted" if is_new_number else "connected_no_alert"
    calldb.log_call(normalized_caller, action, session_id=session_id, risk_level=reputation["risk_level"])
    if is_new_number and sms and OWNER_PHONE_NUMBER:
        try:
            sms.send(message=call_screening.build_alert_sms(normalized_caller, reputation), recipients=[OWNER_PHONE_NUMBER])
        except Exception as sms_err:
            print(f"SMS Warning: {sms_err}")
    xml = call_screening.xml_response(call_screening.dial(OWNER_PHONE_NUMBER))
    return xml, 200, {"Content-Type": "text/plain"}


# ==========================================
# 6. TRUSTED CONTACTS + CALL LOG API
# ==========================================
@app.route("/api/calls/trusted", methods=["GET"])
@require_auth
def list_trusted_numbers():
    """Retrieve list of trusted numbers (requires auth token)."""
    return jsonify(calldb.list_trusted())


@app.route("/api/calls/trusted", methods=["POST"])
@require_auth
def add_trusted_number():
    """Add a trusted number (requires auth token)."""
    data = request.get_json() or {}
    number = data.get("number", "")
    label = (data.get("label") or "").strip()
    if not number.strip():
        return jsonify({"error": "A phone number is required"}), 400
    return jsonify(calldb.add_trusted(number, label)), 201


@app.route("/api/calls/trusted/<number>", methods=["DELETE"])
@require_auth
def remove_trusted_number(number):
    """Remove a trusted number (requires auth token)."""
    removed = calldb.remove_trusted(number)
    if not removed:
        return jsonify({"error": "Number not found in trusted list"}), 404
    return jsonify({"removed": True})


@app.route("/api/calls/recent", methods=["GET"])
@require_auth
def recent_call_log():
    """Retrieve recent call logs (requires auth token)."""
    limit = request.args.get("limit", 20, type=int)
    limit = max(1, min(limit, 50))
    return jsonify(calldb.recent_calls(limit))


# ==========================================
# 7. USSD ENDPOINT (Basic Phone Interface)
# ==========================================
@app.route("/ussd", methods=["POST"])
@rate_limit(max_requests=30, window_seconds=60, key_func=lambda: request.values.get("phoneNumber", "unknown"))
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
        sessions[session_id] = {"lang": LANGUAGES[lang_code]}
        response_text = "CON 1. Describe an issue\n2. Check a phone number\n3. Manage Trusted Numbers\n0. Back"
        return response_text, 200, {'Content-Type': 'text/plain'}

    is_owner = bool(OWNER_PHONE_NUMBER) and normalize_number(phone_number) == normalize_number(OWNER_PHONE_NUMBER)

    if len(inputs) == 2 and inputs[1] in ("1", "2"):
        session = sessions.get(session_id, {})
        session["mode"] = "query" if inputs[1] == "1" else "check"
        sessions[session_id] = session
        prompt_text = "CON Describe your legal/digital safety issue:" if inputs[1] == "1" \
            else "CON Enter the phone number to check:"
        return prompt_text, 200, {'Content-Type': 'text/plain'}

    # -- Trusted-number management (owner only) --
    if inputs[1:2] == ["3"]:
        if not is_owner:
            return "END This feature is only available to the Bridge line owner.", 200, {'Content-Type': 'text/plain'}

        if len(inputs) == 2:
            return "CON 1. Add a number\n2. Remove a number\n3. List trusted numbers\n0. Back", 200, {'Content-Type': 'text/plain'}

        sub = inputs[2]
        if sub == "0":
            return "CON 1. Describe an issue\n2. Check a phone number\n3. Manage Trusted Numbers\n0. Back", 200, {'Content-Type': 'text/plain'}

        if sub == "1":  # Add
            if len(inputs) == 3:
                return "CON Enter the phone number to trust:", 200, {'Content-Type': 'text/plain'}
            if len(inputs) == 4:
                return "CON Enter a name for this contact, or 0 to skip:", 200, {'Content-Type': 'text/plain'}
            number = inputs[3]
            label = "" if inputs[4] == "0" else inputs[4]
            saved = calldb.add_trusted(number, label)
            label_note = f" ({label})" if label else ""
            return f"END Saved. {saved['number']}{label_note} will now connect without alerts.", 200, {'Content-Type': 'text/plain'}

        if sub == "2":  # Remove
            if len(inputs) == 3:
                return "CON Enter the phone number to remove:", 200, {'Content-Type': 'text/plain'}
            number = inputs[3]
            removed = calldb.remove_trusted(number)
            msg = f"END Removed {normalize_number(number)} from trusted numbers." if removed \
                else f"END {normalize_number(number)} was not in your trusted list."
            return msg, 200, {'Content-Type': 'text/plain'}

        if sub == "3":  # List
            contacts = calldb.list_trusted()
            if not contacts:
                return "END No trusted numbers yet.", 200, {'Content-Type': 'text/plain'}
            lines = [f"{c['number']} - {c['label']}" if c['label'] else c['number'] for c in contacts[:8]]
            return "END Trusted Numbers:\n" + "\n".join(lines), 200, {'Content-Type': 'text/plain'}

        return "END Invalid choice.", 200, {'Content-Type': 'text/plain'}

    if len(inputs) >= 3:
        session = sessions.get(session_id, {})
        selected_language = session.get("lang", "English")
        mode = session.get("mode", "query")
        user_input = "*".join(inputs[2:])
        sessions.pop(session_id, None)

        if mode == "check":
            result = check_number(user_input)
            risk_labels = {"high": "HIGH RISK", "medium": "MEDIUM RISK", "low": "LOW RISK", "unknown": "NO REPORTS YET"}
            response_text = f"END {result['number']}: {risk_labels.get(result['risk_level'], 'UNKNOWN')}\n" \
                             f"Reports: {result['report_count']}. " \
                             f"{result['flags'][0] if result['flags'] else ''}"
            return response_text, 200, {'Content-Type': 'text/plain'}

        try:
            ai_advice = get_bridge_ai_response(user_input, selected_language)
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

    return "END Invalid entry. Please dial again.", 200, {'Content-Type': 'text/plain'}


if __name__ == "__main__":
    app.run(port=5000, debug=True)

#
#    And a few lines down, find:
#
#        ai_advice = get_bridge_ai_response(user_input, selected_language)
#
#    Change it to:
#
#        ai_advice = get_bridge_ai_response(user_input, selected_lang_code)
 
