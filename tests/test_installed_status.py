from types import SimpleNamespace
from jatayu_driver_assistant.apt_analysis import installed_version, inspect_package
from jatayu_driver_assistant.recommendations import ALLOWED

P = sorted(ALLOWED)[0]

def dpkg_ok(cmd, **kw):
    assert cmd[:2] == ['/usr/bin/dpkg-query', '-W']
    assert kw['shell'] is False
    return SimpleNamespace(returncode=0, stdout='install ok installed\t20250410-2\n')

def apt_empty(cmd, **kw):
    return SimpleNamespace(returncode=0, stdout='0 upgraded, 0 newly installed\n', stderr='')

def test_installed_version():
    assert installed_version(P, runner=dpkg_ok) == ('installed', '20250410-2')

def test_installed_noop():
    r = inspect_package(P, runner=apt_empty, dpkg_runner=dpkg_ok)
    assert r['status'] == 'already_installed'
    assert r['installed_version'] == '20250410-2'
    assert r['installation_enabled'] is False

def test_missing_package_still_blocked_without_operations():
    def absent(*a, **kw):
        return SimpleNamespace(returncode=1, stdout='')
    r = inspect_package(P, runner=apt_empty, dpkg_runner=absent)
    assert r['status'] == 'blocked'
    assert r['installed_state'] == 'not_installed'

def test_unknown_package_rejected():
    import pytest
    with pytest.raises(ValueError):
        installed_version('invalid;command')
