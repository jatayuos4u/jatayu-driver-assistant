import pytest
from types import SimpleNamespace
from jatayu_driver_assistant.apt_analysis import analyze_output, simulate_package
from jatayu_driver_assistant.recommendations import ALLOWED

PACKAGE = sorted(ALLOWED)[0]

def test_success_needs_review():
    r = analyze_output(PACKAGE, f'Inst {PACKAGE} (1.0 Debian:13/stable [all])\nConf {PACKAGE} (1.0)', 0)
    assert r.status == 'review_required' and not r.installation_enabled

def test_removal_blocked():
    r = analyze_output(PACKAGE, f'Inst {PACKAGE} (1.0)\nRemv linux-image-amd64 (1.0)', 0)
    assert r.status == 'blocked'

def test_unallowlisted_dependency_blocked():
    assert analyze_output(PACKAGE, f'Inst {PACKAGE} (1.0)\nInst unknown-package (1.0)', 0).status == 'blocked'

def test_failure_blocked():
    assert analyze_output(PACKAGE, 'E: no candidate', 100).status == 'blocked'

def test_no_operations_blocked():
    assert analyze_output(PACKAGE, '0 upgraded, 0 newly installed', 0).status == 'blocked'

def test_oversize_blocked():
    assert analyze_output(PACKAGE, 'x'*70000, 0).status == 'blocked'

def test_reject_invalid_package():
    with pytest.raises(ValueError):
        simulate_package('bad; rm -rf /')

def test_runner_fixed_arguments():
    def fake(cmd, **kwargs):
        assert cmd == ['/usr/bin/apt-get', '-s', '-o', 'Debug::NoLocking=1', 'install', '--', PACKAGE]
        assert kwargs['shell'] is False and kwargs['timeout'] == 15
        return SimpleNamespace(stdout=f'Inst {PACKAGE} (1.0)', stderr='', returncode=0)
    assert simulate_package(PACKAGE, runner=fake).status == 'review_required'

def test_timeout_blocked():
    import subprocess
    def fake(*args, **kwargs):
        raise subprocess.TimeoutExpired('apt', 15)
    assert simulate_package(PACKAGE, runner=fake).status == 'blocked'
