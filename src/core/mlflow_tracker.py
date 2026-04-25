import mlflow
import mlflow.tracking
from src.utils.logger import get_logger

logger = get_logger(__name__)

MLFLOW_TRACKING_URI = "sqlite:///mlflow.db"
EXPERIMENT_NAME = "ab_testing_platform"

mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
mlflow.set_experiment(EXPERIMENT_NAME)


def log_experiment_results(
    experiment_name: str,
    variant_stats: list,
    srm_check: dict
):
    """
    Log A/B test results to MLflow.
    Each experiment = one MLflow run.
    """
    with mlflow.start_run(run_name=experiment_name):

        # Log SRM check
        mlflow.log_param("srm_has_mismatch", srm_check["has_srm"])
        mlflow.log_param("srm_p_value", srm_check["p_value"])

        # Log per-variant metrics
        for stat in variant_stats:
            variant = stat["variant"]
            mlflow.log_metric(f"{variant}_assignments", stat["assignments"])
            mlflow.log_metric(f"{variant}_conversions", stat["conversions"])
            mlflow.log_metric(f"{variant}_conversion_rate", stat["conversion_rate"])

            # Log significance for treatment variants
            if "significance" in stat:
                sig = stat["significance"]
                mlflow.log_metric(f"{variant}_p_value", sig["p_value"])
                mlflow.log_metric(f"{variant}_relative_lift", sig["relative_lift"])
                mlflow.log_metric(f"{variant}_z_score", sig["z_score"])
                mlflow.log_param(f"{variant}_is_significant", sig["is_significant"])

                # Log winner decision
                if sig["is_significant"] and sig["relative_lift"] > 0:
                    mlflow.set_tag("winner", variant)
                    mlflow.set_tag("decision", "ship_treatment")
                elif sig["is_significant"] and sig["relative_lift"] < 0:
                    mlflow.set_tag("winner", "control")
                    mlflow.set_tag("decision", "keep_control")
                else:
                    mlflow.set_tag("winner", "none")
                    mlflow.set_tag("decision", "keep_running")

        mlflow.set_tag("experiment_name", experiment_name)
        logger.info("MLflow run logged", extra={"experiment": experiment_name})

    return {"status": "logged", "experiment": experiment_name}
