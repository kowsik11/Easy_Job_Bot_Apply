"""
answers.py  – central place to tune default answers
──────────────────────────────────────────────────────────────────────────────
• The bot lower-cases each question label and looks for keywords here.
• If a keyword is found, that value is used.
• Everything else falls back to generic defaults in linkedin.py
"""

_DEFAULTS = {
    # keyword ➜ answer
    "visa":           "No",
    "sponsorship":    "No",
    "salary":         "0",
    "compensation":   "0",
    "notice period":  "0",
    "notice":         "0",
    "pronoun":        "They/Them",
    "javascript":     "0",
    "react.js":        "0",
    "wordpress":      "0",
    "dashboard":      "0",
    "background":     "Yes",
    # add / tweak as you like …
}

def lookup(label: str):
    """Return a default answer or *None* so caller can fall back."""
    label = label.lower()
    for kw, ans in _DEFAULTS.items():
        if kw in label:
            return ans
    return None
