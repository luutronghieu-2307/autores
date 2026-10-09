import pandas as pd
import logging
from typing import List, Dict, Any

from data_analysis.src.schemas.analyzer_states import (
    State,
    Variable,
    VariableType,
    ScaleType,
    VariableRole
)
from data_analysis.src.modules.utils import get_current_dataframe

logger = logging.getLogger(__name__)

def is_binary_data(series: pd.Series) -> bool:
    """Check if a series contains binary data (0/1 or similar two unique values)."""
    try:
        unique_values = series.dropna().unique()
        if len(unique_values) == 2:
            # Check if values are 0 and 1 (or similar representations if needed, but strict 0/1 for now based on prompt)
            # The prompt says "dependent variable data is binary (0/1)"
            # Let's be slightly flexible but safe: check if set is {0, 1}
            return set(unique_values).issubset({0, 1, 0.0, 1.0})
        return False
    except Exception:
        return False

def get_tool_availability(state: State) -> List[Dict[str, Any]]:
    """
    Returns a list of available tools with their status and comments based on the current state.
    
    Args:
        state: The current analysis state containing variables and data.
        
    Returns:
        List of dicts: [{tool_name: str, status: bool, comment: str}, ...]
    """
    variables = state.get("current_variables", [])
    
    # Helper conditions
    has_time_index = any(var.variable_type == VariableType.TIME_INDEX for var in variables)
    has_entity_index = any(var.variable_type == VariableType.ENTITY_INDEX for var in variables)
    
    # Check for latent variables (Variables that are parents) or Observed variables that HAVE parents?
    # "Insufficient number of parent variables" -> Likely refers to the number of constructs defined.
    # We can count unique parent_codes that are not None.
    parent_codes = {var.parent_code for var in variables if var.parent_code}
    num_parent_variables = len(parent_codes)
    has_parent_variables = num_parent_variables > 0
    insufficient_parent_variables = num_parent_variables < 2 # Assuming SEM needs at least 2 constructs
    
    has_nominal = any(var.scale == ScaleType.NOMINAL for var in variables)
    
    dependent_vars = [var for var in variables if var.role == VariableRole.DEPENDENT]
    has_dependent = len(dependent_vars) > 0
    
    # Check for binary dependent variable
    # We need the dataframe for this
    current_data = get_current_dataframe(state)
    has_binary_dependent = False
    if has_dependent:
        for var in dependent_vars:
            if var.code in current_data.columns:
                if is_binary_data(current_data[var.code]):
                    has_binary_dependent = True
                    break
    
    available_tools = []
    
    # 1. Time Series
    time_series_tools = [
        "run_stationarity_assessment",
        "run_model_structure_identification",
        "run_model_estimation_and_diagnostics"
    ]
    for tool in time_series_tools:
        if not has_time_index:
            available_tools.append({
                "tool_name": tool,
                "status": False,
                "comment": "No time column (VariableType.TIME_INDEX) found."
            })
        else:
            available_tools.append({
                "tool_name": tool,
                "status": True,
                "comment": "Time column available."
            })

    # 2. Panel Data
    panel_tools = [
        "run_panel_model_selection",
        "run_advanced_panel_analysis"
    ]
    for tool in panel_tools:
        if not has_entity_index:
             available_tools.append({
                "tool_name": tool,
                "status": False,
                "comment": "No ID column (VariableType.ENTITY_INDEX) found."
            })
        else:
            available_tools.append({
                "tool_name": tool,
                "status": True,
                "comment": "ID column available."
            })

    # 3. Structural Equation Modeling (SEM)
    sem_tools = [
        "run_cfa_analysis",
        "run_cb_sem_analysis",
        "run_pls_sem_analysis",
        "run_gsca_analysis"
    ]
    for tool in sem_tools:
        if insufficient_parent_variables:
             available_tools.append({
                "tool_name": tool,
                "status": False,
                "comment": f"Insufficient number of parent variables (found {num_parent_variables}, need at least 2)."
            })
        else:
            available_tools.append({
                "tool_name": tool,
                "status": True,
                "comment": "Sufficient parent variables."
            })

    # 4. Factor Analysis & Scale Reliability
    factor_tools = [
        "run_reliability_analysis",
        "single_factor_scale_reliability_testing",
        "run_efa_analysis"
    ]
    for tool in factor_tools:
        if not has_parent_variables:
             available_tools.append({
                "tool_name": tool,
                "status": False,
                "comment": "No parent variables found."
            })
        else:
            available_tools.append({
                "tool_name": tool,
                "status": True,
                "comment": "Parent variables available."
            })

    # 5. Inferential Statistics & Regression
    # ANOVA & T-Tests
    if not has_nominal:
        available_tools.append({
            "tool_name": "run_anova_ttest_analysis",
            "status": False,
            "comment": "No nominal variables found."
        })
    else:
         available_tools.append({
            "tool_name": "run_anova_ttest_analysis",
            "status": True,
            "comment": "Nominal variables available."
        })

    # Multiple Linear Regression
    if not has_dependent:
        available_tools.append({
            "tool_name": "run_regression_analysis",
            "status": False,
            "comment": "No dependent variable found."
        })
    else:
        available_tools.append({
            "tool_name": "run_regression_analysis",
            "status": True,
            "comment": "Dependent variable available."
        })

    # Logistic Regression
    if not has_binary_dependent:
         available_tools.append({
            "tool_name": "run_logistic_regression_analysis",
            "status": False,
            "comment": "No binary dependent variable (0/1) found."
        })
    else:
        available_tools.append({
            "tool_name": "run_logistic_regression_analysis",
            "status": True,
            "comment": "Binary dependent variable available."
        })
    
    # Other tools (Overview, Cluster) - Assume enabled unless specified otherwise
    other_tools = [
        "run_overview_charts_analysis",
        "run_clustering_analysis"
    ]
    for tool in other_tools:
        available_tools.append({
            "tool_name": tool,
            "status": True,
            "comment": "Always available."
        })
        
    return available_tools
