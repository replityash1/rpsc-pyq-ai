import json
import requests
import sys

API_URL = "http://127.0.0.1:8080/v1/chat/completions"

REFINEMENT_PROMPT = """
You are an expert bilingual editor for RPSC competitive exam question papers.
I will give you a JSON array containing a batch of questions in Hindi and English. 

Your task is to review the questions and options to ensure they strictly follow these quality rules:
1. Check if the Hindi text matches the English text accurately in meaning and structure.
2. Fix any OCR typos, garbled characters, or watermark corruptions (such as stray digits from vertical watermarks like "366373") in the Hindi text ("question_hi" and option "hi" fields).
3. USE THE ENGLISH TEXT ("question_en" and option "en" fields) AS YOUR GROUND TRUTH REFERENCE for proper names, historical terms, scientific spelling, and technical concepts.
4. Do NOT change question numbers, English text, option labels, or image paths.
5. Return ONLY valid JSON matching the exact input structure (an array of question objects). Do NOT use Markdown or ```json fences.
"""

def refine_batch(questions_batch):
    payload = {
        "messages": [
            {"role": "system", "content": REFINEMENT_PROMPT},
            {"role": "user", "content": json.dumps(questions_batch, ensure_ascii=False)}
        ],
        "temperature": 0.0,
        "max_tokens": 4000
    }
    
    try:
        response = requests.post(API_URL, json=payload, timeout=300)
        if response.status_code == 200:
            res_json = response.json()
            content = res_json["choices"][0]["message"]["content"]
            # Clean markdown fences if model adds them
            content = content.replace("```json", "").replace("```", "").strip()
            
            # Isolate JSON array bounds
            start = content.find("[")
            end = content.rfind("]")
            if start != -1 and end != -1:
                content = content[start:end+1]
                
            return json.loads(content)
    except Exception as e:
        print(f"Refinement batch failed: {e}")
    
    # Fallback: return original batch if AI step encounters an error
    return questions_batch

def main():
    print("======================================")
    print("STARTING POST-MERGE HINDI REFINEMENT")
    print("======================================")
    
    try:
        with open("question_bank.json", "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        print(f"ERROR: Could not load question_bank.json: {e}")
        sys.exit(1)
        
    questions = data.get("questions", [])
    batch_size = 15  # Chunk size optimized for local 8K context limits
    refined_questions = []
    
    for i in range(0, len(questions), batch_size):
        batch = questions[i:i + batch_size]
        print(f"Refining questions {i+1} to {min(i+batch_size, len(questions))}...")
        
        refined_batch_data = refine_batch(batch)
        refined_questions.extend(refined_batch_data)
        
    data["questions"] = refined_questions
    
    with open("question_bank.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
        
    print("SUCCESS: Question bank fully refined and polished!")

if __name__ == "__main__":
    main()
