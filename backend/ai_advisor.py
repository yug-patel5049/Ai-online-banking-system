"""
AI Financial Advisor - rule-based + simple ML-style insights.
No external AI API needed; uses heuristics and pattern analysis.
"""
from datetime import datetime


def analyze_spending(transactions):
    """Analyze spending patterns and return insights."""
    if not transactions:
        return {"message": "No transactions yet. Start banking to get AI insights!"}

    debits = [t for t in transactions if t["type"] == "debit"]
    credits = [t for t in transactions if t["type"] == "credit"]

    total_spent = sum(t["amount"] for t in debits)
    total_earned = sum(t["amount"] for t in credits)
    avg_spend = total_spent / len(debits) if debits else 0

    insights = []
    tips = []

    # Spending vs income ratio
    if total_earned > 0:
        ratio = total_spent / total_earned
        if ratio > 0.9:
            insights.append("You're spending over 90% of your income. Consider cutting back.")
            tips.append("Try the 50/30/20 rule: 50% needs, 30% wants, 20% savings.")
        elif ratio > 0.7:
            insights.append("Spending is at 70-90% of income. Room for improvement.")
            tips.append("Aim to save at least 20% of your income each month.")
        else:
            insights.append("Great job! You're spending less than 70% of your income.")
            tips.append("Consider investing your savings for long-term growth.")

    # Large transactions
    if debits:
        max_debit = max(debits, key=lambda x: x["amount"])
        if max_debit["amount"] > avg_spend * 2:
            insights.append(f"Large transaction detected: INR {max_debit['amount']:.2f} - {max_debit['description']}")

    # Frequency analysis
    if len(debits) > 10:
        tips.append("High transaction frequency detected. Review for unnecessary spending.")

    return {
        "total_spent": round(total_spent, 2),
        "total_earned": round(total_earned, 2),
        "avg_transaction": round(avg_spend, 2),
        "transaction_count": len(transactions),
        "insights": insights,
        "tips": tips
    }


def get_savings_advice(balance, account_type):
    """Give savings advice based on balance."""
    advice = []
    if balance < 500:
        advice.append("Low balance alert! Try to maintain a minimum of INR 1000.")
    elif balance < 5000:
        advice.append("Consider building an emergency fund of at least 3 months expenses.")
    elif balance > 50000:
        advice.append("You have a healthy balance. Consider fixed deposits or mutual funds.")
    
    if account_type == "Savings":
        advice.append("Savings accounts earn interest. Keep funds here when not needed.")
    elif account_type == "Current":
        advice.append("Current accounts are for frequent transactions. Move surplus to savings.")
    
    return advice


def detect_fraud(transactions):
    """Simple fraud detection based on transaction patterns."""
    if len(transactions) < 2:
        return {"risk": "low", "alerts": []}

    alerts = []
    recent = transactions[:5]  # last 5 transactions

    # Check for rapid successive withdrawals
    debits = [t for t in recent if t["type"] == "debit"]
    if len(debits) >= 3:
        total = sum(t["amount"] for t in debits)
        if total > 10000:
            alerts.append("Multiple large withdrawals detected recently. Please verify.")

    # Check for unusually large single transaction
    for t in recent:
        if t["amount"] > 25000:
            alerts.append(f"Unusually large transaction: INR {t['amount']:.2f}. Please confirm this was you.")
            break

    risk = "high" if len(alerts) > 1 else ("medium" if alerts else "low")
    return {"risk": risk, "alerts": alerts}


def chat_response(message, balance, transactions):
    """Simple AI chatbot for banking queries."""
    msg = message.lower()

    if any(w in msg for w in ["balance", "how much", "money"]):
        return f"Your current balance is INR {balance:.2f}."

    if any(w in msg for w in ["spend", "spending", "expense"]):
        analysis = analyze_spending(transactions)
        tips = analysis.get("tips", [])
        return f"You've spent INR {analysis['total_spent']} recently. " + (tips[0] if tips else "Keep tracking!")

    if any(w in msg for w in ["save", "saving", "invest"]):
        return "A good rule: save 20% of income. For INR 10,000 income, save INR 2,000 monthly. Consider SIPs for long-term growth."

    if any(w in msg for w in ["loan", "borrow", "credit"]):
        return "For loans, ensure your EMI doesn't exceed 40% of monthly income. Maintain a good credit score by paying bills on time."

    if any(w in msg for w in ["fraud", "suspicious", "stolen", "hack"]):
        return "If you suspect fraud, immediately change your password and contact support. Never share OTPs or passwords with anyone."

    if any(w in msg for w in ["hello", "hi", "hey"]):
        return "Hello! I'm your AI banking assistant. Ask me about your balance, spending tips, savings advice, or fraud protection."

    return "I can help with balance inquiries, spending analysis, savings tips, and fraud alerts. What would you like to know?"
