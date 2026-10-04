import os

from PIL import Image


# ============================================================
# STUDYHUB SECURE UPLOAD VALIDATION
# ============================================================

PROFILE_IMAGE_EXTENSIONS = {
    "png",
    "jpg",
    "jpeg",
    "webp"
}

PROFILE_IMAGE_MIME_TYPES = {
    "image/png",
    "image/jpeg",
    "image/webp"
}

PDF_EXTENSION = "pdf"

PDF_MIME_TYPES = {
    "application/pdf"
}


# ============================================================
# SIZE LIMITS
# ============================================================

MAX_PROFILE_IMAGE_SIZE = 2 * 1024 * 1024       # 2 MB
MAX_PDF_SIZE = 25 * 1024 * 1024                # 25 MB


# ============================================================
# EXTENSION
# ============================================================

def get_extension(filename):
    if not filename:
        return ""

    filename = os.path.basename(filename)

    if "." not in filename:
        return ""

    return filename.rsplit(".", 1)[1].lower().strip()


# ============================================================
# PROFILE IMAGE VALIDATION
# ============================================================

def validate_profile_image(file):

    if not file:
        return False, "No image was uploaded."

    filename = file.filename or ""

    extension = get_extension(filename)

    if extension not in PROFILE_IMAGE_EXTENSIONS:
        return (
            False,
            "Only PNG, JPG, JPEG or WEBP images are allowed."
        )

    # --------------------------------------------------------
    # SIZE CHECK
    # --------------------------------------------------------

    try:
        file.stream.seek(0, os.SEEK_END)

        size = file.stream.tell()

        file.stream.seek(0)

    except Exception:
        return (
            False,
            "Unable to determine image size."
        )

    if size <= 0:
        return (
            False,
            "The uploaded image is empty."
        )

    if size > MAX_PROFILE_IMAGE_SIZE:
        return (
            False,
            "Profile photo must be smaller than 2 MB."
        )

    # --------------------------------------------------------
    # CONTENT VALIDATION
    # --------------------------------------------------------

    try:

        file.stream.seek(0)

        image = Image.open(file.stream)

        image.verify()

        file.stream.seek(0)

        image = Image.open(file.stream)

        detected_format = (
            image.format or ""
        ).upper()

        allowed_formats = {
            "PNG",
            "JPEG",
            "WEBP"
        }

        if detected_format not in allowed_formats:
            return (
                False,
                "The uploaded file is not a supported image."
            )

        # Prevent extremely large decompression-bomb images.
        width, height = image.size

        if width <= 0 or height <= 0:
            return (
                False,
                "Invalid image dimensions."
            )

        if width > 6000 or height > 6000:
            return (
                False,
                "Image dimensions are too large."
            )

    except Exception:
        return (
            False,
            "The uploaded image is invalid or corrupted."
        )

    finally:
        try:
            file.stream.seek(0)
        except Exception:
            pass

    return True, None


# ============================================================
# PDF VALIDATION
# ============================================================

def validate_pdf(file):

    if not file:
        return False, "No PDF was uploaded."

    filename = file.filename or ""

    extension = get_extension(filename)

    if extension != PDF_EXTENSION:
        return (
            False,
            "Only PDF files are allowed."
        )

    # --------------------------------------------------------
    # SIZE CHECK
    # --------------------------------------------------------

    try:

        file.stream.seek(0, os.SEEK_END)

        size = file.stream.tell()

        file.stream.seek(0)

    except Exception:

        return (
            False,
            "Unable to determine PDF size."
        )

    if size <= 0:
        return (
            False,
            "The uploaded PDF is empty."
        )

    if size > MAX_PDF_SIZE:
        return (
            False,
            "PDF files must be smaller than 25 MB."
        )

    # --------------------------------------------------------
    # PDF MAGIC HEADER
    # --------------------------------------------------------

    try:

        file.stream.seek(0)

        header = file.stream.read(5)

        file.stream.seek(0)

        if header != b"%PDF-":

            return (
                False,
                "The uploaded file is not a valid PDF."
            )

    except Exception:

        return (
            False,
            "Unable to validate the PDF."
        )

    finally:

        try:
            file.stream.seek(0)
        except Exception:
            pass

    return True, None

# =========================================================
# SECURE STUDY NOTE FILE VALIDATION
# =========================================================

NOTE_FILE_EXTENSIONS = {
    "pdf",
    "doc",
    "docx",
    "ppt",
    "pptx",
}

MAX_NOTE_FILE_SIZE = 25 * 1024 * 1024


def validate_note_file(file):
    """
    Validate uploaded StudyHub note files using:
    - extension
    - file size
    - actual file signature
    """

    if not file:
        return False, "No file was uploaded."

    filename = file.filename or ""

    extension = get_extension(filename)

    if extension not in NOTE_FILE_EXTENSIONS:
        return (
            False,
            "Only PDF, DOC, DOCX, PPT or PPTX files are allowed."
        )

    # -----------------------------------------------------
    # FILE SIZE
    # -----------------------------------------------------

    try:

        file.stream.seek(0, os.SEEK_END)

        size = file.stream.tell()

        file.stream.seek(0)

    except Exception:

        return False, "Unable to determine file size."

    if size <= 0:
        return False, "The uploaded file is empty."

    if size > MAX_NOTE_FILE_SIZE:
        return False, "Study material must be smaller than 25 MB."

    # -----------------------------------------------------
    # FILE SIGNATURE
    # -----------------------------------------------------

    try:

        file.stream.seek(0)

        header = file.stream.read(8)

        file.stream.seek(0)

        # PDF
        if extension == "pdf":

            if not header.startswith(b"%PDF-"):

                return (
                    False,
                    "The uploaded file is not a valid PDF."
                )

        # DOC / PPT legacy Microsoft Office
        elif extension in {"doc", "ppt"}:

            if header[:8] != (
                b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"
            ):

                return (
                    False,
                    "The uploaded file is not a valid Office document."
                )

        # DOCX / PPTX are ZIP-based Office Open XML files
        elif extension in {"docx", "pptx"}:

            if header[:4] != b"PK\x03\x04":

                return (
                    False,
                    "The uploaded file is not a valid Office document."
                )

    except Exception:

        return (
            False,
            "Unable to validate the uploaded file."
        )

    finally:

        try:
            file.stream.seek(0)
        except Exception:
            pass

    return True, None
