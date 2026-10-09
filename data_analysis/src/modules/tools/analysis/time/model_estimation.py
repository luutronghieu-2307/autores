import base64
import io
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from datetime import datetime
from statsmodels.tsa.statespace.sarimax import SARIMAX
from statsmodels.tsa.exponential_smoothing.ets import ETSModel
from statsmodels.tsa.api import VAR
from statsmodels.tsa.vector_ar.vecm import VECM

from typing import Any, Optional

from data_analysis.src.schemas.analyzer_states import Variable, ToolOutput, VariableType
from data_analysis.src.modules.tools.analysis.time.utils import model_helpers as model_helpers_util

# --- Helper Functions ---
def fig_to_base64(fig: Figure) -> str:
    """Converts a matplotlib Figure to a base64 encoded string."""
    buf = io.BytesIO()
    fig.savefig(buf, format='png', bbox_inches='tight')
    plt.close(fig) # Close the specific figure
    buf.seek(0)
    return base64.b64encode(buf.getvalue()).decode('utf-8')

def df_to_csv_string(df: pd.DataFrame, index: bool = False) -> str:
    """Converts a pandas DataFrame to a CSV string."""
    return df.to_csv(index=index)


# --- Tool 5: Model Estimation & Initial Evaluation ---
def run_model_estimation(
    data: pd.DataFrame,
    variables: list[Variable],
    params: dict
) -> tuple[ToolOutput, Optional[Any]]: # Returns ToolOutput and the fitted_model object
    """
    Tool 5: Fit the specified model and perform initial evaluation.
    """
    logs = []
    file_contents = {}
    tool_results = {}
    fitted_model = None

    # --- 1. Initialization and Parameter Extraction ---
    now = datetime.now()
    timestamp = f"{now.microsecond // 10000:02d}"
    base_output_name = params.get("output_name", "model_estimation")
    output_dir_id = f"{timestamp}_{base_output_name}"

    model_type = params.get('model_type')
    if not model_type:
        logs.append("Error: 'model_type' not specified in params.")
        return ToolOutput(results={}, logs=logs, file_contents=file_contents)

    logs.append(f"--- Starting Model Estimation: {model_type} ---")

    return_model = params.get('return_model', False)

    # --- 2. Data Preparation ---
    time_index_var = next((v for v in variables if v.variable_type == VariableType.TIME_INDEX), None)
    if not time_index_var:
        logs.append("Error: Time index variable not found in metadata.")
        return ToolOutput(results={}, logs=logs, file_contents=file_contents)
    time_index_col_name = time_index_var.code

    current_data = data.copy()
    if time_index_col_name not in current_data.columns and current_data.index.name != time_index_col_name :
         logs.append(f"Error: Time index column '{time_index_col_name}' not found in data columns or as index.")
         return ToolOutput(results={}, logs=logs, file_contents=file_contents)

    if time_index_col_name in current_data.columns and current_data.index.name != time_index_col_name:
        try:
            current_data[time_index_col_name] = pd.to_datetime(current_data[time_index_col_name])
            current_data = current_data.set_index(time_index_col_name)
        except Exception as e:
            logs.append(f"Error setting time index '{time_index_col_name}': {e}")
            return ToolOutput(results={}, logs=logs, file_contents=file_contents)

    if not isinstance(current_data.index, pd.DatetimeIndex):
        logs.append(f"Error: Index '{current_data.index.name}' is not a DatetimeIndex after processing.")
        return ToolOutput(results={}, logs=logs, file_contents=file_contents)

    if not current_data.index.is_monotonic_increasing:
        current_data = current_data.sort_index()
        logs.append("Data sorted by time index.")

    # Target and Exogenous Variables
    target_series = None
    exog_df = None

    if model_type in ["ARIMA", "SARIMAX", "ETS"]:
        target_variable_code = params.get('target_variable_code')
        if not target_variable_code or target_variable_code not in current_data.columns:
            logs.append(f"Error: Target variable '{target_variable_code}' not found or not specified for {model_type}.")
            return ToolOutput(results={}, logs=logs, file_contents=file_contents)
        target_series = current_data[target_variable_code].dropna()
        logs.append(f"Target variable for {model_type}: {target_variable_code}")
    elif model_type in ["VAR", "VECM"]:
        target_variables_codes = params.get('target_variables_codes', [])
        if not target_variables_codes or not all(c in current_data.columns for c in target_variables_codes):
            logs.append(f"Error: One or more target variables not found or not specified for {model_type}.")
            return ToolOutput(results={}, logs=logs, file_contents=file_contents)
        target_series = current_data[target_variables_codes].dropna() # This will be a DataFrame
        logs.append(f"Target variables for {model_type}: {', '.join(target_variables_codes)}")
    else:
        logs.append(f"Error: Unknown model_type '{model_type}'.")
        return ToolOutput(results={}, logs=logs, file_contents=file_contents)

    if target_series.empty:
        logs.append(f"Error: Target series/data for {model_type} is empty after dropping NaNs.")
        return ToolOutput(results={}, logs=logs, file_contents=file_contents)

    exog_variable_codes = params.get('exog_variable_codes', [])
    if exog_variable_codes:
        if not all(c in current_data.columns for c in exog_variable_codes):
            logs.append("Error: One or more exogenous variables not found in data.")
            return ToolOutput(results={}, logs=logs, file_contents=file_contents)
        # Align exog_df with target_series index
        exog_df = current_data.loc[target_series.index, exog_variable_codes].copy() # Ensure alignment
        if exog_df.isnull().any().any():
            # Simple ffill for exog, or could be an error/warning
            exog_df.fillna(method='ffill', inplace=True)
            exog_df.fillna(method='bfill', inplace=True) # Handle leading NaNs
            logs.append(f"Exogenous variables used: {', '.join(exog_variable_codes)}. NaNs handled by ffill/bfill.")
            if exog_df.isnull().any().any():
                 logs.append("Error: Exogenous variables still contain NaNs after fill. Please preprocess.")
                 return ToolOutput(results={}, logs=logs, file_contents=file_contents)
        else:
            logs.append(f"Exogenous variables used: {', '.join(exog_variable_codes)}")


    # --- 3. Model Fitting ---
    try:
        if model_type == "ARIMA" or model_type == "SARIMAX":
            order = tuple(params.get('model_order', (1,0,0)))
            seasonal_order = tuple(params.get('seasonal_order', (0,0,0,0)))
            trend = params.get('trend', 'c')
            enforce_stationarity = params.get('enforce_stationarity', True)
            enforce_invertibility = params.get('enforce_invertibility', True)

            # Use SARIMAX for flexibility with exog and seasonal components
            model = SARIMAX(target_series,
                            exog=exog_df,
                            order=order,
                            seasonal_order=seasonal_order,
                            trend=trend,
                            enforce_stationarity=enforce_stationarity,
                            enforce_invertibility=enforce_invertibility)
            fitted_model = model.fit(disp=False)
            logs.append(f"{model_type} model fitted with order={order}, seasonal_order={seasonal_order}, trend='{trend}'.")

        elif model_type == "ETS":
            ets_params = params.get('ets_params', {})
            error = ets_params.get('error', 'add')
            trend = ets_params.get('trend', None)
            seasonal = ets_params.get('seasonal', None)
            damped_trend = ets_params.get('damped_trend', False)
            seasonal_periods = ets_params.get('seasonal_periods', None)

            model = ETSModel(target_series,
                             error=error, trend=trend, seasonal=seasonal,
                             damped_trend=damped_trend, seasonal_periods=seasonal_periods,
                             initialization_method='estimated')
            fitted_model = model.fit(disp=False)
            logs.append(f"ETS model fitted with error='{error}', trend='{trend}', seasonal='{seasonal}'.")

        elif model_type == "VAR":
            lags = params.get('var_lags') # Should be an int, determined by Tool 4
            trend_var = params.get('trend', 'c') # 'n', 'c', 'ct', 't'
            if lags is None:
                logs.append("Error: 'var_lags' not specified for VAR model.")
                return ToolOutput(results={}, logs=logs, file_contents=file_contents)
            model = VAR(target_series, exog=exog_df, dates=target_series.index, freq=target_series.index.freqstr)
            fitted_model = model.fit(maxlags=lags, trend=trend_var, ic=None) # Fit with specific lags
            logs.append(f"VAR model fitted with {fitted_model.k_ar} lags, trend='{trend_var}'.")


        elif model_type == "VECM":
            vecm_params = params.get('vecm_params', {})
            k_ar_diff = vecm_params.get('k_ar_diff') # Lag order in differences
            coint_rank = vecm_params.get('coint_rank') # Number of cointegrating relationships
            deterministic = vecm_params.get('deterministic', 'ci') # e.g., 'n', 'co', 'ci', 'lo', 'li'

            if k_ar_diff is None or coint_rank is None:
                logs.append("Error: 'k_ar_diff' or 'coint_rank' not specified for VECM model.")
                return ToolOutput(results={}, logs=logs, file_contents=file_contents)

            model = VECM(target_series, exog=exog_df, dates=target_series.index, freq=target_series.index.freqstr,
                         k_ar_diff=k_ar_diff, coint_rank=coint_rank, deterministic=deterministic)
            fitted_model = model.fit()
            logs.append(f"VECM model fitted with k_ar_diff={k_ar_diff}, coint_rank={coint_rank}, deterministic='{deterministic}'.")

        else: # Should have been caught earlier
            logs.append(f"Error: Model type '{model_type}' not supported for fitting.")
            return ToolOutput(results={}, logs=logs, file_contents=file_contents)

    except Exception as e:
        logs.append(f"Error fitting {model_type} model: {e}")
        return ToolOutput(results={"error": str(e)}, logs=logs, file_contents=file_contents)

    # --- 4. Model Evaluation & Reporting ---
    if fitted_model:
        logs.append("Model fitting successful. Generating summary...")
        try:
            summary_text = fitted_model.summary().as_text()
            summary_path = f"{output_dir_id}/model_summary.txt"
            file_contents[summary_path] = summary_text
            logs.append(f"Full model summary saved to: `{summary_path}`")

            # Parse summary tables
            parsed_summary_dfs = model_helpers_util.format_statsmodels_summary_to_df(fitted_model.summary())
            tool_results['parsed_summary'] = {}
            for name, df_table in parsed_summary_dfs.items():
                if not df_table.empty:
                    csv_str = df_to_csv_string(df_table, index=True) # Statsmodels summaries often have meaningful index
                    table_path = f"{output_dir_id}/{name}.csv"
                    file_contents[table_path] = csv_str
                    logs.append(f"Parsed summary table '{name}' saved to: `{table_path}`")
                    tool_results['parsed_summary'][name] = df_table.to_dict(orient='split') # For JSON serializable results

            # Extract key parameters and fit statistics
            extracted_params = model_helpers_util.extract_fitted_model_params(fitted_model)
            tool_results['model_parameters'] = extracted_params
            logs.append(f"Extracted model parameters: {extracted_params}")

            # Basic interpretation from coefficients table (if exists)
            if 'coefficients' in parsed_summary_dfs and not parsed_summary_dfs['coefficients'].empty:
                coeffs_df = parsed_summary_dfs['coefficients']
                logs.append("\nCoefficients Summary:")
                significant_coeffs = []
                for idx, row in coeffs_df.iterrows():
                    p_value_col = next((col for col in ['P>|t|', 'P>|z|'] if col in row.index), None)
                    if p_value_col and pd.notna(row[p_value_col]):
                        p_val = row[p_value_col]
                        is_sig = p_val < 0.05 # Common significance level
                        logs.append(f"- {idx}: Coef={row.get('coef', row.get(coeffs_df.columns[0], 'N/A')):.4f}, P-value={p_val:.4f} ({'Significant' if is_sig else 'Not Significant'})")
                        if is_sig:
                            significant_coeffs.append(idx)
                tool_results['significant_coefficients'] = significant_coeffs
            else:
                logs.append("Coefficient table not found or empty in parsed summary.")


            # Note any immediate concerns (example)
            if 'coefficients' in parsed_summary_dfs and not parsed_summary_dfs['coefficients'].empty:
                coeffs_df = parsed_summary_dfs['coefficients']
                p_value_col_name = next((col for col in ['P>|t|', 'P>|z|'] if col in coeffs_df.columns), None)
                if p_value_col_name:
                    num_coeffs = len(coeffs_df)
                    num_insignificant = (coeffs_df[p_value_col_name] >= 0.05).sum()
                    if num_insignificant > num_coeffs / 2 and num_coeffs > 1: # Heuristic
                        logs.append(f"Warning: Many ({num_insignificant}/{num_coeffs}) coefficients are not statistically significant at the 0.05 level.")
                        tool_results['warnings'] = tool_results.get('warnings', []) + ["Many insignificant coefficients."]

        except Exception as e:
            logs.append(f"Error generating model summary/report: {e}")
            tool_results['reporting_error'] = str(e)
    else:
        logs.append("Model fitting failed. No summary to generate.")
        # This case should have been returned earlier

    # --- 5. Final Output ---
    if return_model:
        return fitted_model
    
    return ToolOutput(results=tool_results, logs=logs, file_contents=file_contents)
