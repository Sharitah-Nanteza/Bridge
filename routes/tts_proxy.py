"""
Text-to-speech for Bridge, backed by Sunbird AI's /tasks/tts endpoint
(https://salt.sunbird.ai/API/), which is a real speech model trained for
Ugandan languages -- unlike the browser's built-in speechSynthesis, which
has no Luganda/Runyankole/Lugbara/Acholi voices at all and was silently
mispronouncing them with a fallback English/Swahili voice.

English keeps using the browser's speechSynthesis on the frontend (it's
well supported there) -- this module only covers the five local languages
Sunbird has trained voices for.

Two things this module handles that the frontend can't safely do itself:
  1. The Sunbird API key must never reach the browser.
  2. Sunbird's response is a signed download URL that expires in ~120
     seconds, so we fetch the audio immediately, server-side, and hand
     the browser the actual mp3 bytes -- not the URL.

Identical text is cached to disk (keyed by text + speaker_id) so the same
canned strings -- like the "how Bridge works" intro, which every first-
time visitor hears -- aren't re-synthesized (and re-billed) every time.
"""
import hashlib
import os
from pathlib import Path

import requests
from flask import Blueprint, Response, jsonify, request

tts_bp = Blueprint("tts", __name__)

SUNBIRD_API_KEY = os.getenv("SUNBIRD_API_KEY", "")
SUNBIRD_TTS_URL = "https://api.sunbird.ai/tasks/tts"

# Only languages Sunbird has a trained voice for. "en" is deliberately
# absent -- that one stays on the frontend's browser speechSynthesis.
SPEAKER_IDS = {
    "lg": 248,   # Luganda
    "sw": 246,   # Swahili
    "nyn": 243,  # Runyankole / Rukiga
    "lgg": 245,  # Lugbara
    "ach": 241,  # Acholi
}

CACHE_DIR = Path(os.getenv("TTS_CACHE_DIR", Path(__file__).parent / "tts_cache"))
CACHE_DIR.mkdir(exist_ok=True)


def _cache_path(text: str, speaker_id: int) -> Path:
    digest = hashlib.sha256(f"{speaker_id}:{text}".encode("utf-8")).hexdigest()
    return CACHE_DIR / f"{digest}.mp3"


@tts_bp.route("/api/tts", methods=["POST"])
def synthesize():
    if not SUNBIRD_API_KEY:
        return jsonify({"error": "TTS is not configured on the server (missing SUNBIRD_API_KEY)."}), 503

    data = request.get_json() or {}
    text = (data.get("text") or "").strip()
    language = data.get("language", "")

    if not text:
        return jsonify({"error": "Text is required"}), 400
    if language not in SPEAKER_IDS:
        return jsonify({"error": f"No Sunbird voice for language '{language}'. Use browser TTS for English."}), 400
    if len(text) > 5000:
        text = text[:5000]

    speaker_id = SPEAKER_IDS[language]
    cache_file = _cache_path(text, speaker_id)

    if cache_file.exists():
        return Response(cache_file.read_bytes(), mimetype="audio/mpeg")

    try:
        tts_resp = requests.post(
            SUNBIRD_TTS_URL,
            headers={"Authorization": f"Bearer {SUNBIRD_API_KEY}", "Content-Type": "application/json"},
            json={"text": text, "speaker_id": speaker_id, "temperature": 0.6},
            timeout=30,
        )
        tts_resp.raise_for_status()
        audio_url = tts_resp.json()["output"]["audio_url"]

        # Signed URL expires in ~120s -- fetch it immediately, don't hand it to the client.
        audio_resp = requests.get(audio_url, timeout=30)
        audio_resp.raise_for_status()
        audio_bytes = audio_resp.content

        cache_file.write_bytes(audio_bytes)
        return Response(audio_bytes, mimetype="audio/mpeg")

    except requests.exceptions.Timeout:
        return jsonify({"error": "Voice service timed out. Please try again."}), 504
    except requests.exceptions.RequestException as e:
        print(f"Sunbird TTS error: {e}")
        return jsonify({"error": "Voice service is temporarily unavailable."}), 502