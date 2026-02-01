#!/usr/bin/env python3
"""
Quick PDF analyzer to understand structure and extract sample content
"""
import fitz  # PyMuPDF
import sys
import json

def analyze_pdf(pdf_path):
    doc = fitz.open(pdf_path)
    
    analysis = {
        "total_pages": len(doc),
        "images": [],
        "text_sample": [],
        "has_tables": False
    }
    
    # Analyze first 3 pages
    for page_num in range(min(3, len(doc))):
        page = doc[page_num]
        
        # Extract images
        images = page.get_images()
        if images:
            analysis["images"].append({
                "page": page_num + 1,
                "count": len(images),
                "details": [{"xref": img[0], "width": img[2], "height": img[3]} for img in images[:3]]
            })
        
        # Extract text sample
        text = page.get_text()
        if text.strip():
            analysis["text_sample"].append({
                "page": page_num + 1,
                "preview": text[:500]
            })
    
    doc.close()
    return analysis

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python analyze_pdf.py <pdf_path>")
        sys.exit(1)
    
    result = analyze_pdf(sys.argv[1])
    print(json.dumps(result, indent=2))
