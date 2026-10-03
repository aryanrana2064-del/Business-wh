"""Extra deposit-date behaviour: editing keeps/clears dates, register export, legacy rows in totals."""
from datetime import datetime
from pathlib import Path

from openpyxl import load_workbook

from tests.helpers import ServiceTestCase
from vx7khata import exports
from vx7khata.service import ValidationError

GENERATED = datetime(2026, 10, 3, 14, 30)


class TestDepositEdits(ServiceTestCase):
    def setUp(self):
        super().setUp()
        self.c = self.svc.add_customer("Rahul")
        self.u = self.add(self.c.id, "UDHAAR", "10-01-2025", "Box", "5000")
        self.d = self.add(self.c.id, "JAMA", "01-06-2025", "Cash", "2000", deposit_date="20-01-2025")

    def test_edit_without_a_deposit_date_keeps_the_saved_one(self):
        t = self.svc.update_transaction(self.d.id, "JAMA", "01-06-2025", "Cash", amount="2500")
        self.assertEqual(t.deposit_date, "2025-01-20")
        self.assertEqual(t.amount_paise, 250000)

    def test_blank_deposit_date_on_edit_resets_to_the_entry_date(self):
        t = self.svc.update_transaction(self.d.id, "JAMA", "01-06-2025", "Cash", amount="2000", deposit_date="")
        self.assertEqual(t.deposit_date, "2025-06-01")

    def test_switching_a_deposit_to_udhaar_clears_its_deposit_date(self):
        t = self.svc.update_transaction(self.d.id, "UDHAAR", "01-06-2025", "Cash", amount="2000")
        self.assertIsNone(t.deposit_date)
        with self.assertRaises(ValidationError):
            self.svc.update_transaction(self.d.id, "UDHAAR", "01-06-2025", "Cash", amount="2000",
                                        deposit_date="01-01-2025")

    def test_switching_udhaar_to_deposit_defaults_to_its_date(self):
        t = self.svc.update_transaction(self.u.id, "JAMA", "10-01-2025", "Box", amount="5000")
        self.assertEqual(t.deposit_date, "2025-01-10")

    def test_failed_edit_changes_nothing(self):
        with self.assertRaises(ValidationError):
            self.svc.update_transaction(self.d.id, "JAMA", "01-06-2025", "Cash", amount="2000", deposit_date="31-02-2025")
        self.assertEqual(self.svc.get_transaction(self.d.id).deposit_date, "2025-01-20")


class TestRegisterExport(ServiceTestCase):
    def test_register_workbook_has_deposit_date_and_matches_the_database(self):
        a = self.svc.add_customer("A")
        b = self.svc.add_customer("B")
        self.add(a.id, "UDHAAR", "10-01-2025", "Gold ring", "1000")
        self.add(b.id, "JAMA", "11-06-2025", "Cash", "400", deposit_date="05-02-2025")
        reg = self.svc.register(date_from="01-02-2025", date_to="28-02-2025")
        self.assertEqual([r.customer_name for r in reg.rows], ["B"])  # filtered by deposit date, not entry date
        path = exports.export_register_xlsx(reg, Path(self.tmp.name) / "r.xlsx", generated_at=GENERATED)
        ws = load_workbook(path, data_only=True)["Register"]
        rows = [[c.value for c in row] for row in ws.iter_rows()]
        head = next(r for r in rows if r[0] == "TRANSACTION DATE")
        self.assertEqual(head[5:8], ["UDHAAR (₹)", "TOTAL DEPOSIT (₹)", "DEPOSIT DATE"])
        line = next(r for r in rows if r[1] == "B")
        self.assertEqual(round(float(line[6]) * 100), 40000)
        self.assertEqual(line[7].date().isoformat(), "2025-02-05")
