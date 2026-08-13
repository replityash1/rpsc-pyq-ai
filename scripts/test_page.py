import base64
import json
import re
import sys
import os
import requests
from PIL import Image

# ---------------------------------------------------------
# Dynamic Configuration (Reads page number from GitHub Matrix)
# ---------------------------------------------------------
if len(sys.argv) < 2:
    print("ERROR: Page number not provided.")
    sys.exit(1)

PAGE_NUM = sys.argv[1]
IMAGE = f"pages/page_{PAGE_NUM}.jpg"
OUTPUT = f"output/page_{PAGE_NUM}.json"
RAW_OUTPUT = f"output/page_{PAGE_NUM}_raw.txt"

API_URL = "http://127.0.0.1:8080/v1/chat/completions"

# ---------------------------------------------------------
# Prompt
# ---------------------------------------------------------
PROMPT = r"""
You are an expert document-extraction system.

You are analyzing ONE PAGE from a scanned RPSC/Rajasthan competitive examination question paper.
Your job is ONLY to accurately extract the questions visible on this page.

IMPORTANT RULES:

1. Hindi and English versions of the same question are ONE question. Do NOT create two separate questions.
2. Preserve the original question number.
3. Extract the Hindi question text carefully.
4. Extract the English question text carefully.
5. Extract EVERY answer option visible.
6. NUMBERED OPTIONS: The options in this paper are numbered (1, 2, 3, 4, 5). Preserve these exact numeric labels. Do NOT change them to A, B, C, D.
7. FIVE OPTIONS: Note that there are 5 options per question (Option 5 is usually "Question not attempted"). Include all 5.
8. BEWARE OF WATERMARKS: There is a faint vertical number watermark (e.g., "366373") running through the text. Ignore these numbers. Do not let them corrupt the words.
9. CROSS-CHECK SPELLING: Use the clear English names to verify the Hindi spelling (e.g., if English says "Karauli", ensure the Hindi says "करौली", not a corrupted word).
10. HANDLING MULTI-STATEMENT/CODE QUESTIONS: If a question has statements (e.g., a, b, c) followed by a "Codes" section (e.g., 1, 2, 3, 4), include ALL the statements inside the main "question_hi" and "question_en" text. ONLY put the final numeric code choices inside the "options" array. Do not mix them.
11. VISUALS & DIAGRAMS (CRITICAL): If the question body OR any of the options contain images, complex diagrams, charts, or heavy structural chemical formulas, do NOT try to describe them with text. Instead, provide the [x_min, y_min, x_max, y_max] pixel coordinates of the bounding box around the image.
12. Preserve mathematical expressions in standard LaTeX wrapped in $ delimiters as accurately as possible (e.g., $\text{BF}_3$, $x^2$).
13. Return ONLY valid JSON. Do not put the JSON inside ```json fences.

Return exactly this structure:

{
  "questions": [
    {
      "number": 1,
      "question_hi": "...",
      "question_en": "...",
      "diagram_box": null, 
      "diagram_path": null,
      "options": [
        {
          "label": "1",
          "hi": "...",
          "en": "...",
          "image_box": null,
          "image_path": null
        },
        {
          "label": "2",
          "hi": "...",
          "en": "...",
          "image_box": null,
          "image_path": null
        },
        {
          "label": "3",
          "hi": "...",
          "en": "...",
          "image_box": null,
          "image_path": null
        },
        {
          "label": "4",
          "hi": "...",
          "en": "...",
          "image_box": null,
          "image_path": null
        },
        {
          "label": "5",
          "hi": "...",
          "en": "...",
          "image_box": null,
          "image_path": null
        }
      ]
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
    text = re.sub(r"^```json\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"^```\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    text = text.strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        candidate = text[start:end + 1]
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            pass

    raise ValueError("The model did not return valid JSON.\n\nMODEL RESPONSE:\n" + text)


# ---------------------------------------------------------
# Crop Diagrams using coordinates
# ---------------------------------------------------------
def crop_diagrams(structured_json, original_image_path, page_num):
    try:
        img = Image.open(original_image_path)
    except Exception as e:
        print(f"Warning: Could not open image for cropping: {e}")
        return structured_json

    os.makedirs("output/images", exist_ok=True)

    for q in structured_json.get("questions", []):
        q_num = q.get("number", "unknown")
        
        # 1. Crop the main question diagram (if it exists)
        if q.get("diagram_box") and isinstance(q["diagram_box"], list) and len(q["diagram_box"]) == 4:
            box = q["diagram_box"] 
            try:
                cropped_img = img.crop((box[0], box[1], box[2], box[3]))
                save_path = f"output/images/page{page_num}_q{q_num}_diagram.jpg"
                cropped_img.save(save_path)
                q["diagram_path"] = save_path 
            except Exception as e:
                print(f"Failed to crop diagram for Q{q_num}: {e}")

        # 2. Crop the option diagrams (if they exist)
        for opt in q.get("options", []):
            if opt.get("image_box") and isinstance(opt["image_box"], list) and len(opt["image_box"]) == 4:
                box = opt["image_box"]
                opt_label = opt.get("label", "X")
                try:
                    cropped_img = img.crop((box[0], box[1], box[2], box[3]))
                    save_path = f"output/images/page{page_num}_q{q_num}_opt{opt_label}.jpg"
                    cropped_img.save(save_path)
                    opt["image_path"] = save_path
                except Exception as e:
                    print(f"Failed to crop option {opt_label} for Q{q_num}: {e}")
                    
    return structured_json


# ---------------------------------------------------------
# Main
# ---------------------------------------------------------
def main():
    print("======================================")
    print(f"RPSC PYQ AI TEST - PAGE {PAGE_NUM}")
    print("======================================")

    try:
        image_b64 = image_to_base64(IMAGE)
    except FileNotFoundError:
        print(f"ERROR: Could not find {IMAGE}")
        sys.exit(1)

    payload = {
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": PROMPT},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_b64}"}}
                ]
            }
        ],
        "temperature": 0.0,
        "max_tokens": 6000,
        "frequency_penalty": 1.2  # This strictly prevents infinite loops
    }

    print("Sending page to Qwen3-VL...")
    
    try:
        response = requests.post(API_URL, json=payload, timeout=1800)
    except requests.RequestException as error:
        print("ERROR communicating with llama-server:", error)
        sys.exit(1)

    if response.status_code != 200:
        print("SERVER RESPONSE ERROR:\n", response.text)
        sys.exit(1)

    try:
        result = response.json()
    except json.JSONDecodeError:
        print("ERROR: llama-server returned invalid JSON.\n", response.text)
        sys.exit(1)

    try:
        model_text = result["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError):
        print("ERROR: Unexpected llama-server response.")
        sys.exit(1)

    with open(RAW_OUTPUT, "w", encoding="utf-8") as f:
        f.write(model_text)

    try:
        structured = extract_json(model_text)
    except ValueError as error:
        print("ERROR: Model output could not be parsed.\n", error)
        sys.exit(1)

    if not isinstance(structured, dict) or "questions" not in structured:
        print("ERROR: Invalid JSON structure.")
        sys.exit(1)

    # -----------------------------------------------------
    # Crop Diagrams and inject file paths into JSON
    # -----------------------------------------------------
    structured = crop_diagrams(structured, IMAGE, PAGE_NUM)

    with open(OUTPUT, "w", encoding="utf-8") as f:
        json.dump(structured, f, ensure_ascii=False, indent=2)

    print(f"SUCCESS! Extracted {len(structured['questions'])} questions for page {PAGE_NUM}.")

if __name__ == "__main__":
    main()
