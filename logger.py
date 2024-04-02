from datetime import datetime


class Logger:
    def __init__(self, db):
        self.db = db

    def save_log(self, error):
        description = {
            "type": type(error).__name__,
            "message": str(error),
            "line": error.__traceback__.tb_lineno,
            "file": error.__traceback__.tb_frame.f_code.co_filename
        }

        self.db.add_data_to_table('logs', datetime.now().strftime('%Y-%m-%d %H:%M:%S').replace(' ', '|'), description)
