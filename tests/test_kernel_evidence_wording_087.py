from pathlib import Path

APP = (Path(__file__).resolve().parents[1] / "jatayu_driver_assistant" / "app.py").read_text()


def test_empty_match_result_is_not_presented_as_proof_of_device_health():
    assert "no matching firmware-failure messages were found in the checked current-boot kernel log" in APP
    assert "No matching message is not proof that hardware works" in APP


def test_kernel_log_scope_is_explicit_in_ui_and_export():
    assert "last 4,000 records" in APP
    assert "current_boot_kernel_journal_last_4000_records" in APP
    assert "kernel_evidence_interpretation" in APP


def test_hindi_evidence_wording_warns_against_overclaiming():
    assert "जाँचे गए लॉग में संदेश न मिलना" in APP
    assert "इंस्टॉलेशन बंद है" in APP


def test_no_match_table_label_is_scoped_to_checked_logs():
    assert "No match in checked logs" in APP
    assert "जाँचे गए लॉग में मेल नहीं मिला" in APP
