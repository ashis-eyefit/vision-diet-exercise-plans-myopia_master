import mysql.connector
from mysql.connector import Error
from dotenv import load_dotenv
import os

load_dotenv()

# Correct generator-style DB dependency
def get_db():
    try:
        connection = mysql.connector.connect(
            host=os.getenv("DB_HOST"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
            database=os.getenv("DB_NAME")
        )
        if connection.is_connected():
            yield connection  # yields control to the route function
    except Error as e:
        print("Error connecting to MySQL database:", e)
        raise e
    finally:
        # Finalizer must run **after** request is done
        try:
            if connection.is_connected():
                connection.close()
        except:
            pass
