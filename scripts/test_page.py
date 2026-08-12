import base64
import json
import requests

IMAGE = "pages/page-1.jpg"

with open(IMAGE, "rb") as f:
    image_b64 = base64.b64encode(f.read()).decode()

prompt = r"""
You are processing an RPSC/Rajasthan competitive-exam question paper.

Analyze this page carefully.

Your task is ONLY to extract the questions visible on this page.

Important:
- Hindi and English versions of the same question are ONE question.
- Preserve the question number.
- Preserve the Hindi text.
- Preserve the English text.
- Preserve all four options.
- Preserve mathematical notation.
- Preserve statement-based questions.
- Do not solve the questions.
- Do not invent missing text.
- If a diagram/table/map is present, describe it.
- Return ONLY valid JSON.

Return:

{
  "questions": [
    {
      "number": 1,
      "question_hi": "...",
      "question_en": "...",
      "options": [
        {"label": "A", "hi": "...", "en": "..."},
        {"label": "B", "hi": "...", "en": "..."},
        {"label": "C", "hi": "...", "en": "..."},
        {"label": "D", "hi": "...", "en": "..."}
      ],
      "visual": null
    }
  ]
}
"""

payload = {
    "messages": [
        {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": prompt
                },
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/jpeg;base64,{image_b64}"
                    }
                }
            ]
        }
    ],
    "temperature": 0.0,
    "max_tokens": 6000
}

response = requests.post(
    "http://127.0.0.1:8080/v1/chat/completions",
    json=payload,
    timeout=1800
)

response.raise_for_status()

data = response.json()

text = data["choices"][0]["message"]["content"]

print(text)

with open("output/page_1.json", "w", encoding="utf-8") as f:
    f.write(text)
