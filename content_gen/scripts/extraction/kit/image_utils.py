"""Image crop helpers for PDF-Extract-Kit wrapper."""
from __future__ import annotations

from pathlib import Path
from typing import List, Optional

import fitz


class KitImageUtilsMixin:
    images_dir: Optional[Path]
    def _extract_bbox_image(
        self,
        page: fitz.Page,
        bbox: List[float],
        q_num: int,
        element_type: str,
    ) -> Path:
        """
        Extract and save image from bounding box

        Args:
            page: PyMuPDF page object
            bbox: Bounding box [x0, y0, x1, y1]
            q_num: Question number
            element_type: Type of element (figure, table, formula)

        Returns:
            Path to saved image
        """
        width = max(1.0, bbox[2] - bbox[0])
        height = max(1.0, bbox[3] - bbox[1])
        pad = max(12.0, min(width, height) * 0.08)

        final_bbox = [
            max(0, bbox[0] - pad),
            max(0, bbox[1] - pad),
            min(page.rect.width, bbox[2] + pad),
            min(page.rect.height, bbox[3] + pad),
        ]

        images_dir = self.images_dir
        if images_dir is None:
            raise ValueError("images_dir must be initialized before extracting images")
        img_name = f"q{q_num}_{element_type}.png"
        img_path = images_dir / img_name

        pix = page.get_pixmap(matrix=fitz.Matrix(3, 3), clip=fitz.Rect(final_bbox))
        pix.save(str(img_path))

        return img_path
