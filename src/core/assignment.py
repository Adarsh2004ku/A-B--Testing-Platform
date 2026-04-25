import hashlib
from sqlalchemy.orm import Session
from src.models.experiment import Experiment
from src.models.variant import Variant
from src.models.assignment import Assignment
from src.models.user import User
from src.utils.logger import get_logger

logger = get_logger(__name__)


def get_bucket(user_id: str, experiment_id: str) -> int:
    """
    Deterministic bucket assignment using MD5 hash.
    Same user_id + experiment_id always returns same bucket (0-99).
    This is consistent hashing — the core of fair user assignment.
    """
    key = f"{user_id}:{experiment_id}"
    hash_hex = hashlib.md5(key.encode()).hexdigest()
    bucket = int(hash_hex[:8], 16) % 100
    return bucket


def select_variant(bucket: int, variants: list[Variant]) -> Variant | None:
    """
    Given a bucket (0-99), find which variant owns it
    based on traffic weights.

    Example: control=0.5, treatment=0.5
    Buckets 0-49  → control
    Buckets 50-99 → treatment
    """
    cumulative = 0.0
    for variant in variants:
        cumulative += variant.traffic_weight * 100
        if bucket < cumulative:
            return variant
    return None


def check_segment(user: User, target_segments: dict) -> bool:
    """
    Check if user matches experiment targeting rules.
    If no segments defined, everyone qualifies.

    Example target_segments:
        {"country": ["IN", "US"], "user_type": ["free"]}
    """
    if not target_segments:
        return True

    if "country" in target_segments:
        if user.country not in target_segments["country"]:
            logger.info("User excluded by country segment", extra={
                "user_id": str(user.id),
                "user_country": user.country
            })
            return False

    if "device_type" in target_segments:
        if user.device_type not in target_segments["device_type"]:
            logger.info("User excluded by device_type segment", extra={
                "user_id": str(user.id),
                "user_device": user.device_type
            })
            return False

    if "user_type" in target_segments:
        if user.user_type not in target_segments["user_type"]:
            logger.info("User excluded by user_type segment", extra={
                "user_id": str(user.id),
                "user_type": user.user_type
            })
            return False

    return True


def assign_user(user_external_id: str, experiment_name: str, db: Session) -> dict:
    """
    Main assignment function.
    1. Load user and experiment from DB
    2. Check segmentation
    3. Compute bucket via consistent hash
    4. Select variant
    5. Save assignment (or return existing one)
    """

    # Load user
    user = db.query(User).filter(User.external_id == user_external_id).first()
    if not user:
        logger.warning("User not found", extra={"user_id": user_external_id})
        return {"assigned": False, "reason": "user_not_found"}

    # Load experiment
    experiment = db.query(Experiment).filter(
        Experiment.name == experiment_name,
        Experiment.status == "running"
    ).first()
    if not experiment:
        logger.warning("Experiment not found or not running", extra={"experiment": experiment_name})
        return {"assigned": False, "reason": "experiment_not_found"}

    # Check if already assigned — return existing assignment
    existing = db.query(Assignment).filter(
        Assignment.user_id == user.id,
        Assignment.experiment_id == experiment.id
    ).first()
    if existing:
        variant = db.query(Variant).filter(Variant.id == existing.variant_id).first()
        logger.info("Returning existing assignment", extra={
            "user_id": user_external_id,
            "experiment_id": str(experiment.id),
            "variant": variant.name
        })
        return {
            "assigned": True,
            "user_id": user_external_id,
            "experiment": experiment_name,
            "variant": variant.name,
            "config": variant.config,
            "from_cache": False
        }

    # Check segmentation
    if not check_segment(user, experiment.target_segments):
        return {"assigned": False, "reason": "segment_mismatch"}

    # Compute bucket
    bucket = get_bucket(user_external_id, str(experiment.id))

    # Load variants and select
    variants = db.query(Variant).filter(
        Variant.experiment_id == experiment.id
    ).order_by(Variant.name).all()

    variant = select_variant(bucket, variants)
    if not variant:
        logger.error("No variant selected", extra={"bucket": bucket})
        return {"assigned": False, "reason": "no_variant"}

    # Save assignment to DB
    assignment = Assignment(
        user_id=user.id,
        experiment_id=experiment.id,
        variant_id=variant.id
    )
    db.add(assignment)
    db.commit()

    logger.info("User assigned", extra={
        "user_id": user_external_id,
        "experiment_id": str(experiment.id),
        "variant": variant.name,
        "bucket": bucket
    })

    return {
        "assigned": True,
        "user_id": user_external_id,
        "experiment": experiment_name,
        "variant": variant.name,
        "config": variant.config,
        "bucket": bucket
    }
