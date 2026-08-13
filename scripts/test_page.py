import sys
import os
import json
import requests
import base64

API_URL = "http://127.0.0.1:8080/v1/chat/completions"

SYSTEM_PROMPT = """
You are an expert data extraction AI for RPSC competitive exam question papers.
Your task is to extract all questions, options, and diagram paths from the provided image into a strict JSON array.

CRITICAL EXTRACTION RULES:

1. THE "5 OPTIONS" RULE (MANDATORY): 
   EVERY single question has exactly 5 answer options labelled (1), (2), (3), (4), and (5). 
   The 5th option is ALWAYS "Question not attempted" / "अनुत्तरित प्रश्न". 
   The "options" array MUST strictly contain ONLY these 5 choices. Do not put statements or premises in the options.

2. STATEMENTS & MATCHMAKING COLUMNS: 
   If a question contains lists (e.g., I, II, III), Statements (e.g., A, B, C), or Matchmaking Tables, these are PART OF THE QUESTION. You MUST include them inside the main "question_hi" and "question_en" text strings. Use line breaks (\n) to format them.

3. MATH FORMATTING (CRITICAL):
   You MUST enclose ALL mathematical expressions, variables, formulas, physics values, and fractions in inline LaTeX dollar signs. 
   Example: Write $\frac{w_1 + w_2}{2}$ instead of \frac{w_1 + w_2}{2}. Write $x^2$ instead of x^2.

4. NO FORCED TRANSLATION: 
   If a question is printed ONLY in English or ONLY in Hindi, DO NOT TRANSLATE IT. Set the missing language field to "".

5. IGNORE GHOST QUESTIONS: 
   Do not hallucinate questions. If a page only contains a reading passage or diagram, return an empty array [].

Return ONLY valid JSON matching this exact structure:
{
  "questions": [
    {
      "number": 1,
      "question_hi": "हिंदी प्रश्न...",
      "question_en": "English question...",
      "diagram_path": null,
      "options": [
        {"label": "1", "hi": "विकल्प 1", "en": "Option 1", "image_path": null},
        {"label": "5", "hi": "अनुत्तरित प्रश्न", "en": "Question not attempted", "image_path": null}
      ]
    }
  ]
}
"""

REFINEMENT_PROMPT = """
You are an expert bilingual editor for RPSC exam papers.
Review this batch. Fix OCR typos, garbled Hindi characters, or watermark corruptions. 
Use the English text as your ground-truth reference for scientific terms.
CRITICAL: Ensure ALL math/science formulas remain wrapped in $ symbols. Do NOT change question numbers, option labels, or image paths. Return ONLY valid JSON.
"""

def clean_json_response(content):
    content = content.replace("```json", "").replace("```", "").strip()
    start = content.find("{")
    end = content.rfind("}")
    if start != -1 and end != -1:
        return content[start:end+1]
    return content

def refine_extracted_data(questions_array):
    print("Running inline refinement...")
    payload = {
        "messages": [
            {"role": "system", "content": REFINEMENT_PROMPT},
            {"role": "user", "content": json.dumps({"questions": questions_array}, ensure_ascii=False)}
        ],
        "temperature": 0.0,
        "max_tokens": 2500
    }
    try:
        response = requests.post(API_URL, json=payload, timeout=300)
        if response.status_code == 200:
            content = clean_json_response(response.json()["choices"][0]["message"]["content"])
            parsed = json.loads(content)
            if "questions" in parsed:
                return parsed["questions"]
    except Exception as e:
        print(f"Refinement failed, bypassing: {e}")
    return questions_array

def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

def main():
    if len(sys.argv) < 2:
        sys.exit(1)
        
    page_num = sys.argv[1]
    image_path = f"pages/page_{page_num}.jpg"
    output_json_path = f"output/page_{page_num}.json"
    
    if not os.path.exists(image_path):
        sys.exit(1)

    print(f"Processing page {page_num}...")
    base64_image = encode_image(image_path)
    
    payload = {
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}},
                    {"type": "text", "text": "Extract questions from this page into JSON. Ensure math uses $."}
                ]
            }
        ],
        "temperature": 0.0,
        "max_tokens": 4000
    }

    try:
        response = requests.post(API_URL, json=payload, timeout=900)
        response.raise_for_status()
        content = clean_json_response(response.json()["choices"][0]["message"]["content"])
        json_data = json.loads(content)
        
        if "questions" in json_data and len(json_data["questions"]) > 0:
            json_data["questions"] = refine_extracted_data(json_data["questions"])
            
        with open(output_json_path, 'w', encoding='utf-8') as f:
            json.dump(json_data, f, ensure_ascii=False, indent=4)
            
        print(f"Success: {output_json_path}")
    except Exception as e:
        print(f"Extraction failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
