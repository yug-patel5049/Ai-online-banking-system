from flask import Flask, jsonify
from flask_cors import CORS
from database import init_db
from auth import auth_bp
from routes import api_bp
import config
import time

app = Flask(__name__)
app.secret_key = config.SECRET_KEY
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024

CORS(app, supports_credentials=True, origins=[
    "http://localhost:3000", "http://localhost:8080",
    "http://127.0.0.1:3000", "http://127.0.0.1:8080",
    "http://localhost:5500", "http://127.0.0.1:5500",
    "https://ai-online-banking-system.onrender.com",
    "https://aibankingsystem.netlify.app"
])

app.register_blueprint(auth_bp)
app.register_blueprint(api_bp)

# Initialize DB on startup (works with both gunicorn and python app.py)
init_db()

# ── Rate limiting ─────────────────────────────────────────────────────────────
_req_log = {}

@app.before_request
def rate_limit():
    from flask import request, abort
    ip = request.remote_addr
    now = time.time()
    window = [t for t in _req_log.get(ip, []) if now - t < 60]
    if len(window) >= 100:
        abort(429)
    window.append(now)
    _req_log[ip] = window

# ── Security headers ──────────────────────────────────────────────────────────
@app.after_request
def security_headers(response):
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Cache-Control"] = "no-store"
    return response

@app.errorhandler(404)
def not_found(e): return jsonify({"error": "Not found"}), 404

@app.errorhandler(429)
def too_many(e): return jsonify({"error": "Too many requests"}), 429

@app.errorhandler(500)
def server_error(e): return jsonify({"error": "Internal server error"}), 500

if __name__ == "__main__":
    print("✅ Database initialized")
    print("🚀 AI Bank running at http://127.0.0.1:5000")
    app.run(debug=config.DEBUG, port=5000)
