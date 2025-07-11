import os
import mysql.connector
from mysql.connector import Error
from dotenv import load_dotenv, dotenv_values

load_dotenv()
env_values = dotenv_values(".env")
for k, v in env_values.items():
    os.environ[k] = v

def get_db():
    connection = None
    try:
        connection = mysql.connector.connect(
            host=os.getenv("DB_HOST"),
            port=int(os.getenv("DB_PORT")),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
            database=os.getenv("DB_NAME")
        )
        if connection.is_connected():
            return connection
    except Error as e:
        print("Error connecting to MySQL database:", e)
        raise e
   