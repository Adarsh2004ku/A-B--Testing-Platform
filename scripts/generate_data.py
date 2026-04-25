import sys
import os
import random
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from src.utils.database import SessionLocal
from src.models.user import User
from src.models.experiment import Experiment
from src.models.variant import Variant
from src.models.assignment import Assignment
from src.models.event import Event
from src.core.assignment import assign_user
from src.utils.logger import get_logger

logger = get_logger(__name__)

random.seed(42)

COUNTRIES   = ["IN", "US", "UK", "SG", "AU"]
DEVICES     = ["mobile", "desktop", "tablet"]
USER_TYPES  = ["free", "premium", "enterprise"]

# Conversion rates per variant — treatment is genuinely better
CONVERSION_RATES = {
    "control":   0.10,  # 10% convert with red button
    "treatment": 0.15   # 15% convert with green button
}

def generate_users(db, n=1000):
    print(f"Creating {n} users...")
    users = []
    for i in range(1, n + 1):
        user = User(
            external_id=f"user_{i:04d}",
            country=random.choice(COUNTRIES),
            device_type=random.choice(DEVICES),
            user_type=random.choice(USER_TYPES)
        )
        users.append(user)

    # add in batches
    for i in range(0, len(users), 100):
        batch = users[i:i+100]
        for u in batch:
            existing = db.query(User).filter(User.external_id == u.external_id).first()
            if not existing:
                db.add(u)
        db.commit()
        print(f"  ✅ {min(i+100, n)} users created")

    return db.query(User).filter(
        User.external_id.like("user_%")
    ).all()

def assign_all_users(db, users, experiment_name):
    print(f"\nAssigning {len(users)} users to experiment...")
    assigned = 0
    skipped = 0
    for user in users:
        result = assign_user(user.external_id, experiment_name, db)
        if result.get("assigned"):
            assigned += 1
        else:
            skipped += 1
    print(f"  ✅ Assigned: {assigned} | Skipped (segment mismatch): {skipped}")

def simulate_conversions(db):
    print("\nSimulating conversion events...")

    experiment = db.query(Experiment).filter(
        Experiment.name == "checkout_button_color"
    ).first()

    assignments = db.query(Assignment).filter(
        Assignment.experiment_id == experiment.id
    ).all()

    conversions = 0
    for assignment in assignments:
        variant = db.query(Variant).filter(
            Variant.id == assignment.variant_id
        ).first()

        rate = CONVERSION_RATES.get(variant.name, 0.10)

        # Simulate whether this user converted
        if random.random() < rate:
            event = Event(
                user_id=assignment.user_id,
                experiment_id=experiment.id,
                event_type="conversion",
                metadata={"source": "checkout_page"}
            )
            db.add(event)
            conversions += 1

    db.commit()
    print(f"  ✅ {conversions} conversion events logged")

def print_summary(db):
    print("\n" + "="*50)
    print("📊 DATASET SUMMARY")
    print("="*50)

    experiment = db.query(Experiment).filter(
        Experiment.name == "checkout_button_color"
    ).first()

    variants = db.query(Variant).filter(
        Variant.experiment_id == experiment.id
    ).all()

    for variant in variants:
        assignments = db.query(Assignment).filter(
            Assignment.experiment_id == experiment.id,
            Assignment.variant_id == variant.id
        ).count()

        conversions = db.query(Event).filter(
            Event.experiment_id == experiment.id,
            Event.event_type == "conversion"
        ).join(
            Assignment,
            (Assignment.user_id == Event.user_id) &
            (Assignment.experiment_id == Event.experiment_id) &
            (Assignment.variant_id == variant.id)
        ).count()

        rate = conversions / assignments if assignments > 0 else 0
        print(f"\n  Variant: {variant.name.upper()}")
        print(f"  Users assigned:  {assignments}")
        print(f"  Conversions:     {conversions}")
        print(f"  Conversion rate: {rate:.1%}")

    print("\n" + "="*50)
    print("Now call: GET /api/v1/results/checkout_button_color")
    print("="*50)

if __name__ == "__main__":
    db = SessionLocal()
    try:
        users = generate_users(db, n=1000)
        assign_all_users(db, users, "checkout_button_color")
        simulate_conversions(db)
        print_summary(db)
    finally:
        db.close()
