from __future__ import annotations

import io
import logging

from PIL import Image, ImageDraw
from plasmapdf.models.types import OpenContractsSinglePageAnnotationType, PawlsPagePythonType
from reportlab.lib.colors import Color  # For alpha-based transparency
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

logger = logging.getLogger(__name__)


def _compute_pixel_coordinates(
    annotation: OpenContractsSinglePageAnnotationType,
    page_width: float,
    page_height: float,
    image_width: int,
    image_height: int,
) -> tuple[float, float, float, float]:
    """
    Convert a PDF (point-based) bounding box to pixel coordinates
    for use with a rasterized image.

    Args:
        annotation: Dict with 'bounds' containing 'left','right','top','bottom' in PDF coords.
        page_width:  The width of the page in PDF points.
        page_height: The height of the page in PDF points.
        image_width: The rasterized image width in pixels.
        image_height: The rasterized image height in pixels.

    Returns:
        (left_px, top_px, right_px, bottom_px) in pixel coordinates.
    """
    bbox = annotation["bounds"]
    left_px = (float(bbox["left"]) / page_width) * float(image_width)
    right_px = (float(bbox["right"]) / page_width) * float(image_width)
    top_px = (float(bbox["top"]) / page_height) * float(image_height)
    bottom_px = (float(bbox["bottom"]) / page_height) * float(image_height)

    if top_px > bottom_px:
        top_px, bottom_px = bottom_px, top_px

    return (left_px, top_px, right_px, bottom_px)


def redact_pdf_to_images(
    pdf_bytes: bytes,
    pawls_pages: list[PawlsPagePythonType],
    page_annotations: list[list[OpenContractsSinglePageAnnotationType]],
    dpi: float = 300.0,
    poppler_path: str | None = None,
    use_pdftocairo: bool = False,
) -> list[Image.Image]:
    """
    Convert a PDF to images (via pdf2image) at the specified dpi and apply rectangular
    fill (e.g., black) over bounding boxes. Returns a list of PIL Images.

    Args:
        pdf_bytes: Raw PDF bytes.
        pawls_pages: PawlsPagePythonType data including page dimension & token info.
        page_annotations: Each page's bounding boxes for redaction.
        dpi:            Rasterization resolution in DPI (default 300).
        poppler_path:   If set, path to poppler installation (for Windows).
        use_pdftocairo: If True, use pdftocairo instead of pdftoppm.

    Returns:
        List of PIL Images (redacted).
    """
    from pdf2image import convert_from_bytes

    pages = convert_from_bytes(
        pdf_bytes,
        dpi=int(dpi),
        poppler_path=poppler_path,
        use_pdftocairo=use_pdftocairo,
        fmt="png",
    )

    redacted_images: list[Image.Image] = []

    for idx, page_img in enumerate(pages):
        draw = ImageDraw.Draw(page_img)
        page_w = float(pawls_pages[idx]["page"]["width"])
        page_h = float(pawls_pages[idx]["page"]["height"])

        annots_for_page = page_annotations[idx]
        for annot in annots_for_page:
            left, top, right, bottom = _compute_pixel_coordinates(
                annot,
                page_width=page_w,
                page_height=page_h,
                image_width=page_img.width,
                image_height=page_img.height,
            )
            draw.rectangle([left, top, right, bottom], fill="black")

        redacted_images.append(page_img)

    return redacted_images


def build_text_redacted_pdf(
    output_pdf: str,
    redacted_images: list[Image.Image],
    pawls_pages: list[PawlsPagePythonType],
    page_redactions: list[list[OpenContractsSinglePageAnnotationType]],
    dpi: float,
    hide_text: bool = True,
) -> None:
    """
    Build a new PDF from redacted raster images plus a text layer for copy/paste,
    omitting tokens that fall under redacted bounding boxes. The text can be
    fully transparent so it does not obscure the PDF.

    Args:
        output_pdf: Path to the resulting PDF file.
        redacted_images: List of PIL Images (one per page) with blacked-out areas.
        pawls_pages: PawlsPagePythonType data with original PDF dimension/tokens.
        page_redactions: BBoxes to redact (parallel to pawls_pages).
        dpi: The DPI used when converting PDF to images.
        hide_text: If True, text is 100% invisible (transparent).
    """
    c = canvas.Canvas(output_pdf)

    # Predefine a fully transparent color for text
    invisible_color = Color(red=0, green=0, blue=0, alpha=0.0)

    for page_idx, img in enumerate(redacted_images):
        pawls_page = pawls_pages[page_idx]
        redactions = page_redactions[page_idx]

        width_px, height_px = img.size

        # Convert pixel dimensions to PDF points
        width_pts = (width_px * 72.0) / dpi
        height_pts = (height_px * 72.0) / dpi

        c.setPageSize((width_pts, height_pts))

        # Draw the redacted image onto the canvas
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)
        img_reader = ImageReader(buf)
        c.drawImage(img_reader, 0, 0, width=width_pts, height=height_pts)

        # If hide_text is True, paint text with alpha=0.0 for transparency
        if hide_text:
            c.setFillColor(invisible_color)
        else:
            # Visible text in black
            c.setFillColorRGB(0, 0, 0)

        page_w = float(pawls_page["page"]["width"])
        page_h = float(pawls_page["page"]["height"])
        tokens = pawls_page["tokens"]

        for token in tokens:
            # Skip tokens that intersect redactions
            if _is_token_in_redactions(token, redactions):
                continue

            x_left = float(token["x"])
            y_top = float(token["y"])
            token_h = float(token["height"])

            # Convert top-based coords to bottom-based
            x_pt = (x_left / page_w) * width_pts
            y_pt = height_pts - ((y_top + token_h) / page_h) * height_pts

            # Add a space so the tokens remain separated on copy/paste
            c.drawString(x_pt, y_pt, token["text"] + " ")

        c.showPage()

    c.save()
    logger.info(f"Created {output_pdf} with fully transparent text.")


def _is_token_in_redactions(
    token_dict: dict[str, float | str], redactions: list[OpenContractsSinglePageAnnotationType]
) -> bool:
    """
    Checks if a token's bounding box intersects any redaction bounding box.

    Args:
        token_dict: A single token with x,y,width,height in PDF coords.
        redactions: A list of annotation bboxes in PDF coords.

    Returns:
        True if the token overlaps at least one redaction region, False otherwise.
    """
    x_left = float(token_dict["x"])
    y_top = float(token_dict["y"])
    w = float(token_dict["width"])
    h = float(token_dict["height"])

    token_r = x_left + w
    token_b = y_top + h

    for annotation in redactions:
        bbox = annotation["bounds"]
        b_left = float(bbox["left"])
        b_right = float(bbox["right"])
        b_top = float(bbox["top"])
        b_bottom = float(bbox["bottom"])

        # Check for overlap (token vs. bbox)
        if not (
            token_r < b_left  # entirely left
            or x_left > b_right  # entirely right
            or token_b < b_top  # entirely above
            or y_top > b_bottom  # entirely below
        ):
            return True

    return False
