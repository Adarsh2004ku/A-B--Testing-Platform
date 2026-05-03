import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from src.utils.database import SessionLocal
from src.models.user import User
from src.models.experiment import Experiment
from src.models.variant import Variant
from src.utils.logger import get_logger

logger = get_logger(__name__)

def seed():
    db = SessionLocal()
    try:
        # Check if already seeded
        existing_experiment = db.query(Experiment).filter_by(name="checkout_button_color").first()
        if existing_experiment:
            logger.info("Data already seeded, skipping")
            print("✅ Data already seeded")
            return

        # Create users
        users = [
            User(external_id="user_001", country="US", device_type="mobile", user_type="free"),
            User(external_id="user_002", country="US", device_type="desktop", user_type="premium"),
            User(external_id="user_003", country="UK", device_type="mobile", user_type="free"),
        ]
        db.add_all(users)
        db.commit()
        print(f"✅ Created {len(users)} users")

        # Create experiment
        experiment = Experiment(
            name="checkout_button_color",
            description="Test button colors",
            status="running",
            layer="checkout"
        )
        db.add(experiment)
        db.commit()

        # Create variants
        control = Variant(
            experiment_id=experiment.id,
            name="control",
            is_control=True,
            traffic_weight=50.0
        )
        treatment = Variant(
            experiment_id=experiment.id,
            name="treatment",
            is_control=False,
            traffic_weight=50.0
        )
        db.add(control)
        db.add(treatment)
        db.commit()
        
        print("✅ Created experiment and variants")

    except Exception as e:
        db.rollback()
        print(f"❌ Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    seed()
