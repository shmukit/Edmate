import cv2
import sys
import os
import numpy as np

def crop_diagram(image_path, output_path):
    print(f"Processing {image_path}...")
    img = cv2.imread(image_path)
    if img is None:
        print(f"Error: Could not load image from {image_path}")
        return

    # Convert to grayscale
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    # Threshold to get black content on white background
    # OTSU is good for bimodal diagrams (scan vs background)
    _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    
    # Dilate to connect broken lines (like text or dashed graph lines) into a single blob
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (10, 10))
    dilated = cv2.dilate(thresh, kernel, iterations=2)
    
    # Find contours on the dilated image
    contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    if not contours:
        print("No contours found.")
        return

    # Find the largest reasonable bounding box
    img_h, img_w = img.shape[:2]
    img_area = img_w * img_h
    
    best_candidate = None
    max_area = 0

    for c in contours:
        x, y, w, h = cv2.boundingRect(c)
        area = w * h
        aspect_ratio = w / float(h)
        
        # Heuristics:
        # 1. Area > 5% of page (too small = text line)
        # 2. Area < 90% of page (too big = page border)
        # 3. Aspect ratio between 0.2 and 5 (avoid extremely thin lines)
        if 0.05 * img_area < area < 0.95 * img_area and 0.2 < aspect_ratio < 5:
            if area > max_area:
                max_area = area
                best_candidate = (x, y, w, h)
                
    if best_candidate:
        x, y, w, h = best_candidate
        # Add padding
        pad = 20
        x = max(0, x - pad)
        y = max(0, y - pad)
        w = min(img_w - x, w + 2*pad)
        h = min(img_h - y, h + 2*pad)
        
        crop = img[y:y+h, x:x+w]
        cv2.imwrite(output_path, crop)
        print(f"Success! Diagram extracted to {output_path}")
    else:
        print("No suitable diagram region found.")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python extract_diagram.py <input_image> <output_image>")
        sys.exit(1)
    
    crop_diagram(sys.argv[1], sys.argv[2])
