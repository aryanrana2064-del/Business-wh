"""Main window: Dashboard, Customers, Quick Entry, Ledger, Reports, Backup."""
from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import QStandardPaths, Qt, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QFileDialog, QFormLayout, QFrame, QGridLayout, QGroupBox, QHBoxLayout, QLabel,
    QLineEdit, QMainWindow, QMessageBox, QPushButton, QTabWidget, QVBoxLayout, QWidget,
)

from .. import APP_NAME, __version__, backup, dates, exports, money
from ..service import DuplicateEntryError, KhataError, KhataService
from .dialogs import CustomerDialog, EditEntryDialog
from .widgets import (
    DateField, EntryForm, balance_color, fit_columns, make_table, populate_customer_combo, selected_id, set_cell,
)

TAB_DASHBOARD, TAB_CUSTOMERS, TAB_ENTRY, TAB_LEDGER, TAB_REPORTS, TAB_BACKUP = range(6)


def _safe_filename(text: str) -> str:
    return re.sub(r"[^\w\-]+", "_", text, flags=re.UNICODE).strip("_") or "khata"


def _documents_dir() -> str:
    return QStandardPaths.writableLocation(QStandardPaths.StandardLocation.DocumentsLocation) or str(Path.home())


class StatCard(QFrame):
    def __init__(self, title: str):
        super().__init__()
        self.setObjectName("card")
        self.title = QLabel(title)
        self.title.setObjectName("cardTitle")
        self.value = QLabel("-")
        self.value.setObjectName("cardValue")
        layout = QVBoxLayout(self)
        layout.addWidget(self.title)
        layout.addWidget(self.value)

    def set(self, text: str, color: str | None = None) -> None:
        self.value.setText(text)
        self.value.setStyleSheet(f"color: {color};" if color else "")


class MainWindow(QMainWindow):
    def __init__(self, service: KhataService):
        super().__init__()
        self.svc = service
        self.setWindowTitle(f"{APP_NAME}  –  Khata-Bahi")
        self.resize(1180, 740)
        self._saving = False

        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)
        self._build_dashboard()
        self._build_customers()
        self._build_entry()
        self._build_ledger()
        self._build_reports()
        self._build_backup()
        self.tabs.currentChanged.connect(self._on_tab_changed)
        self.refresh_all()

    # ------------------------------------------------------------ shared
    def info(self, title: str, text: str) -> None:
        QMessageBox.information(self, title, text)

    def warn(self, title: str, text: str) -> None:
        QMessageBox.warning(self, title, text)

    def confirm(self, title: str, text: str, default_no: bool = True) -> bool:
        box = QMessageBox(QMessageBox.Icon.Question, title, text,
                          QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, self)
        box.setDefaultButton(QMessageBox.StandardButton.No if default_no else QMessageBox.StandardButton.Yes)
        return box.exec() == QMessageBox.StandardButton.Yes

    def shop_name(self) -> str:
        return self.svc.get_setting("shop_name", "")

    def website(self) -> str:
        """Printed on reports only when the user has configured one."""
        return " ".join(self.svc.get_setting("website", "").split())

    def _on_tab_changed(self, index: int) -> None:
        self.refresh_all()

    def refresh_all(self) -> None:
        summaries = self.svc.list_customers()
        self._refresh_dashboard()
        self._refresh_customers(summaries)
        populate_customer_combo(self.entry_form.customer, summaries)
        populate_customer_combo(self.ledger_customer, summaries)
        populate_customer_combo(self.report_customer, summaries, include_all=True)
        self.entry_form.date.refresh_limits()
        self.entry_form.deposit_date.refresh_limits()
        self.ledger_from.refresh_limits()
        self.ledger_to.refresh_limits()
        self.rep_from.refresh_limits()
        self.rep_to.refresh_limits()
        self._refresh_ledger()
        self._refresh_backup_info()

    def _export_path(self, title: str, default_name: str, pattern: str) -> str | None:
        path, _ = QFileDialog.getSaveFileName(self, title, str(Path(_documents_dir()) / default_name), pattern)
        return path or None

    def _offer_open(self, path) -> None:
        if self.confirm("Export complete", f"Saved:\n{path}\n\nOpen it now?", default_no=False):
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))

    # ------------------------------------------------------------ dashboard
    def _build_dashboard(self) -> None:
        page = QWidget()
        outer = QVBoxLayout(page)
        grid = QGridLayout()
        self.cards = {
            "customers": StatCard("Total Customers"),
            "udhaar": StatCard("Total Udhaar"),
            "jama": StatCard("Total Deposit"),
            "net": StatCard("Net Outstanding Balance"),
            "today": StatCard("Today's Transactions"),
            "historical": StatCard("Historical Transactions"),
        }
        for i, card in enumerate(self.cards.values()):
            grid.addWidget(card, i // 3, i % 3)
        outer.addLayout(grid)
        note = QLabel(
            "Today's = entries dated today (a deposit counts on its deposit date).  Historical = dated before today.\n"
            "Net outstanding = total udhaar − total deposit (positive: customers owe you)."
        )
        note.setStyleSheet("color: #666;")
        outer.addWidget(note)
        outer.addStretch(1)
        self.tabs.addTab(page, "Dashboard")

    def _refresh_dashboard(self) -> None:
        d = self.svc.dashboard()
        self.cards["customers"].set(str(d.total_customers))
        self.cards["udhaar"].set(money.format_inr(d.total_udhaar))
        self.cards["jama"].set(money.format_inr(d.total_jama))
        self.cards["net"].set(money.format_inr(d.net_outstanding), balance_color(d.net_outstanding))
        self.cards["today"].set(str(d.todays_transactions))
        self.cards["historical"].set(str(d.historical_transactions))

    # ------------------------------------------------------------ customers
    def _build_customers(self) -> None:
        page = QWidget()
        layout = QVBoxLayout(page)
        top = QHBoxLayout()
        self.cust_search = QLineEdit()
        self.cust_search.setPlaceholderText("Search by name or phone…")
        self.cust_search.setClearButtonEnabled(True)
        self.cust_search.textChanged.connect(lambda _t: self._refresh_customers())
        add = QPushButton("Add customer")
        edit = QPushButton("Edit")
        ledger = QPushButton("Open ledger")
        entry = QPushButton("Add entry")
        delete = QPushButton("Delete customer")
        add.clicked.connect(self._add_customer)
        edit.clicked.connect(self._edit_customer)
        ledger.clicked.connect(self._open_customer_ledger)
        entry.clicked.connect(self._entry_for_customer)
        delete.clicked.connect(self._delete_customer)
        top.addWidget(self.cust_search, 1)
        for b in (add, edit, ledger, entry, delete):
            top.addWidget(b)
        layout.addLayout(top)

        self.cust_table = make_table(["Name", "Mobile", "Address", "Total Udhaar (₹)", "Total Deposit (₹)", "Deposit Balance (₹)"])
        fit_columns(self.cust_table, 2)
        self.cust_table.doubleClicked.connect(lambda _i: self._open_customer_ledger())
        layout.addWidget(self.cust_table, 1)
        self.cust_total = QLabel("")
        self.cust_total.setStyleSheet("font-weight: bold; font-size: 13px;")
        layout.addWidget(self.cust_total)
        self.tabs.addTab(page, "Customers")

    def _refresh_customers(self, summaries=None) -> None:
        all_summaries = summaries if summaries is not None else self.svc.list_customers()
        needle = self.cust_search.text()
        shown = self.svc.list_customers(needle) if needle.strip() else all_summaries
        keep = selected_id(self.cust_table)
        self.cust_table.setRowCount(len(shown))
        for r, s in enumerate(shown):
            c = s.customer
            set_cell(self.cust_table, r, 0, c.name, data=c.id)
            set_cell(self.cust_table, r, 1, c.mobile)
            set_cell(self.cust_table, r, 2, c.address.replace("\n", " "))
            set_cell(self.cust_table, r, 3, money.format_inr(s.total_udhaar), right=True)
            set_cell(self.cust_table, r, 4, money.format_inr(s.total_jama), right=True)
            set_cell(self.cust_table, r, 5, money.format_inr(s.balance), right=True,
                     color=balance_color(s.balance), bold=True)
            if keep == c.id:
                self.cust_table.selectRow(r)
        tu = sum(s.total_udhaar for s in all_summaries)
        tj = sum(s.total_jama for s in all_summaries)
        self.cust_total.setText(
            f"Overall (all {len(all_summaries)} customers):  Udhaar {money.format_inr(tu)}   "
            f"Deposit {money.format_inr(tj)}   Deposit balance {money.format_inr(tu - tj)}"
        )

    def _current_customer_id(self) -> int | None:
        cid = selected_id(self.cust_table)
        if cid is None:
            self.info("Select a customer", "Click a customer row first.")
        return cid

    def _add_customer(self) -> None:
        dlg = CustomerDialog(self.svc, parent=self)
        if dlg.exec():
            self.refresh_all()

    def _edit_customer(self) -> None:
        cid = self._current_customer_id()
        if cid is None:
            return
        dlg = CustomerDialog(self.svc, self.svc.get_customer(cid), parent=self)
        if dlg.exec():
            self.refresh_all()

    def _delete_customer(self) -> None:
        cid = self._current_customer_id()
        if cid is None:
            return
        customer = self.svc.get_customer(cid)
        if not self.confirm("Delete customer", f"Delete customer '{customer.name}'?\n"
                            "Only customers with no khata entries can be deleted."):
            return
        try:
            self.svc.delete_customer(cid)
        except KhataError as exc:
            self.warn("Cannot delete", str(exc))
            return
        self.refresh_all()

    def _open_customer_ledger(self) -> None:
        cid = self._current_customer_id()
        if cid is None:
            return
        self.ledger_customer.setCurrentIndex(max(0, self.ledger_customer.findData(cid)))
        self.tabs.setCurrentIndex(TAB_LEDGER)

    def _entry_for_customer(self) -> None:
        cid = self._current_customer_id()
        if cid is None:
            return
        self.entry_form.select_customer(cid)
        self.tabs.setCurrentIndex(TAB_ENTRY)
        self.entry_form.item.setFocus()

    # ------------------------------------------------------------ quick entry
    def _build_entry(self) -> None:
        page = QWidget()
        layout = QVBoxLayout(page)
        box = QGroupBox("Quick entry – record udhaar or jama (any date, including old dates)")
        inner = QVBoxLayout(box)
        self.entry_form = EntryForm(with_customer=True)
        self.entry_form.new_customer_button.clicked.connect(self._quick_new_customer)
        self.entry_form.item.returnPressed.connect(self._save_entry)
        self.entry_form.amount.returnPressed.connect(self._save_entry)
        inner.addWidget(self.entry_form)
        buttons = QHBoxLayout()
        self.entry_save = QPushButton("Save entry")
        self.entry_save.setDefault(True)
        self.entry_save.clicked.connect(self._save_entry)
        clear = QPushButton("Clear")
        clear.clicked.connect(self.entry_form.clear_for_next)
        buttons.addStretch(1)
        buttons.addWidget(clear)
        buttons.addWidget(self.entry_save)
        inner.addLayout(buttons)
        layout.addWidget(box)

        hint = QLabel("After saving, the customer, type and date stay selected so you can enter the next item immediately.")
        hint.setStyleSheet("color: #666;")
        layout.addWidget(hint)
        layout.addWidget(QLabel("Entries saved in this session:"))
        self.recent_table = make_table(["Customer", "Transaction date", "Item / Description", "Type", "Amount", "Deposit date", "Saved at"])
        fit_columns(self.recent_table, 2)
        layout.addWidget(self.recent_table, 1)
        self.tabs.addTab(page, "Quick Entry")

    def _quick_new_customer(self) -> None:
        dlg = CustomerDialog(self.svc, parent=self)
        if dlg.exec() and dlg.saved:
            self.refresh_all()
            self.entry_form.select_customer(dlg.saved.id)

    def _save_entry(self) -> None:
        if self._saving:
            return
        self._saving = True
        self.entry_save.setEnabled(False)
        try:
            try:
                cid = self.entry_form.customer_id()
                values = self.entry_form.values()
                try:
                    txn = self.svc.add_transaction(cid, **values)
                except DuplicateEntryError as exc:
                    if not self.confirm("Possible duplicate", f"{exc}\n\nSave it again anyway?"):
                        return
                    txn = self.svc.add_transaction(cid, allow_duplicate=True, **values)
            except KhataError as exc:
                self.warn("Cannot save entry", str(exc))
                return
            customer = self.svc.get_customer(cid)
            row = 0
            self.recent_table.insertRow(row)
            set_cell(self.recent_table, row, 0, customer.name)
            set_cell(self.recent_table, row, 1, dates.format_date(txn.txn_date))
            set_cell(self.recent_table, row, 2, txn.item)
            set_cell(self.recent_table, row, 3, txn.txn_type)
            set_cell(self.recent_table, row, 4, money.format_inr(txn.amount_paise), right=True,
                     color=balance_color(txn.amount_paise if txn.txn_type == "UDHAAR" else -txn.amount_paise))
            set_cell(self.recent_table, row, 5, dates.format_date(txn.deposit_date) if txn.deposit_date else "")
            set_cell(self.recent_table, row, 6, datetime.fromisoformat(txn.created_at).strftime("%H:%M:%S"))
            self.entry_form.clear_for_next()
            self.refresh_all()
        finally:
            self._saving = False
            self.entry_save.setEnabled(True)

    # ------------------------------------------------------------ ledger
    def _build_ledger(self) -> None:
        page = QWidget()
        layout = QVBoxLayout(page)

        filters = QHBoxLayout()
        self.ledger_customer = QComboBox()
        self.ledger_customer.setMinimumWidth(220)
        self.ledger_range = QCheckBox("Date range")
        self.ledger_range.setToolTip("Udhaar is filtered by its transaction date, deposits by their deposit date.")
        self.ledger_from = DateField()
        self.ledger_to = DateField()
        self.ledger_from.setEnabled(False)
        self.ledger_to.setEnabled(False)
        self.ledger_search = QLineEdit()
        self.ledger_search.setPlaceholderText("Search item description…")
        self.ledger_search.setClearButtonEnabled(True)
        filters.addWidget(QLabel("Customer"))
        filters.addWidget(self.ledger_customer)
        filters.addWidget(self.ledger_range)
        filters.addWidget(QLabel("From"))
        filters.addWidget(self.ledger_from)
        filters.addWidget(QLabel("To"))
        filters.addWidget(self.ledger_to)
        filters.addWidget(self.ledger_search, 1)
        layout.addLayout(filters)

        self.ledger_customer.currentIndexChanged.connect(lambda _i: self._refresh_ledger())
        self.ledger_range.toggled.connect(self._ledger_range_toggled)
        self.ledger_from.dateChanged.connect(lambda _d: self._refresh_ledger())
        self.ledger_to.dateChanged.connect(lambda _d: self._refresh_ledger())
        self.ledger_search.textChanged.connect(lambda _t: self._refresh_ledger())

        self.ledger_table = make_table(["Transaction Date", "Item / Description", "Qty", "Rate", "Udhaar (₹)", "Total Deposit (₹)",
                                   "Deposit Date", "Deposit Balance (₹)", "Notes"])
        fit_columns(self.ledger_table, 1)
        self.ledger_table.doubleClicked.connect(lambda _i: self._edit_entry())
        layout.addWidget(self.ledger_table, 1)

        self.ledger_summary = QLabel("")
        self.ledger_summary.setStyleSheet("font-weight: bold; font-size: 13px;")
        self.ledger_note = QLabel("")
        self.ledger_note.setStyleSheet("color: #666;")
        layout.addWidget(self.ledger_summary)
        layout.addWidget(self.ledger_note)

        buttons = QHBoxLayout()
        add = QPushButton("Add entry")
        edit = QPushButton("Edit selected")
        delete = QPushButton("Delete selected")
        pdf = QPushButton("Export statement PDF")
        xlsx = QPushButton("Export statement Excel")
        add.clicked.connect(self._ledger_add_entry)
        edit.clicked.connect(self._edit_entry)
        delete.clicked.connect(self._delete_entry)
        pdf.clicked.connect(lambda: self._export_statement("pdf"))
        xlsx.clicked.connect(lambda: self._export_statement("xlsx"))
        for b in (add, edit, delete):
            buttons.addWidget(b)
        buttons.addStretch(1)
        buttons.addWidget(pdf)
        buttons.addWidget(xlsx)
        layout.addLayout(buttons)
        self.tabs.addTab(page, "Ledger")

    def _ledger_range_toggled(self, on: bool) -> None:
        self.ledger_from.setEnabled(on)
        self.ledger_to.setEnabled(on)
        self._refresh_ledger()

    def _ledger_args(self) -> dict:
        args = {"search": self.ledger_search.text()}
        if self.ledger_range.isChecked():
            args["date_from"] = self.ledger_from.text_dmy()
            args["date_to"] = self.ledger_to.text_dmy()
        return args

    def _current_ledger(self):
        cid = self.ledger_customer.currentData()
        if cid is None:
            return None
        return self.svc.ledger(cid, **self._ledger_args())

    def _refresh_ledger(self) -> None:
        self.ledger_table.setRowCount(0)
        try:
            led = self._current_ledger()
        except KhataError as exc:
            self.ledger_summary.setText("")
            self.ledger_note.setText(str(exc))
            return
        if led is None:
            self.ledger_summary.setText("Add a customer to begin.")
            self.ledger_note.setText("")
            return
        self.ledger_table.setRowCount(len(led.rows))
        for r, row in enumerate(led.rows):
            t = row.txn
            set_cell(self.ledger_table, r, 0, dates.format_date(t.txn_date), data=t.id)
            set_cell(self.ledger_table, r, 1, t.item)
            set_cell(self.ledger_table, r, 2, t.quantity or "", right=True)
            set_cell(self.ledger_table, r, 3, money.format_inr(t.rate_paise, symbol=False) if t.rate_paise else "", right=True)
            set_cell(self.ledger_table, r, 4, money.format_inr(row.udhaar, symbol=False) if row.udhaar else "",
                     right=True, color=RED_IF(row.udhaar))
            set_cell(self.ledger_table, r, 5, money.format_inr(row.jama, symbol=False) if row.jama else "",
                     right=True, color="#1b6e3c" if row.jama else None)
            set_cell(self.ledger_table, r, 6, dates.format_date(row.deposit_date) if row.deposit_date else "")
            set_cell(self.ledger_table, r, 7, money.format_inr(row.balance, symbol=False), right=True,
                     color=balance_color(row.balance), bold=True)
            set_cell(self.ledger_table, r, 8, t.notes.replace("\n", " "))
        self.ledger_summary.setText(
            f"Opening {money.format_inr(led.opening_balance)}   |   "
            f"Total Udhaar {money.format_inr(led.total_udhaar)}   Total Deposit {money.format_inr(led.total_deposit)}   "
            f"({len(led.rows)} entries)   |   Final Deposit Balance {money.format_inr(led.deposit_balance)}"
        )
        note = ("Entries are in date order; a deposit sits at its Deposit Date, not the day it was entered. "
                "Entries on the same date keep the order they were entered.")
        if led.search:
            note = "Item search is active: running balance still shows the true account balance. " + note
        self.ledger_note.setText(note)

    def _ledger_add_entry(self) -> None:
        cid = self.ledger_customer.currentData()
        if cid is not None:
            self.entry_form.select_customer(cid)
        self.tabs.setCurrentIndex(TAB_ENTRY)

    def _selected_txn_id(self) -> int | None:
        tid = selected_id(self.ledger_table)
        if tid is None:
            self.info("Select an entry", "Click an entry row first.")
        return tid

    def _edit_entry(self) -> None:
        tid = self._selected_txn_id()
        if tid is None:
            return
        txn = self.svc.get_transaction(tid)
        customer = self.svc.get_customer(txn.customer_id)
        dlg = EditEntryDialog(self.svc, txn, customer.name, parent=self)
        if dlg.exec():
            self.refresh_all()

    def _delete_entry(self) -> None:
        tid = self._selected_txn_id()
        if tid is None:
            return
        txn = self.svc.get_transaction(tid)
        when = dates.format_date(txn.txn_date)
        if txn.txn_type == "JAMA":
            when += f"  (deposit date {dates.format_date(txn.deposit_date or txn.txn_date)})"
        text = (f"Delete this entry?\n\n{when}  {txn.txn_type}  "
                f"{money.format_inr(txn.amount_paise)}\n{txn.item}\n\nThis cannot be undone. "
                "All balances will be recalculated.")
        if not self.confirm("Delete entry", text):
            return
        try:
            self.svc.delete_transaction(tid)
        except KhataError as exc:
            self.warn("Cannot delete", str(exc))
            return
        self.refresh_all()

    def _export_statement(self, kind: str) -> None:
        try:
            led = self._current_ledger()
        except KhataError as exc:
            self.warn("Cannot export", str(exc))
            return
        if led is None:
            self.info("No customer", "Select a customer first.")
            return
        period = ""
        if led.date_from or led.date_to:
            period = f"_{led.date_from or 'start'}_{led.date_to or 'latest'}"
        default = f"Statement_{_safe_filename(led.customer.name)}{period}.{kind}"
        pattern = "PDF files (*.pdf)" if kind == "pdf" else "Excel files (*.xlsx)"
        path = self._export_path("Export statement", default, pattern)
        if not path:
            return
        try:
            fn = exports.export_statement_pdf if kind == "pdf" else exports.export_statement_xlsx
            fn(led, path, self.shop_name(), website=self.website())
        except (OSError, KhataError) as exc:
            self.warn("Export failed", str(exc))
            return
        self._offer_open(path)

    # ------------------------------------------------------------ reports
    def _build_reports(self) -> None:
        page = QWidget()
        layout = QVBoxLayout(page)

        reg_box = QGroupBox("Transaction register – filter by customer, dates and item, then export exactly that selection")
        reg = QFormLayout(reg_box)
        self.report_customer = QComboBox()
        self.rep_range = QCheckBox("Limit to date range")
        self.rep_from = DateField()
        self.rep_to = DateField()
        self.rep_from.setEnabled(False)
        self.rep_to.setEnabled(False)
        self.rep_range.toggled.connect(lambda on: (self.rep_from.setEnabled(on), self.rep_to.setEnabled(on)))
        dates_row = QHBoxLayout()
        dates_row.addWidget(self.rep_range)
        dates_row.addWidget(QLabel("From"))
        dates_row.addWidget(self.rep_from)
        dates_row.addWidget(QLabel("To"))
        dates_row.addWidget(self.rep_to)
        dates_row.addStretch(1)
        self.rep_search = QLineEdit()
        self.rep_search.setPlaceholderText("Item description contains… (optional)")
        reg.addRow("Customer", self.report_customer)
        reg.addRow("Dates", dates_row)
        reg.addRow("Item search", self.rep_search)
        reg_buttons = QHBoxLayout()
        reg_pdf = QPushButton("Register PDF")
        reg_xlsx = QPushButton("Register Excel")
        reg_pdf.clicked.connect(lambda: self._export_register("pdf"))
        reg_xlsx.clicked.connect(lambda: self._export_register("xlsx"))
        reg_buttons.addStretch(1)
        reg_buttons.addWidget(reg_pdf)
        reg_buttons.addWidget(reg_xlsx)
        reg.addRow(reg_buttons)
        layout.addWidget(reg_box)

        cust_box = QGroupBox("Customer balance summary (all customers, or those matching a name/phone filter)")
        cust = QFormLayout(cust_box)
        self.rep_cust_filter = QLineEdit()
        self.rep_cust_filter.setPlaceholderText("Name or phone contains… (optional)")
        cust.addRow("Customers", self.rep_cust_filter)
        cb = QHBoxLayout()
        cpdf = QPushButton("Balances PDF")
        cxlsx = QPushButton("Balances Excel")
        cpdf.clicked.connect(lambda: self._export_customers("pdf"))
        cxlsx.clicked.connect(lambda: self._export_customers("xlsx"))
        cb.addStretch(1)
        cb.addWidget(cpdf)
        cb.addWidget(cxlsx)
        cust.addRow(cb)
        layout.addWidget(cust_box)

        tip = QLabel("For a single customer's statement with opening/closing balance and running balance, "
                     "use the Ledger tab.")
        tip.setStyleSheet("color: #666;")
        layout.addWidget(tip)
        layout.addStretch(1)
        self.tabs.addTab(page, "Reports")

    def _export_register(self, kind: str) -> None:
        cid = self.report_customer.currentData()
        args = {"search": self.rep_search.text(), "customer_ids": None if cid is None else [cid]}
        if self.rep_range.isChecked():
            args["date_from"] = self.rep_from.text_dmy()
            args["date_to"] = self.rep_to.text_dmy()
        try:
            reg = self.svc.register(**args)
        except KhataError as exc:
            self.warn("Cannot export", str(exc))
            return
        if not reg.rows:
            self.info("Nothing to export", "No entries match these filters.")
            return
        label = self.report_customer.currentText() or "All customers"
        default = f"Register_{_safe_filename(label)}.{kind}"
        pattern = "PDF files (*.pdf)" if kind == "pdf" else "Excel files (*.xlsx)"
        path = self._export_path("Export register", default, pattern)
        if not path:
            return
        try:
            fn = exports.export_register_pdf if kind == "pdf" else exports.export_register_xlsx
            fn(reg, path, self.shop_name(), label, website=self.website())
        except (OSError, KhataError) as exc:
            self.warn("Export failed", str(exc))
            return
        self._offer_open(path)

    def _export_customers(self, kind: str) -> None:
        text = self.rep_cust_filter.text()
        summaries = self.svc.list_customers(text)
        if not summaries:
            self.info("Nothing to export", "No customers match this filter.")
            return
        default = f"Customer_balances.{kind}"
        pattern = "PDF files (*.pdf)" if kind == "pdf" else "Excel files (*.xlsx)"
        path = self._export_path("Export customer balances", default, pattern)
        if not path:
            return
        try:
            fn = exports.export_customers_pdf if kind == "pdf" else exports.export_customers_xlsx
            fn(summaries, path, self.shop_name(), text.strip(), website=self.website())
        except (OSError, KhataError) as exc:
            self.warn("Export failed", str(exc))
            return
        self._offer_open(path)

    # ------------------------------------------------------------ backup & settings
    def _build_backup(self) -> None:
        page = QWidget()
        layout = QVBoxLayout(page)

        data_box = QGroupBox("Your data")
        data = QVBoxLayout(data_box)
        self.backup_info = QLabel("")
        self.backup_info.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.backup_info.setWordWrap(True)
        data.addWidget(self.backup_info)
        open_folder = QPushButton("Open data folder")
        open_folder.clicked.connect(lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.svc.db_path.parent))))
        row = QHBoxLayout()
        row.addWidget(open_folder)
        row.addStretch(1)
        data.addLayout(row)
        layout.addWidget(data_box)

        bk_box = QGroupBox("Backup and restore")
        bk = QVBoxLayout(bk_box)
        create = QPushButton("Create backup…")
        restore = QPushButton("Restore from backup…")
        create.clicked.connect(self._create_backup)
        restore.clicked.connect(self._restore_backup)
        bk.addWidget(create)
        bk.addWidget(restore)
        bk.addWidget(QLabel("A restore first checks the backup file, then saves a safety copy of your current data "
                            "before replacing it."))
        layout.addWidget(bk_box)

        set_box = QGroupBox("Statement header")
        sf = QFormLayout(set_box)
        self.shop_edit = QLineEdit(self.shop_name())
        self.shop_edit.setPlaceholderText("Optional extra business name shown under the SHREEJI BOXES header")
        self.website_edit = QLineEdit(self.website())
        self.website_edit.setPlaceholderText("Optional - leave empty to print no website")
        self.website_edit.setMaxLength(120)
        save_shop = QPushButton("Save")
        save_shop.clicked.connect(self._save_shop)
        line = QHBoxLayout()
        line.addWidget(self.website_edit, 1)
        line.addWidget(save_shop)
        sf.addRow("Business name", self.shop_edit)
        sf.addRow("Website", line)
        sf.addRow(QLabel("Every PDF and Excel report carries the SHREEJI BOXES header and SJB watermark. "
                         "A website is printed only if you enter one here."))
        layout.addWidget(set_box)

        about = QLabel(f"{APP_NAME} v{__version__}  –  works fully offline.")
        about.setStyleSheet("color: #666;")
        layout.addWidget(about)
        layout.addStretch(1)
        self.tabs.addTab(page, "Backup && Settings")

    def _refresh_backup_info(self) -> None:
        d = self.svc.dashboard()
        self.backup_info.setText(
            f"Data file: {self.svc.db_path}\n{d.total_customers} customers, {d.total_transactions} entries."
        )

    def _save_shop(self) -> None:
        self.svc.set_setting("shop_name", " ".join(self.shop_edit.text().split()))
        self.svc.set_setting("website", " ".join(self.website_edit.text().split()))
        self.info("Saved", "Statement header settings saved.")

    def _create_backup(self) -> None:
        default = f"VX7_KHATA_backup_{datetime.now():%Y%m%d_%H%M%S}.db"
        path = self._export_path("Save backup", default, "VX7 KHATA backup (*.db)")
        if not path:
            return
        try:
            self.svc.create_backup(path)
            info = backup.validate_backup(path)
        except (backup.BackupError, OSError) as exc:
            self.warn("Backup failed", str(exc))
            return
        self.info("Backup complete", f"Saved and verified:\n{path}\n\n{info.customers} customers, "
                  f"{info.transactions} entries.")

    def _restore_backup(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Choose a backup to restore", _documents_dir(),
                                              "VX7 KHATA backup (*.db);;All files (*)")
        if not path:
            return
        try:
            info = backup.validate_backup(path)
        except backup.BackupError as exc:
            self.warn("This backup cannot be used", str(exc))
            return
        current = self.svc.dashboard()
        text = (f"Restore this backup?\n\n{path}\n\nBackup contains {info.customers} customers and "
                f"{info.transactions} entries.\nYour current data ({current.total_customers} customers, "
                f"{current.total_transactions} entries) will be replaced.\n\n"
                "A safety copy of the current data is saved first.")
        if not self.confirm("Restore backup", text):
            return
        try:
            safety = self.svc.restore_backup(path, safety_dir=self.svc.db_path.parent / "safety_backups")
        except (backup.BackupError, KhataError, OSError) as exc:
            self.warn("Restore failed", f"{exc}\n\nYour current data was not changed.")
            return
        self.shop_edit.setText(self.shop_name())
        self.website_edit.setText(self.website())
        self.refresh_all()
        self.info("Restore complete", f"Backup restored.\n\nSafety copy of your previous data:\n{safety}")


def RED_IF(amount: int):
    return "#b3261e" if amount else None
