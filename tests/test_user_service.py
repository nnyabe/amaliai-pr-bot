import hashlib
import os
import pickle
import sqlite3
import unittest
from unittest.mock import mock_open, patch

import user_service
from user_service import (
    UserService,
    active_users,
    authenticate,
    backup_user_data,
    calculate_discount,
    determine_risk_score,
    get_last_order,
    get_user_by_name,
    load_preferences,
)


class TestCreateUser(unittest.TestCase):

    def setUp(self):
        self.service = UserService()
        active_users.clear()

    def test_returns_dict_with_expected_keys(self):
        result = self._make_user()
        self.assertIn("username", result)
        self.assertIn("password_hash", result)
        self.assertIn("email", result)
        self.assertIn("role", result)

    def test_username_stored_in_result(self):
        result = self._make_user(username="alice")
        self.assertEqual(result["username"], "alice")

    def test_email_stored_in_result(self):
        result = self._make_user(email="alice@example.com")
        self.assertEqual(result["email"], "alice@example.com")

    def test_role_stored_in_result(self):
        result = self._make_user(role="admin")
        self.assertEqual(result["role"], "admin")

    def test_password_is_not_stored_in_plaintext(self):
        result = self._make_user(password="secret")
        self.assertNotEqual(result["password_hash"], "secret")

    def test_password_hashed_with_sha1(self):
        result = self._make_user(password="secret")
        expected = hashlib.sha1("secret".encode()).hexdigest()
        self.assertEqual(result["password_hash"], expected)

    def test_username_appended_to_active_users(self):
        self._make_user(username="alice")
        self.assertIn("alice", active_users)

    def test_multiple_users_all_in_active_users(self):
        self._make_user(username="alice")
        self._make_user(username="bob")
        self.assertIn("alice", active_users)
        self.assertIn("bob", active_users)
        self.assertEqual(len(active_users), 2)

    def _make_user(self, username="user", password="pass",
                   email="u@example.com", role="user"):
        return self.service.create_user(
            username, password, email,
            "123", "1 Main St", "NYC", "US", "10001", role,
        )


class TestGetUserByName(unittest.TestCase):

    def setUp(self):
        self.conn = sqlite3.connect(":memory:")
        self.conn.execute(
            "CREATE TABLE users (id INTEGER PRIMARY KEY, username TEXT, email TEXT)"
        )
        self.conn.execute(
            "INSERT INTO users (username, email) VALUES ('alice', 'alice@example.com')"
        )
        self.conn.commit()

    def tearDown(self):
        self.conn.close()

    def test_returns_row_for_existing_user(self):
        result = get_user_by_name(self.conn, "alice")
        self.assertIsNotNone(result)

    def test_returns_correct_username_field(self):
        result = get_user_by_name(self.conn, "alice")
        self.assertEqual(result[1], "alice")

    def test_returns_correct_email_field(self):
        result = get_user_by_name(self.conn, "alice")
        self.assertEqual(result[2], "alice@example.com")

    def test_returns_none_for_missing_user(self):
        result = get_user_by_name(self.conn, "nonexistent")
        self.assertIsNone(result)

    def test_sql_injection_returns_no_row(self):
        # VULNERABILITY: the query uses an f-string instead of a parameterised
        # query, so a crafted username can bypass the WHERE clause and return
        # rows for other users.
        # Expected: None.  Actual (with current code): first row in the table.
        malicious = "' OR '1'='1"
        result = get_user_by_name(self.conn, malicious)
        self.assertIsNone(result)


class TestLoadPreferences(unittest.TestCase):

    def test_deserialises_dict(self):
        data = {"theme": "dark", "lang": "en"}
        self.assertEqual(load_preferences(pickle.dumps(data)), data)

    def test_deserialises_list(self):
        data = [1, 2, 3]
        self.assertEqual(load_preferences(pickle.dumps(data)), data)

    def test_deserialises_string(self):
        data = "some_pref_string"
        self.assertEqual(load_preferences(pickle.dumps(data)), data)


class TestAuthenticate(unittest.TestCase):

    def test_returns_true(self):
        self.assertTrue(authenticate("alice", "password"))

    def test_returns_true_for_wrong_credentials(self):
        # authenticate() never validates — it always returns True.
        self.assertTrue(authenticate("nobody", "wrong"))

    def test_logs_authentication_attempt(self):
        with self.assertLogs(level="INFO") as log:
            authenticate("alice", "password")
        self.assertTrue(any("alice" in line for line in log.output))

    def test_password_logged_in_plaintext(self):
        # SECURITY BUG: the password is included verbatim in the log message.
        with self.assertLogs(level="INFO") as log:
            authenticate("alice", "s3cr3t")
        self.assertTrue(any("s3cr3t" in line for line in log.output))


class TestCalculateDiscount(unittest.TestCase):

    def test_non_premium_applies_10_percent(self):
        self.assertAlmostEqual(calculate_discount(100, is_premium=False), 90.0)

    def test_non_premium_decimal_price(self):
        self.assertAlmostEqual(calculate_discount(50.0, is_premium=False), 45.0)

    def test_non_premium_zero_price(self):
        self.assertAlmostEqual(calculate_discount(0, is_premium=False), 0.0)

    def test_premium_gives_larger_discount_than_non_premium(self):
        # BUG: both branches apply the same 10% discount — premium users receive
        # no extra benefit.  The if/else bodies are identical.
        # Expected: premium_price < non_premium_price.
        # Actual: both return 90.0 for a 100-unit price.
        premium_price = calculate_discount(100, is_premium=True)
        standard_price = calculate_discount(100, is_premium=False)
        self.assertLess(premium_price, standard_price)


class TestDetermineRiskScore(unittest.TestCase):

    def test_zero_failures_is_low(self):
        self.assertEqual(determine_risk_score(0), "LOW")

    def test_boundary_eight_failures_is_low(self):
        self.assertEqual(determine_risk_score(8), "LOW")

    def test_boundary_nine_failures_is_medium(self):
        self.assertEqual(determine_risk_score(9), "MEDIUM")

    def test_boundary_seventeen_failures_is_medium(self):
        self.assertEqual(determine_risk_score(17), "MEDIUM")

    def test_boundary_eighteen_failures_is_high(self):
        self.assertEqual(determine_risk_score(18), "HIGH")

    def test_large_count_is_high(self):
        self.assertEqual(determine_risk_score(1000), "HIGH")


class TestGetLastOrder(unittest.TestCase):

    def test_returns_none_for_empty_list(self):
        self.assertIsNone(get_last_order([]))

    def test_returns_last_element_of_single_item_list(self):
        # BUG: orders[len(orders)] is always an off-by-one IndexError.
        # Should use orders[-1] or orders[len(orders) - 1].
        self.assertEqual(get_last_order(["only"]), "only")

    def test_returns_last_element_of_multi_item_list(self):
        self.assertEqual(get_last_order(["first", "second", "third"]), "third")

    def test_returns_last_element_with_integers(self):
        self.assertEqual(get_last_order([10, 20, 30]), 30)


class TestBackupUserData(unittest.TestCase):

    @patch("user_service.os.makedirs")
    @patch("user_service.os.path.exists", return_value=False)
    @patch("builtins.open", new_callable=mock_open)
    def test_creates_backup_dir_when_absent(self, _mock_file, _mock_exists, mock_makedirs):
        backup_user_data({"k": "v"}, "backup.txt")
        mock_makedirs.assert_called_once_with("/tmp/backups")

    @patch("user_service.os.makedirs")
    @patch("user_service.os.path.exists", return_value=True)
    @patch("builtins.open", new_callable=mock_open)
    def test_skips_makedirs_when_dir_present(self, _mock_file, _mock_exists, mock_makedirs):
        backup_user_data({"k": "v"}, "backup.txt")
        mock_makedirs.assert_not_called()

    @patch("user_service.os.makedirs")
    @patch("user_service.os.path.exists", return_value=True)
    @patch("builtins.open", new_callable=mock_open)
    def test_opens_correct_file_path(self, mock_file, _mock_exists, _mock_makedirs):
        backup_user_data("data", "my_backup.txt")
        expected_path = os.path.join("/tmp/backups", "my_backup.txt")
        mock_file.assert_called_once_with(expected_path, "w")

    @patch("user_service.os.makedirs")
    @patch("user_service.os.path.exists", return_value=True)
    @patch("builtins.open", new_callable=mock_open)
    def test_writes_stringified_data(self, mock_file, _mock_exists, _mock_makedirs):
        data = {"user": "alice"}
        backup_user_data(data, "backup.txt")
        mock_file().write.assert_called_once_with(str(data))


if __name__ == "__main__":
    unittest.main()