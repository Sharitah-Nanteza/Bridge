"""
Sunbird AI translation integration for Bridge.

Used to turn a reliable English answer from Gemini into Luganda,
Runyankole, Lugbara, or Acholi -- instead of trusting Gemini to
generate directly in those lower-resource languages, which is far
less predictable.

Swahili is NOT covered here: Sunbird's nllb_translate endpoint only
supports ach/teo/eng/lug/lgg/nyn, no Swahili -- so Swahili keeps
going straight to Gemini (see app.py's GEMINI_DIRECT_LANGS).
"""
import os
import requests

SUNBIRD_API_KEY = os.getenv("SUNBIRD_API_KEY", "")
SUNBIRD_TRANSLATE_URL = "https://api.sunbird.ai/tasks/nllb_translate"

# Bridge's internal language codes -> Sunbird's translation codes.
# Only 'lg' and 'en' actually differ; nyn/lgg/ach already match.
LANG_CODE_MAP = {
    "en": "eng",
    "lg": "lug",
    "nyn": "nyn",
    "lgg": "lgg",
    "ach": "ach",
}

# Languages we can translate INTO via Sunbird. Swahili is deliberately
# excluded -- there is no Sunbird target code for it.
TRANSLATABLE_TARGETS = {"lg", "nyn", "lgg", "ach"}


class SunbirdTranslateError(Exception):
    """Raised when translation fails -- callers should fall back to
    asking Gemini to answer directly in the target language rather
    than surface this as a hard error to the user."""


def supports_target(lang_code: str) -> bool:
    return lang_code in TRANSLATABLE_TARGETS


def translate_to_local(english_text: str, target_lang_code: str) -> str:
    """Translate `english_text` into `target_lang_code` via Sunbird AI.
    Raises SunbirdTranslateError on any failure."""
    if not supports_target(target_lang_code):
        raise SunbirdTranslateError(f"No Sunbird translation target for '{target_lang_code}'")
    if not SUNBIRD_API_KEY:
        raise SunbirdTranslateError("SUNBIRD_API_KEY is not configured")

    text = english_text.strip()
    if not text:
        raise SunbirdTranslateError("Empty text")
    # Sunbird's docs recommend keeping inputs short (<512 tokens) for
    # consistent quality -- Bridge's answers are already capped at ~80
    # words by the Gemini prompt, so this is just a safety ceiling.
    if len(text) > 2000:
        text = text[:2000]

    try:
        resp = requests.post(
            SUNBIRD_TRANSLATE_URL,
            headers={
                "Authorization": f"Bearer {SUNBIRD_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "source_language": "eng",
                "target_language": LANG_CODE_MAP[target_lang_code],
                "text": text,
            },
            timeout=30,
        )
        resp.raise_for_status()
        payload = resp.json()

        if payload.get("status") not in (None, "success"):
            error_detail = (payload.get("output") or {}).get("Error")
            raise SunbirdTranslateError(f"Sunbird translation job failed: {error_detail}")

        translated = (payload.get("output") or {}).get("translated_text")
        if not translated:
            raise SunbirdTranslateError("Empty translation returned")
        return translated
    except requests.RequestException as e:
        raise SunbirdTranslateError(f"Sunbird translate request failed: {e}") from e
    except (KeyError, ValueError) as e:
        raise SunbirdTranslateError(f"Unexpected Sunbird translate response shape: {e}") from e