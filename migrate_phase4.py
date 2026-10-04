from app import create_app, db
from sqlalchemy import text


app = create_app()


with app.app_context():

    print("Starting Phase 4 database migration...")

    # -------------------------------------------------
    # USERS
    # -------------------------------------------------

    try:

        db.session.execute(
            text(
                """
                ALTER TABLE users
                ADD COLUMN is_admin
                BOOLEAN NOT NULL DEFAULT 0
                """
            )
        )

        print("Added users.is_admin")

    except Exception as e:

        print(
            "users.is_admin already exists or was skipped:",
            e
        )

        db.session.rollback()


    # -------------------------------------------------
    # NOTES
    # -------------------------------------------------

    try:

        db.session.execute(
            text(
                """
                ALTER TABLE notes
                ADD COLUMN verification_status
                VARCHAR(20) NOT NULL DEFAULT 'approved'
                """
            )
        )

        print(
            "Added notes.verification_status"
        )

    except Exception as e:

        print(
            "notes.verification_status already exists or was skipped:",
            e
        )

        db.session.rollback()


    # -------------------------------------------------
    # PYQS
    # -------------------------------------------------

    try:

        db.session.execute(
            text(
                """
                ALTER TABLE pyqs
                ADD COLUMN verification_status
                VARCHAR(20) NOT NULL DEFAULT 'approved'
                """
            )
        )

        print(
            "Added pyqs.verification_status"
        )

    except Exception as e:

        print(
            "pyqs.verification_status already exists or was skipped:",
            e
        )

        db.session.rollback()


    db.session.commit()


    print()
    print("Phase 4 database migration completed.")