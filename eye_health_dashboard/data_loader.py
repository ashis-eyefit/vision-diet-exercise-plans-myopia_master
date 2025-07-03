from apscheduler.schedulers.background import BackgroundScheduler
import pymysql
import datetime
import time

def finalize_logs():
    print(f"Running finalization job at {datetime.datetime.now()}")

    connection = pymysql.connect(
        host="localhost",
        user="root",
        ….
        ….
    )

    try:
        with connection.cursor() as cursor:
            # Step 1: Finalize rows that are fully completed
            finalize_complete_query = """
            UPDATE user_daily_logs
            SET is_finalized = 1
            WHERE log_date = CURDATE()
              AND is_finalized = 0
              AND exercise_1_done = 1
              AND exercise_2_done = 1
              AND exercise_3_done = 1
              AND breakfast_done = 1
              AND lunch_done = 1
              AND snack_done = 1
              AND dinner_done = 1
              AND hydration_done = 1
            """
            cursor.execute(finalize_complete_query)

            # Step 2: Finalize all remaining (incomplete) logs with NULL → 0 fallback
            finalize_remaining_query = """
            UPDATE user_daily_logs
            SET
                exercise_1_done = IFNULL(exercise_1_done, 0),
                exercise_2_done = IFNULL(exercise_2_done, 0),
                exercise_3_done = IFNULL(exercise_3_done, 0),
                breakfast_done = IFNULL(breakfast_done, 0),
                lunch_done = IFNULL(lunch_done, 0),
                snack_done = IFNULL(snack_done, 0),
                dinner_done = IFNULL(dinner_done, 0),
                hydration_done = IFNULL(hydration_done, 0),
                is_finalized = 1
            WHERE
                log_date = CURDATE()
                AND is_finalized = 0
            """
            cursor.execute(finalize_remaining_query)

        connection.commit()
        print("Finalization job completed.")
    except Exception as e:
        print(f"Error during finalization: {e}")
    finally:
        connection.close()


# Start scheduler
scheduler = BackgroundScheduler()
scheduler.add_job(finalize_logs, 'cron', hour=23, minute=59)
scheduler.start()

# Keeping the script running 
try:
    while True:
        time.sleep(60)
except (KeyboardInterrupt, SystemExit):
    scheduler.shutdown()
