import oracledb
from config import get_current_db_config

def get_connection():
    config = get_current_db_config()
    dsn = oracledb.makedsn(
        config["host"],
        int(config["port"]),
        service_name=config["service_name"]
    )
    connection = oracledb.connect(
        user=config["user"],
        password=config["password"],
        dsn=dsn
    )
    return connection

def fetch_all_dict(query, config=None, params=None):
    try:
        with get_connection() as conn:
            with conn.cursor() as cursor:
                if params:
                    cursor.execute(query, params)
                else:
                    cursor.execute(query)
                columns = [col[0].lower() for col in cursor.description]
                rows = cursor.fetchall()
                return [{columns[i]: row[i] for i in range(len(columns))} for row in rows]
    except Exception as e:
        print(f"[QUERY ERROR] fetch_all_dict failed: {e}")
        return []

def fetch_one_dict(query, config=None, params=None):
    try:
        with get_connection() as conn:
            with conn.cursor() as cursor:
                if params:
                    cursor.execute(query, params)
                else:
                    cursor.execute(query)
                columns = [col[0].lower() for col in cursor.description]
                row = cursor.fetchone()
                return {columns[i]: row[i] for i in range(len(columns))} if row else None
    except Exception as e:
        print(f"[QUERY ERROR] fetch_one_dict failed: {e}")
        return None
