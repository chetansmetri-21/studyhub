import os
import shutil
from datetime import datetime


BASE_DIR = os.path.abspath(
    os.path.join(
        os.path.dirname(__file__),
        "..",
        ".."
    )
)

DATABASE_FILE = os.path.join(
    BASE_DIR,
    "studyhub.db"
)

UPLOADS_FOLDER = os.path.join(
    BASE_DIR,
    "uploads"
)

BACKUPS_FOLDER = os.path.join(
    BASE_DIR,
    "backups"
)


def create_backup():
    """
    Create a complete local backup of StudyHub.

    Backup includes:
        - studyhub.db
        - uploads/

    Returns:
        The path of the created backup folder.
    """

    timestamp = datetime.now().strftime(
        "%Y%m%d_%H%M%S"
    )

    backup_folder = os.path.join(
        BACKUPS_FOLDER,
        f"studyhub_backup_{timestamp}"
    )

    os.makedirs(
        backup_folder,
        exist_ok=True
    )

    # ---------------------------------------------------------
    # BACK UP DATABASE
    # ---------------------------------------------------------

    if os.path.isfile(
        DATABASE_FILE
    ):

        shutil.copy2(
            DATABASE_FILE,
            os.path.join(
                backup_folder,
                "studyhub.db"
            )
        )

    # ---------------------------------------------------------
    # BACK UP UPLOADED FILES
    # ---------------------------------------------------------

    if os.path.isdir(
        UPLOADS_FOLDER
    ):

        shutil.copytree(
            UPLOADS_FOLDER,
            os.path.join(
                backup_folder,
                "uploads"
            )
        )

    return backup_folder