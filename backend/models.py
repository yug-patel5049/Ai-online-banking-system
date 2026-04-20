import hashlib
import secrets
import re
from database import get_db

# ── Helpers ───────────────────────────────────────────────────────────────────

def hash_password(password):
    salt = secrets.token_hex(16)
    h = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 260_000)
    return f"{salt}:{h.hex()}"

def verify_password(password, stored):
    try:
        salt, h = stored.split(":", 1)
        check = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 260_000)
        return secrets.compare_digest(check.hex(), h)
    except Exception:
        return False

def gen_account_number():
    return "".join(str(secrets.randbelow(10)) for _ in range(10))

def sanitize(val, max_len=100):
    return str(val).strip()[:max_len] if val else ""

def validate_username(u):
    if not re.match(r"^[a-zA-Z0-9_\.@]{3,50}$", u):
        return "Username: 3-50 chars, letters/numbers/underscore/dot/@ only"

def validate_password(p):
    if len(p) < 8: return "Password must be at least 8 characters"
    if not re.search(r"[A-Za-z]", p): return "Password must contain a letter"
    if not re.search(r"[0-9]", p): return "Password must contain a number"

def validate_email(e):
    if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", e):
        return "Invalid email address"

# ── Users ─────────────────────────────────────────────────────────────────────

def create_user(username, password, name, email, phone):
    username = sanitize(username, 30)
    name     = sanitize(name, 80)
    email    = sanitize(email, 100).lower()
    phone    = sanitize(phone, 20)

    for check in [validate_username(username), validate_password(password),
                  validate_email(email)]:
        if check:
            return None, check

    with get_db() as db:
        existing = db.execute("SELECT id FROM users WHERE username=? OR email=?",
                              (username, email)).fetchone()
        if existing:
            return None, "Username or email already exists"
        db.execute(
            "INSERT INTO users (username,password,name,email,phone) VALUES (?,?,?,?,?)",
            (username, hash_password(password), name, email, phone)
        )
        user = db.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()
    return dict(user), None


def get_user_by_username(username):
    with get_db() as db:
        row = db.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()
    return dict(row) if row else None


def is_locked_out(username, ip):
    """Block if 5+ failed attempts in last 15 minutes."""
    with get_db() as db:
        count = db.execute("""
            SELECT COUNT(*) FROM login_attempts
            WHERE username=? AND success=0
            AND created_at > datetime('now','-15 minutes')
        """, (username,)).fetchone()[0]
    return count >= 5


def log_attempt(username, ip, success):
    with get_db() as db:
        db.execute(
            "INSERT INTO login_attempts (username,ip,success) VALUES (?,?,?)",
            (username, ip, 1 if success else 0)
        )

# ── Accounts ──────────────────────────────────────────────────────────────────

def create_account(user_id, account_type, initial_balance=1000.0):
    if account_type not in ("Savings", "Current"):
        return None, "Invalid account type"
    with get_db() as db:
        count = db.execute("SELECT COUNT(*) FROM accounts WHERE user_id=?",
                           (user_id,)).fetchone()[0]
        if count >= 5:
            return None, "Maximum 5 accounts allowed"
        acc_num = gen_account_number()
        db.execute(
            "INSERT INTO accounts (account_number,account_type,balance,user_id) VALUES (?,?,?,?)",
            (acc_num, account_type, round(initial_balance, 2), user_id)
        )
        _log_txn(db, acc_num, "credit", initial_balance, "Account opened", initial_balance)
        acc = db.execute("SELECT * FROM accounts WHERE account_number=?", (acc_num,)).fetchone()
    return dict(acc), None


def get_accounts(user_id):
    with get_db() as db:
        rows = db.execute("SELECT * FROM accounts WHERE user_id=? ORDER BY created_at",
                          (user_id,)).fetchall()
    return [dict(r) for r in rows]


def get_account(account_number):
    with get_db() as db:
        row = db.execute("SELECT * FROM accounts WHERE account_number=?",
                         (account_number,)).fetchone()
    return dict(row) if row else None

# ── Transactions ──────────────────────────────────────────────────────────────

def _validate_amount(amount):
    try:
        amount = round(float(amount), 2)
    except (TypeError, ValueError):
        return None, "Invalid amount"
    if amount <= 0:
        return None, "Amount must be positive"
    if amount > 1_000_000:
        return None, "Amount exceeds maximum limit"
    return amount, None


def deposit(account_number, amount, description="Deposit"):
    amount, err = _validate_amount(amount)
    if err: return None, err
    description = sanitize(description, 100)
    with get_db() as db:
        acc = db.execute("SELECT * FROM accounts WHERE account_number=?",
                         (account_number,)).fetchone()
        if not acc: return None, "Account not found"
        new_bal = round(acc["balance"] + amount, 2)
        db.execute("UPDATE accounts SET balance=? WHERE account_number=?",
                   (new_bal, account_number))
        _log_txn(db, account_number, "credit", amount, description, new_bal)
        acc = db.execute("SELECT * FROM accounts WHERE account_number=?",
                         (account_number,)).fetchone()
    return dict(acc), None


def withdraw(account_number, amount, description="Withdrawal"):
    amount, err = _validate_amount(amount)
    if err: return None, err
    if amount > 500_000: return None, "Single withdrawal limit is INR 5,00,000"
    description = sanitize(description, 100)
    with get_db() as db:
        acc = db.execute("SELECT * FROM accounts WHERE account_number=?",
                         (account_number,)).fetchone()
        if not acc: return None, "Account not found"
        if acc["balance"] < amount: return None, "Insufficient funds"
        new_bal = round(acc["balance"] - amount, 2)
        db.execute("UPDATE accounts SET balance=? WHERE account_number=?",
                   (new_bal, account_number))
        _log_txn(db, account_number, "debit", amount, description, new_bal)
        acc = db.execute("SELECT * FROM accounts WHERE account_number=?",
                         (account_number,)).fetchone()
    return dict(acc), None


def transfer(from_acc, to_acc, amount, user_id):
    if from_acc == to_acc: return None, "Cannot transfer to same account"
    with get_db() as db:
        dest = db.execute("SELECT * FROM accounts WHERE account_number=?",
                          (to_acc,)).fetchone()
        if not dest: return None, "Recipient account not found"
    acc, err = withdraw(from_acc, amount, f"Transfer to ****{to_acc[-4:]}")
    if err: return None, err
    deposit(to_acc, amount, f"Transfer from ****{from_acc[-4:]}")
    return acc, None


def _log_txn(db, account_number, txn_type, amount, description, balance_after):
    db.execute(
        "INSERT INTO transactions (account_number,type,amount,description,balance_after) VALUES (?,?,?,?,?)",
        (account_number, txn_type, amount, description, balance_after)
    )


def get_transactions(account_number, limit=20):
    limit = min(int(limit), 100)
    with get_db() as db:
        rows = db.execute("""
            SELECT * FROM transactions WHERE account_number=?
            ORDER BY created_at DESC LIMIT ?
        """, (account_number, limit)).fetchall()
    return [dict(r) for r in rows]
