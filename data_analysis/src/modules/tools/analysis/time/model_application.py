import base64
import io
from typing import Any, Optional, Union
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
import json

from statsmodels.tsa.vector_ar.irf import IRAnalysis
from statsmodels.tsa.vector_ar.var_model import VARResults
from statsmodels.tsa.vector_ar.vecm import VECMResults

from data_analysis.src.schemas.analyzer_states import Variable, Action
from data_analysis.src.modules.tools.analysis.time.utils import transformations as transformations_util

def _run_model_application_step(
    fitted_model: Any,
    target_series_data: Union[pd.Series, pd.DataFrame],
    variables: list[Variable],
    params: dict,
    logs: list[str],
    file_contents: dict[str, str],
    tool_results: dict[str, Any],
    actions: list[Action],
    output_dir_id: str,
    model_prefix: str
) -> None:
    """
    Performs model application (Forecasting or Relationship Analysis) on a pre-fitted model.
    
    This function applies the fitted model for either forecasting future values or analyzing
    relationships between variables through impulse response functions and variance decomposition.
    
    Parameters:
        fitted_model: The successfully fitted statsmodels model object
        target_series_data: The original data used to fit the model (Series or DataFrame)
        variables: list of Variable objects containing metadata and transformation history
        params: dictionary containing application parameters:
            - application_goal (str): 'Forecasting' or 'RelationshipAnalysis'
            - forecast_horizon (int): Number of periods to forecast (default: 12)
            - confidence_level (float): Confidence level for intervals (default: 0.95)
            - irf_periods (int): Periods for impulse response analysis (default: 10)
            - fevd_periods (int): Periods for variance decomposition (default: 10)
            - future_exogenous_data (optional): Future exogenous variables for forecasting
        logs: list to append report content messages
        file_contents: dictionary to store generated file contents
        tool_results: dictionary to store analysis results
        actions: list of suggested actions (passed for consistency)
        output_dir_id: Unique directory identifier for file naming
        model_prefix: String prefix for output file names
    
    Returns:
        None (modifies passed dictionaries in place)
    """
    # Extract parameters at the start
    application_goal = params.get('application_goal')
    forecast_horizon = params.get('forecast_horizon', 12)
    confidence_level = params.get('confidence_level', 0.95)
    irf_periods = params.get('irf_periods', 10)
    fevd_periods = params.get('fevd_periods', 10)
    future_exog_data = params.get('future_exogenous_data')
    
    alpha = 1.0 - confidence_level
    
    if not application_goal:
        logs.append(f"Model application skipped: application goal not specified for {model_prefix}")
        return

    logs.append(f"Model Application Analysis - {application_goal} for {model_prefix}")
    tool_results['application'] = {}
    app_results = tool_results['application']

    if application_goal == "Forecasting":
        _perform_forecasting_analysis(
            fitted_model, target_series_data, variables, 
            forecast_horizon, confidence_level, alpha, future_exog_data,
            logs, file_contents, app_results, output_dir_id, model_prefix
        )
    
    elif application_goal == "RelationshipAnalysis":
        _perform_relationship_analysis(
            fitted_model, target_series_data, 
            irf_periods, fevd_periods,
            logs, file_contents, app_results, output_dir_id, model_prefix
        )
    
    else:
        logs.append(f"Unknown application goal '{application_goal}' for {model_prefix}. Available options: 'Forecasting', 'RelationshipAnalysis'")


def _perform_forecasting_analysis(
    fitted_model: Any,
    target_series_data: Union[pd.Series, pd.DataFrame],
    variables: list[Variable],
    forecast_horizon: int,
    confidence_level: float,
    alpha: float,
    future_exog_data: Optional[Any],
    logs: list[str],
    file_contents: dict[str, str],
    app_results: dict[str, Any],
    output_dir_id: str,
    model_prefix: str
) -> None:
    """Perform forecasting analysis and generate results."""
    
    # Check for exogenous variables requirement
    future_exog = None
    if hasattr(fitted_model.model, 'exog') and fitted_model.model.exog is not None:
        if future_exog_data is None:
            logs.append(f"Warning: {model_prefix} model requires future exogenous variables but none provided - forecasting may be inaccurate")
        else:
            future_exog = future_exog_data

    try:
        # Generate forecast
        forecast_obj = fitted_model.get_forecast(steps=forecast_horizon, exog=future_exog, alpha=alpha)
        
        # Determine if multivariate
        is_multivariate = isinstance(target_series_data, pd.DataFrame) and target_series_data.shape[1] > 1
        primary_target_code = target_series_data.columns[0] if is_multivariate else target_series_data.name
        
        # Extract forecast components
        if is_multivariate:
            forecast_summary = forecast_obj.summary_frame(alpha=alpha)
            point_forecasts = forecast_summary[f'mean']
            conf_int = forecast_summary[[f'mean_ci_lower', f'mean_ci_upper']]
            conf_int.columns = ['lower', 'upper']
        else:
            point_forecasts = forecast_obj.predicted_mean
            conf_int = forecast_obj.conf_int(alpha=alpha)
            conf_int.columns = ['lower', 'upper']

        # Apply inverse transformations to get original scale
        hist_original_scale = apply_inverse_transformations(
            target_series_data, primary_target_code, variables, logs
        )
        fcst_original_scale = apply_inverse_transformations(
            point_forecasts, primary_target_code, variables, logs
        )
        ci_original_scale = apply_inverse_transformations(
            conf_int, primary_target_code, variables, logs
        )

        # Create forecast table
        forecast_table = pd.DataFrame({
            'forecast': fcst_original_scale,
            'ci_lower': ci_original_scale['lower'],
            'ci_upper': ci_original_scale['upper']
        })
        
        # Store results
        app_results['forecast_table'] = forecast_table.to_dict(orient='split')
        app_results['forecast_horizon'] = forecast_horizon
        app_results['confidence_level'] = confidence_level
        
        # Generate files
        fcst_path = f"{output_dir_id}/{model_prefix}_forecast_table.csv"
        file_contents[fcst_path] = df_to_csv_string(forecast_table, index=True)
        
        # Create enhanced forecast plot
        fig_fcst = _create_enhanced_forecast_plot(
            hist_original_scale, fcst_original_scale, ci_original_scale, 
            f"{model_prefix} Forecast ({forecast_horizon} periods, {confidence_level*100:.0f}% CI)"
        )
        
        plot_path = f"{output_dir_id}/{model_prefix}_forecast_plot.png"
        file_contents[plot_path] = fig_to_base64(fig_fcst)
        
        # Report to logs
        logs.append(f"Forecast table with {forecast_horizon} periods ahead at {confidence_level*100:.0f}% confidence level: {fcst_path}")
        logs.append(f"Forecast visualization plot: {plot_path}")
        
        # Summary statistics
        mean_forecast = fcst_original_scale.mean()
        forecast_range = fcst_original_scale.max() - fcst_original_scale.min()
        logs.append(f"Forecast summary - Mean: {mean_forecast:.4f}, Range: {forecast_range:.4f}")

    except Exception as e:
        error_msg = f"Forecasting analysis failed for {model_prefix}: {str(e)}"
        logs.append(error_msg)
        app_results['error'] = str(e)


def _perform_relationship_analysis(
    fitted_model: Any,
    target_series_data: Union[pd.Series, pd.DataFrame],
    irf_periods: int,
    fevd_periods: int,
    logs: list[str],
    file_contents: dict[str, str],
    app_results: dict[str, Any],
    output_dir_id: str,
    model_prefix: str
) -> None:
    """Perform relationship analysis (IRF and FEVD) for VAR/VECM models."""
    
    if not isinstance(fitted_model, (VARResults, VECMResults)):
        model_class_name = type(fitted_model).__name__
        logs.append(f"Relationship analysis requires VAR/VECM models but found {model_class_name} for {model_prefix}")
        return
        
    try:
        # Generate IRF and FEVD based on model type
        if isinstance(fitted_model, VECMResults):
            logs.append(f"Performing relationship analysis for VECM model: {model_prefix}")
            irf = IRAnalysis(fitted_model, periods=irf_periods, vecm=True)
            fevd = irf.fevd(periods=fevd_periods)
        else:  # VARResults
            logs.append(f"Performing relationship analysis for VAR model: {model_prefix}")
            irf = fitted_model.irf(periods=irf_periods)
            fevd = fitted_model.fevd(periods=fevd_periods)

        # Generate Impulse Response Functions plot
        fig_irf = irf.plot(orth=False)
        _enhance_irf_plot(fig_irf, f"{model_prefix} Impulse Response Functions")
        
        irf_path = f"{output_dir_id}/{model_prefix}_impulse_response_functions.png"
        file_contents[irf_path] = fig_to_base64(fig_irf)

        # Generate FEVD summary and plot
        fevd_summary_df = fevd.summary().as_df()
        app_results['fevd_summary'] = fevd_summary_df.to_dict(orient='split')
        app_results['irf_periods'] = irf_periods
        app_results['fevd_periods'] = fevd_periods
        
        fevd_path = f"{output_dir_id}/{model_prefix}_fevd_summary.csv"
        file_contents[fevd_path] = df_to_csv_string(fevd_summary_df, index=True)

        fig_fevd = fevd.plot()
        _enhance_fevd_plot(fig_fevd, f"{model_prefix} Forecast Error Variance Decomposition")
        
        fevd_plot_path = f"{output_dir_id}/{model_prefix}_fevd_plot.png"
        file_contents[fevd_plot_path] = fig_to_base64(fig_fevd)

        # Report to logs
        logs.append(f"Impulse Response Functions analysis over {irf_periods} periods: {irf_path}")
        logs.append(f"Forecast Error Variance Decomposition over {fevd_periods} periods: {fevd_plot_path}")
        logs.append(f"FEVD summary statistics table: {fevd_path}")
        
        # Summary insights
        variable_names = list(fevd_summary_df.columns) if not fevd_summary_df.empty else []
        logs.append(f"Relationship analysis completed for {len(variable_names)} variables: {', '.join(variable_names)}")

    except Exception as e:
        error_msg = f"Relationship analysis failed for {model_prefix}: {str(e)}"
        logs.append(error_msg)
        app_results['error'] = str(e)


def _create_enhanced_forecast_plot(
    historical_data: pd.Series,
    forecast_data: pd.Series,
    confidence_intervals: pd.DataFrame,
    title: str
) -> Figure:
    """Create an enhanced forecast plot with professional styling."""
    
    fig, ax = plt.subplots(figsize=(6, 4))
    
    # Plot historical data
    ax.plot(historical_data.index, historical_data.values, 
            color='#2E86AB', linewidth=1, label='Historical Data')
    
    # Plot forecast
    ax.plot(forecast_data.index, forecast_data.values, 
            color='#F24236', linewidth=1, label='Forecast', linestyle='--')
    
    # Plot confidence intervals
    ax.fill_between(forecast_data.index, 
                   confidence_intervals['lower'], 
                   confidence_intervals['upper'],
                   alpha=0.3, color='#F24236', label='Confidence Interval')
    
    # Styling
    ax.set_title(title, fontsize=16, fontweight='bold', pad=20)
    ax.set_xlabel('Time Period', fontsize=12)
    ax.set_ylabel('Value', fontsize=12)
    ax.legend(loc='upper left', fontsize=10)
    ax.grid(True, alpha=0.3, linestyle='-', linewidth=0.5)
    
    # Format axes
    ax.tick_params(axis='both', which='major', labelsize=10)
    plt.xticks(rotation=45)
    plt.tight_layout()
    
    return fig


def _enhance_irf_plot(fig: Figure, title: str) -> None:
    """Enhance IRF plot with professional styling."""
    
    fig.suptitle(title, fontsize=16, fontweight='bold', y=0.98)
    
    for ax in fig.axes:
        ax.grid(True, alpha=0.3, linestyle='-', linewidth=0.5)
        ax.tick_params(axis='both', which='major', labelsize=9)
        
        # Add zero line for reference
        ax.axhline(y=0, color='black', linestyle='-', alpha=0.5, linewidth=0.8)
    
    plt.tight_layout()


def _enhance_fevd_plot(fig: Figure, title: str) -> None:
    """Enhance FEVD plot with professional styling."""
    
    fig.suptitle(title, fontsize=16, fontweight='bold', y=0.98)
    
    for ax in fig.axes:
        ax.grid(True, alpha=0.3, linestyle='-', linewidth=0.5)
        ax.tick_params(axis='both', which='major', labelsize=9)
        ax.set_ylim(0, 1)  # FEVD values are proportions
    
    plt.tight_layout()


def fig_to_base64(fig: Figure) -> str:
    """Convert a matplotlib Figure to a base64 encoded string."""
    buf = io.BytesIO()
    fig.savefig(buf, format='png', bbox_inches='tight', dpi=300)
    plt.close(fig)
    buf.seek(0)
    return base64.b64encode(buf.getvalue()).decode('utf-8')


def fig_ax_to_base64(fig_or_ax: Union[Figure, plt.Axes], is_ax: bool = False, fig_for_ax: Optional[Figure] = None) -> str:
    """Convert a matplotlib Figure or Axes to a base64 encoded string."""
    buf = io.BytesIO()
    if is_ax:
        if fig_for_ax is None:
            raise ValueError("fig_for_ax must be provided when saving an Axes object.")
        ax = fig_or_ax
        renderer = fig_for_ax.canvas.get_renderer()
        bbox = ax.get_tightbbox(renderer)
        if bbox:
            fig_for_ax.savefig(buf, format='png', bbox_inches=bbox, dpi=300)
        else:
            temp_fig_placeholder = plt.figure(figsize=(0.1, 0.1))
            temp_fig_placeholder.savefig(buf, format='png', dpi=300)
            plt.close(temp_fig_placeholder)
    else:
        fig = fig_or_ax
        fig.savefig(buf, format='png', bbox_inches='tight', dpi=300)
    
    buf.seek(0)
    img_base64 = base64.b64encode(buf.getvalue()).decode('utf-8')
    
    if not is_ax:
        plt.close(fig_or_ax)
    return img_base64


def save_figure_processing_subplots(
    fig: Figure, 
    base_path_key: str, 
    file_contents: dict[str, str], 
    logs: list[str],
    is_single_plot_preferred: bool = False
) -> None:
    """Save a figure, extracting subplots if multiple exist and single plot not preferred."""
    
    if not fig:
        logs.append(f"Warning: No figure provided for {base_path_key}")
        return

    try:
        if not fig.axes:
            logs.append(f"Warning: Figure for {base_path_key} contains no axes")
            plt.close(fig)
            return

        if is_single_plot_preferred or len(fig.axes) == 1:
            plot_path_key = f"{base_path_key}.png"
            file_contents[plot_path_key] = fig_ax_to_base64(fig)
            logs.append(f"Analysis visualization: {plot_path_key}")
        else:
            for i, ax in enumerate(fig.axes):
                subplot_path_key = f"{base_path_key}_subplot_{i}.png"
                try:
                    file_contents[subplot_path_key] = fig_ax_to_base64(ax, is_ax=True, fig_for_ax=fig)
                    logs.append(f"Subplot {i} visualization: {subplot_path_key}")
                except Exception as e_sub:
                    logs.append(f"Error processing subplot {i} for {base_path_key}: {e_sub}")
            plt.close(fig)
    except Exception as e_fig:
        logs.append(f"Error processing figure {base_path_key}: {e_fig}")
        if plt.fignum_exists(fig.number):
            plt.close(fig)


def df_to_csv_string(df: pd.DataFrame, index: bool = True) -> str:
    """Convert a pandas DataFrame to a CSV string."""
    return df.to_csv(index=index)


def apply_inverse_transformations(
    series: pd.Series,
    target_variable_code: str,
    variables_metadata: list[Variable],
    logs: list[str]
) -> pd.Series:
    """
    Apply inverse transformations to convert series back to original scale.
    
    Parameters:
        series: The transformed series to inverse transform
        target_variable_code: Code of the target variable
        variables_metadata: list of Variable objects containing transformation history
        logs: list to append transformation messages
    
    Returns:
        Series in original scale after applying inverse transformations
    """
    
    var_meta = next((v for v in variables_metadata if v.code == target_variable_code), None)
    if not var_meta or not var_meta.transform_history:
        logs.append(f"No transformation history found for {target_variable_code} - using series as is")
        return series

    transformed_series = series.copy()
    history = var_meta.transform_history
    
    logs.append(f"Applying inverse transformations for {target_variable_code}")
    
    # Apply transformations in reverse order
    for transform_info in reversed(history):
        transform_type = transform_info.transform_type
        params = transform_info.params
        
        try:
            if transform_type == "log":
                transformed_series = transformations_util.inverse_log_transform(transformed_series)
                logs.append(f"Applied inverse log transformation")
                
            elif transform_type == "sqrt":
                transformed_series = transformations_util.inverse_sqrt_transform(transformed_series)
                logs.append(f"Applied inverse square root transformation")
                
            elif transform_type == "box_cox":
                lambda_val = params.get("lambda_val")
                if lambda_val is not None:
                    transformed_series = transformations_util.inverse_box_cox_transform(transformed_series, lambda_val)
                    logs.append(f"Applied inverse Box-Cox transformation (lambda={lambda_val})")
                else:
                    logs.append(f"Warning: Lambda parameter missing for inverse Box-Cox transformation")
                    
            elif transform_type == "differencing":
                if 'head_values_for_inversion' in params:
                    head_values = params['head_values_for_inversion']
                    if isinstance(head_values, str):
                        try:
                            head_values = json.loads(head_values)
                        except json.JSONDecodeError:
                            logs.append(f"Error parsing head values for differencing inversion")
                            continue
                    
                    inversion_params = {
                        'd': params.get('d', 0),
                        'D': params.get('D', 0),
                        'm': params.get('m', 0),
                        'original_head_values': pd.Series(head_values) if head_values else None
                    }
                    
                    transformed_series = transformations_util.inverse_differencing(transformed_series, inversion_params)
                    logs.append(f"Applied inverse differencing (d={inversion_params['d']}, D={inversion_params['D']}, m={inversion_params['m']})")
                else:
                    logs.append(f"Warning: Head values missing for inverse differencing transformation")
                    
            elif transform_type == "standard_scale" or transform_type == "scaling":
                scaler_params = params.get("scaler_params")
                method = params.get("method", "standard")
                
                if scaler_params:
                    # This is a complex operation that requires specific implementation
                    # For now, we'll log a warning as robust scaler inversion needs careful handling
                    logs.append(f"Warning: Inverse scaling transformation requires specific implementation for {method} method")
                else:
                    logs.append(f"Warning: Scaler parameters missing for inverse scaling transformation")
                    
            else:
                logs.append(f"Warning: Unknown transformation type '{transform_type}' for inverse transformation")
                
        except Exception as e:
            logs.append(f"Error applying inverse transformation '{transform_type}': {str(e)}")
    
    return transformed_series