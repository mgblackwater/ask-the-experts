"""Exclusive locks on an open file, on macOS, Linux and Windows.

roundtable_server.py and roundtable_log.py both rewrite transcript files; they take this lock
so a page action and a moderator write never interleave.
"""
import os
import time

if os.name == "nt":
    import msvcrt

    def lock(f):
        """Block until we hold an exclusive lock on byte 0 of the open file."""
        while True:
            try:
                f.seek(0)
                msvcrt.locking(f.fileno(), msvcrt.LK_NBLCK, 1)
                return
            except OSError:
                time.sleep(0.05)

    def unlock(f):
        try:
            f.seek(0)
            msvcrt.locking(f.fileno(), msvcrt.LK_UNLCK, 1)
        except OSError:
            pass
else:
    import fcntl

    def lock(f):
        fcntl.flock(f, fcntl.LOCK_EX)

    def unlock(f):
        fcntl.flock(f, fcntl.LOCK_UN)
