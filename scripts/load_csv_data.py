import sys
import os
import pandas as pd
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from src.utils.database import SessionLocal
from src.models.user import User
from src.models.experiment import Experiment
from src.models.variant import Variant
from src.models.assignment import Assignment
from src.models.event import Event
from src.utils.logger import get_logger

logger = get_logger(__name__)

def load_csv(filepath: str):
    db = SessionLocal()
    try:
        df = pd.read_csv(filepath)
        print(f"✅ Loaded {len(df)} rows from CSV")

        # Get experiment
        experiment = db.query(Experiment).filter(
            Experiment.name == "checkout_button_color"
        ).first()
        if not experiment:
            print("❌ Experiment not found. Run seed first.")
            return

        # Get variants
        control_variant = db.query(Variant).filter(
            Variant.experiment_id == experiment.id,
            Variant.name == "control"
        ).first()
        treatment_variant = db.query(Variant).filter(
            Variant.experiment_id == experiment.id,
            Variant.name == "treatment"
        ).first()

        assigned = 0
        conversions = 0
        skipped = 0

        for _, row in df.iterrows():
            user_id = f"csv_user_{row['USER_ID']}"
            variant_name = "control" if row["VARIANT_NAME"] == "control" else "treatment"
            revenue = row["REVENUE"]

            # Create user if not exists
            user = db.query(User).filter(User.external_id == user_id).first()
            if not user:
                user = User(
                    external_id=user_id,
                    country="US",
                    device_type="mobile",
                    user_type="free"
                )
                db.add(user)
                db.flush()

            # Check if already assigned
            existing = db.query(Assignment).filter(
                Assignment.user_id == user.id,
                Assignment.experiment_id == experiment.id
            ).first()

            if existing:
                skipped += 1
                continue

            # Assign to correct variant from CSV
            variant = control_variant if variant_name == "control" else treatment_variant
            assignment = Assignment(
                user_id=user.id,
                experiment_id=experiment.id,
                variant_id=variant.id
            )
            db.add(assignment)
            db.flush()
            assigned += 1

            # Log conversion event if revenue > 0
            if revenue > 0:
                event = Event(
                    user_id=user.id,
                    experiment_id=experiment.id,
                    event_type="conversion",
                    metadata={"revenue": float(revenue), "source": "csv_import"}
                )
                db.add(event)
                conversions += 1

        db.commit()
        print(f"✅ Users assigned: {assigned}")
        print(f"✅ Conversions logged: {conversions}")
        print(f"⏭️  Skipped (already exists): {skipped}")
        print()
        print("Now call: GET /api/v1/results/checkout_button_color")

    except Exception as e:
        db.rollback()
        print(f"❌ Error: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    filepath = sys.argv[1] if len(sys.argv) > 1 else "data/AB_Test_Results.csv"
    load_csv(filepath)
