import jwt
import datetime
from functools import wraps
from flask import Blueprint, request, jsonify
import models
import config

auth_bp = Blueprint("auth", __name__)

def create_token(user_id, username):
    payload = {
        "user_id": user_id,
        "username": username,
        "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=8),
        "iat": datetime.datetime.utcnow()
    }
    token = jwt.encode(payload, config.JWT_SECRET, algorithm="HS256")
    # PyJWT >= 2.0 returns str, older versions return bytes
    return token if isinstance(token, str) else token.decode("utf-8")


def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get("Authorization", "")
        token = auth_header.replace("Bearer ", "").strip()
        if not token:
            return jsonify({"error": "Token missing"}), 401
        try:
            data = jwt.decode(token, config.JWT_SECRET, algorithms=["HS256"])
            request.user_id = data["user_id"]
            request.username = data["username"]
        except jwt.ExpiredSignatureError:
            return jsonify({"error": "Session expired, please login again"}), 401
        except jwt.InvalidTokenError as e:
            return jsonify({"error": "Invalid token"}), 401
        return f(*args, **kwargs)
    return decorated


@auth_bp.route("/api/register", methods=["POST"])
def register():
    data = request.get_json(silent=True) or {}
    required = ["username", "password", "name", "email", "phone"]
    if not all(data.get(k) for k in required):
        return jsonify({"error": "All fields are required"}), 400

    user, err = models.create_user(
        data["username"], data["password"],
        data["name"], data["email"], data["phone"]
    )
    if err:
        return jsonify({"error": err}), 400

    models.create_account(user["id"], "Savings", 1000.0)
    return jsonify({"message": "Account created successfully"}), 201


@auth_bp.route("/api/login", methods=["POST"])
def login():
    data = request.get_json(silent=True) or {}
    username = data.get("username", "").strip()
    password = data.get("password", "")
    ip = request.remote_addr

    if not username or not password:
        return jsonify({"error": "Username and password required"}), 400

    if models.is_locked_out(username, ip):
        return jsonify({"error": "Too many failed attempts. Try again in 15 minutes."}), 429

    user = models.get_user_by_username(username)
    if not user or not models.verify_password(password, user["password"]):
        models.log_attempt(username, ip, False)
        return jsonify({"error": "Invalid username or password"}), 401

    models.log_attempt(username, ip, True)
    token = create_token(user["id"], user["username"])
    return jsonify({
        "token": token,
        "name": user["name"],
        "username": user["username"]
    }), 200
