import os
import glob
import re
import zipfile

INPUT_DIR = 'content_gen/data/inputs'
OUTPUT_DIR = 'content_gen/data/outputs'


def extract_text(docx_path):
    try:
        with zipfile.ZipFile(docx_path) as z:
            xml_content = z.read('word/document.xml').decode('utf-8')
            # Replace paragraph ends with newlines
            xml_content = re.sub(r'</w:p>', '\n', xml_content)
            # Remove all tags
            text = re.sub(r'<[^>]+>', '', xml_content)
            # Fix excessive spacing but keep newlines
            text = re.sub(r'[ \t]+', ' ', text)
            text = re.sub(r'\n\s+', '\n', text)
            text = re.sub(r'\n+', '\n\n', text).strip()

            # Formatting Logic (Safety Check)
            # Remove LaTeX delimiters if present (e.g. $E_a$ -> E_a) - simplistic
            text = text.replace('$', '')

            return text
    except Exception as e:
        return f"Error reading {docx_path}: {e}"


def main():
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)

    files = glob.glob(os.path.join(INPUT_DIR, '*.docx'))
    print(f"Found {len(files)} DOCX files.")

    for file_path in files:
        filename = os.path.basename(file_path)
        name_only = os.path.splitext(filename)[0]
        output_path = os.path.join(OUTPUT_DIR, f"{name_only}_processed.txt")

        print(f"Processing {filename}...")
        text = extract_text(file_path)

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(text)

    print("Batch processing complete.")


if __name__ == "__main__":
    main()
