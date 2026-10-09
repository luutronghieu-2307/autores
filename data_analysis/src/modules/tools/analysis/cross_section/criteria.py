from typing import Any, Optional

DIAGNOSTIC_CRITERIA = {
    "cronbach_alpha": {
        "metric": "alpha",
        "criteria": [
            {"range": {"max": 0.6}, "status": "Unreliable (remove scale)", "warning": "Remove scale: Alpha < 0.6"},
            {"range": {"min": 0.6, "max": 0.7}, "status": "Acceptable"},
            {"range": {"min": 0.7, "max": 0.8}, "status": "Good (recommended)"},
            {"range": {"min": 0.8, "max": 0.9}, "status": "Very good"},
            {"range": {"min": 0.9}, "status": "Too high (possible variable redundancy)", "warning": "Check for variable redundancy: Alpha > 0.9"}
        ],
        "optimal_range": "0.7–0.8",
        "notes": "≥ 0.7 preferred (per 3.2.8)",
        "additional_checks": {
            "item_total_corr": {
                "threshold": 0.3,
                "warning": "Consider removing items with low correlation (< 0.3): {items}"
            }
        }
    },
    "kmo_test": {
        "metric": "kmo_total",
        "criteria": [
            {"range": {"max": 0.5}, "status": "Unsuitable (remove EFA)", "warning": "Remove EFA: KMO < 0.5"},
            {"range": {"min": 0.5, "max": 0.6}, "status": "Acceptable"},
            {"range": {"min": 0.6, "max": 0.7}, "status": "Fairly good"},
            {"range": {"min": 0.7, "max": 0.8}, "status": "Good"},
            {"range": {"min": 0.8, "max": 0.9}, "status": "Very good"},
            {"range": {"min": 0.9}, "status": "Excellent"}
        ],
        "optimal_range": "0.7–0.9",
        "notes": "Higher KMO indicates better suitability for EFA."
    },
    "bartlett_sphericity": {
        "metric": "p_value",
        "criteria": [
            {"range": {"min": 0.05}, "status": "Fail to reject H0 (variables uncorrelated)", "suitability": "Unsuitable for EFA", "warning": "Remove EFA: p-value > 0.05"},
            {"range": {"max": 0.05}, "status": "Reject H0 (variables are correlated)", "suitability": "Suitable for EFA"}
        ],
        "optimal_range": "p < 0.05 (p ≤ 0.01 is better)",
        "notes": "Significant p-value indicates EFA is appropriate."
    },
    "eigenvalue_analysis": {
        "metric": "eigenvalue",
        "criteria": [
            {"range": {"min": 1}, "status": "Keep Factor: Eigenvalue > 1"},
            {"range": {"max": 1}, "status": "Remove Factor: Eigenvalue <= 1", "warning": "Exclude factor: Eigenvalue < 1"}
        ],
        "optimal_range": "≥ 1",
        "notes": "Factors with eigenvalues > 1 are retained (Kaiser criterion)."
    },
    "factor_loading": {
        "metric": "loading",
        "criteria": [
            {"range": {"max": 0.3}, "status": "Remove variable", "warning": "Remove variable: Loading < 0.3"},
            {"range": {"min": 0.3, "max": 0.5}, "status": "Acceptable"},
            {"range": {"min": 0.5, "max": 0.7}, "status": "Good"},
            {"range": {"min": 0.7}, "status": "Very good"}
        ],
        "optimal_range": "> 0.5 (acceptable), > 0.7 (best)",
        "notes": "Loadings evaluated as absolute values."
    },
    "communality_analysis": {
        "metric": "communality",
        "criteria": [
            {"range": {"max": 0.3}, "status": "Remove variable", "warning": "Remove variable: Communality < 0.3"},
            {"range": {"min": 0.3, "max": 0.5}, "status": "Acceptable but review"},
            {"range": {"min": 0.5}, "status": "Good"}
        ],
        "optimal_range": "> 0.5",
        "notes": "Higher communalities indicate better variable contribution."
    },
    "number_of_factors": {
        "metric": "total_variance",
        "criteria": [
            {"range": {"max": 0.5}, "status": "Insufficient", "warning": "Remove EFA: Total variance < 50%"},
            {"range": {"min": 0.5, "max": 0.6}, "status": "Acceptable"},
            {"range": {"min": 0.6, "max": 0.7}, "status": "Good"},
            {"range": {"min": 0.7}, "status": "Very good"}
        ],
        "optimal_range": "≥ 50% (minimum), ≥ 60% (best)",
        "notes": "Also considers Kaiser criterion (eigenvalues > 1)."
    },
    "regression_r_squared": {
        "metric": "R_squared",
        "criteria": [
            {"range": {"max": 0.3}, "status": "Insufficient", "warning": "Poor model fit: R² < 0.3"},
            {"range": {"min": 0.3, "max": 0.5}, "status": "Acceptable (weak model)"},
            {"range": {"min": 0.5, "max": 0.7}, "status": "Fairly good"},
            {"range": {"min": 0.7, "max": 0.9}, "status": "Good"},
            {"range": {"min": 0.9}, "status": "Possible overfitting", "warning": "Possible overfitting: R² > 0.9"}
        ],
        "optimal_range": "0.5–0.7 (avoids overfitting)",
        "notes": "Adjusted R² ≥ 0.5 preferred (Section 3.2.8)."
    },
    "student_t_test": {
        "metric": "p_value",
        "criteria": [
            {"range": {"max": 0.05}, "status": "Significant"},
            {"range": {"min": 0.05}, "status": "Not Significant", "warning": "Consider removing variables with p > 0.05: {variables}"}
        ],
        "optimal_range": "p < 0.05",
        "notes": "p ≤ 0.01 indicates stronger significance."
    },
    "fisher_f_test": {
        "metric": "p_value",
        "criteria": [
            {"range": {"max": 0.05}, "status": "Model suitable"},
            {"range": {"min": 0.05}, "status": "Model unsuitable", "warning": "Adjust model: p > 0.05 indicates model is not suitable"}
        ],
        "optimal_range": "p < 0.05",
        "notes": "p ≤ 0.01 indicates stronger model significance."
    },
    "durbin_watson": {
        "metric": "DW_statistic",
        "criteria": [
            {"range": {"min": 1.5, "max": 2.5}, "status": "No autocorrelation"},
            {"range": {"max": 1.5}, "status": "Autocorrelation detected", "warning": "Review model: Autocorrelation detected"},
            {"range": {"min": 2.5}, "status": "Autocorrelation detected", "warning": "Review model: Autocorrelation detected"}
        ],
        "optimal_range": "1.5–2.5",
        "notes": "Ideal value ~2 (no autocorrelation)."
    },
    "vif_test": {
        "metric": "VIF",
        "criteria": [
            {"range": {"max": 2}, "status": "No multicollinearity"},
            {"range": {"min": 2, "max": 5}, "status": "Acceptable but review"},
            {"range": {"min": 5}, "status": "Severe multicollinearity (remove variable)", "warning": "Remove variables with VIF > 5: {variables}"}
        ],
        "optimal_range": "< 2",
        "notes": "VIF < 2 indicates no multicollinearity."
    },
    "item_total_correlation": {
        "metric": "correlation",
        "criteria": [
            {"range": {"max": 0.3}, "status": "Low (consider removal)", "warning": "Item-total correlation < 0.3: Consider removing item"},
            {"range": {"min": 0.3, "max": 0.5}, "status": "Acceptable"},
            {"range": {"min": 0.5}, "status": "Good"}
        ],
        "optimal_range": "≥ 0.3 (acceptable), ≥ 0.5 (preferred)",
        "notes": "Correlation ≥ 0.3 indicates item contributes to scale reliability."
    }
}

def get_diagnostic_criteria(analysis_type: str, metric_value: Optional[float] = None, 
                           additional_data: dict[str, Any] = None) -> dict[str, Any]:
    """
    Retrieve diagnostic criteria for a given analysis type and optionally evaluate a metric value.
    
    Parameters:
    - analysis_type: str, name of the analysis (e.g., 'cronbach_alpha', 'kmo_test').
    - metric_value: float, optional value of the metric to evaluate (e.g., alpha score).
    - additional_data: dict, optional data for dynamic warnings (e.g., low_corr_items).
    
    Returns:
    - dict, containing criteria, optimal range, notes, status, and warnings.
    """
    if analysis_type not in DIAGNOSTIC_CRITERIA:
        raise ValueError(f"Analysis type '{analysis_type}' not found in diagnostic criteria.")
    
    criteria = DIAGNOSTIC_CRITERIA[analysis_type]
    result = {
        "analysis_type": analysis_type,
        "metric": criteria["metric"],
        "criteria": criteria["criteria"],
        "optimal_range": criteria["optimal_range"],
        "notes": criteria.get("notes", ""),
        "status": None,
        "warnings": []
    }
    
    # Evaluate metric value if provided
    if metric_value is not None:
        for criterion in criteria["criteria"]:
            range_dict = criterion.get("range", {})
            min_val = range_dict.get("min", float("-inf"))
            max_val = range_dict.get("max", float("inf"))
            if min_val <= metric_value < max_val:
                result["status"] = criterion["status"]
                if "warning" in criterion:
                    result["warnings"].append(criterion["warning"])
                break
    
    # Handle additional checks (e.g., item-total correlations)
    if additional_data and "additional_checks" in criteria:
        for check_name, check_info in criteria["additional_checks"].items():
            if check_name in additional_data:
                items = additional_data[check_name]
                if items:  # Assuming items is a list of problematic items
                    warning = check_info["warning"].format(items=", ".join(items))
                    result["warnings"].append(warning)
    
    return result

# Example usage
if __name__ == "__main__":
    # Get criteria for Cronbach’s Alpha with a specific alpha value
    result = get_diagnostic_criteria(
        analysis_type="cronbach_alpha",
        metric_value=0.65,
        additional_data={"item_total_corr": ["item1", "item2"]}
    )
    print(result)