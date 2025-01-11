# PdfRedact

[![PyPI - Version](https://img.shields.io/pypi/v/pdfredact.svg)](https://pypi.org/project/pdfredact)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/pdfredact.svg)](https://pypi.org/project/pdfredact)

A robust PDF redaction library that securely removes sensitive information while preserving document integrity.

## Features at a Glance

🔒 **Comprehensive Redaction**
- Handles both visual content and searchable text layers
- True removal of sensitive information

⚙️ **Flexible Configuration**
- Adjustable image quality (DPI)
- Configurable text handling (invisible or removed)
- Cross-platform support (Windows & Unix)

🛠️ **Professional-Grade Tools**
- High-resolution image processing
- Precise coordinate-based redaction
- Document searchability preservation

## Installation

```bash
pip install pdfredact
```

### Dependencies
- Python 3.10+
- Poppler (PDF to image conversion)
- Pillow (Image processing)
- ReportLab (PDF generation)

#### Windows Setup
Windows users must install Poppler and either:
- Set the `POPPLER_PATH` environment variable
- Provide the path explicitly in function calls

## How It Works

The redaction process follows a secure two-step approach:

1. **Image Layer Redaction** 📸
   - Converts PDF pages to high-resolution images
   - Applies black rectangles to specified areas
   - Maintains quality through configurable DPI

2. **Text Layer Processing** 📝
   - Generates a new searchable text layer
   - Removes or obscures text in redacted regions
   - Preserves document searchability

## Usage Example

```python
from pdfredact import redact_pdf_to_images, build_text_redacted_pdf

# Define redaction areas using page coordinates
redactions = [{
    "bounds": {
        "left": 100,
        "right": 200,
        "top": 50,
        "bottom": 75
    },
    "tokensJsons": [...],  # Token information
    "rawText": "sensitive text"
}]

# Step 1: Generate redacted images
redacted_images = redact_pdf_to_images(
    pdf_bytes=pdf_content,
    pawls_pages=page_data,
    page_annotations=[redactions],
    dpi=300
)

# Step 2: Create final PDF with redacted text layer
build_text_redacted_pdf(
    output_pdf="redacted_document.pdf",
    redacted_images=redacted_images,
    pawls_pages=page_data,
    page_redactions=[redactions],
    dpi=300,
    hide_text=True  # Text remains copyable but invisible
)
```

## Best Practices

📋 **Quality Assurance**
- Use 300+ DPI for optimal output quality
- Verify redactions through:
  - Visual inspection
  - Copy/paste testing
  - Text extraction tool verification

⚠️ **Known Limitations**
- Processing time scales with DPI and document size
- Large documents require substantial memory
- Image-based PDFs need special handling

## Security Advisory

⚠️ **Important**: Always verify redacted documents thoroughly. The PDF format is complex and support can vary. Multiple verification methods are recommended for sensitive materials.

**Disclaimer**: We are not liable for consequences arising from improperly redacted PDFs.

## License

`pdfredact` is distributed under the terms of the [MIT](https://spdx.org/licenses/MIT.html) license.
