import logging 

class ColoredLevelFormatter(logging.Formatter):
    COLOR_CODE = {
        'WARNING':  "\x1b[31m",
    }

    def format(self, record):
        levelname = record.levelname
        levelname_color = self.COLOR_CODE.get(levelname, "")
        reset_color = "\x1b[0m"
        log_msg = super().format(record)
        colored_log_msg = f"{levelname_color}{log_msg}{reset_color}"
        return colored_log_msg
