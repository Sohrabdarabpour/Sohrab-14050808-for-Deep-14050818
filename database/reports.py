from .connection import get_connection
def get_project_report():
    connection = get_connection()
    rows = connection.execute(
        """
        SELECT project_name, COUNT(*) AS total
        FROM documents
        WHERE project_name IS NOT NULL
        AND project_name != ''
        GROUP BY project_name
        ORDER BY total DESC
        """
    ).fetchall()
    connection.close()
    return rows
def get_contractor_report():
    connection = get_connection()
    rows = connection.execute(
        """
        SELECT contractor, COUNT(*) AS total
        FROM documents
        WHERE contractor IS NOT NULL
        AND contractor != ''
        GROUP BY contractor
        ORDER BY total DESC
        """
    ).fetchall()
    connection.close()
    return rows
def get_delay_report():
    connection = get_connection()
    rows = connection.execute(
        """
        SELECT *
        FROM documents
        WHERE final_delay IS NOT NULL
        AND final_delay != ''
        ORDER BY id DESC
        """
    ).fetchall()
    connection.close()
    return rows
def get_status_report():
    connection = get_connection()
    rows = connection.execute(
        """
        SELECT doc_response_status, COUNT(*) AS total
        FROM documents
        WHERE doc_response_status IS NOT NULL
        AND doc_response_status != ''
        GROUP BY doc_response_status
        ORDER BY total DESC
        """
    ).fetchall()
    connection.close()
    return rows
def get_unit_report():
    connection = get_connection()
    rows = connection.execute(
        """
        SELECT unit, COUNT(*) AS total
        FROM documents
        WHERE unit IS NOT NULL
        AND unit != ''
        GROUP BY unit
        ORDER BY total DESC
        """
    ).fetchall()
    connection.close()
    return rows
def get_expert_report():
    connection = get_connection()
    rows = connection.execute(
        """
        SELECT expert_name, COUNT(*) AS total
        FROM documents
        WHERE expert_name IS NOT NULL
        AND expert_name != ''
        GROUP BY expert_name
        ORDER BY total DESC
        """
    ).fetchall()
    connection.close()
    return rows