from notifications.utils import send_push_notification, send_email, send_notification
from datetime import datetime, timedelta
from contextlib import contextmanager
import mysql.connector
from mysql.connector import Error
from dotenv import load_dotenv
import os
load_dotenv()


@contextmanager
def get_db_connection():
    conn = mysql.connector.connect(
            host=os.getenv("DB_HOST"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
            database=os.getenv("DB_NAME")
        )
    try:
        yield conn
    finally:
        conn.close()
    


def send_feedback_reminder_if_due():

    today = datetime.now()
    today_str = today.strftime('%Y-%m-%d %H:%M:%S')

    with get_db_connection() as db:
        cursor = db.cursor(dictionary=True)

    

        # 1. Find users whose plan started >= 14 days ago and not filled feedback
        cursor.execute("""
            SELECT fq.user_id, fq.plan_id, fq.plan_start_date,
                fq.feedback_submitted, fq.last_reminder_sent,
                un.preferred_time, un.frequency, un.preferred_channel
            FROM feedback_queue fq
            JOIN user_notification_settings un ON fq.user_id = un.user_id
            WHERE fq.feedback_submitted = 0
            AND DATEDIFF(CURDATE(), fq.plan_start_date) >= 13
        """)
        users = cursor.fetchall()

        for user in users:
            user_id = user['user_id']
            last_sent = user['last_reminder_sent']
            frequency = user['frequency'] or 'daily'

            # Compute gap for next reminder
            interval_days = 2  # we send every 2 days
            if last_sent:
                days_since_last = (today.date() - last_sent).days

                if days_since_last < interval_days:
                    continue  # Not due yet


            # All checks passed, send the reminder
            message = "Please fill your feedback for the last days vision care plan."
            if user['preferred_channel']:
                channel = user['preferred_channel']
            else:
                channel = "push"
            send_notification(user_id, message, channel)

            # Log and update
            cursor.execute("""
                INSERT INTO notification_log (user_id, notification_type, sent_at)
                VALUES (%s, %s, %s)
            """, (user_id, 'feedback_reminder', today_str))

            cursor.execute("""
                UPDATE feedback_queue
                SET last_reminder_sent = %s
                WHERE user_id = %s
            """, (today_str, user_id))
        


        db.commit()
        cursor.close()
        db.close()

