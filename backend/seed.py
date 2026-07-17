"""
Seed demo users so the portal can authenticate against the live API.
Runs once at startup; skips users that already exist.
"""
from passlib.context import CryptContext

from db.database import SessionLocal
from models.orm import User

_pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")

DEMO_USERS = [
    {"id": "U001", "name": "Nora Al-Rashidi",  "role": "Chief Compliance Officer",  "clearance": 5},
    {"id": "U002", "name": "Faisal Al-Otaibi", "role": "Senior AML Analyst",        "clearance": 4},
    {"id": "U003", "name": "Lama Al-Zahrani",  "role": "Risk Intelligence Officer", "clearance": 4},
    {"id": "U004", "name": "Tariq Al-Dawsari", "role": "Transaction Reviewer",      "clearance": 3},
    {"id": "U005", "name": "Reem Al-Sulami",   "role": "Audit Coordinator",         "clearance": 3},
]

DEMO_PIN = "1234"


def seed_demo_users() -> None:
    db = SessionLocal()
    try:
        hashed = _pwd.hash(DEMO_PIN)
        for u in DEMO_USERS:
            if db.query(User).filter(User.id == u["id"]).first():
                continue
            db.add(User(
                id=u["id"],
                name=u["name"],
                role=u["role"],
                clearance=u["clearance"],
                hashed_pin=hashed,
                is_active=True,
            ))
        db.commit()
    finally:
        db.close()
