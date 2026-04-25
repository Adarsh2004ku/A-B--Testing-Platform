import numpy as np
from scipy import stats
from src.utils.logger import get_logger

logger = get_logger(__name__)


def z_test_proportions(
    control_conversions: int,
    control_total: int,
    treatment_conversions: int,
    treatment_total: int
) -> dict:
    """
    Z-test for difference in proportions.
    Answers: is the conversion rate difference real or random chance?

    Example:
        Control:   50/500  = 10% conversion
        Treatment: 75/500  = 15% conversion
        Is that 5% lift statistically significant?
    """
    if control_total == 0 or treatment_total == 0:
        return {"error": "empty group"}

    p_control   = control_conversions / control_total
    p_treatment = treatment_conversions / treatment_total
    p_pooled    = (control_conversions + treatment_conversions) / (control_total + treatment_total)

    # Standard error of the difference
    se = np.sqrt(p_pooled * (1 - p_pooled) * (1/control_total + 1/treatment_total))

    if se == 0:
        return {"error": "zero standard error"}

    z_score = (p_treatment - p_control) / se
    p_value = 2 * (1 - stats.norm.cdf(abs(z_score)))  # two-tailed

    # 95% confidence interval for the difference
    margin = 1.96 * se
    ci_lower = (p_treatment - p_control) - margin
    ci_upper = (p_treatment - p_control) + margin

    result = {
        "control_rate":        round(p_control, 4),
        "treatment_rate":      round(p_treatment, 4),
        "relative_lift":       round((p_treatment - p_control) / p_control * 100, 2) if p_control > 0 else 0,
        "absolute_lift":       round(p_treatment - p_control, 4),
        "z_score":             round(z_score, 4),
        "p_value":             round(p_value, 4),
        "ci_lower":            round(ci_lower, 4),
        "ci_upper":            round(ci_upper, 4),
        "is_significant":      p_value < 0.05,
        "confidence_level":    "95%"
    }

    logger.info("Z-test completed", extra={
        "p_value": result["p_value"],
        "is_significant": result["is_significant"]
    })

    return result


def srm_check(
    expected_weights: list[float],
    observed_counts: list[int]
) -> dict:
    """
    Sample Ratio Mismatch (SRM) Check.

    Detects if users were assigned in the expected ratio.
    If not — the experiment is broken and results are invalid.

    Example:
        Expected: 50% control, 50% treatment
        Observed: 600 control, 400 treatment (out of 1000)
        → SRM detected! Assignment engine has a bug.

    Uses chi-square goodness of fit test.
    """
    total = sum(observed_counts)
    expected_counts = [w * total for w in expected_weights]

    chi2, p_value = stats.chisquare(
        f_obs=observed_counts,
        f_exp=expected_counts
    )

    has_srm = p_value < 0.01  # stricter threshold for SRM

    result = {
        "expected_counts":  [round(e) for e in expected_counts],
        "observed_counts":  observed_counts,
        "chi2_statistic":   round(chi2, 4),
        "p_value":          round(p_value, 4),
        "has_srm":          has_srm,
        "verdict":          " SRM DETECTED - results invalid" if has_srm else " No SRM - assignment looks healthy"
    }

    if has_srm:
        logger.warning("SRM detected", extra={"chi2": chi2, "p_value": p_value})
    else:
        logger.info("SRM check passed", extra={"p_value": p_value})

    return result


def power_analysis(
    baseline_rate: float,
    minimum_detectable_effect: float,
    alpha: float = 0.05,
    power: float = 0.80
) -> dict:
    """
    Calculate required sample size BEFORE running an experiment.

    Answers: how many users do I need to detect a real effect?

    Example:
        Baseline conversion: 10%
        Want to detect: 2% improvement (to 12%)
        Need: ~3,500 users per variant
    """
    p1 = baseline_rate
    p2 = baseline_rate + minimum_detectable_effect
    p_avg = (p1 + p2) / 2

    z_alpha = stats.norm.ppf(1 - alpha / 2)  # 1.96 for 95% confidence
    z_beta  = stats.norm.ppf(power)           # 0.84 for 80% power

    n = (
        (z_alpha * np.sqrt(2 * p_avg * (1 - p_avg)) +
         z_beta  * np.sqrt(p1 * (1 - p1) + p2 * (1 - p2))) ** 2
    ) / (p2 - p1) ** 2

    return {
        "baseline_rate":              round(p1, 4),
        "target_rate":                round(p2, 4),
        "minimum_detectable_effect":  round(minimum_detectable_effect, 4),
        "required_sample_per_variant": int(np.ceil(n)),
        "total_sample_required":      int(np.ceil(n)) * 2,
        "alpha":                      alpha,
        "power":                      power
    }


def bonferroni_correction(p_values: list[float]) -> dict:
    """
    Multiple testing correction — Bonferroni method.

    When testing multiple variants, running each at p<0.05
    inflates false positive rate. Bonferroni corrects for this.

    Example:
        3 variants, alpha=0.05
        Corrected threshold = 0.05/3 = 0.0167
        Only variants with p < 0.0167 are truly significant
    """
    n = len(p_values)
    corrected_alpha = 0.05 / n
    results = []
    for i, p in enumerate(p_values):
        results.append({
            "variant_index":   i,
            "p_value":         round(p, 4),
            "corrected_alpha": round(corrected_alpha, 4),
            "is_significant":  p < corrected_alpha
        })
    return {
        "original_alpha":  0.05,
        "corrected_alpha": round(corrected_alpha, 4),
        "n_comparisons":   n,
        "results":         results
    }
