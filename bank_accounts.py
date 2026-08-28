from abc import ABC, abstractmethod

class Account(ABC): 
    def __init__(self, owner, account_number, balance): 
        self._owner = owner
        self._account_number = account_number
        self._balance = balance
        self._transactions = []

    @property
    def owner(self): 
        return self._owner
    
    @property
    def balance(self): 
        return self._balance

    @property
    def account_number(self):
        return self._account_number

    @property
    def transactions(self):
        return self._transactions.copy()

    def deposit(self, amount): 
        if amount <= 0:
            raise ValueError("Deposit amount must be greater than zero!") 
        self._balance += amount
        self._transactions.append(("Deposit", amount))

    def withdraw(self, amount): 
        if amount <= 0:
            raise ValueError("Withdrawal amount must be greater than zero!") 
        if amount > self._balance:
            raise ValueError("Insufficient funds!")
        self._balance -= amount
        self._transactions.append(("Withdraw", amount))

    def transfer(self, other_account, amount):
        if not isinstance(other_account, Account):
            raise TypeError("Can only transfer to another Account")
        self.withdraw(amount)
        other_account.deposit(amount)
        self._transactions.append((f"Transfer_out from {self._account_number}", amount, other_account.owner))
        other_account._transactions.append((f"Transfer_in to {other_account.account_number}", amount, self._owner))

    def __str__(self):
        return f"{self.__class__.__name__}(owner={self._owner}, account number = {self._account_number}, balance={self._balance})"

    @abstractmethod
    def apply_monthly_effect(self): 
        pass

class ChequingAccount(Account):
    def __init__(self, owner, account_number, balance, overdraft_limit, overdraft_fee):
        super().__init__(owner, account_number, balance)
        if overdraft_limit < 0:
            raise ValueError("Overdraft limit cannot be negative!")
        self._overdraft_limit = overdraft_limit
        if overdraft_fee < 0:
            raise ValueError("Overdraft fee cannot be negative!")
        self._overdraft_fee = overdraft_fee

    @property
    def overdraft_limit(self):
        return self._overdraft_limit

    @property
    def overdraft_fee(self):
        return self._overdraft_fee

    def withdraw(self, amount): 
        if amount <= 0:
            raise ValueError("Withdrawal amount must be greater than zero!") 
        if amount > self._balance + self._overdraft_limit:
            raise ValueError("Insufficient funds!")
        self._balance -= amount
        self._transactions.append(("Withdraw", amount))

    def apply_monthly_effect(self): 
        if self._balance < 0:
            self._balance -= self._overdraft_fee
            self._transactions.append(("Overdraft Fee", self._overdraft_fee))

class SavingsAccount(Account):
    def __init__(self, owner, account_number, balance, interest_rate, withdrawal_limit): 
        super().__init__(owner, account_number, balance)
        if interest_rate < 0:
            raise ValueError("Interest_rate cannot be negative!")
        self._interest_rate = interest_rate 
        if withdrawal_limit < 0:
            raise ValueError("withdrawal_limit be negative!")
        self._withdrawal_limit = withdrawal_limit
        self._withdrawals_this_month = 0

    @property
    def interest_rate(self):
        return self._interest_rate

    @property
    def withdrawal_limit(self):
        return self._withdrawal_limit

    @property
    def withdrawals_this_month(self):
        return self._withdrawals_this_month 

    def withdraw(self, amount):
        if self.withdrawals_this_month < self.withdrawal_limit:
            self._withdrawals_this_month += 1
            return super().withdraw(amount)
        else: 
            raise PermissionError("Max withdrawal limit reached!")

    def new_month(self): 
        self._withdrawals_this_month = 0

    def apply_monthly_effect(self):
        self._balance += self._balance * self.interest_rate / 12

class BusinessAccount(ChequingAccount):
    def __init__(self, owner, account_number, balance, overdraft_limit, overdraft_fee, monthly_maintenance_fee, transaction_limit, 
                 transaction_fee, authorized_users):
        super().__init__(owner, account_number, balance, overdraft_limit, overdraft_fee)
        if monthly_maintenance_fee < 0:
            raise ValueError("Monthly maintenance fee cannot be negative!")
        self._monthly_maintenance_fee = monthly_maintenance_fee
        if transaction_limit < 0:
            raise ValueError("Transaction limit cannot be negative!")
        self._transaction_limit = transaction_limit
        if transaction_fee < 0:
            raise ValueError("Transaction fee cannot be negative!")
        self._transaction_fee = transaction_fee
        self._transactions_this_month = 0
        self._authorized_users = authorized_users.copy()
    @property
    def monthly_maintenance_fee(self):
        return self._monthly_maintenance_fee

    @property
    def transaction_limit(self):
        return self._transaction_limit

    @property
    def transaction_fee(self):
        return self._transaction_fee

    @property
    def transactions_this_month(self):
        return self._transactions_this_month 

    @property
    def authorized_users(self): 
        return self._authorized_users.copy()

    def add_user(self, first_name, last_name): 
        self._authorized_users.append((f"{last_name}, {first_name}"))

    def remove_user(self, first_name, last_name): 
        self._authorized_users.remove((f"{last_name}, {first_name}"))

    def _charge_transaction_fee_if_over_limit(self):
        self._transactions_this_month += 1
        if self._transactions_this_month > self._transaction_limit:
            self._balance -= self._transaction_fee
            self._transactions.append(("Transaction Fee", self._transaction_fee))
 
    def deposit(self, amount):
        super().deposit(amount)
        self._charge_transaction_fee_if_over_limit()
 
    def withdraw(self, amount):
        super().withdraw(amount)
        self._charge_transaction_fee_if_over_limit()
 
    def new_month(self):
        self._transactions_this_month = 0
 
    def apply_monthly_effect(self):
        self._balance -= self._monthly_maintenance_fee
        self._transactions.append(("Maintenance Fee", self._monthly_maintenance_fee))
        super().apply_monthly_effect()