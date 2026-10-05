import pyodbc
from contextlib import contextmanager
import os
from dotenv import load_dotenv

load_dotenv()

# Database connection configuration (can be overridden via environment variables)
DB_DRIVER = os.getenv("DB_DRIVER", "{ODBC Driver 18 for SQL Server}")
DB_SERVER = os.getenv("DB_SERVER", "localhost\\SQLEXPRESS")
DB_NAME = os.getenv("DB_NAME", "ITAssets")
DB_TRUSTED = os.getenv("DB_TRUSTED", "yes")
DB_TRUST_CERT = os.getenv("DB_TRUST_CERT", "yes")

CONNECTION_STRING = (
    f"DRIVER={DB_DRIVER};"
    f"SERVER={DB_SERVER};"
    f"DATABASE={DB_NAME};"
    f"Trusted_Connection={DB_TRUSTED};"
    f"TrustServerCertificate={DB_TRUST_CERT};"
)

def get_connection():
    """Returns a raw pyodbc connection to the SQL Server database."""
    return pyodbc.connect(CONNECTION_STRING)

@contextmanager
def get_db_cursor(commit: bool = False):
    """
    Context manager for safe database cursor handling.
    Automatically closes cursor and connection when done.
    If commit=True, commits transaction before closing.
    """
    conn = get_connection()
    cursor = conn.cursor()
    try:
        yield cursor
        if commit:
            conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT @@VERSION")
        row = cursor.fetchone()
        print("Database connection successful!")
        print("SQL Server Version:", row[0].split("\n")[0])
        
        # Test query to check tables
        cursor.execute("SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_TYPE='BASE TABLE'")
        tables = [t[0] for t in cursor.fetchall()]
        print("Found tables:", tables)
        
        cursor.close()
        conn.close()
    except Exception as exc:
        print("Failed to connect to database:", exc)
