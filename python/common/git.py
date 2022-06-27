import subprocess
from typing import Optional

_version = None


def fetch_version() -> Optional[str]:
    global _version
    if _version is None:
        cmd = ['git', 'rev-list', 'HEAD', '--count']
        try:
            _version = subprocess.run(cmd, stdout=subprocess.PIPE, text=True).stdout.strip()
        except Exception as ex:
            print(ex)
    return _version
