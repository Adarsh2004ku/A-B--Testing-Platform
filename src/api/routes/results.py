from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from src.utils.database import get_db
from src.models.experiment import Experiment
from src.models.variant import Variant
from src.models.assignment import Assignment
from src.models.event import Event
from src.core.stats.engine import z_test_proportions, srm_check
from src.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter()


@router.get("/results/{experiment_name}")
def get_results(
    experiment_name: str,
    db: Session = Depends(get_db)
):
    experiment = db.query(Experiment).filter(
        Experiment.name == experiment_name
    ).first()
    if not experiment:
        raise HTTPException(status_code=404, detail="experiment_not_found")

    variants = db.query(Variant).filter(
        Variant.experiment_id == experiment.id
    ).all()

    variant_stats = []
    observed_counts = []
    expected_weights = []
    control_data = None

    for variant in variants:
        assignments = db.query(Assignment).filter(
            Assignment.experiment_id == experiment.id,
            Assignment.variant_id == variant.id
        ).count()

        conversions = db.query(Event).join(
            Assignment,
            (Assignment.user_id == Event.user_id) &
            (Assignment.experiment_id == Event.experiment_id)
        ).filter(
            Assignment.variant_id == variant.id,
            Event.experiment_id == experiment.id,
            Event.event_type == "conversion"
        ).count()

        observed_counts.append(assignments)
        expected_weights.append(variant.traffic_weight)

        stat = {
            "variant": variant.name,
            "is_control": variant.is_control,
            "assignments": assignments,
            "conversions": conversions,
            "conversion_rate": round(conversions / assignments, 4) if assignments > 0 else 0
        }
        variant_stats.append(stat)

        if variant.is_control:
            control_data = stat

    # SRM check
    srm = srm_check(expected_weights, observed_counts)

    # Z-test vs control
    if control_data:
        for stat in variant_stats:
            if not stat["is_control"]:
                stat["significance"] = z_test_proportions(
                    control_data["conversions"],
                    control_data["assignments"],
                    stat["conversions"],
                    stat["assignments"]
                )

    return {
        "experiment": experiment_name,
        "status": experiment.status,
        "srm_check": srm,
        "variants": variant_stats
    }
