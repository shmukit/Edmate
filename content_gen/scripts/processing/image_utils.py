import base64
import os
from pathlib import Path

class ImageHandler:
    @staticmethod
    def to_base64_html(image_path: str) -> str:
        """
        Converts an image file to a base64 string and wraps it in the specified HTML format.
        
        Format:
        <div>
          &lt;p&gt;...&lt;/p&gt;<br/>
          <img src="data:image/png;base64,...base64string..." alt="Question Image" style="max-width:100%; height:auto;"/>
        </div>
        """
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Image not found at {image_path}")
            
        with open(image_path, "rb") as image_file:
            encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
            
        # Standard HTML wrapper for embedded images in the Edmate project
        html_snippet = (
            f'<div>\n'
            f'  <img src="data:image/png;base64,{encoded_string}" '
            f'alt="Question Image" style="max-width:100%; height:auto;"/>\n'
            f'</div>'
        )
        return html_snippet

    @staticmethod
    def embed_images_in_text(text: str, image_paths: list) -> str:
        """
        Embeds multiple images at the end of the text.
        Useful for 'title' or 'detailedExplanation' fields.
        """
        snippets = []
        for path in image_paths:
            try:
                snippets.append(ImageHandler.to_base64_html(path))
            except Exception as e:
                print(f"Warning: Failed to embed image {path}: {e}")
        
        return text + "\n<br/>\n" + "\n".join(snippets) if snippets else text
