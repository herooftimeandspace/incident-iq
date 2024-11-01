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
    if env_vars["env"] in [
        "-d",
        "-debug",
        "-dev",
        "--debug",
        "--dev",
        "-s",
        "-staging",
        "--staging",
        "-p",
        "-prod",
        "--prod",
    ]:
        logging.info(
            f"The {config.env} flag was passed from the command line. Running once."
        )
        # ff.run()
        room.run()
    else:
        app.main()
        try:
            config.scheduler.start()
        except KeyboardInterrupt:
            logging.warning(
                "Scheduled Jobs shut down due to Keyboard Interrupt."
            )
            config.scheduler.shutdown()
