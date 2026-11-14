"""Presentation-only localized PCI details; no hardware matching decisions."""

CATEGORIES = {
    'graphics': ('Graphics', 'ग्राफिक्स'), 'network': ('Network', 'नेटवर्क'),
    'storage': ('Storage', 'स्टोरेज'), 'multimedia': ('Multimedia', 'मल्टीमीडिया'),
    'controller': ('Controller', 'कंट्रोलर'), 'other': ('Other', 'अन्य'),
}
CONFIDENCE = {'low': ('Low (unverified)', 'कम (असत्यापित)'),
              'insufficient': ('Insufficient', 'अपर्याप्त')}
EXPLANATIONS = {
    'No conservative package mapping for this PCI device.': (
        'No conservative package mapping for this PCI device.',
        'इस PCI डिवाइस के लिए कोई विश्वसनीय पैकेज मैपिंग उपलब्ध नहीं है।'),
    'Vendor/class family suggests a possible firmware package; device-level match and firmware failure are not verified.': (
        'Vendor/class suggests a possible package; device match and firmware failure remain unverified.',
        'विक्रेता/श्रेणी से एक संभावित पैकेज का संकेत मिलता है; डिवाइस मिलान और फ़र्मवेयर विफलता सत्यापित नहीं हैं।'),
}


def detail_fields(hint, hindi, evidence):
    """Return display-only label/value pairs. Preserve identifiers verbatim."""
    def t(en, hi):
        return hi if hindi else en
    explanation = EXPLANATIONS.get(hint.explanation)
    return [
        (t('PCI address', 'PCI पता'), hint.address),
        (t('Vendor ID', 'विक्रेता ID'), hint.vendor_id),
        (t('Device ID', 'डिवाइस ID'), hint.device_id),
        (t('Class ID', 'क्लास ID'), hint.class_id),
        (t('Kernel driver', 'कर्नेल ड्राइवर'), hint.driver or '—'),
        (t('Category', 'श्रेणी'), CATEGORIES.get(hint.category, CATEGORIES['other'])[int(hindi)]),
        (t('Possible package (unverified)', 'संभावित पैकेज (असत्यापित)'), hint.package_hint or '—'),
        (t('Confidence', 'विश्वास'), CONFIDENCE.get(hint.confidence, CONFIDENCE['insufficient'])[int(hindi)]),
        (t('Kernel evidence', 'कर्नेल प्रमाण'), evidence),
        (t('Explanation', 'व्याख्या'), (explanation[int(hindi)] if explanation else
          t('No verified device-to-package mapping.', 'डिवाइस से पैकेज का सत्यापित मिलान उपलब्ध नहीं है।'))),
    ]


def package_state_text(state, version, hindi):
    """Installed status is informational, never installation approval."""
    if state == 'installed':
        prefix = 'पैकेज स्थापित है' if hindi else 'Package installed'
        return f'{prefix}: {version}\n' + ('इससे हार्डवेयर की आवश्यकता सिद्ध नहीं होती।' if hindi
                                             else 'This does not prove the hardware needs this package.')
    if state == 'not_installed':
        return ('पैकेज स्थापित नहीं है। इससे उसकी आवश्यकता सिद्ध नहीं होती।' if hindi else
                'Package not installed. This does not prove it is needed.')
    return ('पैकेज की स्थिति सत्यापित नहीं हो सकी।' if hindi else 'Package status could not be verified.')
