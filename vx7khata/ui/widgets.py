"""Small reusable Qt widgets and helpers."""
from __future__ import annotations

from typing import Optional

from PySide6.QtCore import QDate, Qt
from PySide6.QtWidgets import (
    QAbstractItemView, QComboBox, QCompleter, QDateEdit, QFormLayout, QHBoxLayout, QLabel, QLineEdit,
    QPlainTextEdit, QPushButton, QRadioButton, QTableWidget, QTableWidgetItem, QWidget, QHeaderView,
)

from .. import dates, money
from ..service import KhataError

MIN_DATE = QDate(dates.MIN_YEAR, 1, 1)
DISPLAY_FORMAT = "dd-MM-yyyy"

RED = "#b3261e"
GREEN = "#1b6e3c"


class DateField(QDateEdit):
    """Date picker (calendar popup) that also accepts typing in DD-MM-YYYY."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setDisplayFormat(DISPLAY_FORMAT)
        self.setCalendarPopup(True)
        self.setMinimumDate(MIN_DATE)
        self.set_today()

    def set_today(self) -> None:
        today = QDate.currentDate()
        self.setMaximumDate(today)
        self.setDate(today)

    def refresh_limits(self) -> None:
        self.setMaximumDate(QDate.currentDate())

    def text_dmy(self) -> str:
        return self.date().toString(DISPLAY_FORMAT)

    def set_iso(self, iso: str) -> None:
        self.setDate(QDate.fromString(iso, "yyyy-MM-dd"))


def make_table(headers: list[str]) -> QTableWidget:
    table = QTableWidget(0, len(headers))
    table.setHorizontalHeaderLabels(headers)
    table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
    table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
    table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
    table.setAlternatingRowColors(True)
    table.verticalHeader().setVisible(False)
    table.horizontalHeader().setHighlightSections(False)
    table.setWordWrap(False)
    return table


def set_cell(table: QTableWidget, row: int, col: int, text: str, right: bool = False,
             data=None, color: Optional[str] = None, bold: bool = False) -> QTableWidgetItem:
    from PySide6.QtGui import QBrush, QColor, QFont

    item = QTableWidgetItem(text)
    if right:
        item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
    if data is not None:
        item.setData(Qt.ItemDataRole.UserRole, data)
    if color:
        item.setForeground(QBrush(QColor(color)))
    if bold:
        font = QFont(item.font())
        font.setBold(True)
        item.setFont(font)
    item.setToolTip(text)
    table.setItem(row, col, item)
    return item


def balance_color(paise: int) -> Optional[str]:
    if paise > 0:
        return RED  # customer owes
    if paise < 0:
        return GREEN  # advance / overpaid
    return None


def selected_id(table: QTableWidget, col: int = 0) -> Optional[int]:
    rows = table.selectionModel().selectedRows()
    if not rows:
        return None
    item = table.item(rows[0].row(), col)
    return None if item is None else item.data(Qt.ItemDataRole.UserRole)


def populate_customer_combo(combo: QComboBox, customers, keep_id=None, include_all: bool = False) -> None:
    """Fill a combo with customers; item data = customer id (None for 'All customers')."""
    if keep_id is None and combo.currentIndex() >= 0:
        keep_id = combo.currentData()
    combo.blockSignals(True)
    combo.clear()
    if include_all:
        combo.addItem("All customers", None)
    for s in customers:
        combo.addItem(s.customer.name, s.customer.id)
    index = combo.findData(keep_id) if keep_id is not None else -1
    if index >= 0:
        combo.setCurrentIndex(index)
    elif combo.count():
        combo.setCurrentIndex(0)
    combo.blockSignals(False)


class EntryForm(QWidget):
    """Fields of one khata entry. Used by Quick Entry and by the edit dialog."""

    def __init__(self, with_customer: bool, parent=None):
        super().__init__(parent)
        form = QFormLayout(self)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self.customer = QComboBox()
        self.customer.setEditable(True)
        self.customer.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.customer.completer().setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        self.customer.completer().setFilterMode(Qt.MatchFlag.MatchContains)
        self.customer.completer().setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        if with_customer:
            self.new_customer_button = QPushButton("+ New customer")
            row = QHBoxLayout()
            row.addWidget(self.customer, 1)
            row.addWidget(self.new_customer_button)
            form.addRow("Customer", row)

        self.udhaar = QRadioButton("UDHAAR  (customer took on credit)")
        self.jama = QRadioButton("JAMA  (customer paid)")
        self.udhaar.setChecked(True)
        type_row = QHBoxLayout()
        type_row.addWidget(self.udhaar)
        type_row.addWidget(self.jama)
        type_row.addStretch(1)
        form.addRow("Type", type_row)

        self.date = DateField()
        self.date.setToolTip("Pick a date or type it as DD-MM-YYYY. Past dates are fine for old entries.")
        form.addRow("Transaction date", self.date)

        # Deposit date: the day the money was really received (JAMA only). It follows the transaction
        # date until you change it yourself; previous months and years are fine.
        self.deposit_date = DateField()
        self.deposit_date.setToolTip(
            "The day the deposit was actually received. Old dates (previous months or years) are fine; "
            "the ledger puts the deposit at this date.")
        form.addRow("Deposit date", self.deposit_date)
        self._deposit_label = form.labelForField(self.deposit_date)
        self._deposit_touched = False
        self._syncing = False

        self.item = QLineEdit()
        self.item.setPlaceholderText("e.g. Gold chain repair, Previous payment")
        self.item.setMaxLength(200)
        form.addRow("Item / description", self.item)

        self.quantity = QLineEdit()
        self.quantity.setPlaceholderText("optional")
        self.rate = QLineEdit()
        self.rate.setPlaceholderText("optional (₹)")
        qr = QHBoxLayout()
        qr.addWidget(QLabel("Qty"))
        qr.addWidget(self.quantity)
        qr.addWidget(QLabel("× Rate"))
        qr.addWidget(self.rate)
        form.addRow("Quantity × Rate", qr)

        self.amount = QLineEdit()
        self.amount.setPlaceholderText("0.00")
        self.amount_hint = QLabel("")
        self.amount_hint.setStyleSheet("color: #666;")
        amount_row = QHBoxLayout()
        amount_row.addWidget(self.amount, 1)
        amount_row.addWidget(self.amount_hint)
        form.addRow("Amount (₹)", amount_row)

        self.notes = QPlainTextEdit()
        self.notes.setFixedHeight(60)
        form.addRow("Notes", self.notes)

        self.quantity.textChanged.connect(self._recalculate)
        self.rate.textChanged.connect(self._recalculate)
        self.date.dateChanged.connect(self._date_changed)
        self.deposit_date.dateChanged.connect(self._deposit_changed)
        self.jama.toggled.connect(self._type_changed)
        self._type_changed()

    # -- behaviour --------------------------------------------------------
    def _set_deposit_date(self, qdate) -> None:
        self._syncing = True
        try:
            self.deposit_date.setDate(qdate)
        finally:
            self._syncing = False

    def _date_changed(self, qdate) -> None:
        if not self._deposit_touched:
            self._set_deposit_date(qdate)

    def _deposit_changed(self, _qdate) -> None:
        if not self._syncing:
            self._deposit_touched = True  # the user chose a deposit date: stop following the transaction date

    def _type_changed(self, *_args) -> None:
        is_jama = self.jama.isChecked()
        self.deposit_date.setVisible(is_jama)
        if self._deposit_label is not None:
            self._deposit_label.setVisible(is_jama)
        if is_jama and not self._deposit_touched:
            self._set_deposit_date(self.date.date())

    def _recalculate(self) -> None:
        q, r = self.quantity.text().strip(), self.rate.text().strip()
        if q and r:
            try:
                amount = money.compute_amount_paise(money.parse_quantity(q), money.rupees_to_paise(r, "Rate"))
            except money.MoneyError:
                self.amount.setReadOnly(False)
                self.amount_hint.setText("")
                return
            self.amount.setText(money.plain_amount(amount))
            self.amount.setReadOnly(True)
            self.amount_hint.setText("= Qty × Rate")
        else:
            self.amount.setReadOnly(False)
            self.amount_hint.setText("")

    def customer_id(self) -> int:
        text = self.customer.currentText().strip()
        if not text:
            raise KhataError("Select a customer")
        index = self.customer.findText(text, Qt.MatchFlag.MatchFixedString)  # case-insensitive exact match
        if index < 0:
            raise KhataError(f"No customer named '{text}'. Pick one from the list or use '+ New customer'.")
        return self.customer.itemData(index)

    def select_customer(self, customer_id: int) -> None:
        index = self.customer.findData(customer_id)
        if index >= 0:
            self.customer.setCurrentIndex(index)

    def values(self) -> dict:
        both = bool(self.quantity.text().strip() and self.rate.text().strip())
        return {
            "txn_type": "UDHAAR" if self.udhaar.isChecked() else "JAMA",
            "txn_date": self.date.text_dmy(),
            "deposit_date": self.deposit_date.text_dmy() if self.jama.isChecked() else None,
            "item": self.item.text(),
            "amount": None if both else self.amount.text(),
            "quantity": self.quantity.text(),
            "rate": self.rate.text(),
            "notes": self.notes.toPlainText(),
        }

    def set_values(self, txn) -> None:
        # An existing deposit keeps its own saved deposit date even if the transaction date is edited.
        self._deposit_touched = txn.txn_type == "JAMA"
        (self.udhaar if txn.txn_type == "UDHAAR" else self.jama).setChecked(True)
        self.date.setMaximumDate(QDate.currentDate())
        self.deposit_date.setMaximumDate(QDate.currentDate())
        self.date.set_iso(txn.txn_date)
        if txn.txn_type == "JAMA":
            self._set_deposit_date(QDate.fromString(txn.deposit_date or txn.txn_date, "yyyy-MM-dd"))
        self.item.setText(txn.item)
        self.quantity.setText(txn.quantity or "")
        self.rate.setText(money.plain_amount(txn.rate_paise) if txn.rate_paise else "")
        self.amount.setText(money.plain_amount(txn.amount_paise))
        self.notes.setPlainText(txn.notes)
        self._recalculate()

    def clear_for_next(self) -> None:
        """Keep customer, type and date; clear the rest so the next entry can be typed straight away."""
        self.item.clear()
        self.quantity.clear()
        self.rate.clear()
        self.amount.clear()
        self.amount.setReadOnly(False)
        self.amount_hint.setText("")
        self.notes.clear()
        self.item.setFocus()


def fit_columns(table: QTableWidget, stretch_col: int) -> None:
    header = table.horizontalHeader()
    header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
    header.setSectionResizeMode(stretch_col, QHeaderView.ResizeMode.Stretch)
