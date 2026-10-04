import os
from werkzeug.utils import secure_filename


# =========================================================
# LOCAL STORAGE CONFIGURATION
# =========================================================

BASE_DIR = os.path.abspath(
    os.path.join(
        os.path.dirname(__file__),
        "..",
        ".."
    )
)

UPLOAD_FOLDER = os.path.join(
    BASE_DIR,
    "uploads"
)

os.makedirs(
    UPLOAD_FOLDER,
    exist_ok=True
)


# =========================================================
# SAVE FILE
# =========================================================

def save_file(file, filename=None, category="pyq"):
    """
    Save an uploaded file to local storage.

    S3 is handled separately by:
        app.utils.s3_storage

    This function always creates a local copy.
    """

    if filename:
        filename = secure_filename(filename)
    else:
        filename = secure_filename(
            file.filename
        )

    if not filename:
        raise ValueError(
            "Invalid file name."
        )

    category = secure_filename(
        category
    )

    upload_folder = os.path.join(
        UPLOAD_FOLDER,
        category
    )

    os.makedirs(
        upload_folder,
        exist_ok=True
    )

    file_path = os.path.join(
        upload_folder,
        filename
    )

    # Make sure Flask FileStorage starts
    # from the beginning of the file.
    try:
        file.stream.seek(0)
    except AttributeError:
        pass

    file.save(
        file_path
    )

    # Return ONLY the filename.
    return filename


# =========================================================
# GET FILE PATH
# =========================================================

def get_file_path(
    filename,
    category="pyq"
):
    """
    Return the absolute local filesystem path.
    """

    filename = secure_filename(
        filename
    )

    category = secure_filename(
        category
    )

    return os.path.join(
        UPLOAD_FOLDER,
        category,
        filename
    )


# =========================================================
# FILE EXISTS
# =========================================================

def file_exists(
    filename,
    category="pyq"
):
    """
    Check whether a local file exists.
    """

    file_path = get_file_path(
        filename,
        category
    )

    return os.path.isfile(
        file_path
    )


# =========================================================
# DELETE FILE
# =========================================================

def delete_file(
    filename,
    category="pyq"
):
    """
    Delete a local file.
    """

    file_path = get_file_path(
        filename,
        category
    )

    if os.path.isfile(
        file_path
    ):

        os.remove(
            file_path
        )

        return True

    return False