"""
Example script demonstrating the integration of pdftokenizer and pdfredact
to create a complete PDF redaction workflow.
"""

# TODO - this is not actually a working example ATM... Sorry. See tests for now.

# import json

# from typing import Any, Dict, List

# from plasmapdf.models.types import BoundingBoxPythonType

# from pdfredact import build_text_redacted_pdf, redact_pdf_to_images


# def create_redactions_from_text(
#     pages: List[Dict[str, Any]], text_to_redact: str
# ) -> List[List[PageRedaction]]:
#     """
#     Create redaction objects for all instances of specified text in the document.

#     Args:
#         pages: List of page data from pdftokenizer
#         text_to_redact: Text string to search for and redact

#     Returns:
#         List of redactions for each page
#     """
#     all_page_redactions: List[List[PageRedaction]] = []

#     for page_idx, page in enumerate(pages):
#         page_redactions: List[PageRedaction] = []
#         tokens = page.get("tokens", [])

#         # Find sequences of tokens that match our target text
#         text_buffer = ""
#         token_buffer = []

#         for token in tokens:
#             text_buffer += token["text"] + " "
#             token_buffer.append(token)

#             if text_to_redact in text_buffer:
#                 # Calculate bounding box for all tokens in match
#                 left = min(t["x"] for t in token_buffer)
#                 right = max(t["x"] + t["width"] for t in token_buffer)
#                 top = min(t["y"] for t in token_buffer)
#                 bottom = max(t["y"] + t["height"] for t in token_buffer)

#                 redaction = OpenContractsSinglePageAnnotationType(
#                     bounds=BoundingBoxPythonType(left=left, right=right, top=top, bottom=bottom),
#                     tokensJsons=[json.dumps(t) for t in token_buffer],
#                     rawText=text_buffer.strip(),
#                 )
#                 page_redactions.append(redaction)

#                 # Reset buffers
#                 text_buffer = ""
#                 token_buffer = []

#         all_page_redactions.append(page_redactions)

#     return all_page_redactions


# def redact_pdf(input_path: str, output_path: str, text_to_redact: str, dpi: int = 300) -> None:
#     """
#     Redact all instances of specified text from a PDF file.

#     Args:
#         input_path: Path to input PDF file
#         output_path: Path to save redacted PDF
#         text_to_redact: Text to find and redact
#         dpi: DPI for image processing (default: 300)
#     """
#     # Read PDF file
#     with open(input_path, "rb") as f:
#         pdf_bytes = f.read()

#     # Extract text and layout information
#     pages = extract_tokens_from_pdf(pdf_bytes)

#     # Create redaction objects
#     all_redactions = create_redactions_from_text(pages, text_to_redact)

#     # Generate redacted images
#     redacted_images = redact_pdf_to_images(
#         pdf_bytes=pdf_bytes, pawls_pages=pages, page_annotations=all_redactions, dpi=dpi
#     )

#     # Create final PDF with redacted text layer
#     build_text_redacted_pdf(
#         output_pdf=output_path,
#         redacted_images=redacted_images,
#         pawls_pages=pages,
#         page_redactions=all_redactions,
#         dpi=dpi,
#         hide_text=True,
#     )


# if __name__ == "__main__":
#     # Example usage
#     input_pdf = "input.pdf"
#     output_pdf = "redacted_output.pdf"
#     sensitive_text = "confidential"

#     redact_pdf(input_path=input_pdf, output_path=output_pdf, text_to_redact=sensitive_text)

pass
