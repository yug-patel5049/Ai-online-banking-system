import os
from dotenv import load_dotenv

load_dotenv()

SECRET_KEY   = os.getenv("SECRET_KEY", "dev-secret-change-me")
JWT_SECRET   = os.getenv("JWT_SECRET", "dev-jwt-change-me")
DATABASE_PATH = os.getenv("DATABASE_PATH", "bank.db")
DEBUG        = os.getenv("DEBUG", "False").lower() == "true"
