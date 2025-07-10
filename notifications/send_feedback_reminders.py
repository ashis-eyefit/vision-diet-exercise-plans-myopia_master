from notifications.utils import send_push_notification, send_email, send_notification
from datetime import datetime
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


def update_feedback_queue_from_feedback():
    with get_db_connection() as db:
        cursor = db.cursor(dictionary=True)

        # Fetch latest feedback entries
        cursor.execute("""
            SELECT f.user_id, f.session_id, MAX(f.feedback_number) as max_feedback,
                   MAX(f.created_at) as latest_feedback_date
            FROM feedback f
            GROUP BY f.user_id, f.session_id
        """)
        feedback_entries = cursor.fetchall()

        for entry in feedback_entries:
            user_id = entry['user_id']
            session_id = entry['session_id']
            feedback_number = entry['max_feedback']
            created_at = entry['latest_feedback_date']

            # ✅ Ensure user has default notification settings
            cursor.execute("""
                INSERT IGNORE INTO user_notification_settings 
                (user_id, preferred_channel, frequency, preferred_time)
                VALUES (%s, 'push', 'daily', '10:00')
            """, (user_id,))

            # ✅ Mark previous plan as submitted
            cursor.execute("""
                UPDATE feedback_queue
                SET feedback_submitted = 1
                WHERE user_id = %s AND feedback_number = %s
            """, (user_id, feedback_number - 1))

            # ✅ Insert current plan if not exists
            cursor.execute("""
                SELECT 1 FROM feedback_queue
                WHERE user_id = %s AND session_id = %s
            """, (user_id, session_id))
            exists = cursor.fetchone()

            if not exists:
                cursor.execute("""
                    INSERT INTO feedback_queue (
                        user_id, session_id, feedback_number,
                        plan_start_date, feedback_submitted,
                        last_reminder_sent, reminder_count
                    ) VALUES (%s, %s, %s, %s, %s, NULL, 0)
                """, (
                    user_id, session_id, feedback_number,
                    created_at, 0
                ))

        db.commit()
        cursor.close()



def send_feedback_reminder_if_due():
    print("🔄 Triggered feedback reminder function")
    today = datetime.now()
    today_str = today.strftime('%Y-%m-%d %H:%M:%S')

    with get_db_connection() as db:
        cursor = db.cursor(dictionary=True)

        # Only get latest feedback_queue entry per user
        cursor.execute("""
            SELECT fq.user_id, fq.session_id, fq.feedback_number,
                fq.plan_start_date, fq.last_reminder_sent,
                fq.feedback_submitted, un.preferred_channel
            FROM feedback_queue fq
            JOIN user_notification_settings un ON fq.user_id = un.user_id
            WHERE fq.feedback_submitted = 0
            AND fq.feedback_number = (
                SELECT MAX(fq2.feedback_number)
                FROM feedback_queue fq2
                WHERE fq2.user_id = fq.user_id
            )
            AND TIMESTAMPDIFF(MINUTE, fq.plan_start_date, NOW()) >= 2
        """)


        users = cursor.fetchall()

        for user in users:
            user_id = user['user_id']
            last_sent = user['last_reminder_sent']
            channel = user['preferred_channel'] or "push"

            # Send every 2 days if due
            interval_minutes = 1
            if last_sent:
                minutes_since = (today - last_sent).total_seconds() / 60
                if minutes_since < interval_minutes:

                    continue

            message = "Please fill your feedback for the last vision care plan."
            send_notification(user_id, message, channel)

            # Log it
            cursor.execute("""
                INSERT INTO notification_log (user_id, notification_type, sent_at)
                VALUES (%s, %s, %s)
            """, (user_id, 'feedback_reminder', today_str))

            # Update reminder time
            cursor.execute("""
                UPDATE feedback_queue
                SET last_reminder_sent = %s, reminder_count = reminder_count + 1
                WHERE user_id = %s AND feedback_number = %s
            """, (today_str, user_id, user['feedback_number']))

        db.commit()
        cursor.close()
