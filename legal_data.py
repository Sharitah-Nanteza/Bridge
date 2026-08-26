"""
Bridge Legal & Digital Safety Knowledge Base
Distills complex Ugandan tech regulations into plain-language actionable steps.
"""

LEGAL_GUIDANCE = {
    "1": {
        "id": "1",
        "category": "Mobile Money Fraud",
        "act": "Computer Misuse Act (Sec. 14 & 19)",
        "ussd_summary": (
            "CON Mobile Money Scam Guidance:\n"
            "1. Block & Report Fraudulent Number\n"
            "2. Receive Full Legal Steps via SMS\n"
            "0. Back"
        ),
        "sms_details": (
            "BRIDGE ALERT: Under Sec. 14 of the Computer Misuse Act, electronic fraud is a punishable offense.\n\n"
            "Action Steps:\n"
            "1. Do NOT reverse money or share your PIN.\n"
            "2. Note down caller number and transaction ID.\n"
            "3. Call telecom provider (MTN 100 / Airtel 100) immediately to flag number.\n"
            "4. File a report with Police Cybercrime Unit."
        )
    },
    "2": {
        "id": "2",
        "category": "Online Harassment & Impersonation",
        "act": "Computer Misuse Act (Sec. 24 - Cyber Stalking)",
        "ussd_summary": (
            "CON Online Harassment Guidance:\n"
            "1. Preserve Evidence & Block\n"
            "2. Receive Reporting Steps via SMS\n"
            "0. Back"
        ),
        "sms_details": (
            "BRIDGE ALERT: Under Sec. 24 of the Computer Misuse Act, cyber harassment and fake account creation carry legal penalties.\n\n"
            "Action Steps:\n"
            "1. Screenshot messages, profiles, and phone numbers as evidence.\n"
            "2. Block offender on all platforms.\n"
            "3. Report online violence to CERT-UG or nearest police station."
        )
    },
    "3": {
        "id": "3",
        "category": "Data Privacy Rights",
        "act": "Data Protection and Privacy Act 2019",
        "ussd_summary": (
            "CON Your Privacy Rights:\n"
            "1. Right to Consent & Access\n"
            "2. Receive Compliance Summary via SMS\n"
            "0. Back"
        ),
        "sms_details": (
            "BRIDGE RIGHTS: Under Data Protection & Privacy Act 2019:\n"
            "1. Companies must obtain explicit consent before collecting personal data.\n"
            "2. You have the right to request deletion of your number from promo lists.\n"
            "3. Report privacy violations to the Personal Data Protection Office (PDPO)."
        )
    }
}