"""Focused regressions for confidentiality, shell avoidance, and output bounds."""
import os
import stat
import subprocess
import sys
from pathlib import Path
import pytest
from jatayu_driver_assistant.safe_process import bounded_run
from jatayu_driver_assistant.private_export import write_private_json, redact_report

def test_no_shell():
    with pytest.raises(ValueError):
        bounded_run(['echo', 'bad'], shell=True)

def test_output_limit():
    p = bounded_run([sys.executable, '-c', 'print("A"*100000)'], timeout=3, max_output_bytes=4096)
    assert p.returncode == 125
    assert 'limit' in p.stderr.lower()

def test_capture_success():
    p = bounded_run([sys.executable, '-c', 'import sys;print("ok");sys.stderr.write("info")'])
    assert p.returncode == 0
    assert p.stdout.strip() == 'ok' and p.stderr == 'info'

def test_timeout_kills_child():
    with pytest.raises(subprocess.TimeoutExpired):
        bounded_run([sys.executable, '-c', 'import time;time.sleep(3)'], timeout=0.1)

def test_private_export(tmp_path):
    path = tmp_path / 'report.json'
    write_private_json(path, '{"mac":"aa:bb:cc:dd:ee:ff","path":"/home/example/data","id":"550e8400-e29b-41d4-a716-446655440000"}')
    assert stat.S_IMODE(path.stat().st_mode) == 0o600
    data = path.read_text()
    assert 'aa:bb:cc' not in data and '/home/example' not in data and '550e8400' not in data

def test_export_rejects_symlink(tmp_path):
    target = tmp_path / 'target'
    target.write_text('do not overwrite')
    link = tmp_path / 'link.json'
    link.symlink_to(target)
    with pytest.raises(OSError):
        write_private_json(link, '{}')
    assert target.read_text() == 'do not overwrite'

def test_existing_export_becomes_private(tmp_path):
    p = tmp_path / 'report.json'
    p.write_text('old')
    p.chmod(0o644)
    write_private_json(p, '{}')
    assert stat.S_IMODE(p.stat().st_mode) == 0o600

def test_source_gui_forces_plain_text():
    app = (Path(__file__).resolve().parents[1] / 'jatayu_driver_assistant/app.py').read_text()
    assert 'widget.setTextFormat(Qt.TextFormat.PlainText)' in app
    assert 'self.setTextFormat(Qt.TextFormat.PlainText)' in app

def test_no_automatic_release_write_workflows():
    workflows = Path(__file__).resolve().parents[1] / '.github/workflows'
    for yml in workflows.glob('*.yml'):
        content = yml.read_text()
        # A scoped one-off release publisher is allowed only during a
        # reviewed release. Remove it after publishing.
        if yml.name == 'publish-v1.2.4.yml':
            assert "paths:" in content
            assert "- '.github/workflows/publish-v1.2.4.yml'" in content
            assert 'gh release create v1.2.4' in content
            continue
        assert 'contents: write' not in content
        assert 'gh release create' not in content
