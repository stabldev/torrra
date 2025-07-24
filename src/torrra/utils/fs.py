import os
import sys


def get_resource_path(relative_path: str):
    if hasattr(sys, "_MEIPASS"):
        # running in a pyinstaller bundle
        # resources are typically placed under _MEIPASS/torrra/
        _path = getattr(sys, "_MEIPASS")
        return os.path.join(_path, "torrra", relative_path)
    else:
        # running in a dev environment
        package_root_dir = os.path.dirname(os.path.dirname(__file__))
        return os.path.join(package_root_dir, relative_path)
