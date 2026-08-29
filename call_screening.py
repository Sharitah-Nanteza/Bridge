"""
Call screening utilities for Africa's Talking voice calls.
Builds XML responses that control call flow (connect, reject, play messages).
"""


def say(message: str) -> str:
    """Build a <Say> XML element to play text-to-speech to the caller."""
    # Escape XML special characters
    safe_message = (message
                    .replace("&", "&amp;")
                    .replace("<", "&lt;")
                    .replace(">", "&gt;")
                    .replace('"', "&quot;")
                    .replace("'", "&apos;"))
    return f'<Say>{safe_message}</Say>'


def dial(phone_number: str) -> str:
    """Build a <Dial> XML element to connect the caller to a phone number."""
    safe_number = (phone_number
                   .replace("&", "&amp;")
                   .replace("<", "&lt;")
                   .replace(">", "&gt;"))
    return f'<Dial>{safe_number}</Dial>'


def reject() -> str:
    """Build a <Reject> XML element to hang up on the caller."""
    return '<Reject/>'


def xml_response(*elements) -> str:
    """Wrap voice control elements in the Africa's Talking XML format."""
    response_content = "".join(elements)
    return f'<?xml version="1.0" encoding="UTF-8"?><Response>{response_content}</Response>'


def build_alert_sms(caller_number: str, reputation: dict) -> str:
    """Build an SMS alert message for the owner about an unverified caller."""
    risk_label = {
        "high": "🚨 HIGH RISK",
        "medium": "⚠️ MEDIUM RISK",
        "low": "📞 LOW RISK",
        "unknown": "❓ UNKNOWN"
    }.get(reputation.get("risk_level"), "❓ UNKNOWN")
    
    caller_display = reputation.get("number", caller_number)
    report_count = reputation.get("report_count", 0)
    
    if report_count == 0:
        return f"Bridge: Incoming call from {caller_display} — {risk_label}\nNo reports on file. Verify independently."
    
    top_category = reputation.get("top_category", "unknown").replace("_", " ")
    flag = reputation.get("flags", [""])[-1]
    
    return (
        f"Bridge: Incoming call from {caller_display} — {risk_label}\n"
        f"Reports: {report_count} | Type: {top_category}\n"
        f"{flag}"
    )


def build_block_sms(caller_number: str, reputation: dict) -> str:
    """Build an SMS alert when a known scammer is blocked."""
    caller_display = reputation.get("number", caller_number)
    report_count = reputation.get("report_count", 0)
    top_category = reputation.get("top_category", "unknown").replace("_", " ")
    
    return (
        f"Bridge:  BLOCKED HIGH-RISK CALL from {caller_display}\n"
        f"Reports: {report_count} | Type: {top_category}\n"
        f"Call was rejected automatically."
    )
