"""Jatayu Driver Assistant — polished, unprivileged KDE/Qt diagnostics."""
import json
import sys
import platform
from .private_export import write_private_json
from datetime import datetime, timezone
from pathlib import Path

from PySide6.QtCore import Qt, QThread, Signal, QSize, QUrl
from PySide6.QtGui import QColor, QFont, QIcon, QFontMetrics, QDesktopServices
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QComboBox, QLineEdit, QTableWidget, QTableWidgetItem,
    QHeaderView, QFileDialog, QMessageBox, QFrame, QStackedWidget,
    QAbstractItemView, QGraphicsDropShadowEffect, QProgressBar, QScrollArea,
    QSizePolicy, QDialog, QDialogButtonBox, QTextEdit,
)
from .scanner import scan_all, binding_state, summarize
from .diagnostics import analyze
from .firmware import inspect_firmware
from .recommendations import inspect_packages, preview_plan
from .i18n import tr
from .testing import run_scenario
from .live_tests import run_live_checks
from .transaction_foundation import create_plan, audit_record
from .backend_contract import RepairRequest
from .recommendations import ALLOWED
from .apt_analysis import inspect_package, installed_version
from .hardware_compat import inspect_pci, report_payload
from .evidence_engine import inspect_evidence
from .wifi_diagnostics import inspect_wifi
from .recommendation_view import build_advice, counts, physical_device


class ElidedLabel(QLabel):
    """Single-line device name that fits its allocated width without overlapping."""
    def __init__(self, text='', parent=None):
        super().__init__(parent)
        self.full_text = text
        self.setTextFormat(Qt.TextFormat.PlainText)
        self.setMinimumWidth(0)
        self.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)

    def setText(self, text):
        self.full_text = text
        self.setToolTip(text)
        self._fit_text()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._fit_text()

    def _fit_text(self):
        width = max(12, self.contentsRect().width() - 4)
        QLabel.setText(self, QFontMetrics(self.font()).elidedText(
            self.full_text, Qt.TextElideMode.ElideRight, width))


class ScanThread(QThread):
    complete = Signal(list)
    failed = Signal(str)

    def run(self):
        try:
            self.complete.emit(scan_all())
        except Exception as exc:
            self.failed.emit(str(exc))


class FirmwareThread(QThread):
    complete = Signal(list, str)
    def run(self):
        findings, note = inspect_firmware()
        self.complete.emit(findings, note)


class AptSimulationThread(QThread):
    complete = Signal(dict)
    def __init__(self, package):
        super().__init__()
        self.package = package
    def run(self):
        self.complete.emit(inspect_package(self.package))


class KernelEvidenceThread(QThread):
    """Read-only kernel evidence inspection off the GUI thread."""
    complete = Signal(list, str)
    failed = Signal(str)

    def __init__(self, hints):
        super().__init__()
        self.hints = list(hints)

    def run(self):
        try:
            findings, access = inspect_evidence(self.hints)
            self.complete.emit(findings, access)
        except Exception as exc:
            self.failed.emit(str(exc))


class WifiDiagnosticsThread(QThread):
    complete = Signal(dict)

    def run(self):
        self.complete.emit(inspect_wifi())


class PackageStatusThread(QThread):
    """Bounded, read-only dpkg lookup away from the Qt GUI thread."""
    complete = Signal(str, str)

    def __init__(self, package, parent=None):
        super().__init__(parent)
        self.package = package

    def run(self):
        try:
            state, version = installed_version(self.package)
            self.complete.emit(state, version or '')
        except Exception:
            self.complete.emit('unknown', '')


class Window(QMainWindow):
    def __init__(self):
        super().__init__()
        self.language = 'en'
        self.devices = []
        self.worker = None
        self.firmware_worker = None
        self.firmware_findings = []
        self.firmware_note = "Firmware evidence not scanned yet."
        self.page_index = 0
        self.setMinimumSize(920, 660)
        self.setWindowIcon(self.app_icon())
        self.resize(1260, 820)

        central = QWidget()
        self.setCentralWidget(central)
        outer = QHBoxLayout(central)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        self.sidebar = QFrame(objectName='sidebar')
        self.sidebar.setFixedWidth(242)
        side = QVBoxLayout(self.sidebar)
        side.setContentsMargins(18, 28, 18, 22)
        side.setSpacing(8)
        brand_row = QHBoxLayout()
        emblem = QLabel()
        emblem.setPixmap(self.app_icon().pixmap(44, 44))
        emblem.setObjectName('emblem')
        emblem.setFixedSize(44, 44)
        emblem.setAlignment(Qt.AlignmentFlag.AlignCenter)
        brand_row.addWidget(emblem)
        brand_text = QVBoxLayout()
        brand_text.setSpacing(1)
        brand_text.addWidget(self.label('JATAYU', 'brandName'))
        brand_text.addWidget(self.label('DRIVER ASSISTANT', 'brandSub'))
        brand_row.addLayout(brand_text)
        side.addLayout(brand_row)
        side.addSpacing(35)
        self.nav_label = self.label('', 'navSection')
        side.addWidget(self.nav_label)
        self.nav_buttons = []
        for icon, index in [('◫', 0), ('▤', 1), ('⚕', 2), ('▣', 3), ('?', 4), ('ⓘ', 5)]:
            btn = QPushButton()
            btn.setProperty('nav', True)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setMinimumHeight(48)
            btn.clicked.connect(lambda checked=False, i=index: self.navigate(i))
            side.addWidget(btn)
            self.nav_buttons.append((icon, btn))
        side.addStretch()
        self.side_info = QLabel()
        self.side_info.setWordWrap(True)
        self.side_info.setObjectName('sideInfo')
        side.addWidget(self.side_info)
        side.addSpacing(12)
        self.version = self.label('v1.2.4  •  BASIC', 'version')
        side.addWidget(self.version)
        outer.addWidget(self.sidebar)

        self.content = QFrame(objectName='content')
        content_layout = QVBoxLayout(self.content)
        content_layout.setContentsMargins(34, 26, 34, 22)
        content_layout.setSpacing(20)
        header = QHBoxLayout()
        header_title = QVBoxLayout()
        header_title.setSpacing(3)
        self.header_kicker = self.label('JATAYUOS  /  HARDWARE', 'kicker')
        self.header_title = self.label('', 'pageTitle')
        header_title.addWidget(self.header_kicker)
        header_title.addWidget(self.header_title)
        header.addLayout(header_title)
        header.addStretch()
        self.language_box = QComboBox()
        self.language_box.addItem('English', 'en')
        self.language_box.addItem('हिन्दी', 'hi')
        self.language_box.setMinimumWidth(118)
        self.language_box.currentIndexChanged.connect(self.change_language)
        header.addWidget(self.language_box, alignment=Qt.AlignmentFlag.AlignVCenter)
        content_layout.addLayout(header)

        self.stack = QStackedWidget()
        content_layout.addWidget(self.stack, 1)
        self.build_overview()
        self.build_devices()
        self.build_diagnostics()
        self.build_recommendations()
        self.build_help()
        self.build_about()
        outer.addWidget(self.content, 1)

        footer = QHBoxLayout()
        self.footer_status = self.label('', 'footer')
        footer.addWidget(self.footer_status)
        footer.addStretch()
        self.footer_version = self.label('JATAYUOS  •  1.2.4', 'footer')
        footer.addWidget(self.footer_version)
        content_layout.addLayout(footer)
        self.apply_theme()
        self.retranslate()
        self.navigate(0)
        self.scan()

    @staticmethod
    def label(text='', name=''):
        widget = QLabel(text)
        widget.setTextFormat(Qt.TextFormat.PlainText)
        widget.setTextFormat(Qt.TextFormat.PlainText)
        if name:
            widget.setObjectName(name)
        return widget

    @staticmethod
    def panel():
        frame = QFrame(objectName='panel')
        return frame

    def build_overview(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(18)
        hero = QFrame(objectName='hero')
        hero_layout = QHBoxLayout(hero)
        hero_layout.setContentsMargins(25, 22, 25, 22)
        hero_text = QVBoxLayout()
        hero_text.setSpacing(8)
        self.hero_badge = self.label('', 'heroBadge')
        self.hero_title = self.label('', 'heroTitle')
        self.hero_title.setWordWrap(True)
        self.hero_desc = self.label('', 'heroDesc')
        self.hero_desc.setWordWrap(True)
        hero_text.addWidget(self.hero_badge)
        hero_text.addWidget(self.hero_title)
        hero_text.addWidget(self.hero_desc)
        hero_layout.addLayout(hero_text, 1)
        self.scan_button = QPushButton()
        self.scan_button.setObjectName('primaryButton')
        self.scan_button.setMinimumHeight(46)
        self.scan_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.scan_button.clicked.connect(self.scan)
        hero_layout.addWidget(self.scan_button, alignment=Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(hero)

        metrics = QHBoxLayout()
        metrics.setSpacing(14)
        self.cards = []
        for glyph in ('▦', '✓', '◇', 'ⓘ'):
            card = self.panel()
            v = QVBoxLayout(card)
            v.setContentsMargins(22, 20, 22, 20)
            v.setSpacing(6)
            symbol = self.label(glyph, 'metricGlyph')
            value = self.label('—', 'metricValue')
            title = self.label('', 'metricCaption')
            v.addWidget(symbol)
            v.addWidget(value)
            v.addWidget(title)
            metrics.addWidget(card, 1)
            self.cards.append((value, title))
        layout.addLayout(metrics)

        section = QHBoxLayout()
        self.section_title = self.label('', 'sectionTitle')
        section.addWidget(self.section_title)
        section.addStretch()
        self.see_all = QPushButton()
        self.see_all.setObjectName('textButton')
        self.see_all.clicked.connect(lambda: self.navigate(1))
        section.addWidget(self.see_all)
        layout.addLayout(section)
        self.preview = self.panel()
        pv_outer = QVBoxLayout(self.preview)
        pv_outer.setContentsMargins(8, 8, 8, 8)
        pv_outer.setSpacing(0)
        self.preview_scroll = QScrollArea()
        self.preview_scroll.setObjectName('previewScroll')
        self.preview_scroll.setWidgetResizable(True)
        self.preview_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.preview_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.preview_scroll.setMinimumHeight(250)
        self.preview_scroll.setMaximumHeight(340)
        preview_body = QWidget()
        preview_body.setObjectName('previewBody')
        pv = QVBoxLayout(preview_body)
        pv.setContentsMargins(8, 4, 8, 4)
        pv.setSpacing(0)
        self.preview_rows = []
        for i in range(5):
            row = QFrame(objectName='previewRow')
            row.setMinimumHeight(68)
            h = QHBoxLayout(row)
            h.setContentsMargins(12, 8, 12, 8)
            h.setSpacing(12)
            glyph = self.label('◈', 'deviceGlyph')
            glyph.setFixedWidth(28)
            info = QVBoxLayout()
            info.setSpacing(4)
            name = ElidedLabel()
            name.setObjectName('deviceName')
            sub = ElidedLabel()
            sub.setObjectName('deviceSub')
            info.addWidget(name)
            info.addWidget(sub)
            h.addWidget(glyph)
            h.addLayout(info, 1)
            status = self.label('', 'deviceStatus')
            status.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            status.setMinimumWidth(140)
            status.setMaximumWidth(180)
            status.setWordWrap(True)
            h.addWidget(status)
            pv.addWidget(row)
            self.preview_rows.append((row, name, sub, status))
        pv.addStretch()
        self.preview_scroll.setWidget(preview_body)
        pv_outer.addWidget(self.preview_scroll)
        layout.addWidget(self.preview, 1)
        self.notice = self.label('', 'notice')
        self.notice.setWordWrap(True)
        layout.addWidget(self.notice)
        self.stack.addWidget(page)

    def build_devices(self):
        page = QWidget()
        v = QVBoxLayout(page)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(15)
        self.devices_desc = self.label('', 'muted')
        v.addWidget(self.devices_desc)
        controls = QHBoxLayout()
        self.search = QLineEdit()
        self.search.setMinimumHeight(42)
        self.search.textChanged.connect(self.refresh_table)
        self.category = QComboBox()
        self.category.setMinimumWidth(160)
        self.category.currentIndexChanged.connect(self.refresh_table)
        self.export_button = QPushButton()
        self.export_button.setMinimumHeight(42)
        self.export_button.clicked.connect(self.export)
        controls.addWidget(self.search, 1)
        controls.addWidget(self.category)
        controls.addWidget(self.export_button)
        v.addLayout(controls)
        table_panel = self.panel()
        table_layout = QVBoxLayout(table_panel)
        table_layout.setContentsMargins(8, 8, 8, 8)
        self.table = QTableWidget(0, 4)
        self.table.setShowGrid(False)
        self.table.setAlternatingRowColors(False)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(48)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.table.itemSelectionChanged.connect(self.show_detail)
        table_layout.addWidget(self.table)
        v.addWidget(table_panel, 3)
        detail = self.panel()
        detail_layout = QVBoxLayout(detail)
        detail_layout.setContentsMargins(20, 15, 20, 15)
        self.detail_heading = self.label('', 'sectionTitle')
        self.detail_label = self.label('', 'muted')
        self.detail_label.setWordWrap(True)
        self.detail_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        detail_layout.addWidget(self.detail_heading)
        detail_layout.addWidget(self.detail_label)
        v.addWidget(detail, 1)
        self.stack.addWidget(page)

    def build_diagnostics(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(14)
        self.diag_intro = self.label('', 'muted')
        self.diag_intro.setWordWrap(True)
        layout.addWidget(self.diag_intro)
        self.diag_scroll = QScrollArea()
        self.diag_scroll.setWidgetResizable(True)
        self.diag_scroll.setFrameShape(QFrame.Shape.NoFrame)
        body = QWidget()
        self.diag_list = QVBoxLayout(body)
        self.diag_list.setSpacing(12)
        self.diag_list.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.diag_scroll.setWidget(body)
        layout.addWidget(self.diag_scroll, 1)
        self.stack.addWidget(page)

    def refresh_diagnostics(self):
        if not hasattr(self, 'diag_list'):
            return
        self.diag_intro.setText(self.t('diag_intro'))
        while self.diag_list.count():
            item = self.diag_list.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        if not self.devices:
            empty = self.label(self.t('diag_empty'), 'muted')
            self.diag_list.addWidget(empty)
            return
        for finding in analyze(self.devices):
            card = self.panel()
            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(20, 16, 20, 16)
            card_layout.setSpacing(9)
            title = self.label(('⚠  ' if finding.severity == 'review' else 'ⓘ  ') + finding.title, 'sectionTitle')
            title.setWordWrap(True)
            description = self.label(finding.explanation, 'muted')
            description.setWordWrap(True)
            action = self.label(self.t('next_step') + ': ' + finding.next_step, 'muted')
            action.setWordWrap(True)
            for widget in (title, description, action):
                widget.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
                card_layout.addWidget(widget)
            self.diag_list.addWidget(card)
        card = self.panel()
        fl = QVBoxLayout(card)
        fl.setContentsMargins(20, 16, 20, 16)
        heading = self.label(('Firmware evidence' if self.language == 'en' else 'फ़र्मवेयर जाँच'), 'sectionTitle')
        heading.setWordWrap(True)
        fl.addWidget(heading)
        summary = self.label(self.firmware_note if self.language == 'en' else
                             'कर्नेल लॉग से फ़र्मवेयर जाँच: ' + self.firmware_note, 'muted')
        summary.setWordWrap(True)
        fl.addWidget(summary)
        for evidence in self.firmware_findings:
            line = self.label(evidence.message, 'muted')
            line.setWordWrap(True)
            line.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            fl.addWidget(line)
            if evidence.package_hint:
                hint = ('Repository candidate: ' if self.language == 'en' else 'रिपॉज़िटरी पैकेज: ') + evidence.package_hint
                hint += (' (available; not verified as a fix)' if evidence.package_available else
                         ' (not available in enabled repositories)')
                h = self.label(hint, 'muted')
                h.setWordWrap(True)
                fl.addWidget(h)
        disclaimer = self.label(('No packages are installed or modified. A package hint is not a confirmed repair.'
                                 if self.language == 'en' else
                                 'कोई पैकेज इंस्टॉल या बदला नहीं जाता। पैकेज सुझाव निश्चित समाधान नहीं है।'), 'muted')
        disclaimer.setWordWrap(True)
        fl.addWidget(disclaimer)
        self.diag_list.addWidget(card)

    def build_recommendations(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)
        controls = QHBoxLayout()
        self.reco_filter = QComboBox()
        self.reco_filter.setMinimumWidth(185)
        self.reco_filter.currentIndexChanged.connect(self.refresh_recommendations)
        controls.addWidget(self.reco_filter)
        controls.addStretch()
        self.reco_refresh = QPushButton('Refresh recommendations')
        self.reco_refresh.clicked.connect(self.refresh_recommendations)
        controls.addWidget(self.reco_refresh)
        layout.addLayout(controls)
        self.reco_summary = self.label('', 'sectionTitle')
        self.reco_summary.setWordWrap(True)
        layout.addWidget(self.reco_summary)
        self.reco_intro = self.label('', 'muted')
        self.reco_intro.setWordWrap(True)
        layout.addWidget(self.reco_intro)
        self.reco_scroll = QScrollArea()
        self.reco_scroll.setWidgetResizable(True)
        self.reco_scroll.setFrameShape(QFrame.Shape.NoFrame)
        body = QWidget()
        self.reco_list = QVBoxLayout(body)
        self.reco_list.setSpacing(12)
        self.reco_list.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.reco_scroll.setWidget(body)
        layout.addWidget(self.reco_scroll, 1)
        self.stack.addWidget(page)

    def refresh_recommendations(self):
        """Summarize physical hardware only, with evidence-aware status labels."""
        if not hasattr(self, 'reco_list'):
            return
        hi = self.language == 'hi'
        self.reco_refresh.setText('सुझाव फिर से जाँचें' if hi else 'Refresh recommendations')
        items = build_advice(getattr(self, 'devices', []))
        totals = counts(items)
        all_devices = getattr(self, 'devices', [])
        all_bound = sum(bool((d.driver or '').strip()) for d in all_devices)
        excluded_bound = all_bound - totals['working']
        self.reco_summary.setText(
            (f"वास्तविक PCI/USB उपकरण: {len(items)}    •    ड्राइवर जुड़े: {totals['working']}    •    जाँच आवश्यक: {totals['attention']}    •    अज्ञात: {totals['unknown']}" if hi else
             f"Physical PCI/USB devices: {len(items)}    •    Drivers bound: {totals['working']}    •    Needs review: {totals['attention']}    •    Unknown: {totals['unknown']}"))
        self.reco_intro.setText(
            ((f'अवलोकन में सभी {len(all_devices)} प्रविष्टियाँ और {all_bound} जुड़े ड्राइवर गिने जाते हैं। यहाँ केवल PCI/USB उपकरण हैं; अन्य प्रविष्टियों में {excluded_bound} जुड़े ड्राइवर हैं। ड्राइवर जुड़ा होना पूरी कार्यक्षमता का प्रमाण नहीं है।' if hi else
             f'Overview counts all {len(all_devices)} detected entries and {all_bound} bound drivers. Recommendations includes physical PCI/USB devices only; {excluded_bound} bound entries are excluded. Driver binding does not prove functionality.')))
        selected = self.reco_filter.currentData()
        options = [('', 'सभी स्थितियाँ' if hi else 'All statuses'),
                   ('attention', 'जाँच आवश्यक' if hi else 'Needs review'),
                   ('working', 'ड्राइवर जुड़ा' if hi else 'Driver bound'),
                   ('unknown', 'अज्ञात' if hi else 'Unknown')]
        self.reco_filter.blockSignals(True)
        self.reco_filter.clear()
        for value, label in options:
            self.reco_filter.addItem(label, value)
        self.reco_filter.setCurrentIndex(max(0, self.reco_filter.findData(selected)))
        self.reco_filter.blockSignals(False)
        selected = self.reco_filter.currentData()
        while self.reco_list.count():
            child = self.reco_list.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        shown = [x for x in items if not selected or x.status == selected]
        if not shown:
            panel = self.panel()
            v = QVBoxLayout(panel)
            v.addWidget(self.label('इस श्रेणी में कोई उपकरण नहीं मिला' if hi else
                                   'No devices in this category', 'sectionTitle'))
            self.reco_list.addWidget(panel)
        statuses = {
            'working': ('ड्राइवर जुड़ा हुआ', 'Driver bound'),
            'attention': ('जाँच आवश्यक', 'Needs review'),
            'unknown': ('अज्ञात', 'Unknown'),
        }
        for device in shown:
            panel = self.panel()
            v = QVBoxLayout(panel)
            v.setContentsMargins(18, 14, 18, 14)
            v.setSpacing(7)
            title = self.label(device.name, 'sectionTitle')
            title.setWordWrap(True)
            title.setToolTip(device.full_name)
            v.addWidget(title)
            status = statuses[device.status][0 if hi else 1]
            v.addWidget(self.label(status, 'muted'))
            explanation = {
                'working': 'कर्नेल ड्राइवर जुड़ा है। पूरी कार्यक्षमता सत्यापित नहीं हुई; बदलाव का संकेत नहीं है।',
                'attention': 'इस उपकरण का ड्राइवर नहीं मिला। पैकेज बदलने से पहले जाँच करें।',
                'unknown': 'ड्राइवर की जानकारी नहीं मिली। यह सामान्य भी हो सकता है।',
            }[device.status] if hi else device.explanation
            detail = self.label(f'{device.category}  •  {device.identifier}\n' +
                ('ड्राइवर: ' if hi else 'Driver: ') + (device.driver or ('अज्ञात' if hi else 'Not detected')) +
                '\n' + explanation, 'muted')
            detail.setWordWrap(True)
            detail.setToolTip(device.full_name)
            v.addWidget(detail)
            self.reco_list.addWidget(panel)

    def show_package_preview(self, name):
        """Graphical, read-only review wizard. No elevated actions."""
        plan = preview_plan(name)
        hindi = self.language == 'hi'
        dlg = QDialog(self)
        dlg.setWindowTitle('फ़र्मवेयर समीक्षा' if hindi else 'Firmware installation review')
        dlg.setMinimumSize(660, 480)
        root = QVBoxLayout(dlg)
        heading = QLabel(('पैकेज समीक्षा: ' if hindi else 'Review package: ') + name)
        heading.setTextFormat(Qt.TextFormat.PlainText)
        heading.setObjectName('sectionTitle')
        root.addWidget(heading)
        explanation = QLabel(('यह केवल एक पूर्वावलोकन है। कोई ड्राइवर इंस्टॉल नहीं होगा।' if hindi else
            'This is a simulation, not an installation. No system changes will be made.'))
        explanation.setWordWrap(True)
        root.addWidget(explanation)
        state = ('समीक्षा जाँच पूरी (सिमुलेशन)' if hindi else 'Simulation checks passed') if plan['review_passed'] else (
            'मैनुअल समीक्षा आवश्यक' if hindi else 'Manual review required')
        root.addWidget(QLabel(state))
        details = QTextEdit()
        details.setReadOnly(True)
        changes = '\n'.join(plan['changes']) or '(No recognized package changes)'
        warnings = '\n'.join(plan['warnings']) or '(No policy warnings detected)'
        details.setPlainText(f'Package: {name}\n\nAPT simulation:\n{changes}\n\nWarnings:\n{warnings}\n\n'
            'SECURITY: An APT simulation can become stale. This review does not authorize an installation.')
        root.addWidget(details, 1)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(dlg.reject)
        buttons.accepted.connect(dlg.accept)
        root.addWidget(buttons)
        dlg.exec()

    def build_repair_center(self):
        """Read-only guided repair workflow. No root or package changes."""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        body = QWidget()
        self.repair_list = QVBoxLayout(body)
        self.repair_list.setSpacing(16)
        self.repair_list.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.repair_heading = self.label('', 'sectionTitle')
        self.repair_intro = self.label('', 'muted')
        self.repair_intro.setWordWrap(True)
        self.repair_status = self.panel()
        status_layout = QVBoxLayout(self.repair_status)
        self.repair_status_title = self.label('', 'sectionTitle')
        self.repair_status_text = self.label('', 'muted')
        self.repair_status_text.setWordWrap(True)
        status_layout.addWidget(self.repair_status_title)
        status_layout.addWidget(self.repair_status_text)
        self.repair_steps = self.panel()
        steps_layout = QVBoxLayout(self.repair_steps)
        self.repair_steps_title = self.label('', 'sectionTitle')
        self.repair_steps_text = self.label('', 'muted')
        self.repair_steps_text.setWordWrap(True)
        steps_layout.addWidget(self.repair_steps_title)
        steps_layout.addWidget(self.repair_steps_text)
        self.repair_list.addWidget(self.repair_heading)
        self.repair_list.addWidget(self.repair_intro)
        self.repair_list.addWidget(self.repair_status)
        self.repair_list.addWidget(self.repair_steps)
        self.backend_panel = self.panel()
        backend_layout = QVBoxLayout(self.backend_panel)
        self.backend_title = self.label('', 'sectionTitle')
        self.backend_text = self.label('', 'muted')
        self.backend_text.setWordWrap(True)
        backend_layout.addWidget(self.backend_title)
        backend_layout.addWidget(self.backend_text)
        self.repair_list.addWidget(self.backend_panel)
        self.hardware_panel = self.panel()
        hardware_layout = QVBoxLayout(self.hardware_panel)
        self.hardware_heading = self.label('', 'sectionTitle')
        self.hardware_explanation = self.label('', 'muted')
        self.hardware_explanation.setWordWrap(True)
        self.hardware_refresh = QPushButton()
        self.hardware_refresh.clicked.connect(self.refresh_hardware_hints)
        hardware_controls = QHBoxLayout()
        self.hardware_filter = QComboBox()
        self.hardware_filter.currentIndexChanged.connect(self.render_hardware_table)
        self.hardware_search = QLineEdit()
        self.hardware_search.textChanged.connect(self.render_hardware_table)
        hardware_controls.addWidget(self.hardware_filter)
        hardware_controls.addWidget(self.hardware_search, 1)
        self.hardware_table = QTableWidget(0, 8)
        self.hardware_table.verticalHeader().setVisible(False)
        self.hardware_table.itemSelectionChanged.connect(self.update_device_inspection_state)
        self.hardware_table.cellDoubleClicked.connect(self.show_device_details)
        self.hardware_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.hardware_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.hardware_table.setAlternatingRowColors(True)
        self.hardware_table.setMinimumHeight(230)
        self.hardware_table.horizontalHeader().setStretchLastSection(False)
        self.hardware_table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.hardware_table.setHorizontalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.hardware_details = QPushButton()
        self.hardware_details.clicked.connect(self.show_device_details)
        self.hardware_evidence = self.label('', 'muted')
        self.hardware_evidence.setWordWrap(True)
        self.hardware_device_apt = QPushButton()
        self.hardware_device_apt.setEnabled(False)
        self.hardware_device_apt.clicked.connect(self.inspect_selected_device)
        self.hardware_export = QPushButton()
        self.hardware_export.clicked.connect(self.export_hardware_report)
        self.hardware_hints = []
        self.hardware_evidence_results = {}
        self.hardware_evidence_access = 'not_checked'
        self.hardware_evidence_button = QPushButton()
        self.hardware_evidence_button.clicked.connect(self.refresh_firmware_evidence)
        self.evidence_worker = None
        self.hardware_scan_status = self.label('', 'muted')
        self.hardware_scan_status.setWordWrap(True)
        self.hardware_scan_progress = QProgressBar()
        self.hardware_scan_progress.setRange(0, 0)
        self.hardware_scan_progress.setVisible(False)
        for widget in (self.hardware_heading, self.hardware_explanation, self.hardware_refresh):
            hardware_layout.addWidget(widget)
        hardware_layout.addLayout(hardware_controls)
        hardware_layout.addWidget(self.hardware_evidence_button)
        hardware_layout.addWidget(self.hardware_scan_progress)
        hardware_layout.addWidget(self.hardware_scan_status)
        hardware_layout.addWidget(self.hardware_table)
        hardware_layout.addWidget(self.hardware_evidence)
        hardware_layout.addWidget(self.hardware_details)
        hardware_layout.addWidget(self.hardware_device_apt)
        hardware_layout.addWidget(self.hardware_export)
        self.repair_list.addWidget(self.hardware_panel)
        self.wifi_panel = self.panel()
        wifi_layout = QVBoxLayout(self.wifi_panel)
        self.wifi_heading = self.label('', 'sectionTitle')
        self.wifi_description = self.label('', 'muted')
        self.wifi_description.setWordWrap(True)
        self.wifi_button = QPushButton()
        self.wifi_button.clicked.connect(self.run_wifi_diagnostics)
        self.wifi_result = self.label('', 'muted')
        self.wifi_result.setWordWrap(True)
        self.wifi_worker = None
        for widget in (self.wifi_heading, self.wifi_description, self.wifi_button, self.wifi_result):
            wifi_layout.addWidget(widget)
        self.repair_list.addWidget(self.wifi_panel)
        self.preview_panel = self.panel()
        preview_layout = QVBoxLayout(self.preview_panel)
        self.preview_heading = self.label('', 'sectionTitle')
        self.preview_note = self.label('', 'muted')
        self.preview_note.setWordWrap(True)
        self.preview_selector = QComboBox()
        self.preview_run = QPushButton()
        self.preview_run.clicked.connect(self.run_transaction_preview)
        self.apt_run = QPushButton()
        self.apt_run.clicked.connect(self.run_live_apt_preview)
        self.apt_worker = None
        self.preview_safety = self.label('', 'previewSafety')
        self.preview_safety.setWordWrap(True)
        self.preview_status = self.label('', 'previewStatus')
        self.preview_status.setWordWrap(True)
        self.preview_package = self.label('', 'previewField')
        self.preview_package.setWordWrap(True)
        self.preview_operations_title = self.label('', 'sectionTitle')
        self.preview_operations = self.label('', 'previewField')
        self.preview_operations.setWordWrap(True)
        self.preview_warnings_title = self.label('', 'sectionTitle')
        self.preview_warnings = self.label('', 'previewField')
        self.preview_warnings.setWordWrap(True)
        self.preview_fingerprint_title = self.label('', 'sectionTitle')
        self.preview_fingerprint = self.label('', 'previewFingerprint')
        self.preview_fingerprint.setWordWrap(True)
        self.preview_export = QPushButton()
        self.preview_export.setEnabled(False)
        self.preview_export.clicked.connect(self.export_transaction_preview)
        for widget in (self.preview_heading, self.preview_note, self.preview_safety,
                       self.preview_selector, self.preview_run, self.apt_run, self.preview_status,
                       self.preview_package, self.preview_operations_title,
                       self.preview_operations, self.preview_warnings_title,
                       self.preview_warnings, self.preview_fingerprint_title,
                       self.preview_fingerprint, self.preview_export):
            preview_layout.addWidget(widget)
        self.repair_list.addWidget(self.preview_panel)
        self.last_transaction_preview = None
        scroll.setWidget(body)
        layout.addWidget(scroll)
        self.stack.addWidget(page)

    def update_repair_center(self):
        hi = self.language == 'hi'
        self.repair_heading.setText('ड्राइवर मरम्मत केंद्र' if hi else 'Driver Repair Center')
        self.repair_intro.setText('यह जाँच और मार्गदर्शन का सुरक्षित पूर्वावलोकन है। कोई सिस्टम परिवर्तन नहीं होगा।' if hi else
            'Guided diagnosis and installation planning. No packages are changed in this alpha.')
        self.repair_status_title.setText('वर्तमान स्थिति' if hi else 'Current assessment')
        findings = len(self.firmware_findings)
        if findings:
            msg = f'{findings} firmware log finding(s) detected. Review Diagnostics and Recommendations. A finding is not proof that installation will fix the device.'
        else:
            msg = 'No recognized firmware-loading failures in accessible logs. This is not a complete hardware health check. Do not install drivers without evidence.'
        self.repair_status_text.setText(msg)
        self.repair_steps_title.setText('सुरक्षित कार्यप्रवाह' if hi else 'Safe repair workflow')
        self.repair_steps_text.setText(('१. डिवाइस की जाँच करें।\n२. फ़र्मवेयर त्रुटि देखें।\n३. पैकेज का सिमुलेशन देखें।\n४. प्रशासक-अनुमति वाली इंस्टॉलेशन अभी बंद है।' if hi else
            '1. Identify the affected physical device.\n2. Verify firmware or driver failure evidence.\n3. Review trusted Debian package candidates and simulated changes.\n4. Privileged installation is not implemented or enabled.\n5. After a future installation, verify actual device functionality.'))

        self.backend_title.setText('बैकएंड सुरक्षा स्थिति' if hi else 'Installation backend security status')
        self.backend_text.setText(('अनुरोध सत्यापन और पैकेज समीक्षा उपलब्ध हैं। Polkit सेवा और असली इंस्टॉलेशन अभी उपलब्ध नहीं हैं।' if hi else
            'Request validation and transaction review are available. The system D-Bus Polkit authorization probe is separate; real installation remains disabled.'))

    def update_transaction_preview(self):
        hi = self.language == 'hi'
        self.wifi_heading.setText('वाई-फ़ाई जाँच (केवल पढ़ें)' if hi else 'Wi-Fi diagnostics (read-only)')
        self.wifi_description.setText(('वायरलेस इंटरफ़ेस, NetworkManager स्थिति और रेडियो अवरोध देखें। नेटवर्क में कोई बदलाव नहीं होगा।' if hi else
            'Inspect wireless interfaces, NetworkManager state and radio blocks. No network changes or installations.'))
        self.wifi_button.setText('वाई-फ़ाई की स्थिति जाँचें' if hi else 'Inspect Wi-Fi interfaces')
        if not self.wifi_result.text():
            self.wifi_result.setText('अभी जाँच नहीं हुई।' if hi else 'Not inspected yet.')
        self.hardware_heading.setText('हार्डवेयर संगतता (केवल पढ़ें)' if hi else 'Hardware compatibility (read-only)')
        self.hardware_explanation.setText(('PCI विक्रेता/क्लास से केवल कम-विश्वास वाले संकेत मिलते हैं; पैकेज की जरूरत प्रमाणित नहीं है।' if hi else
            'PCI vendor/class provides low-confidence hints only, not proof that firmware is needed.'))
        self.hardware_refresh.setText('हार्डवेयर संकेत जाँचें' if hi else 'Inspect hardware hints')
        self.hardware_evidence_button.setText('कर्नेल फ़र्मवेयर प्रमाण जाँचें (केवल पढ़ें)' if hi else 'Inspect kernel firmware evidence (read-only)')
        self.hardware_export.setText('हार्डवेयर JSON रिपोर्ट सहेजें' if hi else 'Export hardware JSON report')
        self.hardware_details.setText('चयनित डिवाइस का विवरण देखें (केवल पढ़ें)' if hi else 'View selected device details (read-only)')
        self.hardware_device_apt.setText('चयनित डिवाइस का APT निरीक्षण (सत्यापित प्रमाण आवश्यक)' if hi else 'Inspect selected device with APT (verified evidence required)')
        self.hardware_evidence.setText('केवल PCI ID से फ़र्मवेयर की ज़रूरत प्रमाणित नहीं होती। कोई सत्यापित अनुशंसा नहीं है।' if hi else 'PCI identifiers alone do not verify a firmware requirement. No verified recommendation.')
        self.hardware_search.setPlaceholderText('डिवाइस खोजें…' if hi else 'Search devices…')
        filter_value = self.hardware_filter.currentData()
        filters = [('all', 'सभी' if hi else 'All devices'),
                   ('graphics', 'ग्राफिक्स' if hi else 'Graphics'),
                   ('network', 'नेटवर्क / वाई-फ़ाई' if hi else 'Network / Wi-Fi'),
                   ('storage', 'स्टोरेज' if hi else 'Storage'),
                   ('multimedia', 'मल्टीमीडिया' if hi else 'Multimedia'),
                   ('controller', 'कंट्रोलर' if hi else 'Controllers'),
                   ('other', 'अन्य' if hi else 'Other')]
        self.hardware_filter.blockSignals(True)
        self.hardware_filter.clear()
        for value, label in filters:
            self.hardware_filter.addItem(label, value)
        self.hardware_filter.setCurrentIndex(max(0, next((i for i, (v, _) in enumerate(filters) if v == filter_value), 0)))
        self.hardware_filter.blockSignals(False)
        self.hardware_table.setHorizontalHeaderLabels(
            ['पता' if hi else 'PCI address', 'श्रेणी' if hi else 'Category',
             'PCI ID', 'ड्राइवर' if hi else 'Driver',
             'संभावित पैकेज' if hi else 'Possible package', 'विश्वास' if hi else 'Confidence',
             'अनुशंसा' if hi else 'Recommendation', 'कर्नेल प्रमाण' if hi else 'Kernel evidence'])
        self.render_hardware_table()

        self.preview_heading.setText('लेन-देन पूर्वावलोकन (डेमो)' if hi else 'Transaction preview (demo)')
        self.preview_note.setText(
            'केवल काल्पनिक डेटा। यह वास्तविक हार्डवेयर, APT या इंस्टॉलेशन योजना नहीं है।' if hi else
            'Synthetic fixtures only. This does not inspect your hardware, query APT, or propose a real installation.')
        selected = self.preview_selector.currentData()
        self.preview_selector.blockSignals(True)
        self.preview_selector.clear()
        options = [
            ('स्वीकृत पैकेज का उदाहरण' if hi else 'Allowlisted package example', 'review'),
            ('अनधिकृत पैकेज अस्वीकृत' if hi else 'Blocked: unknown package', 'unknown'),
            ('पैकेज हटाना अस्वीकृत' if hi else 'Blocked: package removal', 'removal'),
            ('सिमुलेशन विफल' if hi else 'Blocked: failed simulation', 'failure'),
        ]
        for title, value in options:
            self.preview_selector.addItem(title, value)
        self.preview_selector.setCurrentIndex(max(0, self.preview_selector.findData(selected)))
        self.preview_selector.blockSignals(False)
        self.preview_run.setText('डेमो पूर्वावलोकन बनाएँ' if hi else 'Generate demo preview')
        self.apt_run.setText('सामान्य APT पैकेज जाँच (हार्डवेयर अनुशंसा नहीं)' if hi else 'Generic APT package check (not a hardware recommendation)')
        self.preview_export.setText('JSON पूर्वावलोकन सहेजें' if hi else 'Export preview JSON')
        self.preview_safety.setText('● केवल सिमुलेशन  •  इंस्टॉलेशन बंद है' if hi else
                                    '● SIMULATION ONLY  •  INSTALLATION DISABLED')
        self.render_transaction_preview()

    @staticmethod
    def localized_preview_operation(operation, hindi):
        """Translate known APT-style synthetic tokens for display only.

        Never alter the stored preview, audit record, or package identifiers.
        Unknown strings are shown unchanged rather than interpreted.
        """
        if not hindi:
            return operation
        import re
        match = re.fullmatch(r'(Inst|Remv) ([a-z0-9][a-z0-9+.-]*) \(1\.0 synthetic\)', operation)
        if not match:
            return operation
        verb = 'इंस्टॉल (डेमो)' if match.group(1) == 'Inst' else 'हटाना (डेमो)'
        return f'{verb}: {match.group(2)} (संस्करण 1.0, काल्पनिक)'

    @staticmethod
    def localized_preview_warning(warning, hindi):
        """Translate only explicitly recognized synthetic warning strings."""
        if not hindi:
            return warning
        translations = {
            'Human review and privileged revalidation still required':
                'मानवीय समीक्षा और व्यवस्थापक स्तर पर दोबारा सत्यापन अभी आवश्यक है',
        }
        return translations.get(warning, warning)

    def render_transaction_preview(self):
        """Present stored synthetic data without modifying it or querying the system."""
        hi = self.language == 'hi'
        payload = self.last_transaction_preview
        self.preview_operations_title.setText('प्रस्तावित क्रियाएँ' if hi else 'Proposed operations')
        self.preview_warnings_title.setText('सुरक्षा चेतावनियाँ' if hi else 'Safety warnings')
        self.preview_fingerprint_title.setText('लेन-देन फ़िंगरप्रिंट' if hi else 'Transaction fingerprint')
        if payload is None:
            self.preview_status.setText('अभी कोई पूर्वावलोकन नहीं' if hi else 'No preview generated yet')
            self.preview_status.setProperty('reviewState', 'empty')
            self.preview_package.setText('')
            self.preview_operations.setText('—')
            self.preview_warnings.setText('—')
            self.preview_fingerprint.setText('—')
        else:
            plan = payload['plan']
            blocked = plan['state'] != 'review_required'
            self.preview_status.setText(('● अस्वीकृत — कार्रवाई की अनुमति नहीं' if hi else
                                         '● BLOCKED — action not permitted') if blocked else
                                        ('● समीक्षा आवश्यक — अनुमति नहीं मिली है' if hi else
                                         '● REVIEW REQUIRED — not authorized for installation'))
            self.preview_status.setProperty('reviewState', 'blocked' if blocked else 'review')
            self.preview_package.setText(('पैकेज: ' if hi else 'Package: ') + plan['package'])
            self.preview_operations.setText('\n'.join('• ' + self.localized_preview_operation(op, hi) for op in plan['operations']) or '—')
            self.preview_warnings.setText('\n'.join('• ' + self.localized_preview_warning(warning, hi) for warning in plan['warnings']) or '—')
            self.preview_fingerprint.setText(plan['fingerprint'])
        self.preview_status.style().unpolish(self.preview_status)
        self.preview_status.style().polish(self.preview_status)

    def run_transaction_preview(self):
        # These are fixed, synthetic inputs. Never call APT or execute packages.
        package = sorted(ALLOWED)[0] if ALLOWED else 'firmware-linux'
        scenario = self.preview_selector.currentData()
        requested = package if scenario != 'unknown' else 'untrusted-demo-package'
        operations = [f'Inst {requested} (1.0 synthetic)']
        if scenario == 'removal':
            operations.append('Remv linux-image-amd64 (1.0 synthetic)')
        request = RepairRequest(requested, '0000:00:00.0', 'a' * 64)
        plan = create_plan(request, evidence_packages=(package,),
                           simulation_ok=scenario != 'failure', operations=operations)
        record = audit_record(plan)
        self.last_transaction_preview = {
            'synthetic_demo': True, 'source': 'fixed_demo_fixture',
            'not_real_apt_simulation': True,
            'plan': plan.to_dict(), 'audit': record,
        }
        self.render_transaction_preview()
        self.preview_export.setEnabled(True)

    def run_live_apt_preview(self):
        """Asynchronous generic informational check, not a device recommendation."""
        if self.apt_worker is not None and self.apt_worker.isRunning():
            return
        hints = sorted({item.package_hint for item in self.firmware_findings
                        if item.package_hint in ALLOWED})
        # Kernel log hints are never treated as a confirmed device match.
        package = hints[0] if hints else sorted(ALLOWED)[0]
        self.apt_run.setEnabled(False)
        self.apt_worker = AptSimulationThread(package)
        self.apt_worker.complete.connect(self.show_live_apt_preview)
        self.apt_worker.finished.connect(lambda: self.apt_run.setEnabled(True))
        self.apt_worker.start()

    def run_wifi_diagnostics(self):
        """Read-only sysfs inspection on a worker thread."""
        if self.wifi_worker is not None and self.wifi_worker.isRunning():
            return
        self.wifi_button.setEnabled(False)
        self.wifi_result.setText('जाँच जारी है…' if self.language == 'hi' else 'Inspecting…')
        self.wifi_worker = WifiDiagnosticsThread()
        self.wifi_worker.complete.connect(self.show_wifi_diagnostics)
        self.wifi_worker.finished.connect(lambda: self.wifi_button.setEnabled(True))
        self.wifi_worker.start()

    def show_wifi_diagnostics(self, report):
        hi = self.language == 'hi'
        items = report.get('interfaces', [])
        if report.get('status') != 'ok':
            message = 'नेटवर्क जानकारी उपलब्ध नहीं है।' if hi else 'Network interface information unavailable.'
        elif not items:
            message = ('कोई वायरलेस इंटरफ़ेस नहीं मिला।' if hi else 'No wireless interfaces detected.')
        else:
            lines = []
            for item in items:
                lines.append(f"{item['interface']} | " +
                             ('स्थिति' if hi else 'State') + f": {item['operstate']} | " +
                             ('ड्राइवर' if hi else 'Driver') + f": {item['driver'] or '—'}")
                nm_state = item.get('networkmanager_state')
                lines.append(('NetworkManager स्थिति: ' if hi else 'NetworkManager state: ') +
                             (nm_state or ('उपलब्ध नहीं' if hi else 'Unavailable / not managed')))
                status = item.get('assessment')
                statuses = ({'radio_block_detected': 'ध्यान दें: किसी वाई-फ़ाई रेडियो पर अवरोध मिला',
                             'connected_reported': 'NetworkManager के अनुसार कनेक्टेड',
                             'unable_to_verify': 'कनेक्शन की पुष्टि नहीं हो सकी'} if hi else
                            {'radio_block_detected': 'Attention: a Wi-Fi radio block was detected',
                             'connected_reported': 'Connected according to NetworkManager',
                             'unable_to_verify': 'Connection not verified'})
                lines.append(statuses.get(status, statuses['unable_to_verify']))
            radios = report.get('rfkill', {}).get('radios', [])
            if radios:
                lines.append(('रेडियो अवरोध:' if hi else 'Radio blocks:') + ' ' +
                             ', '.join(f"{r['name']} soft={r['soft_blocked']} hard={r['hard_blocked']}" for r in radios))
            else:
                lines.append('RF-kill: ' + ('जानकारी उपलब्ध नहीं' if hi else 'No Wi-Fi switch data available'))
            message = '\n'.join(lines)
        evidence = report.get('firmware_messages', {})
        if evidence.get('status') == 'permission_restricted':
            evidence_note = ('कर्नेल लॉग देखने के लिए अतिरिक्त अनुमति आवश्यक है; फ़र्मवेयर की स्थिति अज्ञात है।' if hi else
                             'Kernel logs require additional permission; firmware status is unknown.')
        elif evidence.get('status') != 'ok':
            evidence_note = ('कर्नेल लॉग उपलब्ध नहीं हैं; फ़र्मवेयर की स्थिति अज्ञात है।' if hi else
                             'Kernel logs unavailable; firmware status is unknown.')
        elif evidence.get('failure_hints'):
            evidence_note = (('हाल के कर्नेल लॉग में संभावित फ़र्मवेयर त्रुटियाँ मिलीं (डिवाइस से संबंध अप्रमाणित):' if hi else
                              'Possible firmware errors in recent kernel logs (device association unverified):') +
                             '\n' + '\n'.join(evidence['failure_hints']))
        else:
            evidence_note = ('जाँचे गए सीमित कर्नेल लॉग में फ़र्मवेयर लोड विफलता नहीं मिली। यह पूर्ण जाँच नहीं है।' if hi else
                             'No firmware-loading failure found in the limited kernel messages checked. This is not a complete check.')
        events = evidence.get('events', []) if evidence.get('status') == 'ok' else []
        loaded = [e for e in events if e.get('kind') == 'wifi_firmware_loaded']
        graphics = [e for e in events if e.get('kind') == 'graphics_warning']
        if loaded:
            evidence_note += ('\nवाई-फ़ाई फ़र्मवेयर लोड होने का संदेश मिला (सीमित लॉग में)।' if hi else
                              '\nWi-Fi firmware load reported in checked logs.')
        if graphics:
            evidence_note += ('\nअलग ग्राफ़िक्स चेतावनी मिली; यह वाई-फ़ाई फ़र्मवेयर विफलता नहीं है।' if hi else
                              '\nSeparate graphics warning found; not a Wi-Fi firmware failure.')
        message += '\n\n' + evidence_note
        warning = ('यह इंटरनेट या फ़र्मवेयर स्वास्थ्य की पूर्ण जाँच नहीं है। इंस्टॉलेशन बंद है।' if hi else
                   'This does not prove internet access or firmware health. Installation is disabled.')
        self.wifi_result.setText(message + '\n' + warning)
        QMessageBox.information(self, 'वाई-फ़ाई जाँच' if hi else 'Wi-Fi diagnostics', message + '\n\n' + warning)

    def refresh_hardware_hints(self):
        """Refresh the local PCI evidence; no package changes or shell commands."""
        self.hardware_hints = inspect_pci()
        self.hardware_evidence_results = {}
        self.hardware_evidence_access = 'not_checked'
        self.hardware_scan_status.setText('')
        self.render_hardware_table()

    def refresh_firmware_evidence(self):
        """Inspect current-boot kernel logs asynchronously; never modify the system."""
        if self.evidence_worker is not None and self.evidence_worker.isRunning():
            return
        if not self.hardware_hints:
            self.refresh_hardware_hints()
        hi = self.language == 'hi'
        self.hardware_evidence_button.setEnabled(False)
        self.hardware_scan_progress.setVisible(True)
        self.hardware_scan_status.setText('कर्नेल फ़र्मवेयर प्रमाण जाँचे जा रहे हैं…' if hi
                                          else 'Inspecting kernel firmware evidence…')
        self.evidence_worker = KernelEvidenceThread(self.hardware_hints)
        self.evidence_worker.complete.connect(self._firmware_evidence_complete)
        self.evidence_worker.failed.connect(self._firmware_evidence_failed)
        self.evidence_worker.finished.connect(self._firmware_evidence_finished)
        self.evidence_worker.start()

    def _firmware_evidence_finished(self):
        self.hardware_evidence_button.setEnabled(True)
        self.hardware_scan_progress.setVisible(False)

    def _firmware_evidence_failed(self, error):
        self.hardware_evidence_results = {}
        self.hardware_evidence_access = 'unavailable'
        self.render_hardware_table()
        hi = self.language == 'hi'
        self.hardware_scan_status.setText('जाँच विफल — कर्नेल लॉग उपलब्ध नहीं हैं।' if hi
                                          else 'Inspection failed — kernel evidence unavailable.')
        QMessageBox.warning(self, 'कर्नेल जाँच' if hi else 'Kernel inspection',
                            ('जाँच पूरी नहीं हो सकी। कोई फ़र्मवेयर अनुशंसा सत्यापित नहीं हुई।' if hi
                             else 'Inspection could not complete. No firmware recommendation was verified.')
                            + '\n' + str(error))

    def _firmware_evidence_complete(self, findings, access):
        self.hardware_evidence_results = {item.address: item for item in findings}
        self.hardware_evidence_access = access
        self.render_hardware_table()
        # Reposition the horizontal viewport so PCI addresses are visible.
        self.hardware_table.horizontalScrollBar().setValue(0)
        hi = self.language == 'hi'
        count = len(findings)
        correlated = sum(1 for item in findings if item.status == 'correlated_unverified')
        if access != 'available':
            message = ('कर्नेल लॉग पढ़े नहीं जा सके। जाँचे गए लॉग से कोई निष्कर्ष नहीं निकाला जा सकता।' if hi
                       else 'Kernel logs could not be read. No conclusion can be drawn from the unavailable logs.')
        elif correlated:
            message = (f'जाँच पूरी: {count} उपकरण; {correlated} असत्यापित संबंधित लॉग संकेत मिले।' if hi
                       else f'Inspection complete: {count} devices; {correlated} unverified matching log hints found.')
        else:
            message = (f'जाँच पूरी: {count} उपकरण; जाँचे गए वर्तमान-बूट कर्नेल लॉग में कोई मेल खाता फ़र्मवेयर विफलता संदेश नहीं मिला।' if hi
                       else f'Inspection complete: {count} devices; no matching firmware-failure messages were found in the checked current-boot kernel log.')
        self.hardware_scan_status.setText(message)
        QMessagebox_note = (
            'यह केवल उपलब्ध वर्तमान-बूट लॉग के अंतिम 4,000 रिकॉर्ड की जाँच है। लॉग में संदेश न मिलना हार्डवेयर के सही काम करने या फ़र्मवेयर की आवश्यकता न होने का प्रमाण नहीं है। इंस्टॉलेशन बंद है।'
            if hi else
            'This checks only the available current-boot kernel log (up to the last 4,000 records). No matching message is not proof that hardware works or that firmware is unnecessary. Installation remains disabled.'
        )
        QMessageBox.information(self, 'कर्नेल जाँच परिणाम' if hi else 'Kernel inspection results',
                                message + '\\n\\n' + QMessagebox_note)

    def render_hardware_table(self, *_):
        if not hasattr(self, 'hardware_table'):
            return
        hi = self.language == 'hi'
        category = self.hardware_filter.currentData() or 'all'
        search = self.hardware_search.text().strip().lower()
        matches = [h for h in self.hardware_hints if
                   (category == 'all' or h.category == category) and
                   (not search or search in ' '.join((h.address, h.vendor_id, h.device_id,
                         h.class_id, h.driver, h.package_hint or '', h.category)).lower())]
        self.visible_hardware_hints = matches
        self.hardware_table.setRowCount(len(matches))
        category_labels = {'graphics': ('ग्राफिक्स', 'Graphics'), 'network': ('नेटवर्क', 'Network'),
                           'storage': ('स्टोरेज', 'Storage'), 'multimedia': ('मल्टीमीडिया', 'Multimedia'),
                           'controller': ('कंट्रोलर', 'Controller'), 'other': ('अन्य', 'Other')}
        for row, hint in enumerate(matches):
            values = [hint.address, category_labels.get(hint.category, ('अन्य', 'Other'))[0 if hi else 1],
                      f'{hint.vendor_id}:{hint.device_id}', hint.driver or '—',
                      hint.package_hint or '—',
                      ('कम' if hi else 'Low') if hint.confidence == 'low' else
                      ('अपर्याप्त' if hi else 'Insufficient'),
                      ('कोई सत्यापित अनुशंसा नहीं' if hi else 'No verified recommendation'),
                      self._evidence_label(hint.address, hi)]
            for column, value in enumerate(values):
                cell = QTableWidgetItem(value)
                cell.setToolTip(hint.explanation)
                self.hardware_table.setItem(row, column, cell)
        self.hardware_table.resizeColumnsToContents()
        self.update_device_inspection_state()

    def _evidence_label(self, address, hi):
        if self.hardware_evidence_access == 'unavailable':
            return 'लॉग उपलब्ध नहीं' if hi else 'Log unavailable'
        finding = self.hardware_evidence_results.get(address)
        if finding and finding.status == 'correlated_unverified':
            return 'संबंधित (असत्यापित)' if hi else 'Correlated (unverified)'
        if self.hardware_evidence_access == 'available':
            return 'जाँचे गए लॉग में मेल नहीं मिला' if hi else 'No match in checked logs'
        return 'जाँच नहीं हुई' if hi else 'Not checked'

    def update_device_inspection_state(self):
        """Never authorize device-specific inspection from low-confidence hints."""
        self.hardware_device_apt.setEnabled(False)
        hi = self.language == 'hi'
        selected = self.hardware_table.currentRow()
        self.hardware_details.setEnabled(0 <= selected < len(getattr(self, 'visible_hardware_hints', [])))
        hints = getattr(self, 'visible_hardware_hints', [])
        if 0 <= selected < len(hints):
            hint = hints[selected]
            self.hardware_evidence.setText(
                (f'{hint.address}: कोई सत्यापित फ़र्मवेयर अनुशंसा नहीं। PCI संकेत पर्याप्त नहीं हैं।'
                 if hi else f'{hint.address}: No verified firmware recommendation. PCI hints are insufficient.'))
        else:
            self.hardware_evidence.setText(
                'केवल PCI ID से फ़र्मवेयर की ज़रूरत प्रमाणित नहीं होती। कोई सत्यापित अनुशंसा नहीं है।' if hi
                else 'PCI identifiers alone do not verify a firmware requirement. No verified recommendation.')

    def show_device_details(self, *_):
        """Show localized PCI facts and optional asynchronous dpkg status only."""
        row = self.hardware_table.currentRow()
        hints = getattr(self, 'visible_hardware_hints', [])
        if not 0 <= row < len(hints):
            return
        hint = hints[row]
        hi = self.language == 'hi'
        from .device_details import detail_fields, package_state_text
        dialog = QDialog(self)
        dialog.setWindowTitle('डिवाइस विवरण (केवल पढ़ें)' if hi else 'Device details (read-only)')
        dialog.resize(690, 550)
        layout = QVBoxLayout(dialog)
        heading = QLabel(('डिवाइस: ' if hi else 'Device: ') + hint.address)
        heading.setTextFormat(Qt.TextFormat.PlainText)
        heading.setObjectName('sectionTitle')
        layout.addWidget(heading)
        for name, value in detail_fields(hint, hi, self._evidence_label(hint.address, hi)):
            field = QLabel(f'{name}: {value}')
            field.setTextFormat(Qt.TextFormat.PlainText)
            field.setWordWrap(True)
            field.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            layout.addWidget(field)
        warning = QLabel('यह विवरण फ़र्मवेयर की आवश्यकता सिद्ध नहीं करता। इंस्टॉलेशन बंद है।' if hi
                         else 'These details do not prove firmware is needed. Installation is disabled.')
        warning.setWordWrap(True)
        layout.addWidget(warning)
        if hint.package_hint in ALLOWED:
            status_label = QLabel('पैकेज स्थिति: अभी जाँची नहीं गई' if hi else 'Package status: Not checked')
            status_label.setTextFormat(Qt.TextFormat.PlainText)
            status_label.setWordWrap(True)
            layout.addWidget(status_label)
            check_button = QPushButton('पैकेज की स्थिति जाँचें (केवल पढ़ें)' if hi
                                       else 'Check installed package status (read-only)')
            layout.addWidget(check_button)
            def start_check():
                if getattr(dialog, '_package_worker', None) is not None:
                    return
                check_button.setEnabled(False)
                status_label.setText('स्थानीय dpkg डेटाबेस जाँचा जा रहा है…' if hi
                                     else 'Checking local dpkg database…')
                worker = PackageStatusThread(hint.package_hint, dialog)
                dialog._package_worker = worker
                def completed(state, version):
                    status_label.setText(package_state_text(state, version, hi))
                    check_button.setEnabled(True)
                worker.complete.connect(completed)
                worker.finished.connect(lambda: setattr(dialog, '_package_worker', None))
                worker.start()
            check_button.clicked.connect(start_check)
        layout.addStretch(1)
        close_button = QPushButton('बंद करें' if hi else 'Close')
        close_button.clicked.connect(dialog.accept)
        layout.addWidget(close_button)
        dialog.exec()
        # Wait for an in-flight bounded lookup before destroying its Qt parent.
        worker = getattr(dialog, '_package_worker', None)
        if worker is not None and worker.isRunning():
            worker.wait(6000)

    def inspect_selected_device(self):
        """Fail closed: no device-to-package evidence chain is approved in this alpha."""
        QMessageBox.information(self, 'Jatayu Driver Assistant',
            'सत्यापित डिवाइस-विशिष्ट प्रमाण उपलब्ध नहीं है।' if self.language == 'hi'
            else 'No verified device-specific firmware evidence is available.')

    def export_hardware_report(self):
        """Export only local read-only evidence; report always marks matching unverified."""
        if not self.hardware_hints:
            QMessageBox.information(self, 'Hardware report',
                'पहले हार्डवेयर जाँचें।' if self.language == 'hi' else 'Inspect hardware first.')
            return
        filename, _ = QFileDialog.getSaveFileName(self,
            'हार्डवेयर रिपोर्ट सहेजें' if self.language == 'hi' else 'Export hardware report',
            'jatayu-hardware-report.json', 'JSON files (*.json)')
        if filename:
            try:
                write_private_json(filename, json.dumps({**report_payload(self.hardware_hints),
                                              'kernel_evidence_access': self.hardware_evidence_access,
                                              'kernel_evidence_verified': False,
                                              'privacy_notice': 'Inspect the exported report before sharing; redaction is best effort.',
                                              'kernel_evidence_scope': 'current_boot_kernel_journal_last_4000_records',
                                              'kernel_evidence_interpretation': (
                                                  'No matching message in checked logs is not proof of device health or absence of firmware need.'
                                                  if self.language != 'hi' else
                                                  'जाँचे गए लॉग में संदेश न मिलना डिवाइस के सही होने या फ़र्मवेयर की आवश्यकता न होने का प्रमाण नहीं है।'),
                                              'kernel_evidence': [v.to_dict() for v in self.hardware_evidence_results.values()]},
                                              indent=2, ensure_ascii=False))
            except OSError as exc:
                QMessageBox.warning(self, 'Export failed', str(exc))

    def show_live_apt_preview(self, result):
        """Structured, scrollable and bilingual informational APT dialog."""
        hi = self.language == 'hi'
        dialog = QDialog(self)
        dialog.setWindowTitle('APT विश्लेषण (केवल पढ़ें)' if hi else 'APT Analysis (read-only)')
        dialog.resize(760, 610)
        dialog.setMinimumSize(620, 470)
        layout = QVBoxLayout(dialog)
        status_names = {'already_installed': ('पहले से इंस्टॉल', 'Already installed'),
                        'review_required': ('समीक्षा आवश्यक', 'Review required'),
                        'blocked': ('अवरुद्ध', 'Blocked')}
        state_names = {'installed': ('इंस्टॉल है', 'Installed'),
                       'not_installed': ('इंस्टॉल नहीं है', 'Not installed'),
                       'unknown': ('अज्ञात', 'Unknown')}
        def translate(pair):
            return pair[0] if hi else pair[1]
        status = translate(status_names.get(result.get('status'), ('अज्ञात', 'Unknown')))
        installed = translate(state_names.get(result.get('installed_state'), ('अज्ञात', 'Unknown')))
        for heading, value in (
            (('पैकेज', 'Package'), result.get('package', '')),
            (('स्थिति', 'Status'), status),
            (('स्थापित पैकेज', 'Installed package'), installed),
            (('स्थापित संस्करण', 'Installed version'), result.get('installed_version') or '—'),
            (('APT एग्जिट कोड', 'APT exit code'), str(result.get('returncode')))):
            label = self.label(f'{translate(heading)}: {value}', 'previewField')
            label.setWordWrap(True)
            layout.addWidget(label)
        operations_title = self.label('प्रस्तावित क्रियाएँ' if hi else 'Proposed operations', 'sectionTitle')
        layout.addWidget(operations_title)
        operations = QTextEdit()
        operations.setReadOnly(True)
        operations.setMinimumHeight(75)
        operations.setPlainText('\n'.join(result.get('operations') or ['—']))
        layout.addWidget(operations)
        warnings_title = self.label('सुरक्षा चेतावनियाँ' if hi else 'Safety warnings', 'sectionTitle')
        layout.addWidget(warnings_title)
        warning_translations = {
            'Package is already installed; no APT changes proposed': 'पैकेज पहले से इंस्टॉल है; APT ने कोई बदलाव नहीं सुझाया',
            'Installed package does not prove hardware needs or uses it': 'पैकेज इंस्टॉल होने से हार्डवेयर की आवश्यकता सिद्ध नहीं होती',
            'Installed package state could not be verified': 'इंस्टॉल स्थिति की पुष्टि नहीं हो सकी',
            'No package operations found (possibly already installed)': 'कोई पैकेज बदलाव नहीं मिला (संभवतः पहले से इंस्टॉल है)',
            'Requested package not scheduled for installation': 'अनुरोधित पैकेज इंस्टॉल के लिए निर्धारित नहीं है',
            'Live APT simulation is not verified hardware evidence or installation approval': 'APT सिमुलेशन हार्डवेयर का प्रमाण या इंस्टॉलेशन की अनुमति नहीं है',
        }
        warnings = QTextEdit()
        warnings.setReadOnly(True)
        warnings.setPlainText('\n'.join(warning_translations.get(w, w) if hi else w
                                         for w in result.get('warnings', [])) or '—')
        warnings.setMinimumHeight(125)
        layout.addWidget(warnings, 1)
        safety = self.label(('● केवल पढ़ें • इंस्टॉलेशन बंद है • हार्डवेयर मिलान की पुष्टि नहीं' if hi else
                             '● READ ONLY • INSTALLATION DISABLED • HARDWARE MATCH UNVERIFIED'), 'previewSafety')
        safety.setWordWrap(True)
        layout.addWidget(safety)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
        buttons.accepted.connect(dialog.accept)
        layout.addWidget(buttons)
        dialog.exec()

    def export_transaction_preview(self):
        if self.last_transaction_preview is None:
            return
        filename, _ = QFileDialog.getSaveFileName(self, 'Export synthetic transaction preview',
            'jatayu-transaction-demo.json', 'JSON files (*.json)')
        if filename:
            try:
                write_private_json(filename, json.dumps(self.last_transaction_preview, indent=2))
            except OSError as exc:
                QMessageBox.warning(self, 'Export failed', str(exc))

    def build_testing_center(self):
        """Clearly isolated synthetic fixtures: no system changes or real scan injection."""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)
        self.test_intro = self.label('', 'muted')
        self.test_intro.setWordWrap(True)
        layout.addWidget(self.test_intro)
        self.test_panel = self.panel()
        panel = QVBoxLayout(self.test_panel)
        panel.setSpacing(14)
        self.test_heading = self.label('', 'sectionTitle')
        panel.addWidget(self.test_heading)
        self.test_scenario = QComboBox()
        for key in ('wifi', 'graphics', 'network', 'audio', 'bluetooth'):
            self.test_scenario.addItem(key, key)
        panel.addWidget(self.test_scenario)
        self.test_run = QPushButton()
        self.test_run.setMinimumHeight(44)
        self.test_run.clicked.connect(self.run_test_scenario)
        panel.addWidget(self.test_run)
        self.test_result = QTextEdit()
        self.test_result.setReadOnly(True)
        self.test_result.setMinimumHeight(220)
        panel.addWidget(self.test_result)
        self.test_export = QPushButton()
        self.test_export.clicked.connect(self.export_test_result)
        self.test_export.setEnabled(False)
        panel.addWidget(self.test_export)
        layout.addWidget(self.test_panel)
        layout.addStretch()
        self.last_test_result = None
        self.stack.addWidget(page)

    def update_testing_center(self):
        hi = self.language == 'hi'
        self.test_intro.setText('वास्तविक, केवल-पढ़ने वाले हार्डवेयर परीक्षण। कोई ड्राइवर या पैकेज नहीं बदला जाएगा।' if hi else
            'Real read-only hardware checks. No drivers, packages, or system settings are changed.')
        self.test_heading.setText('हार्डवेयर जाँच चुनें' if hi else 'Choose a hardware check')
        labels = (('वाई-फ़ाई', 'ग्राफ़िक्स', 'नेटवर्क', 'ऑडियो', 'ब्लूटूथ') if hi else
                  ('Wi-Fi', 'Graphics', 'Network', 'Audio', 'Bluetooth'))
        for i, title in enumerate(labels):
            self.test_scenario.setItemText(i, title)
        self.test_run.setText('वास्तविक जाँच चलाएँ' if hi else 'Run real hardware check')
        self.test_export.setText('JSON रिपोर्ट सहेजें' if hi else 'Export diagnostic JSON report')
        if self.last_test_result is None:
            self.test_result.setPlainText('जाँच चुनें और चलाएँ। यह केवल-पढ़ने वाला परीक्षण है।' if hi else
                'Select a check and run it. Results come from your current system, not synthetic fixtures.')

    def run_test_scenario(self):
        result = run_live_checks(self.test_scenario.currentData())
        self.last_test_result = result
        hi = self.language == 'hi'
        lines = [('वास्तविक हार्डवेयर जाँच (केवल पढ़ें)' if hi else 'LIVE HARDWARE CHECK (READ-ONLY)'),
                 '', ('जाँच: ' if hi else 'Check: ') + result['category'],
                 ('स्थिति: ' if hi else 'Status: ') + result['status'], '']
        lines.extend(result['details'])
        lines += ['', ('पैकेज स्थापना या सिस्टम परिवर्तन नहीं किया गया।' if hi else
                       'No package installation or system modification was performed.')]
        self.test_result.setPlainText('\n'.join(lines))
        self.test_export.setEnabled(True)

    def export_test_result(self):
        if self.last_test_result is None:
            return
        filename, _ = QFileDialog.getSaveFileName(self, 'Export diagnostic report',
            'jatayu-hardware-check.json', 'JSON files (*.json)')
        if filename:
            try:
                write_private_json(filename, json.dumps(self.last_test_result, indent=2))
            except OSError as exc:
                QMessageBox.warning(self, 'Export failed', str(exc))

    def build_about(self):
        """Branded, scrollable project information with verified project links."""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        content = QWidget()
        self.about_layout = QVBoxLayout(content)
        self.about_layout.setContentsMargins(4, 4, 10, 12)
        self.about_layout.setSpacing(16)

        hero = self.panel()
        hero_row = QHBoxLayout(hero)
        hero_row.setContentsMargins(26, 24, 26, 24)
        icon = QLabel()
        icon.setPixmap(self.app_icon().pixmap(64, 64))
        icon.setFixedSize(72, 72)
        hero_row.addWidget(icon)
        title_col = QVBoxLayout()
        self.about_title = self.label('', 'sectionTitle')
        self.about_text = self.label('', 'aboutBody')
        self.about_text.setWordWrap(True)
        title_col.addWidget(self.about_title)
        title_col.addWidget(self.about_text)
        hero_row.addLayout(title_col, 1)
        self.about_layout.addWidget(hero)

        self.about_os_card = self.panel()
        os_col = QVBoxLayout(self.about_os_card)
        os_col.setContentsMargins(26, 22, 26, 22)
        os_col.setSpacing(12)
        self.about_os_title = self.label('', 'sectionTitle')
        self.about_os_desc = self.label('', 'aboutBody')
        self.about_os_desc.setWordWrap(True)
        self.about_os_info = self.label('', 'muted')
        self.about_os_info.setWordWrap(True)
        os_col.addWidget(self.about_os_title)
        os_col.addWidget(self.about_os_desc)
        os_col.addWidget(self.about_os_info)
        self.website_button = QPushButton()
        self.website_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.website_button.clicked.connect(lambda: QDesktopServices.openUrl(QUrl('https://jatayuos.in')))
        os_col.addWidget(self.website_button, alignment=Qt.AlignmentFlag.AlignLeft)
        self.about_layout.addWidget(self.about_os_card)

        self.about_app_card = self.panel()
        app_col = QVBoxLayout(self.about_app_card)
        app_col.setContentsMargins(26, 22, 26, 22)
        app_col.setSpacing(12)
        self.about_app_title = self.label('', 'sectionTitle')
        self.about_app_info = self.label('', 'aboutBody')
        self.about_app_info.setWordWrap(True)
        self.about_safety = self.label('', 'notice')
        self.about_safety.setWordWrap(True)
        app_col.addWidget(self.about_app_title)
        app_col.addWidget(self.about_app_info)
        app_col.addWidget(self.about_safety)
        self.source_button = QPushButton()
        self.source_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.source_button.clicked.connect(lambda: QDesktopServices.openUrl(QUrl('https://github.com/jatayuos4u/jatayu-driver-assistant')))
        app_col.addWidget(self.source_button, alignment=Qt.AlignmentFlag.AlignLeft)
        self.about_layout.addWidget(self.about_app_card)
        self.about_layout.addStretch()
        scroll.setWidget(content)
        layout.addWidget(scroll)
        self.stack.addWidget(page)

    def build_help(self):
        """Bilingual, offline user guidance with no privileged actions."""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        content = QWidget()
        column = QVBoxLayout(content)
        column.setContentsMargins(6, 6, 14, 18)
        column.setSpacing(14)
        self.help_intro = QLabel()
        self.help_intro.setTextFormat(Qt.TextFormat.PlainText)
        self.help_intro.setWordWrap(True)
        self.help_intro.setObjectName('muted')
        column.addWidget(self.help_intro)
        self.help_sections = []
        for _ in range(6):
            card = self.panel()
            inner = QVBoxLayout(card)
            inner.setContentsMargins(22, 18, 22, 18)
            heading = QLabel()
            heading.setTextFormat(Qt.TextFormat.PlainText)
            heading.setObjectName('sectionTitle')
            body = QLabel()
            body.setTextFormat(Qt.TextFormat.PlainText)
            body.setWordWrap(True)
            body.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            inner.addWidget(heading)
            inner.addWidget(body)
            column.addWidget(card)
            self.help_sections.append((heading, body))
        self.help_site = QPushButton()
        self.help_site.clicked.connect(lambda: QDesktopServices.openUrl(QUrl('https://jatayuos.in')))
        column.addWidget(self.help_site, alignment=Qt.AlignmentFlag.AlignLeft)
        column.addStretch()
        scroll.setWidget(content)
        layout.addWidget(scroll)
        self.stack.addWidget(page)

    def update_help(self):
        hi = self.language == 'hi'
        self.help_intro.setText('सहायता केंद्र • बिना इंटरनेट के उपयोग निर्देश। यह ऐप केवल जाँच करता है।' if hi else
                                'Help Center • Offline usage guide. This application is diagnostic-only.')
        entries_en = [
            ('Getting started', 'Open Overview and select Scan to refresh device information. Use Devices for detected hardware and Diagnostics for basic checks.'),
            ('Recommendations', 'Review detected devices and bound kernel drivers. Package availability does not establish a missing driver or a verified fix.'),
            ('Wi-Fi and firmware', 'The Wi-Fi diagnostic checks interface, driver, NetworkManager and radio-block state. Firmware evidence may require access to restricted kernel logs. Unknown does not mean missing firmware.'),
            ('APT analysis', 'APT analysis only previews package status and possible changes. An installed package does not prove it is required. No packages are installed or removed.'),
            ('Permissions and safety', 'Run the desktop application as your normal user. Do not disable kernel log restrictions or run the whole GUI with sudo. Driver installation and repair are disabled.'),
            ('Troubleshooting and reports', 'If a scan fails, retry and review the error. Use Export to save a hardware report; review it before sharing because hardware identifiers may be included. For help visit jatayuos.in.')
        ]
        entries_hi = [
            ('शुरू कैसे करें', 'ओवरव्यू खोलें और डिवाइस की जानकारी अपडेट करने के लिए स्कैन चुनें। डिवाइस और डायग्नोस्टिक्स पेज पर जानकारी देखें।'),
            ('सुझाव', 'डिवाइस और उनके कर्नेल ड्राइवर देखें। पैकेज उपलब्ध होना किसी समस्या के समाधान का प्रमाण नहीं है।'),
            ('वाई-फ़ाई और फ़र्मवेयर', 'वाई-फ़ाई जाँच इंटरफ़ेस, ड्राइवर, NetworkManager और रेडियो ब्लॉक दिखाती है। कर्नेल लॉग के लिए अतिरिक्त अनुमति आवश्यक हो सकती है। अज्ञात का अर्थ फ़र्मवेयर गायब होना नहीं है।'),
            ('APT विश्लेषण', 'APT विश्लेषण केवल पैकेज की स्थिति और संभावित बदलाव दिखाता है। पैकेज इंस्टॉल होने का अर्थ यह नहीं कि वह ज़रूरी है। कोई पैकेज इंस्टॉल या हटाया नहीं जाता।'),
            ('अनुमतियाँ और सुरक्षा', 'ऐप सामान्य उपयोगकर्ता के रूप में चलाएँ। कर्नेल लॉग की सुरक्षा बंद न करें और पूरे GUI को sudo से न चलाएँ। ड्राइवर इंस्टॉलेशन और मरम्मत बंद हैं।'),
            ('समस्या समाधान और रिपोर्ट', 'स्कैन विफल हो तो दोबारा कोशिश करें और त्रुटि देखें। एक्सपोर्ट से हार्डवेयर रिपोर्ट सहेजें। साझा करने से पहले जाँचें क्योंकि इसमें हार्डवेयर पहचान हो सकती है। सहायता: jatayuos.in।')
        ]
        for (heading, body), (title, desc) in zip(self.help_sections, entries_hi if hi else entries_en):
            heading.setText(title)
            body.setText(desc)
        self.help_site.setText('जटायुOS वेबसाइट खोलें  ↗' if hi else 'Visit JatayuOS website  ↗')

    def update_about(self):
        hi = self.language == 'hi'
        self.about_title.setText('जटायु ड्राइवर असिस्टेंट' if hi else 'Jatayu Driver Assistant')
        self.about_text.setText(('संस्करण 1.2.4 • हार्डवेयर जाँच और सुरक्षित ड्राइवर सुझावों के लिए ऐप।'
            if hi else 'Version 1.2.4 • Read-only hardware diagnostics and driver recommendations.'))
        self.about_os_title.setText('जटायुOS के बारे में' if hi else 'About JatayuOS')
        self.about_os_desc.setText(('JatayuOS एक Linux वितरण परियोजना है। यह ऐप Debian 13 और KDE Plasma 6 के लिए बनाया गया है।'
            if hi else 'JatayuOS is a Linux distribution project. This assistant is developed for its Debian 13 and KDE Plasma 6 environment.'))
        self.about_os_info.setText(('आधिकारिक वेबसाइट: https://jatayuos.in\nपरियोजना: JatayuOS Project'
            if hi else 'Official website: https://jatayuos.in\nProject: JatayuOS Project'))
        self.website_button.setText('वेबसाइट खोलें  ↗' if hi else 'Visit JatayuOS website  ↗')
        self.about_app_title.setText('एप्लिकेशन की जानकारी' if hi else 'Application information')
        self.about_app_info.setText((
            'संस्करण: 1.2.4\nलक्ष्य: Debian 13 / KDE Plasma 6\nलाइसेंस: GPL-3.0-or-later\n'
            'विकास: JatayuOS Project\nस्रोत: github.com/jatayuos4u/jatayu-driver-assistant'
            if hi else 'Version: 1.2.4\nTarget: Debian 13 / KDE Plasma 6\n'
            'License: GPL-3.0-or-later\nDeveloper: JatayuOS Project\nSource: github.com/jatayuos4u/jatayu-driver-assistant'))
        self.about_safety.setText(('सुरक्षा: बेसिक संस्करण केवल जानकारी दिखाता है; ड्राइवर इंस्टॉल या रिपेयर नहीं करता।'
            if hi else 'Safety: Basic Edition is read-only; it cannot install or repair drivers.'))
        self.source_button.setText('GitHub रिपॉजिटरी खोलें  ↗' if hi else 'View GitHub repository  ↗')

    def t(self, key):
        return tr(self.language, key)

    def navigate(self, index):
        self.page_index = index
        self.stack.setCurrentIndex(index)
        names = ('overview', 'devices', 'diagnostics', 'recommendations', 'help', 'about')
        key = names[index]
        self.header_title.setText(('सहायता' if self.language == 'hi' else 'Help') if key == 'help' else self.t(key))
        for i, (_, button) in enumerate(self.nav_buttons):
            button.setProperty('selected', i == index)
            button.style().unpolish(button)
            button.style().polish(button)

    def change_language(self):
        self.language = self.language_box.currentData() or 'en'
        self.retranslate()

    def retranslate(self):
        self.setWindowTitle(self.t('app'))
        self.nav_label.setText(self.t('workspace'))
        for (icon, button), key in zip(self.nav_buttons, ('overview', 'devices', 'diagnostics', 'recommendations', 'help', 'about')):
            title = ('सहायता' if self.language == 'hi' else 'Help') if key == 'help' else self.t(key)
            button.setText(f'{icon}    {title}')
        self.side_info.setText(self.t('side_info'))
        self.hero_badge.setText(self.t('hero_badge'))
        self.hero_title.setText(self.t('hero_title'))
        self.hero_desc.setText(self.t('hero_desc'))
        self.scan_button.setText('↻  ' + self.t('scan'))
        for (_, label), key in zip(self.cards, ('detected', 'drivers', 'unbound', 'unknown')):
            label.setText(self.t(key))
        self.section_title.setText(self.t('recent_devices'))
        self.see_all.setText(self.t('view_all') + '  →')
        self.notice.setText('ⓘ  ' + self.t('notice'))
        self.devices_desc.setText(self.t('devices_desc'))
        self.diag_intro.setText(self.t('diag_intro'))
        self.search.setPlaceholderText('⌕  ' + self.t('search'))
        self.export_button.setText('⇩  ' + self.t('export'))
        self.detail_heading.setText(self.t('details'))
        self.update_about()
        self.update_help()
        self.table.setHorizontalHeaderLabels([self.t(k) for k in ('category', 'device', 'driver', 'status')])
        previous = self.category.currentData()
        self.category.blockSignals(True)
        self.category.clear()
        self.category.addItem(self.t('all'), '')
        for category in sorted({d.category for d in self.devices}):
            self.category.addItem(category, category)
        self.category.setCurrentIndex(max(self.category.findData(previous), 0))
        self.category.blockSignals(False)
        self.update_metrics()
        self.refresh_table()
        self.refresh_diagnostics()
        self.refresh_recommendations()
        self.navigate(self.page_index)

    def update_metrics(self):
        counts = summarize(self.devices)
        values = (counts['detected'], counts['bound'], counts['unbound'], counts['unknown'])
        for (label, _), value in zip(self.cards, values):
            label.setText(str(value))
        # Do not hide child widgets while their stacked page is hidden: in Qt,
        # show() on a child of a hidden page can leave it explicitly invisible.
        # Keep five permanent rows and populate them, including empty states.
        priority = {'unbound': 0, 'unknown': 1, 'bound': 2}
        visible = sorted(self.devices, key=lambda d: (priority[binding_state(d)], d.category, d.name))[:5]
        for index, (row, name, sub, status) in enumerate(self.preview_rows):
            if index < len(visible):
                d = visible[index]
                name.setText(d.name)
                sub.setText(f'{d.category}  ·  {d.driver or self.t("none")}')
                status.setText(self.status_text(d))
            elif not self.devices and index == 0:
                name.setText(self.t('no_devices'))
                sub.setText(self.t('scan'))
                status.setText('')
            else:
                name.setText('')
                sub.setText('')
                status.setText('')
            # Keep rows visible; explicit hide/show before stacked-page activation
            # caused blank previews in earlier Qt builds.
            row.setMinimumHeight(68)

    def status_text(self, d):
        return self.t({'bound': 'bound', 'unbound': 'unbound_status',
                       'unknown': 'unknown_status'}[binding_state(d)])

    @staticmethod
    def app_icon():
        paths = [Path('/usr/share/icons/hicolor/scalable/apps/in.jatayuos.DriverAssistant.svg'),
                 Path(__file__).resolve().parent.parent / 'packaging/in.jatayuos.DriverAssistant.svg']
        for path in paths:
            if path.is_file():
                return QIcon(str(path))
        return QIcon.fromTheme('applications-system')

    def scan(self):
        if self.worker is not None and self.worker.isRunning():
            return
        self.scan_button.setEnabled(False)
        self.footer_status.setText('◌  ' + self.t('scanning'))
        self.worker = ScanThread()
        self.worker.complete.connect(self.scan_finished)
        self.worker.failed.connect(self.scan_failed)
        self.worker.finished.connect(self.worker.deleteLater)
        self.worker.start()

    def scan_finished(self, devices):
        self.devices = devices
        self.scan_button.setEnabled(True)
        self.retranslate()
        self.footer_status.setText('●  ' + self.t('ready'))
        if self.firmware_worker is None or not self.firmware_worker.isRunning():
            self.firmware_note = 'Checking accessible kernel firmware messages…'
            self.firmware_worker = FirmwareThread(self)
            self.firmware_worker.complete.connect(self.firmware_finished)
            self.firmware_worker.start()

    def firmware_finished(self, findings, note):
        self.firmware_findings = findings
        self.firmware_note = note
        self.refresh_diagnostics()
        self.refresh_recommendations()

    def scan_failed(self, error):
        self.scan_button.setEnabled(True)
        self.footer_status.setText(self.t('error'))
        QMessageBox.warning(self, self.t('error'), error)

    def visible_devices(self):
        term = self.search.text().casefold().strip()
        category = self.category.currentData() or ''
        return [d for d in self.devices if (not category or d.category == category) and
                (not term or term in ' '.join((d.name, d.category, d.driver, d.identifier)).casefold())]

    def refresh_table(self):
        items = self.visible_devices()
        self.table.setRowCount(len(items))
        for row, d in enumerate(items):
            for col, value in enumerate((d.category, d.name, d.driver or self.t('none'), self.status_text(d))):
                cell = QTableWidgetItem(value)
                if col == 0:
                    cell.setData(Qt.ItemDataRole.UserRole, d)
                self.table.setItem(row, col, cell)
        if items:
            self.table.selectRow(0)
        else:
            self.detail_label.setText(self.t('no_devices'))

    def show_detail(self):
        row = self.table.currentRow()
        item = self.table.item(row, 0) if row >= 0 else None
        if item is None:
            return
        d = item.data(Qt.ItemDataRole.UserRole)
        self.detail_label.setText(f'{d.name}\n{d.bus} · {d.identifier}\n{self.t("driver")}: {d.driver or self.t("none")}\n{self.t("status")}: {self.status_text(d)}\n{d.detail}\n\n{self.t("binding_note")}')

    def export(self):
        filename, _ = QFileDialog.getSaveFileName(self, self.t('choose'),
                                                   'jatayu-hardware-report.json', 'JSON (*.json)')
        if not filename:
            return
        payload = {'application': 'Jatayu Driver Assistant', 'version': '1.2.4',
                   'generated_utc': datetime.now(timezone.utc).isoformat(),
                   'disclaimer': tr('en', 'disclaimer'),
                   'summary': summarize(self.devices),
                   'devices': [d.as_dict() for d in self.devices],
                   'findings': [f.as_dict() for f in analyze(self.devices)],
                   'firmware_evidence': [f.as_dict() for f in self.firmware_findings],
                   'firmware_access_note': self.firmware_note,
                   'privacy_notice': 'Identifiers are redacted where recognized. Inspect the report before sharing.'}
        try:
            write_private_json(filename, json.dumps(payload, indent=2, ensure_ascii=False) + '\n')
            self.footer_status.setText('●  ' + self.t('saved'))
        except OSError as exc:
            QMessageBox.warning(self, self.t('error'), str(exc))

    def apply_theme(self):
        dark = self.palette().color(self.backgroundRole()).lightness() < 128
        bg, side, panel, border, text, muted, inputbg = (
            ('#10141e', '#151c29', '#1b2432', '#344053', '#f2f6fc', '#a5b2c5', '#121925') if dark else
            ('#f4f7fb', '#ffffff', '#ffffff', '#e1e8f0', '#17243a', '#6b7b91', '#f8fafc'))
        self.setStyleSheet(f'''
            QWidget {{ font-family: "Noto Sans", "Sans Serif"; color: {text}; font-size: 13px; }}
            QMainWindow, #content {{ background: {bg}; }}
            #sidebar {{ background: {side}; border-right: 1px solid {border}; }}
            #emblem {{ background: transparent; border: 0; }}
            #brandName {{ font-size: 18px; font-weight: 800; letter-spacing: 1px; }}
            #brandSub {{ font-size: 9px; font-weight: 700; color: {muted}; letter-spacing: 1px; }}
            #navSection, #kicker, #version, #footer {{ color: {muted}; font-size: 11px; font-weight: 600; }}
            #sideInfo {{ color: {muted}; font-size: 12px; line-height: 1.4; }}
            QPushButton[nav="true"] {{ background: transparent; border: 0; border-radius: 10px; text-align: left; padding: 0 14px; font-weight: 600; }}
            QPushButton[nav="true"]:hover {{ background: {bg}; }}
            QPushButton[nav="true"][selected="true"] {{ background: #2563eb; color: white; }}
            #pageTitle {{ font-size: 29px; font-weight: 800; }}
            #hero {{ background: #173b83; border-radius: 16px; }}
            #heroBadge {{ color: #bcd6ff; font-size: 11px; font-weight: 700; }}
            #heroTitle {{ color: white; font-size: 24px; font-weight: 800; }}
            #heroDesc {{ color: #d7e6ff; font-size: 12px; }}
            #primaryButton {{ background: white; color: #17418c; border: 0; border-radius: 9px; padding: 0 18px; font-weight: 800; }}
            #primaryButton:hover {{ background: #e6efff; }}
            #primaryButton:disabled {{ background: #b6c5df; }}
            #panel {{ background: {panel}; border: 1px solid {border}; border-radius: 13px; }}
            #metricGlyph {{ color: #3b82f6; font-size: 20px; }}
            #metricValue {{ font-size: 30px; font-weight: 800; }}
            #metricCaption, #deviceSub, #muted, #aboutBody {{ color: {muted}; font-size: 12px; }}
            #sectionTitle {{ font-size: 17px; font-weight: 800; }}
            #deviceName {{ font-weight: 650; font-size: 13px; }}
            #deviceGlyph {{ color: #3b82f6; font-size: 21px; }}
            #deviceStatus {{ color: {'#62d9b0' if dark else '#087e61'}; font-weight: 650; font-size: 11px; }}
            #previewScroll, #previewBody, #previewRow {{ background: transparent; border: none; }}
            #previewRow {{ border-bottom: 1px solid {border}; }}
            #previewSafety {{ background: {'#153c55' if dark else '#e4f2fb'}; color: {'#b7e6ff' if dark else '#175275'}; border-radius: 8px; padding: 11px; font-weight: 800; }}
            #previewStatus {{ padding: 12px; border-radius: 9px; font-weight: 800; background: {inputbg}; }}
            #previewStatus[reviewState="review"] {{ color: {'#fcd58d' if dark else '#8b5800'}; }}
            #previewStatus[reviewState="blocked"] {{ color: {'#ff9d9d' if dark else '#a21d1d'}; }}
            #previewField {{ background: {inputbg}; border: 1px solid {border}; border-radius: 8px; padding: 12px; }}
            #previewFingerprint {{ background: {inputbg}; border-radius: 8px; padding: 10px; color: {muted}; font-family: monospace; }}
            #notice {{ color: {muted}; background: {panel}; border: 1px solid {border}; border-radius: 9px; padding: 12px; }}
            #textButton {{ color: #3b82f6; border: none; background: transparent; font-weight: 700; }}
            QLineEdit, QComboBox {{ background: {inputbg}; border: 1px solid {border}; border-radius: 9px; padding: 9px 12px; }}
            QComboBox::drop-down {{ border: 0; width: 24px; }}
            QPushButton {{ background: {panel}; border: 1px solid {border}; border-radius: 9px; padding: 9px 15px; font-weight: 600; }}
            QPushButton:hover {{ border-color: #3b82f6; }}
            QTableWidget {{ background: {panel}; alternate-background-color: {panel}; border: none; selection-background-color: {'#243b5c' if dark else '#e9f1ff'}; selection-color: {text}; }}
            QTableWidget::item {{ padding: 7px; border-bottom: 1px solid {border}; }}
            QHeaderView::section {{ background: {panel}; color: {muted}; border: none; border-bottom: 1px solid {border}; padding: 12px 8px; font-weight: 700; }}
            QScrollBar:vertical {{ background: transparent; width: 10px; }}
            QScrollBar::handle:vertical {{ background: {border}; border-radius: 5px; }}
        ''')


def main():
    app = QApplication(sys.argv)
    app.setApplicationName('Jatayu Driver Assistant')
    app.setDesktopFileName('in.jatayuos.DriverAssistant')
    window = Window()
    window.show()
    sys.exit(app.exec())
