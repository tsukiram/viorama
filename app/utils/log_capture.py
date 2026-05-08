import sys
import os

class Tee(object):
    def __init__(self, name, mode, encoding='utf-8'):
        self.file = open(name, mode, encoding=encoding, buffering=1) # Line buffered
        self.stdout = sys.stdout
        self.stderr = sys.stderr
        sys.stdout = self
        sys.stderr = self

    def __del__(self):
        sys.stdout = self.stdout
        sys.stderr = self.stderr
        self.file.close()

    def write(self, data):
        try:
            self.file.write(data)
            self.stdout.write(data) # Write to original stdout as well
            self.flush()
        except Exception:
            pass # Prevent recursion or errors during write

    def flush(self):
        try:
            self.file.flush()
            self.stdout.flush()
        except Exception:
            pass

def setup_log_capture(app):
    """
    Redirects stdout and stderr to a log file in the instance folder or root.
    """
    log_file_path = os.path.join(app.root_path, '..', 'app.log')
    # Use 'a' for append mode
    sys.stdout = Tee(log_file_path, "a")
    sys.stderr = sys.stdout # Redirect stderr to the same Tee instance
    print(f"Log capture initialized. Writing to {log_file_path}")
