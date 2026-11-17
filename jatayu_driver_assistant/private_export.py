"""Local JSON exports with privacy filtering and private Unix file permissions."""
import os
import re
from pathlib import Path

_MAC = re.compile(r'(?<![0-9a-fA-F])(?:[0-9a-fA-F]{2}:){5}[0-9a-fA-F]{2}(?![0-9a-fA-F])')
_UUID = re.compile(r'(?<![0-9a-fA-F])\b[0-9a-fA-F]{8}-(?:[0-9a-fA-F]{4}-){3}[0-9a-fA-F]{12}\b(?![0-9a-fA-F])')
_HOME = re.compile(r'/home/[^/\s\"\\]+')


def redact_report(text):
    """Best-effort redaction, not a guarantee of anonymization."""
    return _HOME.sub('/home/[redacted]', _UUID.sub('[redacted-uuid]',
        _MAC.sub('[redacted-mac]', text)))


def write_private_json(filename, content):
    """Never follow symlinks; set restrictive permissions even on replacements."""
    path = Path(filename)
    flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC | getattr(os, 'O_NOFOLLOW', 0)
    fd = os.open(path, flags, 0o600)
    with os.fdopen(fd, 'w', encoding='utf-8') as output:
        os.fchmod(output.fileno(), 0o600)
        output.write(redact_report(content))
