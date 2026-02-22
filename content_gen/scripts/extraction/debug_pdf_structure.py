import fitz
import json
import sys

def debug_pdf(pdf_path, page_num):
    doc = fitz.open(pdf_path)
    page = doc[page_num - 1]
    
    # Get text dict
    text_dict = page.get_text("dict")
    
    # Print blocks and spans with coordinates
    print(f"--- Debugging Page {page_num} ---")
    for b_idx, block in enumerate(text_dict["blocks"][:20]):
        if "lines" in block:
            print(f"Block {b_idx}:")
            for l_idx, line in enumerate(block["lines"]):
                line_text = ""
                for s_idx, span in enumerate(line["spans"]):
                    line_text += span["text"]
                    print(f"  Span {s_idx}: '{span['text']}' @ bbox {span['bbox']}, size {span['size']}, font '{span['font']}'")
                print(f" Line {l_idx}: '{line_text}' @ bbox {line['bbox']}")

if __name__ == "__main__":
    debug_pdf(sys.argv[1], int(sys.argv[2]))
