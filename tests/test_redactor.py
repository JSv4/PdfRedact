import os
import io
import logging
import unittest
from pathlib import Path
import json
from typing import List
import sys

# Verify redactions in the text layer
from PyPDF2 import PdfReader

import pytesseract

from src.pdfredact import (
    build_text_redacted_pdf,
    redact_pdf_to_images,
)
from plasmapdf.models.types import (
    PawlsPagePythonType,
    OpenContractsSinglePageAnnotationType
)

logger = logging.getLogger(__name__)

# # Configure Tesseract path for Windows
if os.name == 'nt':
    if 'TESSERACT_PATH' in os.environ:  # Windows
        pytesseract.pytesseract.tesseract_cmd = os.environ['TESSERACT_PATH']
    else:
        pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

# Check env for Poppler path, otherwise use None which will try to use system path
POPPLER_PATH = os.getenv("POPPLER_PATH", None)

class TestImageRedaction(unittest.TestCase):
    """
    Test suite for image redaction functionality, separated into:
    1) A pipeline step that converts PDF to images and redacts them.
    2) (Optionally) building a new PDF with a text layer from those images.
    """

    @classmethod
    def setUpClass(cls) -> None:
        """
        Load test data and PDF once for all tests in this suite.
        """
        # Load PAWLS data
        fixtures_dir = Path(__file__).parent / "fixtures"
        with open(fixtures_dir / "pawls.json", "r") as f:
            cls.pawls_data: List[PawlsPagePythonType] = json.load(f)

        # Load PDF
        with open(fixtures_dir / "doc.pdf", "rb") as f:
            cls.pdf_bytes = f.read()

    def test_redact_specific_date(self) -> None:
        """
        Test the redaction of multiple token sequences from the PDF images.
        Each sequence is a tuple of strings that should appear consecutively in the text.
        """
        redacts = [
            ("Exhibit", "10.1"),
            ("Aucta", "Pharmaceuticals"),
            ("Eton", "Pharmaceuticals"),
            ("Eton",),
            ("Aucta",)
        ]
        
        # Find all matching token sequences
        all_target_tokens = []
        first_page_tokens = self.pawls_data[0]["tokens"]
        
        for redact_tuple in redacts:
            i = 0
            while i < len(first_page_tokens):
                if redact_tuple[0].lower() in first_page_tokens[i]["text"].lower():
                    # Potential match found, check subsequent tokens
                    match_found = True
                    for j, expected_text in enumerate(redact_tuple[1:], 1):
                        if (i + j >= len(first_page_tokens) or 
                            expected_text.lower() not in first_page_tokens[i + j]["text"].lower()):
                            match_found = False
                            break
                    
                    if match_found:
                        # Add all token indices that form this match
                        matched_indices = list(range(i, i + len(redact_tuple)))
                        all_target_tokens.append({
                            "indices": matched_indices,
                            "bounds": {
                                "left": min(first_page_tokens[idx]["x"] for idx in matched_indices),
                                "right": max(first_page_tokens[idx]["x"] + first_page_tokens[idx]["width"] 
                                           for idx in matched_indices),
                                "top": min(first_page_tokens[idx]["y"] for idx in matched_indices),
                                "bottom": max(first_page_tokens[idx]["y"] + first_page_tokens[idx]["height"] 
                                            for idx in matched_indices)
                            },
                            "text": " ".join(redact_tuple)
                        })
                i += 1

        self.assertTrue(
            all_target_tokens, 
            "Could not find any of the specified token sequences for redaction."
        )
        
        # Create annotations for each matched sequence
        test_annotations: List[OpenContractsSinglePageAnnotationType] = [
            {
                "bounds": match["bounds"],
                "tokensJsons": [
                    {"pageIndex": 0, "tokenIndex": idx}
                    for idx in match["indices"]
                ],
                "rawText": match["text"],
            }
            for match in all_target_tokens
        ]

        # We'll wrap our single page annotation list in another list
        # because these are "page_annotations," one list per page
        page_annotations = [test_annotations] + [[] for _ in self.pawls_data[1:]]

        # Use the newly introduced pipeline function to redact images
        redacted_image_list = redact_pdf_to_images(
            pdf_bytes=self.pdf_bytes,
            pawls_pages=self.pawls_data,
            page_annotations=page_annotations,
            dpi=200,
            poppler_path=POPPLER_PATH if os.name == 'nt' else None,
            use_pdftocairo=False
        )

        # Confirm we have as many images as pages
        self.assertEqual(
            len(redacted_image_list),
            len(self.pawls_data),
            "Number of redacted images does not match the number of PDF pages."
        )

        # Now we OCR the first page's image to ensure "Exhibit 10.1" is gone
        redacted_first_page = redacted_image_list[0]
        redacted_first_page.save("debug_redacted.png")
        custom_config = r"--oem 3 --psm 3"
        ocr_data = pytesseract.image_to_data(
            redacted_first_page,
            output_type=pytesseract.Output.DICT,
            config=custom_config
        )
        all_ocr_text = []
        for i in range(len(ocr_data["text"])):
            conf = int(ocr_data["conf"][i])
            text_val = ocr_data["text"][i]
            if conf > 0 and text_val.strip():
                all_ocr_text.append(text_val.upper())

        combined_text = " ".join(all_ocr_text)
        for redact_tuple in redacts:
            redact_text = " ".join(redact_tuple).upper()
            self.assertNotIn(
                redact_text,
                combined_text,
                f"Redacted text '{redact_text}' was still detected in the image layer."
            )

        logger.info("Successfully tested image redaction pipeline step - all sequences redacted.")

    def test_text_redacted_pdf(self) -> None:
        """
        Test the 'build_text_redacted_pdf' function by verifying that
        the text layer is correctly redacted in the output PDF.
        """
        redacts = [
            ("Exhibit", "10.1"),
            ("Aucta", "Pharmaceuticals"),
            ("Eton", "Pharmaceuticals"),
            ("Eton",),
            ("Aucta",)
        ]
        
        # Find all matching token sequences
        all_target_tokens = []
        first_page_tokens = self.pawls_data[0]["tokens"]
        
        for redact_tuple in redacts:
            i = 0
            while i < len(first_page_tokens):
                if redact_tuple[0].lower() in first_page_tokens[i]["text"].lower():
                    # Potential match found, check subsequent tokens
                    match_found = True
                    for j, expected_text in enumerate(redact_tuple[1:], 1):
                        if (i + j >= len(first_page_tokens) or 
                            expected_text.lower() not in first_page_tokens[i + j]["text"].lower()):
                            match_found = False
                            break
                    
                    if match_found:
                        # Add all token indices that form this match
                        matched_indices = list(range(i, i + len(redact_tuple)))
                        all_target_tokens.append({
                            "indices": matched_indices,
                            "bounds": {
                                "left": min(first_page_tokens[idx]["x"] for idx in matched_indices),
                                "right": max(first_page_tokens[idx]["x"] + first_page_tokens[idx]["width"] 
                                           for idx in matched_indices),
                                "top": min(first_page_tokens[idx]["y"] for idx in matched_indices),
                                "bottom": max(first_page_tokens[idx]["y"] + first_page_tokens[idx]["height"] 
                                            for idx in matched_indices)
                            },
                            "text": " ".join(redact_tuple)
                        })
                i += 1

        self.assertTrue(
            all_target_tokens, 
            "Could not find any of the specified token sequences for redaction."
        )

        # Create annotations for each matched sequence
        test_annotations: List[OpenContractsSinglePageAnnotationType] = [
            {
                "bounds": match["bounds"],
                "tokensJsons": [
                    {"pageIndex": 0, "tokenIndex": idx}
                    for idx in match["indices"]
                ],
                "rawText": match["text"],
            }
            for match in all_target_tokens
        ]

        # We'll wrap our single page annotation list in another list
        # because these are "page_annotations," one list per page
        page_annotations = [test_annotations] + [[] for _ in self.pawls_data[1:]]
        
        # Use the newly introduced pipeline function to redact images
        redacted_image_list = redact_pdf_to_images(
            pdf_bytes=self.pdf_bytes,
            pawls_pages=self.pawls_data,
            page_annotations=page_annotations,
            dpi=300,
            poppler_path=POPPLER_PATH if os.name == 'nt' else None,
            use_pdftocairo=False
        )
        
        # We'll redact the first page of the PDF
        build_text_redacted_pdf(
            output_pdf="debug_redacted.pdf",
            redacted_images=redacted_image_list,
            pawls_pages=self.pawls_data,
            page_redactions=page_annotations,
            dpi=300,
            hide_text=True
        )
        
        reader = PdfReader("debug_redacted.pdf")
        extracted_text = reader.pages[0].extract_text()
        extracted_text = extracted_text.upper()
        
        # Check each redaction tuple
        for redact_tuple in redacts:
            redact_text = " ".join(redact_tuple).upper()
            self.assertNotIn(
                redact_text,
                extracted_text,
                f"Redacted text '{redact_text}' was still found in the PDF text layer."
            )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    unittest.main() 