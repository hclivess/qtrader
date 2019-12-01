import logging.handlers


class Logger:
    def __init__(self, filename="log.log", level_string="INFO"):

        if level_string == "DEBUG":
            self.level = logging.DEBUG
        elif level_string == "INFO":
            self.level = logging.INFO
        elif level_string == "WARNING":
            self.level = logging.WARNING
        elif level_string == "ERROR":
            self.level = logging.ERROR
        else:
            self.level = logging.NOTSET

        self.logger = self.define_logger(filename)

        self.logger.info(f"Logging set to {self.level}, {level_string}")

    def define_logger(self, filename):
        logFormatter = logging.Formatter("%(asctime)s [%(threadName)-12.12s] [%(levelname)-5.5s]  %(message)s")
        rootLogger = logging.getLogger()
        rootLogger.setLevel(self.level)
        fileHandler = logging.FileHandler(filename)
        fileHandler.setFormatter(logFormatter)
        rootLogger.addHandler(fileHandler)
        consoleHandler = logging.StreamHandler()
        consoleHandler.setFormatter(logFormatter)
        rootLogger.addHandler(consoleHandler)
        return rootLogger
