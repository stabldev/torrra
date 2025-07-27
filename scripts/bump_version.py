import re
import sys
from pathlib import Path

NEW_VERSION = sys.argv[1] if len(sys.argv) > 1 else None
if not NEW_VERSION:
    print("usage: bump_version.py <new_version>")
    sys.exit(1)

files_to_update = {
    "pyproject.toml": {
        "pattern": r'^(version\s*=\s*)".*?"$',
        "replacement": r'\g<1>"' + NEW_VERSION + '"',
    },
    "docs/conf.py": {
        "pattern": r'^(release\s*=\s*)".*?"$',
        "replacement": r'\g<1>"' + NEW_VERSION + '"',
    },
    "Dockerfile": {
        "pattern": r"^(ENV TORRRA_VERSION=).*?$",
        "replacement": r"\g<1>" + NEW_VERSION,
    },
}

for file, cfg in files_to_update.items():
    path = Path(file)
    if not path.exists():
        print(f'skipping "{file}" (not found)')
        continue

    pattern = cfg["pattern"]
    replacement = cfg["replacement"]

    content = path.read_text()
    new_content = re.sub(pattern, replacement, content, flags=re.MULTILINE)
    path.write_text(new_content)
    print(f"updated {file}")
