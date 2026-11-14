from types import SimpleNamespace
from jatayu_driver_assistant.device_details import detail_fields, package_state_text


def test_hindi_details_translate_values():
    hint = SimpleNamespace(address='0000:00:02.0', vendor_id='0x8086', device_id='0x22b1',
        class_id='0x030000', driver='i915', category='graphics', package_hint=None,
        confidence='insufficient', explanation='No conservative package mapping for this PCI device.')
    fields = dict(detail_fields(hint, True, 'जाँच नहीं हुई'))
    assert fields['श्रेणी'] == 'ग्राफिक्स'
    assert fields['विश्वास'] == 'अपर्याप्त'
    assert 'PCI' in fields['व्याख्या']


def test_package_status_never_authorizes_installation():
    assert 'does not prove' in package_state_text('installed', '20250410-2', False)
    assert 'सिद्ध नहीं' in package_state_text('not_installed', '', True)
    assert 'could not be verified' in package_state_text('unknown', '', False)
