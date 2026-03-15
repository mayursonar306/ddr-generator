# config.py — app-wide constants

# Groq model to use
GROQ_MODEL = "llama-3.3-70b-versatile"

# PDF colours (used by pdf_builder.py)
from reportlab.lib import colors

PDF_WHITE = colors.white
PDF_BLACK = colors.HexColor("#1A1A1A")
PDF_GREY  = colors.HexColor("#555555")
PDF_LIGHT = colors.HexColor("#F5F5F5")
PDF_RED   = colors.HexColor("#C62828")   # High severity
PDF_AMBER = colors.HexColor("#E65100")   # Moderate severity
PDF_GREEN = colors.HexColor("#2E7D32")   # Low severity