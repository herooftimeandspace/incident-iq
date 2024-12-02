import logging
import os
from pathlib import Path

import app.config as config
import app.frequent_fliers as ff
import app.variables as app_vars

parent_dir = str(Path(__file__).parent.parent)
cwd = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
log_location = os.path.join(parent_dir, app_vars.log_location)
logger = logging.getLogger(__name__)


def main(env) -> bool:
    """Configures the scheduler to run jobs. Interval jobs are configured with
      initial defaults, but automatically adapt based on run-time per job.
      Cron jobs are scheduled to run daily with a longer lookback to catch
      any data that was not synced.

    Returns:
        bool: Returns True if main successfully initialized and scheduled jobs,
              False if not.
    """
    try:
        if env in config.stage_env_flags:
            config.scheduler.add_job(
                ff.run,
                "cron",
                args=[env],
                month="*",  # Any month
                day="*",  # Any day
                hour="*",  # Any hour
                minute="13",  # at the 13th minute
                id="create_ff_report_cron_stage",
            )
            return True
        elif env in config.prod_env_flags:
            config.scheduler.add_job(
                ff.run,
                "cron",
                args=[env],
                month="*",  # Any month
                day="1",  # First day
                hour="4",  # 4AM
                id="create_ff_report_cron_prod",
            )
            return True
        else:
            return False

    except Exception as e:
        logging.ERROR(e)
        return False
