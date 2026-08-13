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
   The "options" array MUST strictly contain ONLY these 5 choices.

2. STATEMENTS & MATCHMAKING COLUMNS: 
   If a question contains lists (e.g., I, II, III), Statements (e.g., A, B, C), or Matchmaking Tables (e.g., Column A and Column B), these are PART OF THE QUESTION. You MUST include them inside the main "question_hi" and "question_en" text strings. Use line breaks (\n) to format them cleanly. DO NOT put them in the "options" array.

3. NO FORCED TRANSLATION (SINGLE LANGUAGE QUESTIONS): 
   If a question is printed ONLY in English (e.g., English Grammar questions) or ONLY in Hindi (e.g., Hindi Grammar questions), DO NOT TRANSLATE IT. 
   - If it is English-only: Set "question_hi": "" and set the "hi" field in all options to "".
   - If it is Hindi-only: Set "question_en": "" and set the "en" field in all options to "".

4. IGNORE GHOST QUESTIONS: 
   Do not hallucinate or generate empty questions. If a page only contains a reading passage or a diagram with no numbered questions, return an empty array [].

Return ONLY valid JSON matching this exact structure:
{
  "questions": [
    {
      "number": 26,
      "question_hi": "कॉलम A को कॉलम B से सुमेलित करें:\nकॉलम A\na. mis\nb. de\nकॉलम B\n(i) tie\n(ii) content",
      "question_en": "Match the prefixes under Column A with the words under Column B:\nColumn A\na. mis\nb. de\nColumn B\n(i) tie\n(ii) content",
      "diagram_path": null,
      "options": [
        {"label": "1", "hi": "a-(iv), b-(iii)", "en": "a-(iv), b-(iii)", "image_path": null},
        {"label": "2", "hi": "a-(iii), b-(iv)", "en": "a-(iii), b-(iv)", "image_path": null},
        {"label": "3", "hi": "a-(i), b-(ii)", "en": "a-(i), b-(ii)", "image_path": null},
        {"label": "4", "hi": "a-(ii), b-(i)", "en": "a-(ii), b-(i)", "image_path": null},
        {"label": "5", "hi": "अनुत्तरित प्रश्न", "en": "Question not attempted", "image_path": null}
      ]
    }
  ]
}
"""

REFINEMENT_PROMPT = """
You are an expert bilingual editor for RPSC competitive exam question papers.
Review this small batch of questions and fix any OCR typos, garbled Hindi characters, or watermark corruptions. 
Use the English text as your ground-truth reference for scientific terms and spelling.
CRITICAL: Do NOT change question numbers, English text, option labels, or image paths. Return ONLY valid JSON matching the exact input array structure. Do NOT use Markdown or ```json fences.
"""

def refine_extracted_data(questions_array):
    print("Running instant local refinement on extracted questions...")
    payload = {
        "messages": [
            {"role": "system", "content": REFINEMENT_PROMPT},
            {"role": "user", "content": json.dumps(questions_array, ensure_ascii=False)}
        ],
        "temperature": 0.0,
        "max_tokens": 2000
    }
    
    try:
        response = requests.post(API_URL, json=payload, timeout=120)
        if response.status_code == 200:
            content = response.json()["choices"][0]["message"]["content"]
            content = content.replace("```json", "").replace("```", "").strip()
            
            start = content.find("[")
            end = content.rfind("]")
            if start != -1 and end != -1:
                content = content[start:end+1]
                
            parsed = json.loads(content)
            if isinstance(parsed, list):
                print("Refinement successful!")
                return parsed
    except Exception as e:
        print(f"Refinement failed, using raw data: {e}")
    
    return questions_array

def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 test_page.py <page_number>")
        sys.exit(1)
        
    page_num = sys.argv[1]
    image_path = f"pages/page_{page_num}.jpg"
    output_json_path = f"output/page_{page_num}.json"
    
    if not os.path.exists(image_path):
        print(f"Image {image_path} not found.")
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
                    {"type": "text", "text": "Extract the questions from this page into JSON."}
                ]
            }
        ],
        "temperature": 0.0,
        "max_tokens": 4000
    }

    try:
        response = requests.post(API_URL, json=payload, timeout=300)
        response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"]
        
        content = content.replace("```json", "").replace("```", "").strip()
        start = content.find("{")
        end = content.rfind("}")
        if start != -1 and end != -1:
            content = content[start:end+1]
            
        json_data = json.loads(content)
        
        # Run inline refinement on the extracted array
        if "questions" in json_data and len(json_data["questions"]) > 0:
            json_data["questions"] = refine_extracted_data(json_data["questions"])
            
        with open(output_json_path, 'w', encoding='utf-8') as f:
            json.dump(json_data, f, ensure_ascii=False, indent=4)
            
        print(f"Successfully saved to {output_json_path}")
        
    except Exception as e:
        print(f"Extraction failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
