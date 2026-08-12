import base64
import json
import re
import sys
import requests


IMAGE = "pages/page1.jpg"
OUTPUT = "output/page_1.json"
API_URL = "http://127.0.0.1:8080/v1/chat/completions"


PROMPT = r"""
You are an expert document-extraction system.

You are analyzing ONE PAGE from a scanned RPSC/Rajasthan competitive
examination question paper.

Your job is ONLY to accurately extract the questions visible on this page.

IMPORTANT RULES:

1. Hindi and English versions of the same question are ONE question.
   Do NOT create two questions from the bilingual versions.

2. Preserve the original question number.

3. Extract the Hindi question text.

4. Extract the English question text.

5. Extract every answer option.

6. Preserve the option labels A, B, C and D.

7. Preserve mathematical expressions as accurately as possible.

8. Preserve numbers, dates, names and symbols.

9. Preserve statement-based questions exactly.

10. If a question contains a table, diagram, map, chart or other visual,
    identify it.

11. DO NOT solve any question.

12. DO NOT guess the correct answer.

13. DO NOT add explanations.

14. DO NOT invent text that is not visible.

15. If a small part of the text is genuinely impossible to read,
    write "[UNCLEAR]" rather than inventing it.

16. Return ONLY valid JSON.
    Do not use Markdown.
    Do not put the JSON inside ```json fences.

Use exactly this structure:

{
  "questions": [
    {
      "number": 1,
      "question_hi": "...",
      "question_en": "...",
      "options": [
        {
          "label": "A",
          "hi": "...",
          "en": "..."
        },
        {
          "label": "B",
          "hi": "...",
          "en": "..."
        },
        {
          "label": "C",
          "hi": "...",
          "en": "..."
        },
        {
          "label": "D",
          "hi": "...",
          "en": "..."
        }
      ],
      "visual": null
    }
  ]
}
"""


def image_to_base64(path):
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def extract_json(text):
    """
    Try to recover JSON if the model accidentally wraps it in Markdown
    or adds a little text around it.
    """

    text = text.strip()

    # Remove Markdown JSON fences if present.
    text = re.sub(r"^```json\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"^```\s*", "", text)
    text = re.sub(r"\s*```$", "", text)

    text = text.strip()

    # First attempt: entire response is JSON.
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Second attempt: find the first JSON object.
    start = text.find("{")
    end = text.rfind("}")

    if start != -1 and end != -1 and end > start:
        candidate = text[start:end + 1]

        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            pass

    raise ValueError(
        "The model did not return valid JSON.\n\n"
        f"MODEL RESPONSE:\n{text}"
    )


def main():

    print("Reading page image...")
    image_b64 = image_to_base64(IMAGE)

    payload = {
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": PROMPT
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

    print("Sending page to Qwen3-VL...")
    print("This may take a while on CPU.")

    try:
        response = requests.post(
            API_URL,
            json=payload,
            timeout=1800
        )
    except requests.RequestException as e:
        print("ERROR communicating with llama-server:")
        print(e)
        sys.exit(1)

    print(f"HTTP status: {response.status_code}")

    if response.status_code != 200:
        print("========== SERVER RESPONSE ==========")
        print(response.text)
        sys.exit(1)

    try:
        result = response.json()
    except json.JSONDecodeError:
        print("ERROR: llama-server returned invalid JSON.")
        print(response.text)
        sys.exit(1)

    try:
        model_text = result["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError):
        print("ERROR: Unexpected llama-server response:")
        print(json.dumps(result, indent=2, ensure_ascii=False))
        sys.exit(1)

    print("")
    print("========== RAW MODEL OUTPUT ==========")
    print(model_text)
    print("=======================================")
    print("")

    try:
        structured = extract_json(model_text)
    except ValueError as e:
        print(str(e))

        # Save raw output so we can inspect exactly what went wrong.
        with open(
            "output/page_1_raw.txt",
            "w",
            encoding="utf-8"
        ) as f:
            f.write(model_text)

        sys.exit(1)

    # Basic validation.
    if not isinstance(structured, dict):
        print("ERROR: Root JSON value is not an object.")
        sys.exit(1)

    if "questions" not in structured:
        print("ERROR: JSON does not contain 'questions'.")
        sys.exit(1)

    if not isinstance(structured["questions"], list):
        print("ERROR: 'questions' is not a list.")
        sys.exit(1)

    # Save pretty JSON.
    with open(
        OUTPUT,
        "w",
        encoding="utf-8"
    ) as f:
        json.dump(
            structured,
            f,
            ensure_ascii=False,
            indent=2
        )

    print("=======================================")
    print("SUCCESS")
    print(f"Questions extracted: {len(structured['questions'])}")
    print(f"Saved to: {OUTPUT}")
    print("=======================================")


if __name__ == "__main__":
    main()
