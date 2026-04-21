import zipfile
import re
import sys
import os


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
            return text
    except Exception as e:
        return f"Error reading {docx_path}: {e}"


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python extract_text.py <docx_file>")
        sys.exit(1)

    path = sys.argv[1]
    print(extract_text(path))
