import sqlite3
import os


BASE_DIR = os.path.abspath(
    os.path.dirname(__file__)
)

DATABASE_FILE = os.path.join(
    BASE_DIR,
    "studyhub.db"
)


connection = sqlite3.connect(
    DATABASE_FILE
)

cursor = connection.cursor()


# Check whether file_hash already exists
cursor.execute(
    "PRAGMA table_info(pyqs)"
)

columns = [
    column[1]
    for column in cursor.fetchall()
]


if "file_hash" not in columns:

    print("Adding pyqs.file_hash...")

    cursor.execute(
        """
        ALTER TABLE pyqs
        ADD COLUMN file_hash VARCHAR(64)
        """
    )

    connection.commit()

    print("pyqs.file_hash added successfully.")

else:

    print(
        "pyqs.file_hash already exists."
    )


connection.close()

print(
    "Phase 5 hash database migration completed."
)