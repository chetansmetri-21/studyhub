import os
import re

from pypdf import PdfReader
import pytesseract

from PIL import Image, ImageEnhance, ImageFilter, ImageOps

from pdf2image import convert_from_path


# ============================================================
# CONFIGURATION
# ============================================================

TESSERACT_PATH = (
    r"C:\Program Files\Tesseract-OCR\tesseract.exe"
)

POPPLER_PATH = (
    r"C:\poppler\poppler-26.09.0\Library\bin"
)

pytesseract.pytesseract.tesseract_cmd = TESSERACT_PATH


# ============================================================
# TEXT QUALITY
# ============================================================

def text_quality_score(text):
    """
    Estimate whether extracted text is readable.

    This is only a quality estimate. It does not modify
    the question wording.
    """

    if not text:
        return 0

    text = str(text).strip()

    if len(text) < 30:
        return 0

    total = len(text)

    readable = len(
        re.findall(
            r"[A-Za-z0-9\s.,;:!?()\[\]{}'\"/%&+\-*/=<>]",
            text
        )
    )

    readable_ratio = readable / total

    suspicious = len(
        re.findall(
            r"[¢£¥§©®™¤¦¬±µ¶·¸¹º»¼½¾¿]",
            text
        )
    )

    suspicious_ratio = suspicious / total

    score = readable_ratio * 100

    score -= suspicious_ratio * 100

    return score


# ============================================================
# BASIC TEXT NORMALIZATION
# ============================================================

def normalize_extracted_text(text):
    """
    Basic whitespace and encoding cleanup.

    Does NOT rewrite words.
    """

    if not text:
        return ""

    text = str(text)

    text = text.replace(
        "\r\n",
        "\n"
    )

    text = text.replace(
        "\r",
        "\n"
    )

    text = text.replace(
        "\x00",
        ""
    )

    text = text.replace(
        "¦",
        " "
    )

    # Do not remove normal "|" characters aggressively.
    # They can sometimes occur in extracted academic text.

    text = re.sub(
        r"[ \t]+",
        " ",
        text
    )

    text = re.sub(
        r"\n\s*\n\s*\n+",
        "\n\n",
        text
    )

    return text.strip()


# ============================================================
# NORMAL PDF EXTRACTION
# ============================================================

def extract_pdf_text(file_path):

    try:

        reader = PdfReader(
            file_path
        )

        text_parts = []

        for page_number, page in enumerate(
            reader.pages,
            start=1
        ):

            try:

                page_text = page.extract_text()

                if page_text:

                    text_parts.append(
                        page_text
                    )

            except Exception as e:

                print(
                    f"PDF extraction error "
                    f"on page {page_number}: {e}"
                )

        return "\n".join(
            text_parts
        )

    except Exception as e:

        print(
            "PDF reader error:",
            e
        )

        return ""


# ============================================================
# IMAGE PREPROCESSING
# ============================================================

def preprocess_image(image):
    """
    Prepare scanned PDF page for OCR.

    Steps:
    - grayscale
    - contrast enhancement
    - sharpening
    - automatic thresholding
    """

    # Convert to grayscale
    image = ImageOps.grayscale(
        image
    )

    # Improve contrast
    image = ImageEnhance.Contrast(
        image
    ).enhance(2.0)

    # Slight sharpening
    image = image.filter(
        ImageFilter.SHARPEN
    )

    # Automatic threshold
    image = image.point(
        lambda pixel: 0
        if pixel < 180
        else 255
    )

    return image


# ============================================================
# OCR ONE IMAGE
# ============================================================

def run_ocr(image, psm):

    try:

        text = pytesseract.image_to_string(
            image,
            config=f"--psm {psm}"
        )

        return text or ""

    except Exception as e:

        print(
            f"Tesseract OCR error "
            f"(PSM {psm}):",
            e
        )

        return ""


# ============================================================
# OCR PDF
# ============================================================

def extract_ocr_text(file_path):

    try:

        images = convert_from_path(
            file_path,
            dpi=300,
            poppler_path=POPPLER_PATH
        )

    except Exception as e:

        print(
            "PDF to image conversion error:",
            e
        )

        return ""

    page_results = []

    for page_number, image in enumerate(
        images,
        start=1
    ):

        print(
            f"OCR processing page "
            f"{page_number}/{len(images)}..."
        )

        # ----------------------------------------------------
        # Original image
        # ----------------------------------------------------

        original_text = run_ocr(
            image,
            6
        )

        original_score = text_quality_score(
            original_text
        )

        # ----------------------------------------------------
        # Preprocessed image
        # ----------------------------------------------------

        processed_image = preprocess_image(
            image
        )

        processed_text = run_ocr(
            processed_image,
            6
        )

        processed_score = text_quality_score(
            processed_text
        )

        # ----------------------------------------------------
        # Try another OCR layout mode when useful
        # ----------------------------------------------------

        alternate_text = run_ocr(
            processed_image,
            3
        )

        alternate_score = text_quality_score(
            alternate_text
        )

        # ----------------------------------------------------
        # Select best result for this page
        # ----------------------------------------------------

        candidates = [
            (
                original_score,
                original_text
            ),
            (
                processed_score,
                processed_text
            ),
            (
                alternate_score,
                alternate_text
            )
        ]

        candidates.sort(
            key=lambda item: item[0],
            reverse=True
        )

        best_score, best_text = (
            candidates[0]
        )

        print(
            f"Page {page_number} OCR scores: "
            f"original={original_score:.2f}, "
            f"processed={processed_score:.2f}, "
            f"alternate={alternate_score:.2f}"
        )

        page_results.append(
            best_text
        )

    return "\n".join(
        page_results
    )


# ============================================================
# MAIN EXTRACTION FUNCTION
# ============================================================

def extract_text_from_pdf(file_path):

    if not file_path:

        return ""

    if not os.path.exists(
        file_path
    ):

        print(
            "PDF file not found:",
            file_path
        )

        return ""

    print(
        "\n========================================"
    )

    print(
        "StudyHub PDF text extraction started"
    )

    print(
        "========================================"
    )

    # --------------------------------------------------------
    # STEP 1
    # Normal PDF extraction
    # --------------------------------------------------------

    normal_text = extract_pdf_text(
        file_path
    )

    normal_text = normalize_extracted_text(
        normal_text
    )

    normal_score = text_quality_score(
        normal_text
    )

    print(
        f"Normal extraction quality: "
        f"{normal_score:.2f}"
    )

    # --------------------------------------------------------
    # STEP 2
    # Use normal extraction only when it looks reliable
    # --------------------------------------------------------

    if normal_score >= 80:

        print(
            "Normal PDF extraction appears reliable."
        )

        print(
            "Using normal extracted text."
        )

        return normal_text

    # --------------------------------------------------------
    # STEP 3
    # Run OCR
    # --------------------------------------------------------

    print(
        "Normal extraction appears incomplete "
        "or corrupted."
    )

    print(
        "Starting high-quality OCR..."
    )

    ocr_text = extract_ocr_text(
        file_path
    )

    ocr_text = normalize_extracted_text(
        ocr_text
    )

    ocr_score = text_quality_score(
        ocr_text
    )

    print(
        f"OCR extraction quality: "
        f"{ocr_score:.2f}"
    )

    # --------------------------------------------------------
    # STEP 4
    # Select better result
    # --------------------------------------------------------

    if ocr_score > normal_score:

        print(
            "Using OCR result."
        )

        return ocr_text

    if normal_text:

        print(
            "OCR did not produce a better result."
        )

        print(
            "Using normal PDF extraction."
        )

        return normal_text

    print(
        "No usable normal text found."
    )

    print(
        "Returning OCR result."
    )

    return ocr_text