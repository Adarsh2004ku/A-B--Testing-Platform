import sys
import os
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

def generate_sample_data():
    """Generate sample data for testing A/B testing functionality"""
    db = SessionLocal()
    try:
        # Create sample users
        users = [
            User(external_id="user_001", country="US", device_type="mobile", user_type="free"),
            User(external_id="user_002", country="US", device_type="desktop", user_type="premium"),
            User(external_id="user_003", country="UK", device_type="mobile", user_type="free"),
            User(external_id="user_004", country="UK", device_type="desktop", user_type="free"),
        ]

        for user in users:
            existing = db.query(User).filter(User.external_id == user.external_id).first()
            if not existing:
                db.add(user)

        db.commit()
        print(f"✅ Created {len(users)} sample users")

        # Create sample experiment
        experiment = db.query(Experiment).filter(Experiment.name == "button_test").first()
        if not experiment:
            experiment = Experiment(
                name="button_test",
                description="Testing button colors",
                status="running",
                layer="checkout"
            )
            db.add(experiment)
            db.commit()

            # Create variants
            control = Variant(
                experiment_id=experiment.id,
                name="blue_button",
                is_control=True,
                traffic_weight=50.0
            )
            treatment = Variant(
                experiment_id=experiment.id,
                name="green_button",
                is_control=False,
                traffic_weight=50.0
            )
            db.add(control)
            db.add(treatment)
            db.commit()
            print("✅ Created experiment with variants")

        # Assign users
        assigned_count = 0
        for user in users:
            result = assign_user(user.external_id, "button_test", db)
            if result.get("assigned"):
                assigned_count += 1

        print(f"✅ Assigned {assigned_count} users to experiment")

        # Add some conversion events
        assignments = db.query(Assignment).filter(Assignment.experiment_id == experiment.id).all()
        conversions = 0
        for i, assignment in enumerate(assignments):
            if i % 3 == 0:  # Every 3rd user converts
                event = Event(
                    user_id=assignment.user_id,
                    experiment_id=experiment.id,
                    event_type="conversion"
                )
                db.add(event)
                conversions += 1

        db.commit()
        print(f"✅ Added {conversions} conversion events")

    except Exception as e:
        db.rollback()
        print(f"❌ Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    generate_sample_data()
