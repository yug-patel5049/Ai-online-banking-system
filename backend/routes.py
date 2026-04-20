from flask import Blueprint, request, jsonify
from auth import token_required
import models
import ai_advisor

api_bp = Blueprint("api", __name__)

# ── Accounts ──────────────────────────────────────────────────────────────────

@api_bp.route("/api/accounts", methods=["GET"])
@token_required
def get_accounts():
    return jsonify(models.get_accounts(request.user_id)), 200


@api_bp.route("/api/accounts", methods=["POST"])
@token_required
def open_account():
    data = request.get_json(silent=True) or {}
    acc, err = models.create_account(request.user_id, data.get("account_type", "Savings"))
    if err:
        return jsonify({"error": err}), 400
    return jsonify(acc), 201

# ── Transactions ──────────────────────────────────────────────────────────────

def _owned(account_number):
    """Return account if it belongs to the logged-in user, else None."""
    acc = models.get_account(account_number)
    if acc and acc["user_id"] == request.user_id:
        return acc
    return None


@api_bp.route("/api/deposit", methods=["POST"])
@token_required
def deposit():
    data = request.get_json(silent=True) or {}
    if not _owned(data.get("account_number", "")):
        return jsonify({"error": "Access denied"}), 403
    acc, err = models.deposit(data["account_number"], data.get("amount"),
                              data.get("description", "Deposit"))
    if err:
        return jsonify({"error": err}), 400
    return jsonify({"message": "Deposit successful", "balance": acc["balance"]}), 200


@api_bp.route("/api/withdraw", methods=["POST"])
@token_required
def withdraw():
    data = request.get_json(silent=True) or {}
    if not _owned(data.get("account_number", "")):
        return jsonify({"error": "Access denied"}), 403
    acc, err = models.withdraw(data["account_number"], data.get("amount"),
                               data.get("description", "Withdrawal"))
    if err:
        return jsonify({"error": err}), 400
    return jsonify({"message": "Withdrawal successful", "balance": acc["balance"]}), 200


@api_bp.route("/api/transfer", methods=["POST"])
@token_required
def transfer():
    data = request.get_json(silent=True) or {}
    if not _owned(data.get("from_account", "")):
        return jsonify({"error": "Access denied"}), 403
    acc, err = models.transfer(
        data.get("from_account"), data.get("to_account"),
        data.get("amount"), request.user_id
    )
    if err:
        return jsonify({"error": err}), 400
    return jsonify({"message": "Transfer successful", "balance": acc["balance"]}), 200


@api_bp.route("/api/transactions/<account_number>", methods=["GET"])
@token_required
def transactions(account_number):
    if not _owned(account_number):
        return jsonify({"error": "Access denied"}), 403
    return jsonify(models.get_transactions(account_number)), 200

# ── AI ────────────────────────────────────────────────────────────────────────

@api_bp.route("/api/ai/insights/<account_number>", methods=["GET"])
@token_required
def ai_insights(account_number):
    acc = _owned(account_number)
    if not acc:
        return jsonify({"error": "Access denied"}), 403
    txns = models.get_transactions(account_number, limit=50)
    return jsonify({
        "analysis": ai_advisor.analyze_spending(txns),
        "savings_advice": ai_advisor.get_savings_advice(acc["balance"], acc["account_type"]),
        "fraud": ai_advisor.detect_fraud(txns)
    }), 200


@api_bp.route("/api/ai/chat", methods=["POST"])
@token_required
def ai_chat():
    data = request.get_json(silent=True) or {}
    message = str(data.get("message", ""))[:500]
    if not message:
        return jsonify({"error": "Message required"}), 400
    accs = models.get_accounts(request.user_id)
    balance = accs[0]["balance"] if accs else 0
    txns = models.get_transactions(accs[0]["account_number"]) if accs else []
    return jsonify({"reply": ai_advisor.chat_response(message, balance, txns)}), 200
