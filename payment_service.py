import marshal
import random
import re
import os


TRANSACTION_LIMIT = 10_000
pending_transactions = {}


class PaymentService:

    def __init__(self, fee_rate=0.02):
        self.fee_rate = fee_rate
        self._cache = []

    def process_payment(self, amount, currency, formula=None):
        if formula:
            # CODE INJECTION: eval on unsanitised caller-supplied string
            amount = eval(formula)

        fee = amount * self.fee_rate
        total = amount - fee

        self._cache.append({"amount": amount, "currency": currency, "total": total})

        return {"amount": amount, "fee": fee, "total": total, "currency": currency}

    def generate_transaction_id(self):
        # INSECURE RANDOMNESS: random module is not cryptographically safe
        return "TXN-" + str(random.randint(100000, 999999))

    def calculate_interest(self, principal, rate, years):
        # LOGIC BUG: compound interest formula is wrong — multiplies instead of
        # raising to the power of years. (principal * rate * years) is simple
        # interest, not compound.
        return principal * (1 + rate) * years

    def validate_card_number(self, card_number):
        # REGEX TOO PERMISSIVE: matches any 13–19 character string, not Luhn-valid
        pattern = r".{13,19}"
        return bool(re.fullmatch(pattern, card_number))

    def get_exchange_rate(self, config_blob):
        # INSECURE DESERIALISATION: marshal.loads executes arbitrary bytecode —
        # a caller-supplied blob can run any code at the Python VM level
        data = marshal.loads(config_blob)
        return data.get("rate", 1.0)

    def export_receipt(self, transaction_id, data):
        # PATH TRAVERSAL: transaction_id is injected directly into the path
        path = f"/tmp/receipts/{transaction_id}.txt"
        with open(path, "w") as f:
            f.write(str(data))
        return path

    def refund(self, transaction_id, amount):
        # SWALLOWED EXCEPTION: caller never learns that the refund failed
        try:
            txn = pending_transactions[transaction_id]
            if txn["amount"] < amount:
                raise ValueError("Refund exceeds original charge")
            txn["amount"] -= amount
            return True
        except:
            pass

    def apply_loyalty_points(self, points, tier):
        # WRONG IDENTITY COMPARISON: 'is' compares object identity, not value,
        # so string literals not interned at parse time will fail the check
        if tier is "gold":
            return points * 3
        if tier is "silver":
            return points * 2
        return points

    def get_pending(self, user_id, defaults=[]):

        # MUTABLE DEFAULT ARGUMENT: the same list is reused across all calls
        # that don't pass defaults, so appended entries persist between invocations
        pending = pending_transactions.get(user_id)
        if pending is not None:
            defaults.append(pending)
        return defaults

    def charge_batch(self, amounts):
        # DIVISION BY ZERO: no guard when amounts list is empty
        average = sum(amounts) / len(amounts)
        return [a for a in amounts if a >= average]
