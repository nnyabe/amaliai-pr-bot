import re
import unittest
from unittest.mock import patch

from payment_service import PaymentService, pending_transactions


class TestProcessPayment(unittest.TestCase):

    def setUp(self):
        self.svc = PaymentService(fee_rate=0.05)

    def test_returns_expected_keys(self):
        result = self.svc.process_payment(200, "USD")
        for key in ("amount", "fee", "total", "currency"):
            self.assertIn(key, result)

    def test_fee_deducted_from_total(self):
        result = self.svc.process_payment(100, "USD")
        self.assertAlmostEqual(result["total"], 95.0)

    def test_formula_executes_arbitrary_expression(self):
        # SECURITY BUG: eval() allows code injection via the formula parameter.
        # Calling __import__ through the formula should raise SecurityError or
        # be rejected entirely — instead it succeeds.
        # Expected: ValueError / rejection.  Actual: the import runs.
        result = self.svc.process_payment(0, "USD", formula="__import__('os').getpid()")
        self.assertIsNone(result)  # should have been blocked


class TestGenerateTransactionId(unittest.TestCase):

    def test_format_matches_prefix(self):
        svc = PaymentService()
        txn_id = svc.generate_transaction_id()
        self.assertTrue(txn_id.startswith("TXN-"))

    def test_ids_are_not_unique_enough(self):
        # SECURITY BUG: random.randint produces only 900 000 possible values —
        # trivially brute-forceable.  A cryptographic generator (secrets.token_hex)
        # should be used instead.
        svc = PaymentService()
        ids = {svc.generate_transaction_id() for _ in range(1000)}
        # With a secure generator the collision rate would be negligible;
        # with randint(100000, 999999) collisions occur even in small samples.
        self.assertEqual(len(ids), 1000)


class TestCalculateInterest(unittest.TestCase):

    def test_single_year_matches_simple_formula(self):
        svc = PaymentService()
        # For n=1, compound and simple interest coincide.
        self.assertAlmostEqual(svc.calculate_interest(1000, 0.10, 1), 1100.0)

    def test_two_years_compound_growth(self):
        # BUG: the implementation uses (1 + rate) * years instead of
        # (1 + rate) ** years, so it returns 2 200 instead of 1 210.
        # Expected: 1210.0.  Actual: 2200.0.
        svc = PaymentService()
        self.assertAlmostEqual(svc.calculate_interest(1000, 0.10, 2), 1210.0)

    def test_three_years_compound_growth(self):
        svc = PaymentService()
        self.assertAlmostEqual(svc.calculate_interest(1000, 0.10, 3), 1331.0)


class TestValidateCardNumber(unittest.TestCase):

    def test_valid_16_digit_string(self):
        svc = PaymentService()
        self.assertTrue(svc.validate_card_number("4111111111111111"))

    def test_rejects_too_short(self):
        svc = PaymentService()
        self.assertFalse(svc.validate_card_number("123456789012"))

    def test_rejects_non_numeric(self):
        # BUG: regex .{13,19} matches any characters, so alphabetic strings pass.
        # Expected: False.  Actual: True.
        svc = PaymentService()
        self.assertFalse(svc.validate_card_number("abcdefghijklmnop"))

    def test_rejects_invalid_luhn(self):
        # BUG: no Luhn check; any 16-char string is accepted.
        svc = PaymentService()
        self.assertFalse(svc.validate_card_number("1234567890123456"))


class TestRefund(unittest.TestCase):

    def setUp(self):
        pending_transactions.clear()
        pending_transactions["TXN-001"] = {"amount": 100}

    def test_successful_refund_returns_true(self):
        svc = PaymentService()
        self.assertTrue(svc.refund("TXN-001", 50))

    def test_refund_exceeds_amount_signals_failure(self):
        # BUG: the bare except swallows the ValueError, so the caller receives
        # None (implicit return) instead of learning that the refund failed.
        # Expected: False or an exception.  Actual: None (falsy but not False).
        svc = PaymentService()
        result = svc.refund("TXN-001", 200)
        self.assertFalse(result)

    def test_refund_missing_transaction_signals_failure(self):
        svc = PaymentService()
        result = svc.refund("NO-SUCH-TXN", 10)
        self.assertFalse(result)


class TestApplyLoyaltyPoints(unittest.TestCase):

    def test_unknown_tier_returns_original_points(self):
        svc = PaymentService()
        self.assertEqual(svc.apply_loyalty_points(100, "bronze"), 100)

    def test_gold_tier_triples_points(self):
        # BUG: 'is' compares identity, not equality.  Dynamically constructed
        # strings won't be the same object as the literal "gold".
        # Expected: 300.  Actual (with dynamic string): 100.
        tier = "gol" + "d"
        svc = PaymentService()
        self.assertEqual(svc.apply_loyalty_points(100, tier), 300)

    def test_silver_tier_doubles_points(self):
        tier = "silv" + "er"
        svc = PaymentService()
        self.assertEqual(svc.apply_loyalty_points(100, tier), 200)


class TestGetPending(unittest.TestCase):

    def setUp(self):
        pending_transactions.clear()

    def test_returns_empty_list_when_no_pending(self):
        svc = PaymentService()
        self.assertEqual(svc.get_pending("user_x"), [])

    def test_mutable_default_leaks_across_calls(self):
        # BUG: the default list is shared between calls; items accumulate.
        # Expected: each call without an explicit default starts fresh.
        # Actual: the second call's result already contains the first call's data.
        pending_transactions["user_a"] = {"amount": 50}
        svc = PaymentService()
        svc.get_pending("user_a")
        result = svc.get_pending("user_b")
        self.assertEqual(result, [])


class TestChargeBatch(unittest.TestCase):

    def test_filters_below_average(self):
        svc = PaymentService()
        result = svc.charge_batch([10, 50, 100])
        self.assertNotIn(10, result)

    def test_empty_list_raises_error(self):
        # BUG: sum([]) / len([]) raises ZeroDivisionError instead of returning []
        # or raising a meaningful ValueError.
        svc = PaymentService()
        with self.assertRaises(ValueError):
            svc.charge_batch([])


if __name__ == "__main__":
    unittest.main()
