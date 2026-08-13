import os
import json
import glob

def main():
    print("======================================")
    print("MERGING AND CLEANING JSON ARTIFACTS")
    print("======================================")

    all_questions = []
    search_path = os.path.join("downloaded_outputs", "**", "*.json")
    json_files = glob.glob(search_path, recursive=True)

    if not json_files:
        print("WARNING: No JSON files found to merge.")
    else:
        # Sort files numerically by page number to maintain logical order
        json_files.sort(key=lambda x: int(''.join(filter(str.isdigit, os.path.basename(x) or "0"))))
        seen_questions = set()

        for file_path in json_files:
            print(f"Reading: {file_path}")
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    questions = data.get("questions", [])
                    
                    for q in questions:
                        q_hi = (q.get("question_hi") or "").strip()
                        q_en = (q.get("question_en") or "").strip()
                        q_text = q_hi + q_en
                        
                        # Kill Ghost questions (less than 5 characters total) and Duplicates
                        if len(q_text) < 5 or q_text in seen_questions:
                            continue 
                        
                        seen_questions.add(q_text)
                        all_questions.append(q)
            except Exception as e:
                print(f"Error reading {file_path}: {e}")

    # Re-number every valid question sequentially from 1 to N
    for new_idx, q in enumerate(all_questions, start=1):
        q["number"] = new_idx

    final_output = {"questions": all_questions}
    output_filename = "question_bank.json"
    
    with open(output_filename, 'w', encoding='utf-8') as out_file:
        json.dump(final_output, out_file, ensure_ascii=False, indent=4)

    print(f"\nSUCCESS: Cleaned and combined {len(all_questions)} unique questions into {output_filename}")

if __name__ == "__main__":
    main()
