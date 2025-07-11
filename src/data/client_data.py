import os
from dotenv import load_dotenv
from mysql.connector import connect, Error

# 👇 Absolute load to make sure .env is read no matter what
env_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.env"))
load_dotenv(env_path)

def get_db():
    try:
        print("[DEBUG] CONNECTING TO:", os.getenv("DB_HOST"), os.getenv("DB_PORT"))  # 🔍 log port
        connection = connect(
            host=os.getenv("DB_HOST"),
            port=int(os.getenv("DB_PORT")),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
            database=os.getenv("DB_NAME")
        )
        yield connection
    except Error as e:
        print("❌ Database connection error:", e)
        raise e
    finally:
        if connection and connection.is_connected():
            connection.close()
