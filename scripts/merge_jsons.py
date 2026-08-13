import os
import json
import glob

def main():
    print("======================================")
    print("MERGING JSON ARTIFACTS")
    print("======================================")

    all_questions = []

    # The GitHub action downloads artifacts into 'downloaded_jsons'
    # It creates subfolders for each artifact name, so we search recursively
    search_path = os.path.join("downloaded_outputs", "**", "*.json")
    json_files = glob.glob(search_path, recursive=True)

    if not json_files:
        print("WARNING: No JSON files found to merge.")
    else:
        # Sort files to ensure pages remain in numerical order
        # e.g., page_1.json, page_2.json instead of page_10 coming before page_2
        json_files.sort(key=lambda x: int(''.join(filter(str.isdigit, os.path.basename(x) or "0"))))

        for file_path in json_files:
            print(f"Merging: {file_path}")
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # Extract the questions array and append them
                    questions = data.get("questions", [])
                    all_questions.extend(questions)
            except Exception as e:
                print(f"Error reading {file_path}: {e}")

    # Create the final structure
    final_output = {
        "questions": all_questions
    }

    # Save to the root directory where the Action expects it
    output_filename = "question_bank.json"
    with open(output_filename, 'w', encoding='utf-8') as out_file:
        json.dump(final_output, out_file, ensure_ascii=False, indent=4)

    print(f"\nSUCCESS: Combined {len(all_questions)} total questions into {output_filename}")

if __name__ == "__main__":
    main()
