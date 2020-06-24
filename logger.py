import os
import sys
import inspect
import logging.config

"""
Logger utility for debugging. 

Example usage:
    logger.Logger.log_info("test")
"""


class Color:
    PURPLE = "\033[95m"
    CYAN = "\033[96m"
    DARKCYAN = "\033[36m"
    BLUE = "\033[94m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    BOLD = "\033[1m"
    UNDERLINE = "\033[4m"
    END = "\033[0m"


DEFAULT_LOGGING = {
    "version": 1,
    "formatters": {
        "standard": {
            "format": Color.RED
            + "%(asctime)s,%(msecs)d"
            + Color.END
            + Color.PURPLE
            + " %(levelname)-8s"
            + Color.END
            + " %(message)s",
            "datefmt": "%Y-%m-%d:%H:%M:%S",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "standard",
            "level": "DEBUG",
            "stream": sys.stdout,
        }
        # 'file':     {'class': 'logging.FileHandler',
        #              'formatter': "standard",
        #              'level': 'DEBUG',
        #              'filename': 'live_detector.log','mode': 'w'}
    },
    "loggers": {
        __name__: {"level": "INFO", "handlers": ["console"], "propagate": False,},
    },
}


class Logger:
    def __init__(self, logging_config=DEFAULT_LOGGING):
        logging.config.dictConfig(logging_config)

        self.MAX_FILENAME_LENGTH = 0

        self.root_folder = os.path.dirname(
            os.path.dirname(inspect.currentframe().f_code.co_filename)
        )

    def _log_function(
        self, func, msg: str, header=None, frame=None, traceback_length=5
    ) -> str:
        """
        Internal colored logging function.
        """
        if not frame:
            frame = inspect.currentframe().f_back

        file_name = os.path.basename(frame.f_code.co_filename)
        line_no = str(frame.f_lineno)

        caller = ""

        for i in range(traceback_length):
            if frame is None:
                break

            temp_folder_name = os.path.dirname(frame.f_code.co_filename)

            if self.root_folder == temp_folder_name:
                caller = "(" + frame.f_code.co_name + ") " + caller

                frame = frame.f_back
            else:
                continue

        if caller:
            msg = Color.GREEN + caller + Color.END + msg

        if header:
            msg = Color.YELLOW + header + Color.END + " " + msg

        filename_display = " [" + file_name + ":" + line_no + "] "
        if len(filename_display) > self.MAX_FILENAME_LENGTH:
            self.MAX_FILENAME_LENGTH = len(filename_display)

        msg = (
            Color.CYAN
            + filename_display.ljust(self.MAX_FILENAME_LENGTH)
            + Color.END
            + msg
        )

        func(msg)
        return msg

    @classmethod
    def log_info(
        cls, msg: str, header=None, frame=None, traceback_length: int = 5
    ) -> str:
        """
        Logs info
        """
        log = logging.getLogger(__name__)

        if frame:
            frame = frame.f_back
        else:
            frame = inspect.currentframe().f_back

        return cls()._log_function(log.info, str(msg), header, frame, traceback_length)

    @classmethod
    def log_error(
        cls, msg: str, header=None, frame=None, traceback_length: int = 5
    ) -> str:
        """
        Logs errors
        """
        log = logging.getLogger(__name__)
        if frame:
            frame = frame.f_back
        else:
            frame = inspect.currentframe().f_back

        return cls()._log_function(log.error, str(msg), header, frame, traceback_length)

    @classmethod
    def print_function_call(cls, params=None, header="") -> str:
        """
        Prints function calls and details associated with the call
        """
        frame = inspect.currentframe().f_back

        if params:
            return cls().log_info(
                "Called "
                + inspect.getmodule(frame).__name__
                + "."
                + frame.f_code.co_name
                + " with parameters: "
                + str(params),
                header,
                frame,
            )
        else:
            return cls().log_info(
                "Called "
                + inspect.getmodule(frame).__name__
                + "."
                + frame.f_code.co_name,
                header,
                frame,
            )
