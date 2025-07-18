import os
import sys


def get_resource_path(relative_path: str):
    if hasattr(sys, "_MEIPASS"):
        # running in a pyinstaller bundle
        # resources are typically placed under _MEIPASS/torrra/
        return os.path.join(sys._MEIPASS, "torrra", relative_path)  # pyright: ignore
    else:
        # running in a dev environment
        package_root_dir = os.path.dirname(os.path.dirname(__file__))
        return os.path.join(package_root_dir, relative_path)
