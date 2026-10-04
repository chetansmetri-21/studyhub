"""
StudyHub - PYQ Visual Analyzer

Detects genuinely visually rich pages in PYQ PDFs.

It:
- detects diagrams, figures, graphs, charts and tables
- ignores full-page scanned PDF images
- renders detected pages as PNG images
- performs OCR on detected pages
- creates unique image filenames per PDF
"""

import os
import re

import pymupdf
import pytesseract

from PIL import Image


# ============================================================
# CONFIGURATION
# ============================================================

MAX_PAGES_TO_ANALYZE = 100
OCR_SCALE = 1.5

VISUAL_KEYWORDS = [
    "figure",
    "fig.",
    "diagram",
    "graph",
    "chart",
    "flowchart",
    "architecture",
    "block diagram",
    "table",
    "shown below",
    "shown above",
    "shown in",
    "plot",
    "tree",
    "matrix",
    "circuit",
]


# ============================================================
# VISUAL IMAGE STORAGE
# ============================================================

def get_visual_output_folder(pdf_path):

    pdf_dir = os.path.dirname(
        os.path.abspath(pdf_path)
    )

    output_folder = os.path.join(
        pdf_dir,
        "visuals"
    )

    os.makedirs(
        output_folder,
        exist_ok=True
    )

    return output_folder


# ============================================================
# SAFE PDF NAME
# ============================================================

def get_pdf_prefix(pdf_path):

    filename = os.path.basename(
        pdf_path
    )

    stem = os.path.splitext(
        filename
    )[0]

    stem = re.sub(
        r"[^A-Za-z0-9_-]+",
        "_",
        stem
    )

    return stem[:80] or "pyq"


# ============================================================
# TEXT CLEANING
# ============================================================

def clean_ocr_text(text):

    if not text:
        return ""

    lines = []

    for line in text.splitlines():

        line = re.sub(
            r"\s+",
            " ",
            line
        ).strip()

        if not line:
            continue

        lines.append(line)

    return "\n".join(lines)


# ============================================================
# PAGE TEXT
# ============================================================

def get_page_text(page):

    try:

        return page.get_text(
            "text"
        ) or ""

    except Exception:

        return ""


# ============================================================
# IMAGE DETECTION
# ============================================================

def get_embedded_image_count(page):

    """
    Counts embedded images that do NOT simply represent
    the entire scanned PDF page.

    Full-page scanned images are ignored.
    """

    try:

        page_rect = page.rect

        page_area = (
            abs(page_rect.width)
            * abs(page_rect.height)
        )

        if page_area <= 0:
            return 0

        infos = page.get_image_info(
            full=True
        )

        embedded_count = 0

        for info in infos:

            bbox = info.get(
                "bbox"
            )

            if not bbox:
                continue

            image_rect = pymupdf.Rect(
                bbox
            )

            image_area = (
                abs(image_rect.width)
                * abs(image_rect.height)
            )

            coverage = (
                image_area
                / page_area
            )

            # Ignore full-page scans.
            if coverage >= 0.90:
                continue

            embedded_count += 1

        return embedded_count

    except Exception:

        # Fallback for older PyMuPDF versions.
        try:

            return len(
                page.get_images(
                    full=True
                )
            )

        except Exception:

            return 0


# ============================================================
# DRAWING COUNT
# ============================================================

def get_page_drawing_count(page):

    try:

        drawings = page.get_drawings()

        return len(drawings)

    except Exception:

        return 0


# ============================================================
# KEYWORD DETECTION
# ============================================================

def contains_visual_keyword(text):

    text_lower = (
        text or ""
    ).lower()

    matches = []

    for keyword in VISUAL_KEYWORDS:

        if keyword.lower() in text_lower:

            matches.append(
                keyword
            )

    return matches


# ============================================================
# RENDER PAGE
# ============================================================

def render_page(page):

    try:

        matrix = pymupdf.Matrix(
            OCR_SCALE,
            OCR_SCALE
        )

        pix = page.get_pixmap(
            matrix=matrix,
            alpha=False
        )

        image = Image.frombytes(
            "RGB",
            [
                pix.width,
                pix.height
            ],
            pix.samples
        )

        return image

    except Exception as e:

        print(
            "[StudyHub Visual Analyzer] "
            f"Page rendering failed: {e}"
        )

        return None


# ============================================================
# SAVE RENDERED VISUAL
# ============================================================

def save_visual_image(
    image,
    output_folder,
    pdf_prefix,
    page_number
):

    if image is None:

        return None

    try:

        filename = (
            f"{pdf_prefix}_visual_page_{page_number}.png"
        )

        output_path = os.path.join(
            output_folder,
            filename
        )

        image.save(
            output_path,
            "PNG",
            optimize=True
        )

        return output_path

    except Exception as e:

        print(
            "[StudyHub Visual Analyzer] "
            f"Visual image save failed: {e}"
        )

        return None


# ============================================================
# OCR
# ============================================================

def run_ocr(image):

    if image is None:

        return ""

    try:

        text = pytesseract.image_to_string(
            image
        )

        return clean_ocr_text(
            text
        )

    except Exception as e:

        print(
            "[StudyHub Visual Analyzer] "
            f"OCR failed: {e}"
        )

        return ""


# ============================================================
# VISUAL TYPE ESTIMATION
# ============================================================

def estimate_visual_type(
    page_text,
    image_count,
    drawing_count
):

    text_lower = (
        page_text or ""
    ).lower()

    if (
        "table" in text_lower
        or "column" in text_lower
        or "row" in text_lower
    ):

        return "Table"

    if (
        "graph" in text_lower
        or "chart" in text_lower
        or "x-axis" in text_lower
        or "y-axis" in text_lower
        or "plot" in text_lower
    ):

        return "Graph / Chart"

    if (
        "flowchart" in text_lower
        or "flow chart" in text_lower
    ):

        return "Flowchart"

    if "architecture" in text_lower:

        return "Architecture Diagram"

    if (
        "diagram" in text_lower
        or "figure" in text_lower
        or "fig." in text_lower
    ):

        return "Diagram / Figure"

    if image_count > 0:

        return "Image / Figure"

    if drawing_count >= 5:

        return "Diagram / Figure"

    return "Visual Content"


# ============================================================
# SINGLE PAGE ANALYSIS
# ============================================================

def analyze_page(
    page,
    page_number,
    output_folder,
    pdf_prefix
):

    page_text = get_page_text(
        page
    )

    image_count = get_embedded_image_count(
        page
    )

    drawing_count = get_page_drawing_count(
        page
    )

    keyword_matches = (
        contains_visual_keyword(
            page_text
        )
    )

    # --------------------------------------------------------
    # INITIAL DETECTION
    # --------------------------------------------------------

    visual_detected = (
        image_count > 0
        or drawing_count >= 5
        or bool(keyword_matches)
    )

    if not visual_detected:

        return None

    # --------------------------------------------------------
    # RENDER
    # --------------------------------------------------------

    image = render_page(
        page
    )

    # --------------------------------------------------------
    # OCR
    # --------------------------------------------------------

    ocr_text = run_ocr(
        image
    )

    # --------------------------------------------------------
    # ALSO CHECK OCR FOR VISUAL KEYWORDS
    # --------------------------------------------------------

    ocr_keywords = contains_visual_keyword(
        ocr_text
    )

    combined_keywords = list(
        dict.fromkeys(
            keyword_matches
            + ocr_keywords
        )
    )

    # --------------------------------------------------------
    # SAVE IMAGE
    # --------------------------------------------------------

    image_path = save_visual_image(
        image,
        output_folder,
        pdf_prefix,
        page_number
    )

    if (
        not ocr_text
        and not page_text
        and not image_path
    ):

        return None

    # --------------------------------------------------------
    # VISUAL TYPE
    # --------------------------------------------------------

    combined_text = (
        page_text
        + "\n"
        + ocr_text
    )

    visual_type = estimate_visual_type(
        combined_text,
        image_count,
        drawing_count
    )

    # --------------------------------------------------------
    # RESULT
    # --------------------------------------------------------

    return {

        "page": page_number,

        "visual_detected": True,

        "visual_type": visual_type,

        "image_count": image_count,

        "drawing_count": drawing_count,

        "visual_keywords": combined_keywords,

        "ocr_text": ocr_text[:5000],

        "image_path": image_path,

        "image_filename": (
            os.path.basename(
                image_path
            )
            if image_path
            else None
        ),
    }


# ============================================================
# COMPLETE PDF ANALYSIS
# ============================================================

def analyze_pdf_visuals(
    pdf_path
):

    if not pdf_path:

        return []

    if not os.path.isfile(
        pdf_path
    ):

        print(
            "[StudyHub Visual Analyzer] "
            f"PDF not found: {pdf_path}"
        )

        return []

    results = []

    document = None

    try:

        document = pymupdf.open(
            pdf_path
        )

        output_folder = (
            get_visual_output_folder(
                pdf_path
            )
        )

        pdf_prefix = get_pdf_prefix(
            pdf_path
        )

        total_pages = min(
            len(document),
            MAX_PAGES_TO_ANALYZE
        )

        for index in range(
            total_pages
        ):

            page = document[
                index
            ]

            result = analyze_page(
                page,
                index + 1,
                output_folder,
                pdf_prefix
            )

            if result:

                results.append(
                    result
                )

    except Exception as e:

        print(
            "[StudyHub Visual Analyzer] "
            f"PDF analysis failed: {e}"
        )

    finally:

        if document:

            document.close()

    print(
        "[StudyHub Visual Analyzer] "
        f"Detected {len(results)} visual page(s)."
    )

    return results