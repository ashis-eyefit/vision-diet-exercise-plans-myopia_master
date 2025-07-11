from mysql.connector import connect, Error
from dotenv import load_dotenv, dotenv_values
import os

load_dotenv()

env_values = dotenv_values(".env")
for k, v in env_values.items():
    os.environ[k] = v
def get_db():
    connection = None
    try:
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
with open(".env", "r") as f:
    print("🔎 Raw .env contents:\n", f.read())

import os
print("[DEBUG] os.getenv('DB_HOST'):", os.getenv("DB_HOST"))
print("[DEBUG] os.environ['DB_HOST']:", os.environ.get("DB_HOST"))