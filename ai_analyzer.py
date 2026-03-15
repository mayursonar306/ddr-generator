# ai_analyzer.py — call Groq AI to generate the DDR content

import json
import re
import time
import streamlit as st
from groq import Groq, RateLimitError, APIStatusError

from config import GROQ_MODEL


# Keywords used to score lines when trimming long PDFs.
# Includes property-level fields so they are never dropped.
_KEYWORDS = [
    # Property header fields
    "inspection date", "inspected by", "date and time", "property type",
    "previous structural audit", "previous repair", "floors", "score",
    "flagged", "property age", "customer",
    # Observation keywords
    "damp", "leakage", "seepage", "crack", "tile", "bathroom", "bedroom",
    "hall", "kitchen", "parking", "floor", "thermal", "hotspot", "coldspot",
    "plumbing", "wall", "area", "flat", "impacted", "observed",
]

# JSON structure the AI must return
_JSON_SCHEMA = """{
  "property_summary": {
    "property_type": "e.g. Flat / Bungalow",
    "floors": "total number of floors",
    "inspection_date": "date from Inspection Date and Time field",
    "inspected_by": "name(s) from Inspected By field",
    "overall_score": "percentage score e.g. 85.71%",
    "flagged_items": "number of flagged items",
    "previous_audit": "Yes or No from Previous Structural audit done field",
    "previous_repair": "Yes or No from Previous Repair work done field"
  },
  "issue_summary": "3-4 sentence plain-English summary of all problems found.",
  "area_observations": [
    {
      "area": "area name + flat number",
      "problem": "what was observed",
      "source": "likely cause",
      "thermal_reading": "hotspot and coldspot values, or Not Available"
    }
  ],
  "root_causes": ["cause 1", "cause 2"],
  "severity_assessments": [
    {"area": "...", "severity": "High|Moderate|Low", "reasoning": "..."}
  ],
  "recommended_actions": [
    {"priority": "Immediate|Short-term|Long-term", "action": "..."}
  ],
  "additional_notes": ["..."],
  "missing_information": ["..."]
}"""


def _trim(text: str, max_chars: int) -> str:
    """
    Keep the most relevant lines up to max_chars.
    Header lines (date, inspector, score etc.) are always kept first
    because they appear near the top of the document.
    """
    if len(text) <= max_chars:
        return text

    lines = text.splitlines()

    # Always keep the first 30 lines — they contain property header info
    header_lines = lines[:30]
    rest_lines   = lines[30:]

    # Score remaining lines by keyword relevance
    scored = []
    for line in rest_lines:
        lower = line.lower()
        score = sum(1 for k in _KEYWORDS if k in lower)
        scored.append((score, line))
    scored.sort(reverse=True)

    result = list(header_lines)
    total  = sum(len(l) + 1 for l in header_lines)

    for _, line in scored:
        if total + len(line) + 1 > max_chars:
            break
        result.append(line)
        total += len(line) + 1

    return "\n".join(result)


def analyze(inspection_text: str, thermal_text: str, api_key: str) -> dict:
    """
    Send inspection + thermal text to Groq and return a DDR dict.
    Auto-retries with countdown if rate limit is hit.
    """
    prompt = f"""You are a building diagnostic engineer analysing a property inspection report.

IMPORTANT — extract these fields carefully from the INSPECTION DATA:
- "inspection_date"  → look for "Inspection Date and Time" label
- "inspected_by"     → look for "Inspected By" label
- "previous_audit"   → look for "Previous Structural audit done" label (Yes/No)
- "previous_repair"  → look for "Previous Repair work done" label (Yes/No)
- "overall_score"    → look for "Score" percentage
- "flagged_items"    → look for "Flagged items" count
- "property_type"    → look for "Property Type" label
- "floors"           → look for "Floors" label

INSPECTION DATA:
{_trim(inspection_text, 3000)}

THERMAL DATA:
{_trim(thermal_text, 1500)}

Return ONE valid JSON object matching this structure exactly.
No markdown fences, no extra text — just the JSON:
{_JSON_SCHEMA}

Rules:
- Copy values exactly as they appear in the document
- Write "Not Available" only if a field truly cannot be found
- JSON only, no explanation"""

    client  = Groq(api_key=api_key)
    attempt = 0

    while True:
        attempt += 1
        try:
            response = client.chat.completions.create(
                model=GROQ_MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,   # lower = more faithful extraction
                max_tokens=2048,
            )
            raw = response.choices[0].message.content.strip()
            # Strip markdown fences if model adds them
            if raw.startswith("```"):
                raw = re.sub(r"^```[a-z]*\n?", "", raw)
                raw = re.sub(r"\n?```$", "", raw)
            return json.loads(raw)

        except RateLimitError:
            wait = 30
            box  = st.empty()
            bar  = st.progress(0.0)
            for remaining in range(wait, 0, -1):
                box.warning(f"⏳ Rate limit — retrying in {remaining}s (attempt {attempt})")
                bar.progress(1.0 - remaining / wait)
                time.sleep(1)
            box.empty()
            bar.empty()

        except APIStatusError as e:
            raise RuntimeError(f"Groq error {e.status_code}: {e.message}") from e