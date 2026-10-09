import pandas as pd
import numpy as np
import statsmodels.api as sm
from statsmodels.tsa.stattools import acf, pacf
from statsmodels.tsa.arima.model import ARIMA, ARIMAResultsWrapper
from statsmodels.tsa.statespace.sarimax import SARIMAXResultsWrapper
from statsmodels.tsa.exponential_smoothing.ets import ETSModel, ETSResultsWrapper
from statsmodels.tsa.api import VAR
from statsmodels.tsa.vector_ar.var_model import VARResults
from statsmodels.tsa.vector_ar.vecm import VECMResults
from statsmodels.stats.outliers_influence import variance_inflation_factor
from sklearn.metrics import mean_absolute_error, mean_squared_error, mean_absolute_percentage_error
from typing import Optional, Any, Union, Sequence
import traceback

def calculate_acf_pacf(
    series: pd.Series,
    nlags: Optional[int] = None,
    alpha: Optional[float] = None # Significance level for confidence intervals
) -> dict[str, Union[np.ndarray, Optional[np.ndarray]]]:
    """
    Calculates ACF and PACF values and optional confidence intervals.
    Returns a dictionary with 'acf_values', 'acf_confint', 'pacf_values', 'pacf_confint'.
    """
    if not isinstance(series, pd.Series):
        raise TypeError("Input 'series' must be a pandas Series.")
    
    series_dropped_na = series.dropna()
    
    acf_vals, acf_ci = acf(series_dropped_na, nlags=nlags, alpha=alpha, fft=False) # fft=False for more robust results with NaNs
    pacf_vals, pacf_ci = pacf(series_dropped_na, nlags=nlags, alpha=alpha, method='ywm')

    return {
        'acf_values': acf_vals,
        'acf_confint': acf_ci, # Array of [lower, upper] bounds
        'pacf_values': pacf_vals,
        'pacf_confint': pacf_ci # Array of [lower, upper] bounds
    }

def get_information_criteria_for_arima_orders(
    series: pd.Series,
    p_range: Sequence[int],
    d_range: Sequence[int],
    q_range: Sequence[int],
    P_range: Optional[Sequence[int]] = None,
    D_range: Optional[Sequence[int]] = None,
    Q_range: Optional[Sequence[int]] = None,
    m: int = 0,
    exog: Optional[pd.DataFrame] = None,
    trend: str = 'c' # User's preferred trend
) -> pd.DataFrame:
    """
    Iterates through (S)ARIMA(X) orders, fits models, and collects AIC, BIC.
    Dynamically adjusts the trend parameter to avoid invalid model specifications
    when differencing is applied.
    """
    if not isinstance(series, pd.Series):
        raise TypeError("Input 'series' must be a pandas Series.")
    
    results = []
    series_dropna = series.dropna()
    
    aligned_exog = None
    if exog is not None:
        aligned_exog = exog.reindex(series_dropna.index)

    P_range_loop = P_range if P_range is not None and m > 1 else [0]
    D_range_loop = D_range if D_range is not None and m > 1 else [0]
    Q_range_loop = Q_range if Q_range is not None and m > 1 else [0]

    for p_val in p_range:
        for d_val in d_range:
            for q_val in q_range:
                for P_val in P_range_loop:
                    for D_val in D_range_loop:
                        for Q_val in Q_range_loop:
                            order = (p_val, d_val, q_val)
                            seasonal_order = (P_val, D_val, Q_val, m)
                            
                            if m <= 1 and (P_val > 0 or D_val > 0 or Q_val > 0):
                                continue

                            result_row = {
                                'p': p_val, 'd': d_val, 'q': q_val,
                                'P': P_val, 'D': D_val, 'Q': Q_val, 'm': m,
                                'AIC': np.nan, 'BIC': np.nan, 'LogLikelihood': np.nan
                            }

                            # --- CORE FIX: Dynamically adjust the trend based on differencing ---
                            total_diff_order = d_val + D_val
                            current_trend = trend # Start with user's preference
                            
                            if total_diff_order >= 2 and current_trend in ['c', 't']:
                                # If d+D >= 2, both constant and linear trends are invalid. Force 'n'.
                                current_trend = 'n'
                            elif total_diff_order == 1 and current_trend == 'c':
                                # If d+D = 1, constant trend is invalid. Force 'n'.
                                # A linear trend 't' would be valid here, but 'n' is safer for a general search.
                                current_trend = 'n'
                            # --- END OF CORE FIX ---

                            try:
                                model = ARIMA(
                                    endog=series_dropna, 
                                    exog=aligned_exog, 
                                    order=order, 
                                    seasonal_order=seasonal_order,
                                    trend=current_trend # Use the adjusted trend
                                )
                                
                                model_fit = model.fit(method_kwargs={"warn_convergence": False})
                                
                                result_row['AIC'] = model_fit.aic
                                result_row['BIC'] = model_fit.bic
                                result_row['LogLikelihood'] = model_fit.llf

                            except Exception:
                                # Keep the traceback for any other unexpected errors
                                print(f"--- ERROR FITTING SARIMAX{order}{seasonal_order} with trend '{current_trend}' ---")
                                traceback.print_exc()
                                print("----------------------------------------------------")
                                pass
                            
                            results.append(result_row)
                                    
    return pd.DataFrame(results)

def get_information_criteria_for_ets(
    series: pd.Series,
    error_types: list[str] = ["add", "mul"],
    trend_types: list[str] = ["add", "mul", None],
    seasonal_types: list[str] = ["add", "mul", None],
    seasonal_periods: Optional[int] = None,
    damped_trends: list[bool] = [False, True],
    force_seasonal: bool = False # <-- NEW PARAMETER
) -> pd.DataFrame:
    """
    Iterates through ETS model combinations and collects AIC, BIC.
    Returns a DataFrame with model components and their AIC/BIC.
    """
    if not isinstance(series, pd.Series):
        raise TypeError("Input 'series' must be a pandas Series.")
    
    results = []
    series_dropna = series.dropna()
    
    use_multiplicative = any(s_type == "mul" for s_type in error_types + trend_types + seasonal_types)
    if use_multiplicative and (series_dropna <= 0).any():
        print("Warning: Multiplicative ETS components require positive series. Skipping multiplicative models or use Box-Cox.")
        error_types = [e for e in error_types if e != "mul"]
        trend_types = [t for t in trend_types if t != "mul"]
        seasonal_types = [s for s in seasonal_types if s != "mul"]

    # --- FIX: Implement force_seasonal logic ---
    current_seasonal_types = seasonal_types
    if force_seasonal:
        # If forcing seasonality, remove None from the list of types to check.
        current_seasonal_types = [s_type for s_type in seasonal_types if s_type is not None]
        if not current_seasonal_types:
            print("Warning: `force_seasonal=True` but no seasonal types (e.g., 'add', 'mul') were provided to search. No models will be fit.")
            return pd.DataFrame()

    for error in error_types:
        for trend in trend_types:
            # Use the potentially filtered list of seasonal types
            for seasonal in current_seasonal_types:
                for damped in damped_trends:
                    if trend is None and damped:
                        continue
                    if seasonal is not None and (seasonal_periods is None or seasonal_periods <= 1):
                        continue

                    model_name_parts = [error, trend if trend else 'N', seasonal if seasonal else 'N']
                    if damped and trend:
                        model_name_parts.insert(2, 'damped')
                    model_name = f"ETS({','.join(filter(None, model_name_parts))})"
                    
                    try:
                        current_seasonal_periods = seasonal_periods if seasonal is not None else None
                        
                        model = ETSModel(
                            series_dropna,
                            error=error,
                            trend=trend,
                            seasonal=seasonal,
                            damped_trend=damped if trend is not None else False,
                            seasonal_periods=current_seasonal_periods,
                            initialization_method='estimated'
                        )
                        model_fit = model.fit(disp=False)
                        results.append({
                            'Model': model_name,
                            'Error': error, 'Trend': trend, 'Damped': damped if trend is not None else False,
                            'Seasonal': seasonal, 'Seasonal_Periods': current_seasonal_periods,
                            'AIC': model_fit.aic, 'BIC': model_fit.bic, 'LogLikelihood': model_fit.llf
                        })
                    except Exception:
                        # This block will now only be hit for actual, unexpected errors
                        print(f"--- ERROR FITTING ETS Model {model_name} ---")
                        traceback.print_exc()
                        print("---------------------------------------------")
                        results.append({
                            'Model': model_name,
                            'Error': error, 'Trend': trend, 'Damped': damped if trend is not None else False,
                            'Seasonal': seasonal, 'Seasonal_Periods': current_seasonal_periods,
                            'AIC': np.nan, 'BIC': np.nan, 'LogLikelihood': np.nan
                        })
                        
    return pd.DataFrame(results)

def get_var_lag_order_selection(
    data: pd.DataFrame, # Multivariate time series
    maxlags: Optional[int] = None,
    ic: list[str] = ['aic', 'bic', 'hqic', 'fpe'], # Information criteria to report
    trend: str = 'c' # 'n', 'c', 'ct', 't'
) -> dict[str, Any]:
    """
    Uses statsmodels VAR to select optimal lag order.
    Returns a dictionary containing the selected lag for each criterion.
    The full selection object is also returned for detailed inspection.
    """
    if not isinstance(data, pd.DataFrame):
        raise TypeError("Input 'data' must be a pandas DataFrame.")
    if data.isnull().any().any():
        raise ValueError("Input DataFrame for VAR lag selection should not contain NaNs.")

    # The VAR model is instantiated without the trend.
    model = VAR(data)
    
    lag_selection_results = model.select_order(maxlags=maxlags, trend=trend)
    
    selected_lags = {}
    for criterion in ic:
        try:
            selected_lags[criterion] = getattr(lag_selection_results, criterion)
        except AttributeError:
            selected_lags[criterion] = f"Criterion {criterion} not found in results."
            
    return {
        "selected_lags_by_criterion": selected_lags,
        "full_selection_summary": str(lag_selection_results.summary()), # Text summary
        "lag_selection_object": lag_selection_results # The actual object
    }

def format_statsmodels_summary_to_df(
    summary_object: sm.iolib.summary.Summary
) -> dict[str, pd.DataFrame]:
    """
    Parses statsmodels summary tables (typically coefficients, model overview)
    into pandas DataFrames.
    Returns a dictionary of DataFrames, e.g., {'coefficients': df1, 'model_overview': df2}.
    """
    dfs = {}
    if hasattr(summary_object, 'tables'):
        for i, table in enumerate(summary_object.tables):
            try:
                # SimpleTable to HTML, then to DataFrame
                df = pd.read_html(table.as_html(), header=0, index_col=0)[0]
                
                # Try to give meaningful names
                if i == 0: # Often model overview or general stats
                    dfs['summary_table_0_overview'] = df
                elif i == 1: # Often coefficients
                    dfs['coefficients'] = df
                elif i == 2: # Often diagnostics or other stats
                    dfs['summary_table_2_diagnostics'] = df
                else:
                    dfs[f'summary_table_{i}'] = df
            except Exception as e:
                # print(f"Could not parse table {i} from summary: {e}")
                # Sometimes a table might be just text, try to capture it
                try:
                    dfs[f'summary_table_{i}_text'] = pd.DataFrame([str(table)])
                except:
                    pass # Give up on this table
    else:
        # print("Summary object does not have 'tables' attribute.")
        dfs['raw_summary_text'] = pd.DataFrame([str(summary_object)])
        
    return dfs


def calculate_vif(exog_df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculates Variance Inflation Factor (VIF) for exogenous variables.
    Requires exog_df to have at least two columns (after adding a constant).
    """
    if not isinstance(exog_df, pd.DataFrame):
        raise TypeError("Input 'exog_df' must be a pandas DataFrame.")
    if exog_df.empty:
        return pd.DataFrame(columns=['Variable', 'VIF'])
    
    # Add constant for VIF calculation if not present
    # VIF is calculated for each variable in the context of others
    # Ensure no NaN values
    exog_clean = exog_df.dropna()
    if exog_clean.shape[0] < 2 or exog_clean.shape[1] < 1: # Need at least 2 obs and 1 var
        # print("Not enough data or variables for VIF calculation after dropping NaNs.")
        return pd.DataFrame({'Variable': exog_clean.columns, 'VIF': np.nan})

    # If only one variable, VIF is not meaningful in the usual sense (or can be considered 1)
    if exog_clean.shape[1] == 1:
        vif_data = pd.DataFrame()
        vif_data["Variable"] = exog_clean.columns
        vif_data["VIF"] = 1.0 # Or np.nan, depending on interpretation
        return vif_data.set_index("Variable")


    # Add constant for VIF calculation (standard practice)
    # The constant itself is not included in VIF results
    X_with_const = sm.add_constant(exog_clean, prepend=True, has_constant='skip')
    
    vif_data = pd.DataFrame()
    vif_data["Variable"] = X_with_const.columns[1:] # Exclude the constant
    vif_data["VIF"] = [variance_inflation_factor(X_with_const.values, i) for i in range(1, X_with_const.shape[1])]
    
    return vif_data.set_index("Variable")


def calculate_accuracy_metrics(
    y_true: pd.Series,
    y_pred: pd.Series
) -> dict[str, float]:
    """
    Calculates MAE, MSE, RMSE, MAPE.
    Handles potential NaNs by aligning and dropping.
    """
    if not isinstance(y_true, pd.Series) or not isinstance(y_pred, pd.Series):
        raise TypeError("Inputs 'y_true' and 'y_pred' must be pandas Series.")

    # Align series and drop NaNs from either
    df_aligned = pd.concat([y_true.rename('true'), y_pred.rename('pred')], axis=1).dropna()
    
    if df_aligned.empty:
        # print("No common valid data points between y_true and y_pred for accuracy calculation.")
        return {'mae': np.nan, 'mse': np.nan, 'rmse': np.nan, 'mape': np.nan, 'num_obs': 0}

    true_aligned = df_aligned['true']
    pred_aligned = df_aligned['pred']

    metrics = {}
    metrics['mae'] = mean_absolute_error(true_aligned, pred_aligned)
    metrics['mse'] = mean_squared_error(true_aligned, pred_aligned)
    metrics['rmse'] = np.sqrt(metrics['mse'])
    
    # MAPE: Handle division by zero if true_aligned contains zeros
    # Replace zeros in true_aligned with a very small number to avoid division by zero,
    # or filter them out. Filtering is generally better.
    non_zero_true = true_aligned[true_aligned != 0]
    non_zero_pred = pred_aligned[true_aligned != 0] # Align pred with non-zero true
    
    if not non_zero_true.empty:
        metrics['mape'] = mean_absolute_percentage_error(non_zero_true, non_zero_pred) * 100 # As percentage
    else:
        metrics['mape'] = np.nan # Or 0, or indicate all true values were zero
    
    metrics['num_obs'] = len(df_aligned)
    return metrics


def extract_fitted_model_params(fitted_model: Any) -> dict[str, Any]:
    """
    Extracts key parameters from a fitted statsmodels object.
    This is a generic helper and might need specific implementations
    for different model types if parameters are not standard attributes.
    """
    params = {}
    model_type = type(fitted_model).__name__
    params['model_type'] = model_type

    if isinstance(fitted_model, ARIMAResultsWrapper):
        params['order'] = fitted_model.model.order
        params['seasonal_order'] = fitted_model.model.seasonal_order
        params['trend'] = fitted_model.model.trend
        params['coefficients'] = fitted_model.params.to_dict()
        params['aic'] = fitted_model.aic
        params['bic'] = fitted_model.bic
        params['log_likelihood'] = fitted_model.llf
    elif isinstance(fitted_model, SARIMAXResultsWrapper):
        params['order'] = fitted_model.model.order
        params['seasonal_order'] = fitted_model.model.seasonal_order
        params['trend'] = fitted_model.model.trend
        params['coefficients'] = fitted_model.params.to_dict()
        params['aic'] = fitted_model.aic
        params['bic'] = fitted_model.bic
        params['log_likelihood'] = fitted_model.llf
    elif isinstance(fitted_model, ETSResultsWrapper):
        params['error_comp'] = fitted_model.model.error
        params['trend_comp'] = fitted_model.model.trend
        params['seasonal_comp'] = fitted_model.model.seasonal
        params['damped_trend'] = fitted_model.model.damped_trend
        params['seasonal_periods'] = fitted_model.model.seasonal_periods
        params['coefficients'] = fitted_model.params.to_dict()
        params['aic'] = fitted_model.aic
        params['bic'] = fitted_model.bic
        params['log_likelihood'] = fitted_model.llf
    elif isinstance(fitted_model, VARResults):
        params['lags'] = fitted_model.k_ar
        params['trend'] = fitted_model.model.trend
        params['aic'] = fitted_model.aic
        params['bic'] = fitted_model.bic
        params['log_likelihood'] = fitted_model.llf
        params['hqic'] = fitted_model.hqic
        params['fpe'] = fitted_model.fpe
    elif isinstance(fitted_model, VECMResults):
        params['k_ar_diff'] = fitted_model.k_ar_diff
        params['coint_rank'] = fitted_model.coint_rank
        params['det_terms_in_ce'] = fitted_model.det_terms_in_ce
        params['det_terms_outside_ce'] = fitted_model.det_terms_outside_ce
        params['aic'] = fitted_model.aic
        params['bic'] = fitted_model.bic
        params['log_likelihood'] = fitted_model.llf
    else:
        if hasattr(fitted_model, 'params'):
            params['coefficients'] = fitted_model.params.to_dict() if isinstance(fitted_model.params, pd.Series) else fitted_model.params
        if hasattr(fitted_model, 'aic'):
            params['aic'] = fitted_model.aic
        if hasattr(fitted_model, 'bic'):
            params['bic'] = fitted_model.bic
        if hasattr(fitted_model, 'llf'):
            params['log_likelihood'] = fitted_model.llf

    return params


def generate_future_exog_for_forecasting(
    exog_history: pd.DataFrame,
    forecast_horizon: int,
    method: str = 'last_known', # 'last_known', 'mean', 'scenario'
    scenario_values: Optional[dict[str, list[float]]] = None # {col_name: [val1, val2, ...]}
) -> Optional[pd.DataFrame]:
    """
    Helper to create future exogenous variables for forecasting.
    - 'last_known': Repeats the last known value for each exogenous variable.
    - 'mean': Uses the historical mean of each exogenous variable.
    - 'scenario': Uses user-provided scenario values.
    
    Returns a DataFrame with future exogenous values, indexed appropriately.
    The index should align with the forecast period.
    """
    if exog_history is None or exog_history.empty:
        return None # No exogenous variables to project
        
    if not isinstance(exog_history, pd.DataFrame):
        raise TypeError("exog_history must be a pandas DataFrame.")
    if not isinstance(forecast_horizon, int) or forecast_horizon <= 0:
        raise ValueError("forecast_horizon must be a positive integer.")

    last_date = exog_history.index[-1]
    # Assuming exog_history has a DatetimeIndex with a frequency
    freq = pd.infer_freq(exog_history.index)
    if freq is None and len(exog_history.index) > 1: # Try to infer from differences
        inferred_freq = pd.tseries.frequencies.to_offset((exog_history.index[1:] - exog_history.index[:-1]).min())
        if inferred_freq:
            freq = inferred_freq
    
    if freq is None:
        raise ValueError("Could not infer frequency from exog_history index. Please ensure it has a defined frequency.")

    future_index = pd.date_range(start=last_date + pd.tseries.frequencies.to_offset(freq),
                                 periods=forecast_horizon, freq=freq)
    
    future_exog_df = pd.DataFrame(index=future_index, columns=exog_history.columns)

    if method == 'last_known':
        for col in exog_history.columns:
            future_exog_df[col] = exog_history[col].iloc[-1]
    elif method == 'mean':
        for col in exog_history.columns:
            future_exog_df[col] = exog_history[col].mean()
    elif method == 'scenario':
        if scenario_values is None:
            raise ValueError("scenario_values must be provided for method 'scenario'.")
        for col, values in scenario_values.items():
            if col not in future_exog_df.columns:
                print(f"Warning: Scenario variable '{col}' not in exog_history. Skipping.")
                continue
            if len(values) != forecast_horizon:
                raise ValueError(f"Length of scenario values for '{col}' ({len(values)}) "
                                 f"does not match forecast_horizon ({forecast_horizon}).")
            future_exog_df[col] = values
    else:
        raise ValueError(f"Unknown method for generating future exog: {method}")
        
    return future_exog_df