import sys
import os

PROJECT_ROOT = os.path.abspath(
    os.path.join(
        os.path.dirname(__file__),
        "../.."
    )
)

sys.path.insert(
    0,
    PROJECT_ROOT
)


from database.connection import get_connection




def add_user_profile_columns():

    connection = get_connection()

    try:

        columns = [
            (
                "email",
                "TEXT"
            ),
            (
                "phone",
                "TEXT"
            ),
            (
                "position",
                "TEXT"
            ),
            (
                "avatar",
                "TEXT DEFAULT 'default.png'"
            ),
            (
                "is_active",
                "INTEGER DEFAULT 1"
            ),
            (
                "updated_at",
                "TIMESTAMP"
            ),
            (
                "last_login",
                "TIMESTAMP"
            )
        ]


        existing_columns = connection.execute(
            """
            PRAGMA table_info(users)
            """
        ).fetchall()


        existing_names = {
            column["name"]
            for column in existing_columns
        }


        for name, column_type in columns:

            if name not in existing_names:

                connection.execute(
                    f"""
                    ALTER TABLE users
                    ADD COLUMN {name} {column_type}
                    """
                )

                print(
                    f"ستون {name} اضافه شد"
                )

            else:

                print(
                    f"ستون {name} قبلاً وجود دارد"
                )


        connection.commit()

        print(
            "Migration کاربران با موفقیت انجام شد"
        )


    finally:

        connection.close()



if __name__ == "__main__":

    add_user_profile_columns()