import app.config as config
import app.frequent_fliers as ff


def main():
    """Configures the scheduler to run jobs. Interval jobs are configured with
      initial defaults, but automatically adapt based on run-time per job.
      Cron jobs are scheduled to run daily with a longer lookback to catch
      any data that was not synced.

    Returns:
        bool: Returns True if main successfully initialized and scheduled jobs,
              False if not.
    """
    config.scheduler.add_job(
        ff.run,
        "cron",
        month="*",  # Any month
        day="1",  # First day
        hour="4",  # 4AM
        id="create_ff_report_cron",
    )

    return True
