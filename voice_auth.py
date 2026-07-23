import json
from pathlib import Path

VOICE_DB = Path("voice_users.json")


def save_voice_phrase(email: str, phrase: str):

    if not VOICE_DB.exists():
        with open(VOICE_DB, "w") as f:
            json.dump({}, f)

    with open(VOICE_DB, "r") as f:
        users = json.load(f)

    users[email.lower()] = {
        "voice_phrase": phrase.strip().lower()
    }

    with open(VOICE_DB, "w") as f:
        json.dump(users, f, indent=4)


def load_voice_phrase(email: str):

    if not VOICE_DB.exists():
        return None

    with open(VOICE_DB, "r") as f:
        users = json.load(f)

    user = users.get(email.lower())

    if not user:
        return None

    return user["voice_phrase"]


def enable_voice_login(email: str, phrase: str):
    save_voice_phrase(email, phrase)