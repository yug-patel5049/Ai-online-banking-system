
import random

class Customer:
    def __init__(self,name,address,contact_number):
        self.name = name
        self.address = address
        self.contact_number = contact_number
        self.accounts = []

    def create_account(self, account_type, initial_balance):
        account_number = Bank.generate_account_number()
        account = BankAccount(account_type, initial_balance, self, account_number)
        self.accounts.append(account)
        return account

    def display_info(self):
        print(f"Name: {self.name}, Address: {self.address}, Contact: {self.contact_number}")
        for account in self.accounts:
            print(f"  - {account}")


class BankAccount:
    def __init__(self, account_type, balance, owner, account_number):
        self.account_type = account_type
        self.balance = balance
        self.owner = owner
        self.account_number = account_number

    def deposit(self, amount):
        self.balance += amount
        print(f"Deposited INR {amount}. New balance is INR {self.balance}.")

    def withdraw(self, amount):
        if amount <= self.balance:
            self.balance -= amount
            print(f"Withdrew INR {amount}. New balance is INR {self.balance}.")
        else:
            print("Insufficient funds.")

    def __str__(self):
        return f"{self.account_type} Account [No: {self.account_number}, Balance: INR{self.balance}]"

class Bank: 
    def __init__(self, name):
        self.name = name
        self.customers = []

    def add_customer(self, customer):
        self.customers.append(customer)

    @staticmethod
    def generate_account_number():
        return ''.join(random.choices('0123456789', k=8))

    def display_info(self):
        print(f"Bank: {self.name}")
        for customer in self.customers:
            customer.display_info()

    def find_account(self, account_number):
        for customer in self.customers:
            for account in customer.accounts:
                if account.account_number == account_number:
                    return account
        return None
# Main program
if __name__ == "__main__":
    my_bank = Bank("My Bank")

    while True:
        print("1. New Customer\n2. Existing Customer\n3. Display Bank Info\n4. Exit")
        choice = input("Choose an option: ")

        if choice == "1":
            name = input("Name: ")
            address = input("Address: ")
            contact = input("Contact: ")
            customer = Customer(name, address, contact)
            my_bank.add_customer(customer)

            while True:
                acc_type = input("1. Savings\n2. Current\n3. Exit\nChoose account type: ")
                if acc_type in ["1", "2"]:
                    acc_name = "Savings" if acc_type == "1" else "Current"
                    account = customer.create_account(acc_name, 1000)
                    print(f"Created {acc_name} account: {account}")
                elif acc_type == "3":
                    break
                else:
                    print("Invalid option.")

        elif choice == "2":
            acc_number = input("Enter account number: ")
            account = my_bank.find_account(acc_number)
            if account:
                print(f"Welcome, {account.owner.name}! {account}")
                while True:
                    action = input("1. Deposit\n2. Withdraw\n3. Exit\nChoose: ")
                    if action == "1":
                        amount = int(input("Amount to deposit: "))
                        account.deposit(amount)
                    elif action == "2":
                        amount = int(input("Amount to withdraw: "))
                        account.withdraw(amount)
                    elif action == "3":
                        break
                    else:
                        print("Invalid option.")
            else:
                print("Account not found.")

        elif choice == "3":
            my_bank.display_info()

        elif choice == "4":
            break

        else:
            print("Invalid option.")       

