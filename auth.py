import hashlib, json, os
from datetime import datetime

USERS_FILE = "users.json"

# pip install bcrypt
import bcrypt

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode(), hashed.encode())

def load_users():
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, "r") as f:
            return json.load(f)
    return {}

def save_users(users):
    with open(USERS_FILE, "w") as f:
        json.dump(users, f, indent=2)

def register_user(name, email, password):
    users = load_users()
    if email in users:
        return False, "Email already registered."
    users[email] = {
        "name": name,
        "email": email,
        "password": hash_password(password),
        "created_at": datetime.now().isoformat(),
        "blueprints_generated": 0
    }
    save_users(users)
    return True, "Registration successful!"

def login_user(email, password):
    users = load_users()
    if email not in users:
        return False, None, "Email not found."
    if users[email]["password"] != hash_password(password):
        return False, None, "Incorrect password."
    return True, users[email], "Login successful!"

def increment_blueprint_count(email):
    users = load_users()
    if email in users:
        users[email]["blueprints_generated"] += 1
        save_users(users)
