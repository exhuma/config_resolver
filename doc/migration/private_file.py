"""
Refuse config files others can read or change.
"""

import os
import stat


def check_private(path):
    info = os.stat(path)
    if info.st_uid not in (os.getuid(), 0):
        raise PermissionError(
            f"{path} must be owned by you or root"
        )
    if info.st_mode & (
        stat.S_IRWXG | stat.S_IRWXO
    ):
        mode = stat.filemode(info.st_mode)
        raise PermissionError(
            f"{path} is {mode}, expected 0600"
        )
