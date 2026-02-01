#!/usr/bin/env python3
"""
Comprehensive PDF Content Extractor for Exam Questions
Extracts: Text, Images (vector diagrams), Equations, Tables
Outputs: Structured JSON + PNG images
"""
import fitz  # PyMuPDF
import pdfplumber
import json
import os
import re
from pathlib import Path
from PIL import Image

class PDFContentExtractor:
    def __init__(self, pdf_path, output_dir="content_gen/data/extracted"):
        self.pdf_path = pdf_path
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Create subdirectories
        self.images_dir = self.output_dir / "images"
        self.images_dir.mkdir(exist_ok=True)
        
        self.base_name = Path(pdf_path).stem
        
    def extract_all(self):
        """Main extraction pipeline"""
        print(f"📄 Processing: {self.pdf_path}")
        
        results = {
            "source": self.pdf_path,
            "base_name": self.base_name,
            "pages": [],
            "questions": []
        }
        
        doc = fitz.open(self.pdf_path)
        
        for page_num in range(len(doc)):
            page_data = self.extract_page(doc, page_num)
            results["pages"].append(page_data)
            
        doc.close()
        
        # Parse questions from text
        results["questions"] = self.parse_questions(results["pages"])
        
        # Save JSON
        json_path = self.output_dir / f"{self.base_name}_extracted.json"
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(results, indent=2, fp=f)
        
        print(f"✅ Extraction complete!")
        print(f"   JSON: {json_path}")
        print(f"   Images: {self.images_dir}")
        print(f"   Total Questions: {len(results['questions'])}")
        
        return results
    
    def extract_page(self, doc, page_num):
        """Extract all content from a single page"""
        page = doc[page_num]
        
        page_data = {
            "page_number": page_num + 1,
            "text": "",
            "images": [],
            "has_diagrams": False
        }
        
        # Extract text
        page_data["text"] = page.get_text()
        
        # Check for vector graphics (diagrams drawn with paths)
        drawings = page.get_drawings()
        if drawings and len(drawings) > 5:  # Threshold: more than 5 paths = likely a diagram
            page_data["has_diagrams"] = True
            image_path = self.extract_page_as_image(page, page_num)
            if image_path:
                page_data["images"].append({
                    "type": "vector_diagram",
                    "path": str(image_path),
                    "page": page_num + 1
                })
        
        # Extract embedded images (if any)
        image_list = page.get_images()
        for img_index, img in enumerate(image_list):
            xref = img[0]
            image_path = self.extract_embedded_image(doc, xref, page_num, img_index)
            if image_path:
                page_data["images"].append({
                    "type": "embedded",
                    "path": str(image_path),
                    "page": page_num + 1
                })
        
        return page_data
    
    def extract_page_as_image(self, page, page_num):
        """Render entire page as high-res PNG (for vector diagrams)"""
        try:
            # Render at 2x resolution for crisp diagrams
            mat = fitz.Matrix(2, 2)
            pix = page.get_pixmap(matrix=mat, alpha=False)
            
            image_path = self.images_dir / f"{self.base_name}_page_{page_num + 1:03d}.png"
            pix.save(str(image_path))
            
            return image_path
        except Exception as e:
            print(f"⚠️  Error rendering page {page_num + 1}: {e}")
            return None
    
    def extract_embedded_image(self, doc, xref, page_num, img_index):
        """Extract embedded raster images"""
        try:
            base_image = doc.extract_image(xref)
            image_bytes = base_image["image"]
            image_ext = base_image["ext"]
            
            image_path = self.images_dir / f"{self.base_name}_p{page_num + 1}_img{img_index}.{image_ext}"
            
            with open(image_path, "wb") as img_file:
                img_file.write(image_bytes)
            
            # Convert to PNG if not already
            if image_ext != "png":
                img = Image.open(image_path)
                png_path = image_path.with_suffix(".png")
                img.save(png_path)
                image_path.unlink()  # Delete original
                return png_path
            
            return image_path
        except Exception as e:
            print(f"⚠️  Error extracting image {img_index} from page {page_num + 1}: {e}")
            return None
    
    def parse_questions(self, pages):
        """Parse individual questions from extracted text"""
        questions = []
        full_text = "\n".join([p["text"] for p in pages])
        
        # Simple regex to find question numbers (1, 2, 3... or 1., 2., 3...)
        # This is a heuristic - adjust based on actual PDF format
        question_pattern = r'\n(\d+)\s+'
        matches = list(re.finditer(question_pattern, full_text))
        
        for i, match in enumerate(matches):
            q_num = match.group(1)
            start = match.start()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(full_text)
            
            question_text = full_text[start:end].strip()
            
            # Find which page(s) this question appears on
            question_pages = []
            char_count = 0
            for page in pages:
                page_len = len(page["text"])
                if char_count <= start < char_count + page_len:
                    question_pages.append(page["page_number"])
                char_count += page_len
            
            questions.append({
                "question_number": int(q_num),
                "text": question_text[:500],  # Preview
                "pages": question_pages,
                "full_text": question_text
            })
        
        return questions


def main():
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python extract_pdf_content.py <pdf_path> [output_dir]")
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else "content_gen/data/extracted"
    
    extractor = PDFContentExtractor(pdf_path, output_dir)
    extractor.extract_all()


if __name__ == "__main__":
    main()
