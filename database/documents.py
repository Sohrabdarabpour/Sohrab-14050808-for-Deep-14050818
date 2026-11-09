from .connection import get_connection
def add_document(data):
    connection = get_connection()
    fields = list(data.keys())
    values = [data[field] for field in fields]
    columns = ", ".join(fields)
    placeholders = ", ".join(["?"] * len(fields))
    try:
        cursor = connection.execute(
            f"INSERT INTO documents ({columns}) VALUES ({placeholders})",
            values
        )
        connection.commit()
        return cursor.lastrowid
    except Exception:
        connection.rollback()
        return None
    finally:
        connection.close()
def get_document(document_id):
    connection = get_connection()
    document = connection.execute(
        "SELECT * FROM documents WHERE id = ?",
        (document_id,)
    ).fetchone()
    connection.close()
    return document
def get_all_documents():
    connection = get_connection()
    documents = connection.execute(
        "SELECT * FROM documents ORDER BY id DESC"
    ).fetchall()
    connection.close()
    return documents
def update_document(document_id, data):
    connection = get_connection()
    fields = list(data.keys())
    values = [data[field] for field in fields]
    set_clause = ", ".join([f"{field} = ?" for field in fields])
    values.append(document_id)
    try:
        cursor = connection.execute(
            f"UPDATE documents SET {set_clause} WHERE id = ?",
            values
        )
        connection.commit()
        return cursor.rowcount > 0
    except Exception:
        connection.rollback()
        return False
    finally:
        connection.close()
def delete_document(document_id):
    connection = get_connection()
    try:
        cursor = connection.execute(
            "DELETE FROM documents WHERE id = ?",
            (document_id,)
        )
        connection.commit()
        return cursor.rowcount > 0
    except Exception:
        connection.rollback()
        return False
    finally:
        connection.close()
def get_documents_by_year(year):
    connection = get_connection()
    if year == "all":
        documents = connection.execute(
            "SELECT * FROM documents ORDER BY id DESC"
        ).fetchall()
    else:
        documents = connection.execute(
            """
            SELECT * FROM documents
            WHERE substr(date_received, 1, 4) = ?
            ORDER BY id DESC
            """,
            (str(year),)
        ).fetchall()
    connection.close()
    return documents
def get_available_years():
    connection = get_connection()
    rows = connection.execute(
        """
        SELECT DISTINCT substr(date_received, 1, 4) AS year
        FROM documents
        WHERE date_received IS NOT NULL
        AND date_received != ''
        ORDER BY year DESC
        """
    ).fetchall()
    connection.close()
    return [row["year"] for row in rows if row["year"]]

def add_documents_bulk(documents):
    if not documents:
        return 0
    connection = get_connection()
    fields = list(documents[0].keys())
    columns = ", ".join(fields)
    placeholders = ", ".join(["?"] * len(fields))
    values = [
        [document.get(field) for field in fields]
        for document in documents
    ]
    try:
        connection.executemany(
            f"INSERT INTO documents ({columns}) VALUES ({placeholders})",
            values
        )
        connection.commit()
        return len(values)
    except Exception:
        connection.rollback()
        return 0
    finally:
        connection.close()