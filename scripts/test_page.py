import base64
import json
import re
import sys

import requests


# ---------------------------------------------------------
# Configuration
# ---------------------------------------------------------

IMAGE = "pages/page1.jpg"

OUTPUT = "output/page_1.json"

RAW_OUTPUT = "output/page_1_raw.txt"

API_URL = "http://127.0.0.1:8080/v1/chat/completions"


# ---------------------------------------------------------
# Prompt
# ---------------------------------------------------------

PROMPT = r"""
You are an expert document-extraction system.

You are analyzing ONE PAGE from a scanned RPSC/Rajasthan
competitive examination question paper.

Your job is ONLY to accurately extract the questions visible
on this page.

IMPORTANT RULES:

1. Hindi and English versions of the same question are ONE
   question.

2. Do NOT create two questions from bilingual versions.

3. Preserve the original question number.

4. Extract the Hindi question text.

5. Extract the English question text.

6. Extract EVERY answer option visible.

7. Preserve option labels A, B, C and D.

8. Preserve mathematical expressions as accurately as possible.

9. Preserve numbers, dates, names and symbols.

10. Preserve statement-based questions.

11. If the question contains a table, diagram, map, chart,
    equation or other visual, identify it.

12. DO NOT solve any question.

13. DO NOT guess the correct answer.

14. DO NOT add explanations.

15. DO NOT invent text that is not visible.

16. If a part of the text is genuinely impossible to read,
    write "[UNCLEAR]" instead of guessing.

17. If the page contains no complete question, return an
    empty questions array.

18. Return ONLY valid JSON.

19. Do NOT use Markdown.

20. Do NOT put the JSON inside ```json fences.

Return exactly this structure:

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


# ---------------------------------------------------------
# Convert image to Base64
# ---------------------------------------------------------

def image_to_base64(path):

    with open(path, "rb") as f:
        image_bytes = f.read()

    return base64.b64encode(image_bytes).decode("utf-8")


# ---------------------------------------------------------
# Extract JSON from model response
# ---------------------------------------------------------

def extract_json(text):

    text = text.strip()

    # Remove accidental Markdown fences.

    text = re.sub(
        r"^```json\s*",
        "",
        text,
        flags=re.IGNORECASE
    )

    text = re.sub(
        r"^```\s*",
        "",
        text
    )

    text = re.sub(
        r"\s*```$",
        "",
        text
    )

    text = text.strip()

    # -----------------------------------------------------
    # Attempt 1:
    # Entire response is JSON.
    # -----------------------------------------------------

    try:
        return json.loads(text)

    except json.JSONDecodeError:
        pass

    # -----------------------------------------------------
    # Attempt 2:
    # Find JSON object inside response.
    # -----------------------------------------------------

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
        "MODEL RESPONSE:\n"
        + text
    )


# ---------------------------------------------------------
# Main
# ---------------------------------------------------------

def main():

    print("======================================")
    print("RPSC PYQ AI TEST")
    print("======================================")

    # -----------------------------------------------------
    # Check image
    # -----------------------------------------------------

    print("")
    print("Checking input image...")

    try:

        image_b64 = image_to_base64(IMAGE)

    except FileNotFoundError:

        print(
            f"ERROR: Could not find {IMAGE}"
        )

        sys.exit(1)

    print(
        f"Image loaded successfully."
    )

    print(
        f"Base64 size: {len(image_b64):,} characters"
    )

    # -----------------------------------------------------
    # Build API request
    # -----------------------------------------------------

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

                            "url":
                            f"data:image/jpeg;base64,{image_b64}"

                        }

                    }

                ]

            }

        ],

        "temperature": 0.0,

        "max_tokens": 6000

    }

    # -----------------------------------------------------
    # Send request
    # -----------------------------------------------------

    print("")
    print("Sending page to Qwen3-VL...")
    print("")
    print("IMPORTANT:")
    print(
        "CPU inference may take several minutes."
    )
    print("")

    try:

        response = requests.post(

            API_URL,

            json=payload,

            timeout=1800

        )

    except requests.RequestException as error:

        print("")
        print(
            "ERROR communicating with llama-server:"
        )

        print(error)

        sys.exit(1)

    # -----------------------------------------------------
    # HTTP response
    # -----------------------------------------------------

    print(
        f"HTTP status: {response.status_code}"
    )

    if response.status_code != 200:

        print("")
        print(
            "======================================"
        )

        print(
            "SERVER RESPONSE"
        )

        print(
            "======================================"
        )

        print(response.text)

        sys.exit(1)

    # -----------------------------------------------------
    # Parse API response
    # -----------------------------------------------------

    try:

        result = response.json()

    except json.JSONDecodeError:

        print(
            "ERROR: llama-server returned invalid JSON."
        )

        print(response.text)

        sys.exit(1)

    # -----------------------------------------------------
    # Extract model message
    # -----------------------------------------------------

    try:

        model_text = (
            result
            ["choices"]
            [0]
            ["message"]
            ["content"]
        )

    except (
        KeyError,
        IndexError,
        TypeError
    ):

        print(
            "ERROR: Unexpected llama-server response:"
        )

        print(
            json.dumps(
                result,
                indent=2,
                ensure_ascii=False
            )
        )

        sys.exit(1)

    # -----------------------------------------------------
    # Print raw model response
    # -----------------------------------------------------

    print("")
    print(
        "======================================"
    )

    print(
        "RAW MODEL OUTPUT"
    )

    print(
        "======================================"
    )

    print(model_text)

    print(
        "======================================"
    )

    # -----------------------------------------------------
    # Save raw output
    # -----------------------------------------------------

    with open(
        RAW_OUTPUT,
        "w",
        encoding="utf-8"
    ) as f:

        f.write(model_text)

    # -----------------------------------------------------
    # Convert response to JSON
    # -----------------------------------------------------

    try:

        structured = extract_json(
            model_text
        )

    except ValueError as error:

        print("")
        print(
            "ERROR: Model output could not be parsed."
        )

        print(error)

        print("")
        print(
            f"Raw output saved to: {RAW_OUTPUT}"
        )

        sys.exit(1)

    # -----------------------------------------------------
    # Basic validation
    # -----------------------------------------------------

    if not isinstance(
        structured,
        dict
    ):

        print(
            "ERROR: Root JSON value is not an object."
        )

        sys.exit(1)

    if "questions" not in structured:

        print(
            "ERROR: JSON does not contain 'questions'."
        )

        sys.exit(1)

    if not isinstance(
        structured["questions"],
        list
    ):

        print(
            "ERROR: 'questions' must be a list."
        )

        sys.exit(1)

    # -----------------------------------------------------
    # Save formatted JSON
    # -----------------------------------------------------

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

    # -----------------------------------------------------
    # Success
    # -----------------------------------------------------

    print("")
    print(
        "======================================"
    )

    print(
        "SUCCESS!"
    )

    print(
        "======================================"
    )

    print(
        "Questions extracted:",
        len(structured["questions"])
    )

    print(
        "JSON saved to:",
        OUTPUT
    )

    print(
        "Raw output saved to:",
        RAW_OUTPUT
    )

    print(
        "======================================"
    )


if __name__ == "__main__":

    main()
