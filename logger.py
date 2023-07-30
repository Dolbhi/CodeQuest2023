import time


class Logger:
    def __init__(self, fileName: str):
        self.fileName = fileName
        self.logFile = open(fileName, mode="a")
        self.log("Start of log")

    def log(self, log: str):
        now = time.localtime()
        self.logFile.write(f"\n[{now[3]}:{now[4]}:{now[5]}]: " + log)

    def close(self):
        self.log("End of log\n")
        self.logFile.close()
