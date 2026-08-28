import unittest

from bank_accounts import Account, ChequingAccount, SavingsAccount, BusinessAccount


class TestChequingAccount(unittest.TestCase):
    def setUp(self):
        self.account = ChequingAccount(
            owner="Mac",
            account_number="CHQ-001",
            balance=100,
            overdraft_limit=200,
            overdraft_fee=35,
        )

    def test_deposit_increases_balance_and_logs(self):
        self.account.deposit(50)
        self.assertEqual(self.account.balance, 150)
        self.assertIn(("Deposit", 50), self.account.transactions)

    def test_deposit_rejects_non_positive_amount(self):
        with self.assertRaises(ValueError):
            self.account.deposit(0)
        with self.assertRaises(ValueError):
            self.account.deposit(-10)

    def test_withdraw_within_balance(self):
        self.account.withdraw(50)
        self.assertEqual(self.account.balance, 50)

    def test_withdraw_into_overdraft_allowed(self):
        # balance 100, overdraft_limit 200 -> can withdraw up to 300
        self.account.withdraw(250)
        self.assertEqual(self.account.balance, -150)

    def test_withdraw_beyond_overdraft_limit_raises(self):
        with self.assertRaises(ValueError):
            self.account.withdraw(301)

    def test_withdraw_rejects_non_positive_amount(self):
        with self.assertRaises(ValueError):
            self.account.withdraw(0)
        with self.assertRaises(ValueError):
            self.account.withdraw(-5)

    def test_apply_monthly_effect_charges_fee_when_negative(self):
        self.account.withdraw(250)  # balance -> -150
        self.account.apply_monthly_effect()
        self.assertEqual(self.account.balance, -185)
        self.assertIn(("Overdraft Fee", 35), self.account.transactions)

    def test_apply_monthly_effect_no_fee_when_positive(self):
        self.account.apply_monthly_effect()
        self.assertEqual(self.account.balance, 100)
        self.assertNotIn(("Overdraft Fee", 35), self.account.transactions)

    def test_negative_overdraft_limit_rejected(self):
        with self.assertRaises(ValueError):
            ChequingAccount("Mac", "CHQ-002", 100, -1, 35)

    def test_negative_overdraft_fee_rejected(self):
        with self.assertRaises(ValueError):
            ChequingAccount("Mac", "CHQ-003", 100, 200, -1)

    def test_transactions_property_returns_copy(self):
        log = self.account.transactions
        log.append(("Fake", 999))
        self.assertNotIn(("Fake", 999), self.account.transactions)

    def test_transfer_between_accounts(self):
        other = ChequingAccount("Sam", "CHQ-999", 0, 100, 35)
        self.account.transfer(other, 50)
        self.assertEqual(self.account.balance, 50)
        self.assertEqual(other.balance, 50)


class TestSavingsAccount(unittest.TestCase):
    def setUp(self):
        self.account = SavingsAccount(
            owner="Mac",
            account_number="SAV-001",
            balance=1000,
            interest_rate=0.12,  # 1% per month for easy math
            withdrawal_limit=2,
        )

    def test_deposit_increases_balance(self):
        self.account.deposit(100)
        self.assertEqual(self.account.balance, 1100)

    def test_withdraw_within_limit(self):
        self.account.withdraw(100)
        self.assertEqual(self.account.balance, 900)
        self.assertEqual(self.account.withdrawals_this_month, 1)

    def test_withdraw_beyond_monthly_limit_raises(self):
        self.account.withdraw(50)
        self.account.withdraw(50)
        with self.assertRaises(PermissionError):
            self.account.withdraw(50)

    def test_withdraw_beyond_balance_raises(self):
        with self.assertRaises(ValueError):
            self.account.withdraw(5000)

    def test_new_month_resets_withdrawal_count(self):
        self.account.withdraw(50)
        self.account.withdraw(50)
        self.account.new_month()
        self.assertEqual(self.account.withdrawals_this_month, 0)
        # should be allowed again after reset
        self.account.withdraw(50)
        self.assertEqual(self.account.withdrawals_this_month, 1)

    def test_apply_monthly_effect_adds_interest(self):
        self.account.apply_monthly_effect()
        self.assertAlmostEqual(self.account.balance, 1010.0)

    def test_negative_interest_rate_rejected(self):
        with self.assertRaises(ValueError):
            SavingsAccount("Mac", "SAV-002", 1000, -0.01, 2)

    def test_negative_withdrawal_limit_rejected(self):
        with self.assertRaises(ValueError):
            SavingsAccount("Mac", "SAV-003", 1000, 0.12, -1)


class TestBusinessAccount(unittest.TestCase):
    def setUp(self):
        self.account = BusinessAccount(
            owner="Mac's Bakery",
            account_number="BIZ-001",
            balance=5000,
            overdraft_limit=1000,
            overdraft_fee=50,
            monthly_maintenance_fee=25,
            transaction_limit=2,
            transaction_fee=10,
            authorized_users=["Smith, John"],
        )

    def test_deposit_increases_balance(self):
        self.account.deposit(100)
        self.assertEqual(self.account.balance, 5100)

    def test_withdraw_within_overdraft_allowed(self):
        self.account.withdraw(5500)
        self.assertEqual(self.account.balance, -500)

    def test_withdraw_beyond_overdraft_limit_raises(self):
        with self.assertRaises(ValueError):
            self.account.withdraw(6001)

    def test_transaction_fee_charged_after_limit_exceeded(self):
        # transaction_limit = 2, so the 3rd transaction should trigger a fee
        self.account.deposit(10)   # transaction 1
        self.account.deposit(10)   # transaction 2
        self.account.deposit(10)   # transaction 3 -> fee triggers
        self.assertEqual(self.account.transactions_this_month, 3)
        self.assertIn(("Transaction Fee", 10), self.account.transactions)
        # balance = 5000 + 10 + 10 + 10 - 10 (fee) = 5020
        self.assertEqual(self.account.balance, 5020)

    def test_failed_withdraw_does_not_increment_transaction_count(self):
        with self.assertRaises(ValueError):
            self.account.withdraw(-5)  # invalid amount, should raise before counting
        self.assertEqual(self.account.transactions_this_month, 0)

    def test_failed_withdraw_does_not_charge_transaction_fee(self):
        # use up the free transactions first
        self.account.deposit(10)
        self.account.deposit(10)
        with self.assertRaises(ValueError):
            self.account.withdraw(999999)  # exceeds overdraft limit, should fail
        # count should still reflect only the 2 successful deposits
        self.assertEqual(self.account.transactions_this_month, 2)

    def test_new_month_resets_transaction_count(self):
        self.account.deposit(10)
        self.account.deposit(10)
        self.account.deposit(10)
        self.account.new_month()
        self.assertEqual(self.account.transactions_this_month, 0)

    def test_apply_monthly_effect_charges_maintenance_fee(self):
        self.account.apply_monthly_effect()
        self.assertEqual(self.account.balance, 4975)
        self.assertIn(("Maintenance Fee", 25), self.account.transactions)

    def test_apply_monthly_effect_also_applies_overdraft_fee_when_negative(self):
        self.account.withdraw(5500)  # balance -> -500
        self.account.apply_monthly_effect()
        # -500 - 25 (maintenance) - 50 (overdraft, since still negative) = -575
        self.assertEqual(self.account.balance, -575)
        self.assertIn(("Overdraft Fee", 50), self.account.transactions)

    def test_add_and_remove_authorized_user(self):
        self.account.add_user("Jane", "Doe")
        self.assertIn("Doe, Jane", self.account.authorized_users)
        self.account.remove_user("Jane", "Doe")
        self.assertNotIn("Doe, Jane", self.account.authorized_users)

    def test_authorized_users_property_returns_copy(self):
        users = self.account.authorized_users
        users.append("Fake, User")
        self.assertNotIn("Fake, User", self.account.authorized_users)

    def test_authorized_users_constructor_does_not_alias_input_list(self):
        original_list = ["Smith, John"]
        account = BusinessAccount(
            "Biz", "BIZ-002", 1000, 500, 25, 10, 5, 5, original_list
        )
        original_list.append("Mutated, Externally")
        self.assertNotIn("Mutated, Externally", account.authorized_users)

    def test_negative_monthly_maintenance_fee_rejected(self):
        with self.assertRaises(ValueError):
            BusinessAccount("Biz", "BIZ-003", 1000, 500, 25, -1, 5, 5, [])

    def test_negative_transaction_limit_rejected(self):
        with self.assertRaises(ValueError):
            BusinessAccount("Biz", "BIZ-004", 1000, 500, 25, 10, -1, 5, [])

    def test_negative_transaction_fee_rejected(self):
        with self.assertRaises(ValueError):
            BusinessAccount("Biz", "BIZ-005", 1000, 500, 25, 10, 5, -1, [])


class TestPolymorphism(unittest.TestCase):
    def test_apply_monthly_effect_differs_by_account_type(self):
        chequing = ChequingAccount("Mac", "CHQ-100", -100, 500, 35)
        savings = SavingsAccount("Mac", "SAV-100", 1000, 0.12, 2)
        business = BusinessAccount(
            "Biz", "BIZ-100", 1000, 500, 35, 25, 2, 10, []
        )
        accounts = [chequing, savings, business]

        for account in accounts:
            self.assertIsInstance(account, Account)
            account.apply_monthly_effect()  # same call, different behavior per subclass

        self.assertEqual(chequing.balance, -135)          # overdraft fee applied
        self.assertAlmostEqual(savings.balance, 1010.0)   # interest applied
        self.assertEqual(business.balance, 975)           # maintenance fee applied


if __name__ == "__main__":
    unittest.main(verbosity=2)