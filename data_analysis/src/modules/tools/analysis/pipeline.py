import json
import traceback
import pandas as pd
from datetime import datetime
import math
from typing import Callable, Any
from scipy import stats
import numpy as np
from sklearn.impute import KNNImputer
from sklearn.preprocessing import StandardScaler, MinMaxScaler
from statsmodels.tsa.seasonal import seasonal_decompose

from data_analysis.src.schemas.analyzer_states import (
    Variable,
    Action,
    ToolOutput,
    ActionType,
    AnalyzeStep,
    ExecutionLog,
    State,
    AnalysisStepType,
    Plan,
    ExecutionMode,
    LogEntry,
    TransformationRecord,
    VariableType,
)

from data_analysis.src.modules.tools.analysis.chart.overview_chart import (
    run_overview_charts_analysis
)

from data_analysis.src.modules.tools.analysis.cross_section.efa import (
    run_reliability_analysis,
    run_anova_ttest_analysis,
    run_efa_analysis,
    single_factor_scale_reliability_testing,
    run_cfa_analysis,
    run_cb_sem_analysis,
    run_pls_sem_analysis,
    run_gsca_analysis
)

from data_analysis.src.modules.tools.analysis.cross_section.regression import (
    run_regression_analysis,
    run_logistic_regression_analysis
)

from data_analysis.src.modules.tools.analysis.cross_section.cluster import (
    run_clustering_analysis
)

### TIME SERIES
from data_analysis.src.modules.tools.analysis.time.stationarity_assessment import run_stationarity_assessment
from data_analysis.src.modules.tools.analysis.time.model_structure_identification import run_model_structure_identification
from data_analysis.src.modules.tools.analysis.time.model_estimation_and_diagnostics import run_model_estimation_and_diagnostics
# from deep_analysis.tools.analysis.time.tools.model_estimation import run_model_estimation
# from deep_analysis.tools.analysis.time.tools.model_diagnostics import run_model_diagnostics
# from deep_analysis.tools.analysis.time.tools.model_application import run_model_application

### PANEL DATA
from data_analysis.src.modules.tools.analysis.panel.panel_model_selection import run_panel_model_selection
from data_analysis.src.modules.tools.analysis.panel.advanced_panel_analysis import run_advanced_panel_analysis

from data_analysis.src.modules.utils import get_current_dataframe, set_current_data, get_file_description

TOOL_REGISTRY: dict[str, Callable[[pd.DataFrame, list[Variable], dict], ToolOutput]] = {
    ### OVERVIEW ###
    "run_overview_charts_analysis" : run_overview_charts_analysis,
    
    ### SEM (EFA) ###
    "single_factor_scale_reliability_testing" : single_factor_scale_reliability_testing,
    "run_reliability_analysis": run_reliability_analysis,
    "run_efa_analysis": run_efa_analysis,
    "run_anova_ttest_analysis": run_anova_ttest_analysis,

    ### SEM (CFA, CB-SEM, PLS-SEM, GSCA) ###
    "run_cfa_analysis": run_cfa_analysis,
    "run_cb_sem_analysis": run_cb_sem_analysis,
    "run_pls_sem_analysis": run_pls_sem_analysis,
    "run_gsca_analysis": run_gsca_analysis,

    ### REGRESSION ###
    "run_regression_analysis": run_regression_analysis,
    "run_logistic_regression_analysis": run_logistic_regression_analysis,
    
    ### CLUSTER ###
    "run_clustering_analysis": run_clustering_analysis,
    
    ### TIMES SERIES TOOLS ###
    "run_stationarity_assessment": run_stationarity_assessment,
    "run_model_structure_identification": run_model_structure_identification,
    "run_model_estimation_and_diagnostics": run_model_estimation_and_diagnostics,
    
    ### PANEL DATA ###
    "run_panel_model_selection": run_panel_model_selection,
    "run_advanced_panel_analysis": run_advanced_panel_analysis,

}
def serialize_state(state: Any) -> dict:
    """
    Create a JSON-serializable dictionary from a state object, handling any data type or field.
    
    Args:
        state: The state object to serialize.
    
    Returns:
        dict: A JSON-serializable dictionary representation of the state.
    """
    def serialize_value(obj: Any) -> Any:
        """Recursively serialize any value into a JSON-compatible format."""
        # Handle None
        if obj is None:
            return None
        # Handle basic JSON-serializable types
        try:
            json.dumps(obj)
            return obj
        except (TypeError, OverflowError):
            pass
        # Handle pandas DataFrame
        if isinstance(obj, pd.DataFrame):
            return {
                "_type": "DataFrame",
                "shape": obj.shape,
                "columns": obj.columns.tolist()
            }
        # Handle datetime
        if isinstance(obj, datetime):
            return obj.isoformat()
        # Handle objects with model_dump (e.g., Pydantic models)
        if hasattr(obj, "model_dump"):
            return serialize_value(obj.model_dump())
        # Handle lists and tuples
        if isinstance(obj, (list, tuple)):
            return [serialize_value(item) for item in obj]
        # Handle dictionaries
        if isinstance(obj, dict):
            return {str(k): serialize_value(v) for k, v in obj.items()}
        # Handle enums
        if hasattr(obj, "value"):
            return obj.value
        # Fallback: convert to string for non-serializable types
        return str(obj)

    # Convert state to dictionary if it has model_dump, else use vars()
    state_dict = state.model_dump() if hasattr(state, "model_dump") else vars(state)
    
    # Serialize all fields recursively
    return serialize_value(state_dict)

def serialize_dict(data: Any) -> Any:
    """
    Recursively serialize a dictionary or list, converting pandas DataFrames to CSV strings.
    
    Args:
        data: Input data (dict, list, or other type).
        
    Returns:
        Serialized data with DataFrames converted to CSV strings.
    """
    if isinstance(data, pd.DataFrame):
        return data.to_csv(index=False)
    elif isinstance(data, dict):
        return {key: serialize_dict(value) for key, value in data.items()}
    elif isinstance(data, list):
        return [serialize_dict(item) for item in data]
    elif isinstance(data, (str, int, float, bool, type(None))):
        return data
    else:
        # For other types, assume they're serializable or convert to string as fallback
        try:
            return data
        except:
            return str(data)
        
def _clean_list_for_json(data_list: list[Any]) -> list[Any]:
    """Replaces nan and inf with None in a list."""
    return [None if isinstance(x, float) and (math.isnan(x) or math.isinf(x)) else x for x in data_list]

def _apply_differencing_and_get_inversion_params(
    series: pd.Series, d: int = 0, D: int = 0, m: int = 0
) -> tuple[pd.Series, dict[str, Any]]:
    """
    Applies seasonal and regular differencing to a time series and collects
    head values needed for potential inverse transformation. The returned
    inversion parameters are JSON-compatible (NaN/inf are converted to None).
    """
    if not isinstance(series, pd.Series):
        raise TypeError("Input 'series' must be a pandas Series.")

    transformed_series = series.copy()
    if not pd.api.types.is_float_dtype(transformed_series):
        transformed_series = transformed_series.astype(float)

    seasonal_head_values_history = []
    regular_head_values_history = []

    # Apply seasonal differencing
    if D > 0:
        if m <= 0:
            raise ValueError("Seasonal period 'm' must be positive if D > 0.")
        for _ in range(D):
            if len(transformed_series) < m:
                current_head = transformed_series.iloc[:m].tolist()
                seasonal_head_values_history.append(_clean_list_for_json(current_head))
                transformed_series = pd.Series(index=transformed_series.index, dtype=float)
                break
            
            head_s = transformed_series.iloc[:m].tolist()
            seasonal_head_values_history.append(_clean_list_for_json(head_s))
            transformed_series = transformed_series.diff(periods=m)
            if transformed_series.isnull().all():
                 break

    # Apply regular differencing
    if d > 0 and not transformed_series.isnull().all():
        for _ in range(d):
            if len(transformed_series) < 1:
                current_head = transformed_series.iloc[:1].tolist()
                regular_head_values_history.append(_clean_list_for_json(current_head))
                transformed_series = pd.Series(index=transformed_series.index, dtype=float)
                break
            
            head_r = transformed_series.iloc[:1].tolist()
            regular_head_values_history.append(_clean_list_for_json(head_r))
            transformed_series = transformed_series.diff(periods=1)
            if transformed_series.isnull().all():
                break

    final_transformed_series = transformed_series.dropna()

    inversion_params = {
        "d": d,
        "D": D,
        "m": m,
        "seasonal_head_values": seasonal_head_values_history,
        "regular_head_values": regular_head_values_history
    }
    return final_transformed_series, inversion_params

def apply_action(action: Action, state: State) -> AnalyzeStep:
    """
    Apply an action to modify the state and queue reflection if specified.
    In auto mode, pending actions are automatically approved.
    Appends a LogEntry to state.logs.
    """
    plan_id = state["current_plan"].plan_id if "current_plan" in state else 1
    logs = []
    output = {"status": "executed", "changes": []}

    print(f"Applying action: {action.action_type} ({action.issue})")
    logs.append(f"Applying action: {action.action_type} ({action.issue})")
    logs.append(f"Comment: {action.comment}")

    if state["action_mode"] == ExecutionMode.AUTO and action.status == "pending":
        action.status = "approved"
        logs.append(f"**AUTO-APPROVED**: Action `{action.action_type}` in auto mode.")

    if action.status == "pending":
        logs.append(f"**PAUSED**: Action `{action.action_type}` is pending user approval.")
        output["status"] = "pending"
    elif action.status == "rejected":
        logs.append(f"**SKIPPED**: Action `{action.action_type}` was rejected.")
        output["status"] = "skipped"
    elif action.status in ("done", "skipped", "failed"):
        logs.append(f"**SKIPPED**: Action `{action.action_type}` already processed with status `{action.status}`.")
        output["status"] = action.status
    elif action.status == "approved":
        try:
            current_data_df = get_current_dataframe(state) # Get DataFrame

            if action.action_type == ActionType.REMOVE_VARIABLE:
                variable = action.action_params.get("variable")
                if variable and variable in current_data_df.columns:
                    current_data_df = current_data_df.drop(columns=[variable])
                    set_current_data(state, current_data_df)
                    output["changes"].append(f"Removed variable: {variable}")
                    logs.append(f"Removed variable `{variable}` from dataset.")
                    state["current_variables"] = [
                        var for var in state["current_variables"] if var.code != variable
                    ]
                    output["changes"].append(f"Updated variables list, removed: {variable}")
                else:
                    logs.append(f"**WARNING**: Variable `{variable}` not found in dataset.")
                    output["status"] = "skipped"
            
            elif action.action_type == ActionType.DISCARD_FACTOR:
                factor = action.action_params.get("factor")
                variables_to_remove = [
                    var.code for var in state["current_variables"] if var.parent_code == factor
                ]
                if variables_to_remove:
                    current_data_df = current_data_df.drop(columns=variables_to_remove, errors="ignore")
                    set_current_data(state, current_data_df)
                    state["current_variables"] = [
                        var for var in state["current_variables"] if var.parent_code != factor
                    ]
                    output["changes"].append(f"Removed variables for factor: {factor} ({variables_to_remove})")
                    logs.append(f"Removed factor `{factor}` and variables: {variables_to_remove}")
                else:
                    logs.append(f"**WARNING**: No variables found for factor `{factor}`.")
                    output["status"] = "skipped"

            elif action.action_type == ActionType.RECHECK_DATA:
                variables = action.action_params.get("variables", [])
                issue_type = action.action_params.get("issue_type", "general")
                logs.append(f"**ACTION**: Recheck data requested for variables {variables}, issue type: {issue_type}")
                logs.append(f"Comment: {action.comment}")
                output["changes"].append(f"Recheck data flagged for variables: {variables}")

            elif action.action_type == ActionType.SPLIT_VARIABLE:
                params = action.action_params
                var_to_split = params.get("variable_to_split")
                method = params.get("method")
                
                if not var_to_split or var_to_split not in current_data_df.columns:
                    logs.append(f"**WARNING**: Variable `{var_to_split}` not found for splitting.")
                    output["status"] = "skipped"
                elif method == "seasonal_decompose":
                    model_type = params.get("model_type", "additive")
                    period = params.get("period", 12)
                    output_names = params.get("output_component_names", {})

                    
                    series = current_data_df[var_to_split].dropna()
                    decomp = seasonal_decompose(series, model=model_type, period=period)

                    
                    # Add components as new variables
                    for comp_name, comp_series in [("trend", decomp.trend), ("seasonal", decomp.seasonal), ("resid", decomp.resid)]:
                        new_var_name = output_names.get(comp_name, f"{var_to_split}_{comp_name}")
                        current_data_df[new_var_name] = comp_series
                        
                        # Add to variable metadata
                        new_var = Variable(
                            name=f"{var_to_split} {comp_name.title()}",
                            code=new_var_name,
                            variable_type=VariableType.COMPONENT,
                            parent_code=var_to_split,
                            scale="interval",
                            collection_method="computed"
                        )
                        state["current_variables"].append(new_var)
                    
                    set_current_data(state, current_data_df)
                    output["changes"].append(f"Split variable {var_to_split} into components: {list(output_names.values())}")
                    logs.append(f"Applied seasonal decomposition to {var_to_split}")
                
                elif method == "dummify":
                    drop_first = params.get("drop_first", True)
                    prefix = params.get("prefix", var_to_split)
                    
                    dummies = pd.get_dummies(current_data_df[var_to_split], prefix=prefix, drop_first=drop_first)
                    current_data_df = pd.concat([current_data_df, dummies], axis=1)
                    
                    # Add dummy variables to metadata
                    for col in dummies.columns:
                        new_var = Variable(
                            name=f"{var_to_split} - {col}",
                            code=col,
                            variable_type=VariableType.OBSERVED,
                            parent_code=var_to_split,
                            scale="nominal",
                            collection_method="computed"
                        )
                        state["current_variables"].append(new_var)
                    
                    set_current_data(state, current_data_df)
                    output["changes"].append(f"Created dummy variables from {var_to_split}: {list(dummies.columns)}")
                    logs.append(f"Created dummy variables for {var_to_split}")
                
                else:
                    logs.append(f"**WARNING**: Unknown split method `{method}`. Action skipped.")
                    output["status"] = "skipped"

            elif action.action_type == ActionType.COMBINE_VARIABLES:
                params = action.action_params
                input_vars = params.get("input_variables", [])
                output_var = params.get("output_variable_name")
                method = params.get("method", "sum")
                weights = params.get("weights", None)
                
                if not all(var in current_data_df.columns for var in input_vars):
                    missing_vars = [var for var in input_vars if var not in current_data_df.columns]
                    logs.append(f"**WARNING**: Variables not found: {missing_vars}")
                    output["status"] = "skipped"
                else:
                    if method == "sum":
                        if weights:
                            current_data_df[output_var] = sum(current_data_df[var] * w for var, w in zip(input_vars, weights))
                        else:
                            current_data_df[output_var] = current_data_df[input_vars].sum(axis=1)
                    elif method == "mean":
                        if weights:
                            current_data_df[output_var] = sum(current_data_df[var] * w for var, w in zip(input_vars, weights)) / sum(weights)
                        else:
                            current_data_df[output_var] = current_data_df[input_vars].mean(axis=1)
                    
                    # Add combined variable to metadata
                    new_var = Variable(
                        name=f"Combined: {', '.join(input_vars)}",
                        code=output_var,
                        variable_type=VariableType.OBSERVED,
                        scale="interval",
                        collection_method="computed"
                    )
                    state["current_variables"].append(new_var)
                    set_current_data(state, current_data_df)
                    output["changes"].append(f"Combined variables {input_vars} into {output_var} using {method}")
                    logs.append(f"Combined variables using {method}: {input_vars} -> {output_var}")

            elif action.action_type == ActionType.TRANSFORM_VARIABLES:
                params = action.action_params
                var_code = params.get("variable")
                transform_type = params.get("transform_type")
                transform_params = params.get("transform_params", {})
                
                if not var_code or var_code not in current_data_df.columns:
                    logs.append(f"**WARNING**: Variable `{var_code}` for transformation not found.")
                    output["status"] = "skipped"
                else:
                    original_series = current_data_df[var_code].copy()
                    if transform_type == "differencing":
                        d_order = transform_params.get('d', 0)
                        D_order = transform_params.get('D', 0)
                        m_period = transform_params.get('m', 0)
                        
                        transformed_series, inversion_details = _apply_differencing_and_get_inversion_params(
                            original_series, d=d_order, D=D_order, m=m_period
                        )
                        
                        if not pd.api.types.is_float_dtype(current_data_df[var_code]):
                            current_data_df[var_code] = current_data_df[var_code].astype(float)
                        current_data_df[var_code] = transformed_series
                        
                        # Update variable metadata
                        var_meta = next((v for v in state.current_variables if v.code == var_code), None)
                        if var_meta:
                            record = TransformationRecord(
                                transform_type='differencing',
                                params=inversion_details,
                                applied_to_variable=var_code
                            )
                            var_meta.transform_history.append(record)
                    elif transform_type == "log":
                        base = transform_params.get("base", "natural")
                        offset = transform_params.get("offset", 0)
                        
                        if (original_series + offset <= 0).any():
                            logs.append(f"**WARNING**: Cannot apply log transform - negative/zero values found.")
                            output["status"] = "skipped"
                        else:
                            if base == "natural":
                                transformed_series = np.log(original_series + offset)
                            elif base == 10:
                                transformed_series = np.log10(original_series + offset)
                            else:
                                transformed_series = np.log(original_series + offset) / np.log(base)
                            
                            current_data_df[var_code] = transformed_series
                    
                    elif transform_type == "square_root":
                        if (original_series < 0).any():
                            logs.append(f"**WARNING**: Cannot apply square root - negative values found.")
                            output["status"] = "skipped"
                        else:
                            current_data_df[var_code] = np.sqrt(original_series)
                    
                    elif transform_type == "standard_scale":
                        scaler = StandardScaler()
                        transformed = scaler.fit_transform(original_series.values.reshape(-1, 1)).flatten()
                        current_data_df[var_code] = transformed
                        
                        # Store scaling parameters for potential inverse transform
                        var_meta = next((v for v in state.current_variables if v.code == var_code), None)
                        if var_meta:
                            if not hasattr(var_meta, 'properties') or var_meta.properties is None:
                                var_meta.properties = {}
                            var_meta.properties['scaler_mean'] = scaler.mean_[0]
                            var_meta.properties['scaler_std'] = scaler.scale_[0]
                    
                    elif transform_type == "box_cox":
                        lambda_param = transform_params.get("lambda", None)
                        if (original_series <= 0).any():
                            logs.append(f"**WARNING**: Cannot apply Box-Cox - non-positive values found.")
                            output["status"] = "skipped"
                        else:
                            if lambda_param is None:
                                transformed_series, lambda_param = stats.boxcox(original_series)
                            else:
                                transformed_series = stats.boxcox(original_series, lmbda=lambda_param)
                            
                            current_data_df[var_code] = transformed_series
                            
                            # Store lambda for inverse transform
                            var_meta = next((v for v in state.current_variables if v.code == var_code), None)
                            if var_meta:
                                if not hasattr(var_meta, 'properties') or var_meta.properties is None:
                                    var_meta.properties = {}
                                var_meta.properties['boxcox_lambda'] = lambda_param
                    
                    else:
                        logs.append(f"**WARNING**: Unknown transform_type `{transform_type}`. Action skipped.")
                        output["status"] = "skipped"
                    
                    if output["status"] != "skipped":
                        set_current_data(state, current_data_df)
                        msg = f"Applied {transform_type} transformation to variable: {var_code}"
                        output["changes"].append(msg)
                        logs.append(msg)

            elif action.action_type == ActionType.INVERSE_TRANSFORM_VARIABLES:
                params = action.action_params
                var_code = params.get("variable")
                original_transform_type = params.get("original_transform_type")
                transform_params = params.get("transform_params", {})
                
                if not var_code or var_code not in current_data_df.columns:
                    logs.append(f"**WARNING**: Variable `{var_code}` for inverse transformation not found.")
                    output["status"] = "skipped"
                else:
                    series = current_data_df[var_code].copy()
                    
                    if original_transform_type == "log":
                        base = transform_params.get("base", "natural")
                        offset = transform_params.get("offset", 0)
                        
                        if base == "natural":
                            current_data_df[var_code] = np.exp(series) - offset
                        elif base == 10:
                            current_data_df[var_code] = np.power(10, series) - offset
                        else:
                            current_data_df[var_code] = np.power(base, series) - offset
                    
                    elif original_transform_type == "square_root":
                        current_data_df[var_code] = np.power(series, 2)
                    
                    elif original_transform_type == "standard_scale":
                        mean = transform_params.get("mean")
                        std = transform_params.get("std")
                        if mean is not None and std is not None:
                            current_data_df[var_code] = series * std + mean
                    
                    elif original_transform_type == "box_cox":
                        lambda_param = transform_params.get("lambda")
                        if lambda_param is not None:
                            current_data_df[var_code] = stats.inv_boxcox(series, lambda_param)
                    
                    set_current_data(state, current_data_df)
                    msg = f"Applied inverse {original_transform_type} to variable: {var_code}"

                    output["changes"].append(msg)
                    logs.append(msg)

            elif action.action_type == ActionType.HANDLE_DUPLICATES:
                operation = params.get("operation")
                if operation == "remove_duplicates":
                    initial_rows = len(current_data_df)
                    current_data_df.drop_duplicates(inplace=True)
                    rows_removed = initial_rows - len(current_data_df)
                    state.set_current_data(current_data_df)
                    msg = f"Removed {rows_removed} duplicate rows."
                    output["changes"].append(msg)
                    logs.append(msg)
                else:
                    logs.append(f"**WARNING**: Unknown duplicate handling operation `{operation}`.")
                    output["status"] = "skipped"

            elif action.action_type == ActionType.CONVERT_DATA_TYPE:
                var_code = params.get("variable")
                target_type = params.get("target_type")
                if var_code and target_type:
                    if target_type == 'category':
                        current_data_df[var_code] = current_data_df[var_code].astype('category')
                    elif target_type == 'numeric':
                        current_data_df[var_code] = pd.to_numeric(current_data_df[var_code], errors='coerce')        
                    else:
                        logs.append(f"**WARNING**: Unsupported target type `{target_type}` for conversion.")
                        output["status"] = "skipped"
                    
                    if output["status"] != "skipped":
                        state.set_current_data(current_data_df)
                        msg = f"Converted variable {var_code} to type {target_type}."
                        output["changes"].append(msg)
                        logs.append(msg)

                else:
                    logs.append(f"**WARNING**: Missing parameters for data type conversion.")
                    output["status"] = "skipped"
            elif action.action_type == ActionType.HANDLE_OUTLIERS:
                var_code = params.get("variable")
                method = params.get("method")
                
                if not var_code or var_code not in current_data_df.columns:
                    logs.append(f"**WARNING**: Variable `{var_code}` for outlier handling not found.")
                    output["status"] = "skipped"
                else:
                    if method == "remove":
                        outlier_indices = params.get("outlier_indices", [])
                        current_data_df = current_data_df.drop(index=outlier_indices, errors='ignore')
                    elif method == "cap_floor":
                        method_params = params.get("method_params", {})
                        lower_pct = method_params.get("lower_percentile", 5)
                        upper_pct = method_params.get("upper_percentile", 95)
                        lower_bound = current_data_df[var_code].quantile(lower_pct/100)
                        upper_bound = current_data_df[var_code].quantile(upper_pct/100)
                        current_data_df[var_code] = current_data_df[var_code].clip(lower=lower_bound, upper=upper_bound)
                    elif method == "transform":
                        if (current_data_df[var_code] <= 0).any():
                            logs.append(f"**WARNING**: Cannot apply log transform for outlier handling due to non-positive values.")
                            output["status"] = "skipped"
                        else:
                            current_data_df[var_code] = np.log(current_data_df[var_code])
                    
                    if output["status"] != "skipped":
                        state.set_current_data(current_data_df)
                        msg = f"Handled outliers in {var_code} using {method}"
                        output["changes"].append(msg)
                        logs.append(msg)

            elif action.action_type == ActionType.HANDLE_MISSING_VALUES:
                params = action.action_params
                var_code = params.get("variable")
                method = params.get("method")
                
                if not var_code or var_code not in current_data_df.columns:
                    logs.append(f"**WARNING**: Variable `{var_code}` for missing value handling not found.")
                    output["status"] = "skipped"
                else:
                    if method == "remove":
                        removal_strategy = params.get("removal_strategy", "listwise")
                        if removal_strategy == "listwise":
                            current_data_df = current_data_df.dropna(subset=[var_code])
                    elif method == "mean":
                        current_data_df[var_code] = current_data_df[var_code].fillna(current_data_df[var_code].mean())
                    elif method == "median":
                        current_data_df[var_code] = current_data_df[var_code].fillna(current_data_df[var_code].median())
                    elif method == "mode":
                        mode_val = current_data_df[var_code].mode()
                        if not mode_val.empty:
                            current_data_df[var_code].fillna(mode_val[0], inplace=True)
                        else:
                            logs.append(f"**WARNING**: No mode found for variable {var_code}. Skipping imputation.")       
                    elif method == "forward_fill":
                        limit = params.get("method_params", {}).get("limit", None)
                        current_data_df[var_code] = current_data_df[var_code].fillna(method='ffill', limit=limit)
                    elif method == "linear_interpolate":
                        current_data_df[var_code] = current_data_df[var_code].interpolate(method='linear')
                    elif method == "knn_impute":
                        method_params = params.get("method_params", {})
                        n_neighbors = method_params.get("n_neighbors", 5)
                        
                        imputer = KNNImputer(n_neighbors=n_neighbors)
                        numeric_cols = current_data_df.select_dtypes(include=[np.number]).columns
                        current_data_df[numeric_cols] = imputer.fit_transform(current_data_df[numeric_cols])
                    
                    state.set_current_data(current_data_df)
                    msg = f"Handled missing values in {var_code} using {method}"
                    output["changes"].append(msg)
                    logs.append(msg)
            elif action.action_type == ActionType.MODIFY_MODEL_SPECIFICATION:
                model_type = action.action_params.get("model_type")
                current_spec = action.action_params.get("current_specification", {})
                suggested_spec = action.action_params.get("suggested_specification", {})
                reason = action.action_params.get("modification_reason", "")
                
                logs.append(f"**ACTION**: Model specification modification for {model_type}")
                logs.append(f"Current: {current_spec}, Suggested: {suggested_spec}")
                logs.append(f"Reason: {reason}")
                output["changes"].append(f"Model specification change suggested for {model_type}")

            elif action.action_type == ActionType.REANALYZE:
                action_params = action.action_params or {}
                trigger_reason = action_params.get("trigger_reason", "")
                target_vars = action_params.get("target_variables", [])
                analysis_scope = action_params.get("analysis_scope", "full")
                
                logs.append(f"**ACTION**: Reanalyze requested - {trigger_reason}")
                logs.append(f"Target variables: {target_vars}, Scope: {analysis_scope}")
                output["changes"].append("Reanalysis flagged")

            elif action.action_type == ActionType.UPDATE_VARIABLE_PROPERTIES:
                params = action.action_params
                codes_to_update = params.get("variable_codes", [])
                if "variable_code" in params:
                    codes_to_update.append(params["variable_code"])
                
                properties_to_update = params.get("properties_to_update", {})

                if not codes_to_update:
                    logs.append(f"**WARNING**: No variable codes specified. Action skipped.")
                    output["status"] = "skipped"
                elif not properties_to_update:
                    logs.append(f"**WARNING**: No properties to update specified. Action skipped.")
                    output["status"] = "skipped"
                else:
                    updated_vars = []
                    for var_code in codes_to_update:
                        var_meta = next((v for v in state["current_variables"] if v.code == var_code), None)
                        if var_meta:
                            if not hasattr(var_meta, 'properties') or var_meta.properties is None:
                                var_meta.properties = {}
                            
                            # Deep merge/update logic
                            # This simple version overwrites keys. A more complex merge could be implemented if needed.
                            for key, value in properties_to_update.items():
                                if key in var_meta.properties and isinstance(var_meta.properties[key], dict) and isinstance(value, dict):
                                    var_meta.properties[key].update(value)
                                else:
                                    var_meta.properties[key] = value
                            
                            updated_vars.append(var_code)
                        else:
                            logs.append(f"**WARNING**: Variable metadata for `{var_code}` not found.")
                    
                    if updated_vars:
                        msg = f"Updated properties for variables: {', '.join(updated_vars)}"
                        output["changes"].append(msg)
                        logs.append(msg)
                    else:
                        output["status"] = "skipped" # No variables were actually updated

            # Queue reflection step if specified
            if action.reflection_params and output["status"] not in ["skipped", "failed"]:
                reflection_step = AnalyzeStep(
                    step_type=AnalysisStepType.REFLECTION,
                    tool=action.reflection_params.get("tool"),
                    parameters=action.reflection_params.get("parameters", {}),
                    comment=action.reflection_params.get("comment", "Reflection step"),
                    plan_id=plan_id,
                    recursive=action.reflection_params.get("recursive", False),
                    reset_actions=action.reflection_params.get("reset_actions", False)
                )
                state["execution_log"].pending_steps.insert(0, reflection_step)
                logs.append(
                    f"Queued reflection: {reflection_step.tool} "
                    f"(Recursive: {reflection_step.recursive}, Reset Actions: {reflection_step.reset_actions})"
                )

            if output["status"] == "executed":
                output["status"] = "done"
            logs.append(f"Action `{action.action_type}` processing finished with status: {output['status']}.")

        except Exception as e:
            error_msg = f"**ERROR**: Action `{action.action_type}` failed: {str(e)}. Full traceback: {traceback.format_exc()}"
            logs.append(error_msg)
            output["status"] = "failed"
            output["error_details"] = str(e)


    action_step = AnalyzeStep(
        step_type=AnalysisStepType.ACTION,
        action_type=action.action_type,
        parameters={"action": action.model_dump()},
        comment=action.comment,
        output=output,
        plan_id=plan_id,
        reset_actions=action.reset_actions
    )

    log_entry_content = (
        f"Action: {action.action_type}, "
        f"Params: {action.action_params}, "
        f"Issue: {action.issue}, "
        f"Comment: {action.comment}, "
        f"Initial Status: {action.status}, "
        f"Final Status: {output['status']}, "
        f"Reflection: {action.reflection_params}"
    )
    log_entry = LogEntry(
        step_type=AnalysisStepType.ACTION,
        action_type=action.action_type,
        plan_id=plan_id,
        content=log_entry_content
    )

    if "execution_log" in state:
        state["execution_log"].executed_steps.append(action_step)
        state["execution_log"].logs.append("\n".join(logs))
        state["logs"].append(log_entry)

    return action_step

def execute_pipeline(
    state: State,
    tool_configs: list[dict[str, any]] = None,
    analysis_description: str = "custom_pipeline"
) -> State:
    """
    Execute a pipeline of analysis tools, applying actions and reflections, and update the state.
    Uses a stack-based approach with pending_steps. Supports auto and interactive modes.
    Appends LogEntry to state.logs for each step.
    Prioritizes existing current_plan if valid, otherwise creates a new plan from tool_configs if provided.
    """
    # Initialize execution log if not present
    if "execution_log" not in state or state["execution_log"] is None:
        state["execution_log"] = ExecutionLog(
            plans=[],
            executed_steps=[],
            pending_steps=[],
            logs=[]
        )

    # Initialize tool_configs if None
    tool_configs = tool_configs or []

    # Initialize pipeline logs
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    pipeline_logs = []

    # Case 1: tool_configs provided, create a new plan
    if tool_configs:
        plan_id = len(state["execution_log"].plans) + 1
        plan = Plan(
            analysis_description=analysis_description,
            steps=[
                AnalyzeStep(
                    step_type=AnalysisStepType.TOOL,
                    tool=config["tool"],
                    parameters=config.get("params", {}),
                    comment=f"Execute {config['tool']}",
                    plan_id=plan_id,
                    # By default, tools are recursive unless specified otherwise
                    recursive=config.get("recursive", True)
                ) for config in tool_configs
            ],
            parameters={"timestamp": timestamp},
            plan_id=plan_id
        )
        state["execution_log"].plans.append(plan)
        state["current_plan"] = plan
        state["execution_log"].pending_steps = [step.model_copy() for step in plan.steps]
        pipeline_logs.append(f"# New Pipeline: {analysis_description}\nPlan ID: {plan_id}\nStarted at: {timestamp}\nMode: {state["action_mode"]}\n")

    # Case 2: Current plan exists
    elif "current_plan" in state:
        # Check if current_plan exists in execution_log.plans
        plan_exists = any(plan.plan_id == state["current_plan"].plan_id for plan in state["execution_log"].plans)
        
        if not plan_exists:
            state["execution_log"].plans.append(state["current_plan"])
            state["execution_log"].pending_steps = [step.model_copy() for step in state["current_plan"].steps]
            pipeline_logs.append(f"# New Pipeline: {analysis_description}\nPlan ID: {state["current_plan"].plan_id}\nStarted at: {timestamp}\nMode: {state["action_mode"]}\n")
        else:
            pipeline_logs.append(f"# Resuming Pipeline: {analysis_description}\nPlan ID: {state["current_plan"].plan_id}\nResumed at: {timestamp}\nMode: {state["action_mode"]}\n")
            # Ensure pending_steps are populated if empty but plan has steps
            if not state["execution_log"].pending_steps and state["current_plan"].steps:
                state["execution_log"].pending_steps = [step.model_copy() for step in state["current_plan"].steps]

    # Case 3: No current plan and no tool_configs
    else:
        pipeline_logs.append(f"**ERROR**: No current plan or tool configurations provided.")
        state["execution_log"].logs.append("\n".join(pipeline_logs))
        return state

    # Process pending steps
    while state["execution_log"].pending_steps:
        step = state["execution_log"].pending_steps.pop(0)

        # --- Handle reset_actions flag ---
        if step.reset_actions:
            method_to_reset = None
            if step.step_type == AnalysisStepType.ACTION:
                action_to_execute = Action(**step.parameters["action"])
                method_to_reset = action_to_execute.method
            elif step.step_type == AnalysisStepType.REFLECTION:
                method_to_reset = step.tool

            if method_to_reset:
                pipeline_logs.append(f"**RESET_ACTIONS**: Flag on step for '{method_to_reset}'. Clearing subsequent actions from this source.")
                original_count = len(state["execution_log"].pending_steps)
                steps_to_keep = []
                for pending_step in state["execution_log"].pending_steps:
                    if pending_step.step_type == AnalysisStepType.ACTION:
                        action_in_queue = Action(**pending_step.parameters["action"])
                        if action_in_queue.method == method_to_reset:
                            pipeline_logs.append(f"  - Removing pending action: {action_in_queue.action_type} (from method: {action_in_queue.method})")
                            continue
                    steps_to_keep.append(pending_step)
                state["execution_log"].pending_steps = steps_to_keep
                removed_count = original_count - len(steps_to_keep)
                if removed_count > 0:
                    pipeline_logs.append(f"Removed {removed_count} subsequent action(s) from method '{method_to_reset}'.")

        pipeline_logs.append(f"Processing step: {step.step_type} - {step.comment}")

        if step.step_type == AnalysisStepType.TOOL:
            tool_name = step.tool
            params = step.parameters
            tool_logs = [f"## Executing Tool: {tool_name}\nParameters: {params}"]
            try:
                tool_func = TOOL_REGISTRY[tool_name]
                tool_output = tool_func(
                    data=get_current_dataframe(state),  # Use DataFrame from CSV
                    variables=state["current_variables"],
                    params=params
                )
                step.output = tool_output
                tool_logs.extend(tool_output.logs)

                # Initialize file_descriptions in tool_output if not present
                if tool_output.file_descriptions is None:
                    tool_output.file_descriptions = {}

                # Initialize file_descriptions in state if not present
                if "file_descriptions" not in state:
                    state["file_descriptions"] = {}

                for file_path, content in tool_output.file_contents.items():
                    if file_path in state["generated_files"]:
                        tool_logs.append(f"**WARNING**: Overwriting file '{file_path}'.")
                    state["generated_files"][file_path] = content

                    # Get file description and store it
                    file_desc = get_file_description(file_path)
                    tool_output.file_descriptions[file_path] = file_desc
                    state["file_descriptions"][file_path] = file_desc
                
                if tool_output.action:
                    for action in reversed(tool_output.action):
                        action_step = AnalyzeStep(
                            step_type=AnalysisStepType.ACTION,
                            action_type=action.action_type,
                            parameters={"action": action.model_dump()},
                            comment=action.comment,
                            plan_id=state["current_plan"].plan_id,
                            reset_actions=action.reset_actions
                        )
                        state["execution_log"].pending_steps.insert(0, action_step)
                        tool_logs.append(f"Queued action: {action.action_type} (Reset flag: {action.reset_actions})")
                
                tool_logs.append(f"Tool {tool_name} completed.")
                log_entry = LogEntry(step_type=AnalysisStepType.TOOL, tool=tool_name, plan_id=state["current_plan"].plan_id, content="\n".join(tool_output.logs))
                state["logs"].append(log_entry)
            except Exception as e:
                tool_logs.append(f"**ERROR**: Failed to execute `{tool_name}`: {str(e)}")
                step.output = {"status": "failed", "error": str(e)}
                log_entry = LogEntry(step_type=AnalysisStepType.TOOL, tool=tool_name, plan_id=state["current_plan"].plan_id, content=f"**ERROR**: {str(e)}")
                state["logs"].append(log_entry)
            state["execution_log"].executed_steps.append(step)
            state["execution_log"].logs.append("\n".join(tool_logs))

        elif step.step_type == AnalysisStepType.ACTION:
            action = Action(**step.parameters["action"])
            if action.status == "pending" and state["action_mode"] == ExecutionMode.INTERACTIVE:
                pipeline_logs.append(f"**PAUSED**: Action `{action.action_type}` is pending user approval.")
                state["execution_log"].pending_steps.insert(0, step)
                break
            else:
                action_step = apply_action(action, state)
                if action_step.output["status"] == "failed":
                    pipeline_logs.append(f"**ERROR**: Action `{action.action_type}` failed.")

        elif step.step_type == AnalysisStepType.REFLECTION:
            tool_name = step.tool
            params = step.parameters
            tool_logs = [f"## Executing Reflection: {tool_name}\nParameters: {params} (Recursive: {step.recursive})"]
            try:
                tool_func = TOOL_REGISTRY[tool_name]
                tool_output = tool_func(
                    data=get_current_dataframe(state),  # Use DataFrame from CSV
                    variables=state["current_variables"],
                    params=params
                )
                step.output = tool_output
                tool_logs.extend(tool_output.logs)

                # Initialize file_descriptions in tool_output if not present
                if tool_output.file_descriptions is None:
                    tool_output.file_descriptions = {}

                # Initialize file_descriptions in state if not present
                if "file_descriptions" not in state:
                    state["file_descriptions"] = {}

                for file_path, content in tool_output.file_contents.items():
                    if file_path in state["generated_files"]:
                        tool_logs.append(f"**WARNING**: Overwriting file '{file_path}'.")
                    state["generated_files"][file_path] = content

                    # Get file description and store it (reflect=True for reflection step)
                    file_desc = get_file_description(file_path, reflect=True)
                    tool_output.file_descriptions[file_path] = file_desc
                    state["file_descriptions"][file_path] = file_desc
                
                # Conditionally queue actions based on the 'recursive' flag
                if step.recursive and tool_output.action:
                    tool_logs.append(f"**RECURSIVE REFLECTION**: Queuing {len(tool_output.action)} new action(s).")
                    for action in reversed(tool_output.action):
                        action_step = AnalyzeStep(
                            step_type=AnalysisStepType.ACTION,
                            action_type=action.action_type,
                            parameters={"action": action.model_dump()},
                            comment=action.comment,
                            plan_id=state["current_plan"].plan_id,
                            reset_actions=action.reset_actions
                        )
                        state["execution_log"].pending_steps.insert(0, action_step)
                        tool_logs.append(f"  - Queued action: {action.action_type} (Reset flag: {action.reset_actions})")
                elif tool_output.action:
                    tool_logs.append(f"**NON-RECURSIVE REFLECTION**: Ignoring {len(tool_output.action)} generated action(s).")

                tool_logs.append(f"Reflection {tool_name} completed.")
                log_entry = LogEntry(step_type=AnalysisStepType.REFLECTION, tool=tool_name, plan_id=state["current_plan"].plan_id, content="\n".join(tool_output.logs))
                state["logs"].append(log_entry)
            except Exception as e:
                tool_logs.append(f"**ERROR**: Failed to execute reflection `{tool_name}`: {str(e)}")
                step.output = {"status": "failed", "error": str(e)}
                log_entry = LogEntry(step_type=AnalysisStepType.REFLECTION, tool=tool_name, plan_id=state["current_plan"].plan_id, content=f"**ERROR**: {str(e)}")
                state["logs"].append(log_entry)
            state["execution_log"].executed_steps.append(step)
            state["execution_log"].logs.append("\n".join(tool_logs))

    # Finalize if no pending steps
    if not state["execution_log"].pending_steps:
        pipeline_logs.append(f"Pipeline completed: {analysis_description}\nGenerated files: {list(state["generated_files"].keys())}")
        state["current_plan"] = None

    state["execution_log"].logs.append("\n".join(pipeline_logs))
    return state