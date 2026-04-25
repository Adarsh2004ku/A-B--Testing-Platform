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
            User(external_id="user_001", country="IN", device_type="mobile", user_type="free"),
            User(external_id="user_002", country="US", device_type="desktop", user_type="premium"),
            User(external_id="user_003", country="IN", device_type="desktop", user_type="free"),
            User(external_id="user_004", country="UK", device_type="mobile", user_type="enterprise"),
            User(external_id="user_005", country="US", device_type="mobile", user_type="free"),
        ]
        db.add_all(users)
        db.flush()
        logger.info("Users seeded", extra={"count": len(users)})

        # Create experiment
        experiment = Experiment(
            name="checkout_button_color",
            description="Test green vs red checkout button",
            status="running",
            layer="ui",
            target_segments={"country": ["IN", "US"]}
        )
        db.add(experiment)
        db.flush()
        logger.info("Experiment seeded", extra={"experiment_id": str(experiment.id)})

        # Create variants
        variants = [
            Variant(experiment_id=experiment.id, name="control", is_control=True, traffic_weight=0.5, config={"button_color": "red"}),
            Variant(experiment_id=experiment.id, name="treatment", is_control=False, traffic_weight=0.5, config={"button_color": "green"}),
        ]
        db.add_all(variants)
        db.commit()
        logger.info("Variants seeded")
        print("✅ Seed complete")

    except Exception as e:
        db.rollback()
        logger.error(f"Seed failed: {e}")
        print(f"❌ Seed failed: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    seed()
