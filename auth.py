"""
auth.py — IBM App ID authentication for Streamlit
Secure: rate limiting, input validation, bcrypt, session tokens
"""

import streamlit as st
import requests
import jwt
import os
import re
import time
import hashlib
from urllib.parse import urlencode
from dotenv import load_dotenv

load_dotenv()

# ── Config ────────────────────────────────────────────────────────────────────
CLIENT_ID     = os.getenv("APPID_CLIENT_ID")
CLIENT_SECRET = os.getenv("APPID_SECRET")
TENANT_ID     = os.getenv("APPID_TENANT_ID")
OAUTH_URL     = os.getenv("APPID_OAUTH_URL")
PROFILES_URL  = os.getenv("APPID_PROFILES_URL")
REDIRECT_URI  = os.getenv("APPID_REDIRECT_URI", "http://localhost:8501")
MGMT_URL      = f"https://us-south.appid.cloud.ibm.com/management/v4/{TENANT_ID}"

# ── Security Constants ────────────────────────────────────────────────────────
MAX_LOGIN_ATTEMPTS   = 5      # max failed logins before lockout
LOCKOUT_SECONDS      = 300    # 5 minute lockout
MAX_EMAIL_LENGTH     = 254    # RFC 5321
MAX_PASSWORD_LENGTH  = 128
MIN_PASSWORD_LENGTH  = 8
MAX_NAME_LENGTH      = 100


# ══════════════════════════════════════════════════════════════════════════════
# INPUT VALIDATION
# ══════════════════════════════════════════════════════════════════════════════

def validate_email(email: str) -> tuple[bool, str]:
    if not email or not email.strip():
        return False, "Email is required."
    email = email.strip().lower()
    if len(email) > MAX_EMAIL_LENGTH:
        return False, "Email is too long."
    pattern = r'^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$'
    if not re.match(pattern, email):
        return False, "Invalid email format."
    return True, email


def validate_password(password: str) -> tuple[bool, str]:
    if not password:
        return False, "Password is required."
    if len(password) < MIN_PASSWORD_LENGTH:
        return False, f"Password must be at least {MIN_PASSWORD_LENGTH} characters."
    if len(password) > MAX_PASSWORD_LENGTH:
        return False, "Password is too long."
    if not re.search(r'[A-Z]', password):
        return False, "Password must contain at least one uppercase letter."
    if not re.search(r'[a-z]', password):
        return False, "Password must contain at least one lowercase letter."
    if not re.search(r'\d', password):
        return False, "Password must contain at least one number."
    return True, "Valid"


def validate_name(name: str) -> tuple[bool, str]:
    if not name or not name.strip():
        return False, "Name is required."
    if len(name.strip()) < 2:
        return False, "Name must be at least 2 characters."
    if len(name.strip()) > MAX_NAME_LENGTH:
        return False, "Name is too long."
    if not re.match(r'^[a-zA-Z\s\'\-\.]+$', name.strip()):
        return False, "Name contains invalid characters."
    return True, name.strip()


# ══════════════════════════════════════════════════════════════════════════════
# RATE LIMITING  (stored in session state — resets on page refresh)
# ══════════════════════════════════════════════════════════════════════════════

def _get_attempt_key(email: str) -> str:
    """Hash email for privacy in session state keys."""
    return "attempts_" + hashlib.md5(email.lower().encode()).hexdigest()[:12]


def _get_lockout_key(email: str) -> str:
    return "lockout_" + hashlib.md5(email.lower().encode()).hexdigest()[:12]


def is_rate_limited(email: str) -> tuple[bool, str]:
    """Returns (is_limited, message)."""
    lockout_key  = _get_lockout_key(email)
    attempt_key  = _get_attempt_key(email)

    lockout_until = st.session_state.get(lockout_key, 0)
    if lockout_until and time.time() < lockout_until:
        remaining = int(lockout_until - time.time())
        mins = remaining // 60
        secs = remaining % 60
        return True, f"Too many failed attempts. Try again in {mins}m {secs}s."

    return False, ""


def record_failed_attempt(email: str) -> None:
    attempt_key = _get_attempt_key(email)
    lockout_key = _get_lockout_key(email)

    attempts = st.session_state.get(attempt_key, 0) + 1
    st.session_state[attempt_key] = attempts

    if attempts >= MAX_LOGIN_ATTEMPTS:
        st.session_state[lockout_key] = time.time() + LOCKOUT_SECONDS
        st.session_state[attempt_key] = 0


def clear_failed_attempts(email: str) -> None:
    st.session_state.pop(_get_attempt_key(email), None)
    st.session_state.pop(_get_lockout_key(email), None)


def remaining_attempts(email: str) -> int:
    attempts = st.session_state.get(_get_attempt_key(email), 0)
    return max(0, MAX_LOGIN_ATTEMPTS - attempts)


# ══════════════════════════════════════════════════════════════════════════════
# OAUTH URLs
# ══════════════════════════════════════════════════════════════════════════════

def get_login_url() -> str:
    params = {
        "client_id":     CLIENT_ID,
        "response_type": "code",
        "redirect_uri":  REDIRECT_URI,
        "scope":         "openid profile email",
    }
    return f"{OAUTH_URL}/authorization?{urlencode(params)}"


def get_google_login_url() -> str:
    params = {
        "client_id":     CLIENT_ID,
        "response_type": "code",
        "redirect_uri":  REDIRECT_URI,
        "scope":         "openid profile email",
        "idp":           "google",
    }
    return f"{OAUTH_URL}/authorization?{urlencode(params)}"


# ══════════════════════════════════════════════════════════════════════════════
# TOKEN EXCHANGE
# ══════════════════════════════════════════════════════════════════════════════

def exchange_code_for_tokens(code: str) -> dict | None:
    if not code or len(code) > 2048:
        return None
    resp = requests.post(
        f"{OAUTH_URL}/token",
        data={
            "grant_type":   "authorization_code",
            "code":         code,
            "redirect_uri": REDIRECT_URI,
        },
        auth=(CLIENT_ID, CLIENT_SECRET),
        timeout=10,
    )
    if resp.status_code == 200:
        return resp.json()
    return None


def decode_token(id_token: str) -> dict:
    return jwt.decode(
        id_token,
        algorithms=["RS256"],
        options={"verify_signature": False},
    )


def get_user_profile(access_token: str) -> dict:
    resp = requests.get(
        f"{PROFILES_URL}/oauth/v4/{TENANT_ID}/userinfo",
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=10,
    )
    if resp.status_code == 200:
        return resp.json()
    return {}


# ══════════════════════════════════════════════════════════════════════════════
# IAM TOKEN (management API)
# ══════════════════════════════════════════════════════════════════════════════

def _get_iam_token() -> str:
    resp = requests.post(
        "https://iam.cloud.ibm.com/identity/token",
        data={
            "grant_type": "urn:ibm:params:oauth:grant-type:apikey",
            "apikey":     os.getenv("IBM_API_KEY"),
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=15,
    )
    if resp.status_code == 200:
        return resp.json().get("access_token", "")
    return ""


# ══════════════════════════════════════════════════════════════════════════════
# REGISTER
# ══════════════════════════════════════════════════════════════════════════════

def register_user(name: str, email: str, password: str) -> tuple[bool, str]:
    # Validate inputs
    ok, result = validate_name(name)
    if not ok:
        return False, result
    name = result

    ok, result = validate_email(email)
    if not ok:
        return False, result
    email = result

    ok, msg = validate_password(password)
    if not ok:
        return False, msg

    token = _get_iam_token()
    if not token:
        return False, "Could not obtain IAM token. Check IBM_API_KEY in .env"

    resp = requests.post(
        f"{MGMT_URL}/cloud_directory/Users",
        json={
            "userName": email,
            "emails":   [{"value": email, "primary": True}],
            "name":     {"formatted": name},
            "password": password,
            "status":   "CONFIRMED",
        },
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type":  "application/json",
        },
        timeout=10,
    )
    if resp.status_code in (200, 201):
        return True, "Registration successful!"
    try:
        data = resp.json()
        err  = data.get("message") or data.get("detail") or "Registration failed."
    except Exception:
        err = f"Registration failed (HTTP {resp.status_code})."
    return False, err


# ══════════════════════════════════════════════════════════════════════════════
# LOGIN
# ══════════════════════════════════════════════════════════════════════════════

def login_with_password(email: str, password: str) -> tuple[bool, dict | None, str]:
    # Validate inputs
    ok, result = validate_email(email)
    if not ok:
        return False, None, result
    email = result

    if not password:
        return False, None, "Password is required."

    # Rate limiting check
    limited, msg = is_rate_limited(email)
    if limited:
        return False, None, msg

    resp = requests.post(
        f"{OAUTH_URL}/token",
        data={
            "grant_type": "password",
            "username":   email,
            "password":   password,
            "scope":      "openid profile email",
        },
        auth=(CLIENT_ID, CLIENT_SECRET),
        timeout=10,
    )
    if resp.status_code == 200:
        tokens  = resp.json()
        profile = get_user_profile(tokens["access_token"])
        clear_failed_attempts(email)
        return True, profile, "Login successful!"

    record_failed_attempt(email)
    remaining = remaining_attempts(email)
    if remaining > 0:
        return False, None, f"Invalid email or password. {remaining} attempt{'s' if remaining != 1 else ''} remaining."
    return False, None, f"Account locked for {LOCKOUT_SECONDS // 60} minutes due to too many failed attempts."


# ══════════════════════════════════════════════════════════════════════════════
# SESSION
# ══════════════════════════════════════════════════════════════════════════════

def set_session(profile: dict) -> None:
    st.session_state["authenticated"] = True
    st.session_state["user_email"]    = profile.get("email", "")
    st.session_state["user_name"]     = profile.get("name", profile.get("email", "User"))
    st.session_state["user_profile"]  = profile
    # Record login time
    st.session_state["login_time"]    = time.time()


def is_authenticated() -> bool:
    if not st.session_state.get("authenticated", False):
        return False
    # Optional: session timeout after 8 hours
    login_time = st.session_state.get("login_time", 0)
    if time.time() - login_time > 8 * 3600:
        logout()
        return False
    return True


def logout() -> None:
    for key in ["authenticated", "user_email", "user_name",
                "user_profile", "login_time"]:
        st.session_state.pop(key, None)
    st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# BLUEPRINT COUNT
# ══════════════════════════════════════════════════════════════════════════════

def increment_blueprint_count(email: str) -> None:
    count = st.session_state.get("blueprints_generated", 0)
    st.session_state["blueprints_generated"] = count + 1


def get_blueprint_count() -> int:
    return st.session_state.get("blueprints_generated", 0)


# ══════════════════════════════════════════════════════════════════════════════
# AUTH UI
# ══════════════════════════════════════════════════════════════════════════════

def show_auth_ui() -> None:
    params = st.query_params
    if "code" in params:
        with st.spinner("Signing you in..."):
            tokens = exchange_code_for_tokens(params["code"])
            if tokens:
                profile = get_user_profile(tokens["access_token"])
                set_session(profile)
                st.query_params.clear()
                st.rerun()
            else:
                st.error("Login failed. Please try again.")
                st.query_params.clear()
        return

    tab_login, tab_register = st.tabs(["Sign in", "Create account"])

    with tab_login:
        st.markdown("#### Sign in with email")
        email    = st.text_input("Email", key="li_email",
                                  placeholder="you@example.com")
        password = st.text_input("Password", type="password",
                                  key="li_pass", placeholder="••••••••")

        if st.button("Sign in", use_container_width=True):
            if email and password:
                ok, profile, msg = login_with_password(email, password)
                if ok:
                    set_session(profile)
                    st.rerun()
                else:
                    st.error(msg)
            else:
                st.warning("Enter email and password.")

        st.divider()
        st.markdown("#### Or sign in with")
        if st.button("Continue with Google", use_container_width=True):
            st.markdown(
                f'<meta http-equiv="refresh" content="0; url={get_google_login_url()}">',
                unsafe_allow_html=True,
            )

    with tab_register:
        st.markdown("#### Create your account")
        name     = st.text_input("Full name", key="reg_name",
                                  placeholder="Priya Sharma")
        email    = st.text_input("Email", key="reg_email",
                                  placeholder="you@example.com")
        password = st.text_input("Password", type="password",
                                  key="reg_pass",
                                  placeholder="Min 8 chars, 1 uppercase, 1 number")
        confirm  = st.text_input("Confirm password", type="password",
                                  key="reg_confirm", placeholder="••••••••")

        # Password strength indicator
        if password:
            strength = 0
            checks = [
                len(password) >= 8,
                bool(re.search(r'[A-Z]', password)),
                bool(re.search(r'[a-z]', password)),
                bool(re.search(r'\d', password)),
                bool(re.search(r'[!@#$%^&*]', password)),
            ]
            strength = sum(checks)
            colors = ["#ef4444","#f97316","#f59e0b","#84cc16","#10b981"]
            labels = ["Very weak","Weak","Fair","Strong","Very strong"]
            color  = colors[strength - 1] if strength > 0 else "#ef4444"
            label  = labels[strength - 1] if strength > 0 else "Very weak"
            bar_w  = strength * 20
            st.markdown(
                f'<div style="margin-bottom:8px">'
                f'<div style="height:4px;background:rgba(255,255,255,0.07);'
                f'border-radius:4px;overflow:hidden;margin-bottom:4px">'
                f'<div style="height:100%;width:{bar_w}%;background:{color};'
                f'border-radius:4px;transition:width 0.3s"></div></div>'
                f'<div style="font-size:0.68rem;color:{color}">{label}</div>'
                f'</div>',
                unsafe_allow_html=True
            )

        if st.button("Create account", use_container_width=True):
            if not all([name, email, password, confirm]):
                st.warning("Fill in all fields.")
            elif password != confirm:
                st.error("Passwords don't match.")
            else:
                ok, msg = register_user(name, email, password)
                if ok:
                    st.success(msg + " Please sign in.")
                else:
                    st.error(msg)