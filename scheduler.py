from apscheduler.schedulers.background import BackgroundScheduler
from notifications.send_feedback_reminders import send_feedback_reminder_if_due
from notifications.send_feedback_reminders import get_db_connection



def start_scheduler():
    scheduler = BackgroundScheduler()
    scheduler.add_job(send_feedback_reminder_if_due, 'cron', hour = 10, minute = 33)
    scheduler.start()
    print("✅ Scheduler started: reminder job registered.")
    return scheduler

