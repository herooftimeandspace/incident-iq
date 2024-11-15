import app.app as app
import app.config as config
import app.frequent_fliers as ff
import app.room_updates as room
import logging

if __name__ == "__main__":
    """Runs main(). If main returns True, starts the scheduler. If main
       returns False, logs an error and terminates the application.
    """
    import sys

    env_vars = config.init(sys.argv[1:])
    config.logger
    # For debugging / local dev, run the commands directly rather than
    # with the scheduler
    if env_vars["env"] in config.test_env_flags:
        logging.info(
            f"The '{config.env}' flag was passed from the command line. Running once."
        )
        try:
            ff.run(env_vars["env"])
            room.run(env_vars["env"])
        except KeyboardInterrupt:
            logging.warning(
                "One-time script execution halted by Keyboard Interrupt"
            )
    elif env_vars["env"] in config.prod_env_flags or env_vars["env"] is None:
        logging.info(
            f"Either the '{config.env}' flag was passed from the command line, or no flag was set. "
            "Starting scheduler."
        )
        app.main()
        try:
            config.scheduler.start()
        except KeyboardInterrupt:
            logging.warning(
                "Scheduled Jobs shut down due to Keyboard Interrupt."
            )
            config.scheduler.shutdown()
    else:
        logging.critical(f"Invalid flag '{config.env}' passed. Shutting down.")
