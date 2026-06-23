"""
OmniShield 360 - PII / PHI Masking Module
Simulates the UiPath AI Trust Layer in-flight anonymization gateway.
Strips all Protected Health Information before any text reaches external AI models.
"""

import re


def mask_phi_data(text: str) -> tuple:
    """
    Locally masks critical patient identifiers.
    Returns: (anonymized_text, token_map)
    The token_map is stored ONLY inside the secure local tenant — never sent externally.
    """
    phi_map = {}
    counter = {"n": 0, "d": 0, "s": 0, "p": 0}

    # 1. Patient names — "Patient Name: John Doe" pattern
    def replace_name(match):
        token = f"[PATIENT_NAME_{counter['n']}]"
        phi_map[token] = match.group(1).strip()
        counter["n"] += 1
        return f"Patient Name: {token}"

    text = re.sub(r"Patient Name:\s*([A-Za-z\s\-']+)", replace_name, text)

    # 2. Dates of birth — MM/DD/YYYY
    def replace_dob(match):
        token = f"[DOB_TOKEN_{counter['d']}]"
        phi_map[token] = match.group(0)
        counter["d"] += 1
        return token

    text = re.sub(r"\b\d{2}/\d{2}/\d{4}\b", replace_dob, text)

    # 3. SSNs — XXX-XX-XXXX
    def replace_ssn(match):
        token = f"[SSN_TOKEN_{counter['s']}]"
        phi_map[token] = match.group(0)
        counter["s"] += 1
        return token

    text = re.sub(r"\b\d{3}-\d{2}-\d{4}\b", replace_ssn, text)

    # 4. Phone numbers
    def replace_phone(match):
        token = f"[PHONE_TOKEN_{counter['p']}]"
        phi_map[token] = match.group(0)
        counter["p"] += 1
        return token

    text = re.sub(r"\b(\(?\d{3}\)?[\s\-\.]\d{3}[\s\-\.]\d{4})\b", replace_phone, text)

    return text, phi_map


def restore_phi_data(anonymized_text: str, token_map: dict) -> str:
    """
    Reverses tokenization locally inside the secure tenant.
    Called ONLY after AI reasoning is complete and result is back in the secure boundary.
    """
    for token, real_value in token_map.items():
        anonymized_text = anonymized_text.replace(token, real_value)
    return anonymized_text
