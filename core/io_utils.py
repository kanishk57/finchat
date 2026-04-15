from contextlib import contextmanager
import os
import sys


@contextmanager
def suppress_stdout_stderr():
    """Temporarily redirect stdout/stderr to devnull for noisy model loads."""
    with open(os.devnull, 'w') as fnull:
        old_stdout = sys.stdout
        old_stderr = sys.stderr
        sys.stdout = fnull
        sys.stderr = fnull
        try:
            yield
        finally:
            sys.stdout = old_stdout
            sys.stderr = old_stderr
