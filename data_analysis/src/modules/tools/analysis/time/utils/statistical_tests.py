import pandas as pd
from statsmodels.tsa.stattools import adfuller, kpss, grangercausalitytests
from statsmodels.stats.diagnostic import acorr_ljungbox, het_breuschpagan
from statsmodels.tsa.vector_ar.vecm import coint_johansen, JohansenTestResult
from statsmodels.tsa.vector_ar.var_model import VARResultsWrapper
import statsmodels.api as sm

from scipy import stats
from typing import Union, Optional, Any

# try:
#     from arch.unitroot import CanovaHansen
#     ARCH_AVAILABLE = True
# except ImportError:
#     ARCH_AVAILABLE = False
#     CanovaHansen = None # Placeholder

DEFAULT_TRANSLATIONS = {
    "en": {
        "adf_stationary": "Reject H0 at {sig}% significance. Series is likely stationary (p-value: {p:.4f}).",
        "adf_non_stationary": "Fail to reject H0 at {sig}% significance. Series is likely non-stationary (p-value: {p:.4f}).",
        "kpss_stationary": "Fail to reject H0 at {sig}% significance. Series is likely stationary (p-value: {p}).",
        "kpss_non_stationary": "Reject H0 at {sig}% significance. Series is likely non-stationary (p-value: {p}).",
        "shapiro_normal": "Fail to reject H0 at {sig}% significance. Residuals are likely normally distributed (p-value: {p:.4f}).",
        "shapiro_non_normal": "Reject H0 at {sig}% significance. Residuals are likely not normally distributed (p-value: {p:.4f}).",
        "shapiro_insufficient_data": "Not enough data points ( < 3) for Shapiro-Wilk test.",
        "bp_homoscedastic": "Fail to reject H0 at {sig}% significance. Homoscedasticity is likely present (F-test p-value: {p:.4f}).",
        "bp_heteroscedastic": "Reject H0 at {sig}% significance. Heteroscedasticity is likely present (F-test p-value: {p:.4f}).",
        "bp_insufficient_data": "Not enough common non-NaN data points for Breusch-Pagan test.",
        "var_stable": "Model is stable.",
        "var_unstable": "Model is unstable (some roots are on or outside the unit circle)."
    },
    "vi": {
        "adf_stationary": "Bác bỏ H0 ở mức ý nghĩa {sig}%. Chuỗi có khả năng là chuỗi dừng (p-value: {p:.4f}).",
        "adf_non_stationary": "Chưa đủ cơ sở bác bỏ H0 ở mức ý nghĩa {sig}%. Chuỗi có khả năng là chuỗi không dừng (p-value: {p:.4f}).",
        "kpss_stationary": "Chưa đủ cơ sở bác bỏ H0 ở mức ý nghĩa {sig}%. Chuỗi có khả năng là chuỗi dừng (p-value: {p}).",
        "kpss_non_stationary": "Bác bỏ H0 ở mức ý nghĩa {sig}%. Chuỗi có khả năng là chuỗi không dừng (p-value: {p}).",
        "shapiro_normal": "Chưa đủ cơ sở bác bỏ H0 ở mức ý nghĩa {sig}%. Phần dư có khả năng phân phối chuẩn (p-value: {p:.4f}).",
        "shapiro_non_normal": "Bác bỏ H0 ở mức ý nghĩa {sig}%. Phần dư có khả năng không phân phối chuẩn (p-value: {p:.4f}).",
        "shapiro_insufficient_data": "Không đủ điểm dữ liệu ( < 3) cho kiểm định Shapiro-Wilk.",
        "bp_homoscedastic": "Chưa đủ cơ sở bác bỏ H0 ở mức ý nghĩa {sig}%. Có khả năng có phương sai sai số không đổi (F-test p-value: {p:.4f}).",
        "bp_heteroscedastic": "Bác bỏ H0 ở mức ý nghĩa {sig}%. Có khả năng có phương sai sai số thay đổi (F-test p-value: {p:.4f}).",
        "bp_insufficient_data": "Không đủ điểm dữ liệu chung không phải NaN cho kiểm định Breusch-Pagan.",
        "var_stable": "Mô hình ổn định.",
        "var_unstable": "Mô hình không ổn định (một số nghiệm nằm trên hoặc ngoài vòng tròn đơn vị)."
    }
}

def run_adf_test(
    series: pd.Series,
    regression: str = 'c',
    autolag: str = 'AIC',
    significance_level: float = 0.05,
    t: Optional[dict] = None
) -> dict[str, Any]:
    """
    Performs the Augmented Dickey-Fuller test for stationarity.
    H0: The series has a unit root (non-stationary).
    H1: The series does not have a unit root (stationary).
    """
    if not isinstance(series, pd.Series):
        raise TypeError("Input 'series' must be a pandas Series.")
    
    # Use default translations if not provided
    if t is None:
        t = DEFAULT_TRANSLATIONS["en"]

    result = adfuller(series.dropna(), regression=regression, autolag=autolag)
    output = {
        'test_statistic': result[0],
        'p_value': result[1],
        'lags_used': result[2],
        'n_observations': result[3],
        'critical_values': result[4],
        'autolag_method': autolag,
        'regression_type': regression
    }
    if result[1] <= significance_level:
        output['interpretation'] = t.get("adf_stationary", "Reject H0 at {sig}% significance. Series is likely stationary (p-value: {p:.4f}).").format(sig=significance_level*100, p=result[1])
    else:
        output['interpretation'] = t.get("adf_non_stationary", "Fail to reject H0 at {sig}% significance. Series is likely non-stationary (p-value: {p:.4f}).").format(sig=significance_level*100, p=result[1])
    return output

def run_kpss_test(
    series: pd.Series,
    regression: str = 'c',
    nlags: str = 'auto',
    significance_level: float = 0.05,
    t: Optional[dict] = None
) -> dict[str, Any]:
    """
    Performs the KPSS test for stationarity.
    H0: The series is trend-stationary (or level-stationary if regression='c').
    H1: The series has a unit root (non-stationary).
    Note: Interpretation is opposite to ADF.
    """
    if not isinstance(series, pd.Series):
        raise TypeError("Input 'series' must be a pandas Series.")
        
    # Use default translations if not provided
    if t is None:
        t = DEFAULT_TRANSLATIONS["en"]

    # KPSS test returns: kpss_stat, p_value, lags, crit_values
    # For p-value, statsmodels' KPSS returns a string like '<0.01' or '>0.1'.
    # We need to handle this for comparison.
    # If p-value is, e.g., '<0.01', it means it's very small.
    # If p-value is, e.g., '>0.1', it means it's large.
    
    statistic, p_value_raw, lags, crit = kpss(series.dropna(), regression=regression, nlags=nlags)
    
    p_value_numeric = None
    if isinstance(p_value_raw, str):
        if '>' in p_value_raw:
            p_value_numeric = float(p_value_raw.replace('>', '')) + 1e-6 # Slightly above for comparison
        elif '<' in p_value_raw:
            p_value_numeric = float(p_value_raw.replace('<', '')) - 1e-6 # Slightly below for comparison
    else:
        p_value_numeric = p_value_raw

    output = {
        'test_statistic': statistic,
        'p_value_reported': p_value_raw, # The raw p-value string from kpss
        'p_value_numeric_for_decision': p_value_numeric, # A numeric version for decision making
        'lags_used': lags,
        'critical_values': crit,
        'regression_type': regression,
        'nlags_method': nlags
    }

    # Interpretation: If p-value < sig_level, reject H0 (series is non-stationary)
    if p_value_numeric is not None and p_value_numeric < significance_level:
        output['interpretation'] = t.get("kpss_non_stationary", "Reject H0 at {sig}% significance. Series is likely non-stationary (p-value: {p}).").format(sig=significance_level*100, p=p_value_raw)
    else: # p_value_numeric >= significance_level or p_value_numeric is None (e.g. if p_value_raw was just a number)
        if p_value_numeric is None and p_value_raw >= significance_level: # if p_value_raw was already numeric
             output['interpretation'] = t.get("kpss_stationary", "Fail to reject H0 at {sig}% significance. Series is likely stationary (p-value: {p:.4f}).").format(sig=significance_level*100, p=p_value_raw)
        elif p_value_numeric is not None and p_value_numeric >= significance_level:
             output['interpretation'] = t.get("kpss_stationary", "Fail to reject H0 at {sig}% significance. Series is likely stationary (p-value: {p}).").format(sig=significance_level*100, p=p_value_raw)
        else: # Covers cases like p_value_raw = '<0.01' and sig_level = 0.05 (reject H0)
             output['interpretation'] = t.get("kpss_non_stationary", "Reject H0 at {sig}% significance. Series is likely non-stationary (p-value: {p}).").format(sig=significance_level*100, p=p_value_raw)

    return output


# def run_canova_hansen_test(
#     series: pd.Series,
#     seasonal_period: int,
#     test_type: str = "joint", # "joint", "individual"
#     significance_level: float = 0.05
# ) -> dict[str, Any]:
#     """
#     Performs the Canova-Hansen test for seasonal stationarity.
#     Requires the 'arch' library.
#     H0: The series is seasonally stationary.
#     H1: The series has a seasonal unit root (seasonally non-stationary).
#     """
#     if not ARCH_AVAILABLE:
#         return {"error": "arch library not installed. Canova-Hansen test cannot be run."}
#     if not isinstance(series, pd.Series):
#         raise TypeError("Input 'series' must be a pandas Series.")
#     if not isinstance(seasonal_period, int) or seasonal_period <= 1:
#         raise ValueError("seasonal_period must be an integer greater than 1.")

#     ch_test = CanovaHansen(series.dropna(), lags=0, trend='c', seasonal_dummies=True, period=seasonal_period)
    
#     # The test statistic and p-value depend on the test_type
#     # The `arch` library's CanovaHansen result object might not directly give a single p-value for 'joint'
#     # It provides individual frequency p-values.
#     # For simplicity, we'll report the main statistic and its p-value if available,
#     # or guide the user to interpret based on critical values.
#     # The `summary()` method of `ch_test` provides a good overview.
#     # Let's try to extract key info.
    
#     # The `statistic` attribute is the F-statistic for the joint test.
#     # The `pvalue` attribute is the p-value for this F-statistic.
    
#     stat_val = ch_test.statistic
#     pval = ch_test.pvalue

#     interpretation = ""
#     if pval < significance_level:
#         interpretation = f"Reject H0 at {significance_level*100}% significance. Series is likely seasonally non-stationary (p-value: {pval:.4f})."
#     else:
#         interpretation = f"Fail to reject H0 at {significance_level*100}% significance. Series is likely seasonally stationary (p-value: {pval:.4f})."

#     return {
#         'test_name': 'Canova-Hansen Test for Seasonal Stationarity',
#         'seasonal_period': seasonal_period,
#         'test_statistic_F': stat_val,
#         'p_value': pval,
#         'critical_values': ch_test.critical_values, # This might need specific parsing
#         'interpretation': interpretation,
#         'full_summary_text': str(ch_test.summary()) # For detailed view
#     }


def run_ljung_box_test(
    residuals: pd.Series,
    lags: Optional[Union[int, list[int]]] = None,
    model_df: int = 0,
    return_df: bool = True # If True, returns DataFrame, else dict of DataFrames
) -> Union[pd.DataFrame, dict[str, pd.DataFrame]]:
    """
    Performs the Ljung-Box test for autocorrelation in residuals.
    H0: The data are independently distributed (no autocorrelation).
    H1: The data are not independently distributed.
    """
    if not isinstance(residuals, pd.Series):
        raise TypeError("Input 'residuals' must be a pandas Series.")
        
    # acorr_ljungbox returns lb_stat, lb_pvalue, bp_stat (optional), bp_pvalue (optional)
    # We are interested in lb_stat and lb_pvalue
    result_df = acorr_ljungbox(residuals.dropna(), lags=lags, model_df=model_df, return_df=return_df)
    
    if return_df: # result_df is already a DataFrame
        result_df.index.name = 'Lag'
        return result_df
    else: # result_df is a tuple of arrays (lb_stat, lb_pvalue)
        df = pd.DataFrame({'lb_stat': result_df[0], 'lb_pvalue': result_df[1]})
        if lags is None: # If lags is None, statsmodels determines them
            df.index = range(1, len(result_df[0]) + 1)
        elif isinstance(lags, int):
            df.index = range(1, lags + 1)
        else: # list of lags
            df.index = lags
        df.index.name = 'Lag'
        return {'ljung_box_results': df}


def run_shapiro_wilk_test(
    residuals: pd.Series,
    significance_level: float = 0.05,
    t: Optional[dict] = None
) -> dict[str, Any]:
    """
    Performs the Shapiro-Wilk test for normality of residuals.
    H0: The data was drawn from a normal distribution.
    H1: The data was not drawn from a normal distribution.
    """
    if not isinstance(residuals, pd.Series):
        raise TypeError("Input 'residuals' must be a pandas Series.")
    
    # Use default translations if not provided
    if t is None:
        t = DEFAULT_TRANSLATIONS["en"]
        
    # SciPy's shapiro returns (statistic, p-value)
    # Test requires at least 3 observations
    if len(residuals.dropna()) < 3:
        return {
            'test_statistic': None,
            'p_value': None,
            'interpretation': t.get("shapiro_insufficient_data", "Not enough data points ( < 3) for Shapiro-Wilk test.")
        }
        
    statistic, p_value = stats.shapiro(residuals.dropna())
    output = {
        'test_statistic': statistic,
        'p_value': p_value
    }
    if p_value <= significance_level:
        output['interpretation'] = t.get("shapiro_non_normal", "Reject H0 at {sig}% significance. Residuals are likely not normally distributed (p-value: {p:.4f}).").format(sig=significance_level*100, p=p_value)
    else:
        output['interpretation'] = t.get("shapiro_normal", "Fail to reject H0 at {sig}% significance. Residuals are likely normally distributed (p-value: {p:.4f}).").format(sig=significance_level*100, p=p_value)
    return output

def run_breusch_pagan_test(
    residuals: pd.Series,
    exog_for_test: pd.DataFrame, # Exogenous variables for the test (usually model's exog or fitted values)
    significance_level: float = 0.05,
    t: Optional[dict] = None
) -> dict[str, Any]:
    """
    Performs the Breusch-Pagan test for heteroscedasticity.
    H0: Homoscedasticity is present (residuals have constant variance).
    H1: Heteroscedasticity is present.
    """
    if not isinstance(residuals, pd.Series):
        raise TypeError("Input 'residuals' must be a pandas Series.")
    if not isinstance(exog_for_test, pd.DataFrame):
        raise TypeError("Input 'exog_for_test' must be a pandas DataFrame.")
    if len(residuals) != len(exog_for_test):
        raise ValueError("Length of residuals and exog_for_test must match.")

    # Use default translations if not provided
    if t is None:
        t = DEFAULT_TRANSLATIONS["en"]

    # Ensure exog_for_test has a constant for the test if not already present
    # This is typically handled by the model that generated residuals, but good to be safe.
    # If exog_for_test comes from a model with an intercept, it's usually fine.
    # If it's just fitted values, it's also fine.
    # het_breuschpagan expects exog to be the X matrix from `resids ~ X`
    
    # Drop NaNs that might exist due to differencing or other operations
    # Align residuals and exog_for_test
    common_index = residuals.dropna().index.intersection(exog_for_test.dropna().index)
    if len(common_index) < exog_for_test.shape[1] +1 : # Need enough obs
         return {
            'lm_statistic': None, 'lm_p_value': None,
            'f_statistic': None, 'f_p_value': None,
            'interpretation': t.get("bp_insufficient_data", "Not enough common non-NaN data points for Breusch-Pagan test.")
        }

    residuals_aligned = residuals.loc[common_index]
    exog_aligned = exog_for_test.loc[common_index]
    
    # Add constant to exog if it's not there (Breusch-Pagan regresses squared residuals on exog)
    exog_with_const = sm.add_constant(exog_aligned, prepend=True, has_constant='skip')


    lm_stat, lm_pvalue, f_stat, f_pvalue = het_breuschpagan(residuals_aligned, exog_with_const)
    
    output = {
        'lm_statistic': lm_stat,
        'lm_p_value': lm_pvalue,
        'f_statistic': f_stat,
        'f_p_value': f_pvalue
    }
    # Typically, the F-statistic's p-value is used for interpretation
    if f_pvalue <= significance_level:
        output['interpretation'] = t.get("bp_heteroscedastic", "Reject H0 at {sig}% significance. Heteroscedasticity is likely present (F-test p-value: {p:.4f}).").format(sig=significance_level*100, p=f_pvalue)
    else:
        output['interpretation'] = t.get("bp_homoscedastic", "Fail to reject H0 at {sig}% significance. Homoscedasticity is likely present (F-test p-value: {p:.4f}).").format(sig=significance_level*100, p=f_pvalue)
    return output

def run_johansen_cointegration_test(
    data: pd.DataFrame, # DataFrame of I(1) series
    det_order: int = 0,  # 0: no constant, 1: constant in CE, -1: no intercept
    k_ar_diff: int = 1   # Number of lagged differences in the VECM
) -> JohansenTestResult:
    """
    Performs the Johansen cointegration test.
    Returns the JohansenTestResult object from statsmodels.
    """
    if not isinstance(data, pd.DataFrame):
        raise TypeError("Input 'data' must be a pandas DataFrame.")
    if data.isnull().any().any():
        raise ValueError("Input DataFrame for Johansen test should not contain NaNs. Consider differencing and dropping NaNs before this test if series are I(1).")

    result = coint_johansen(data, det_order=det_order, k_ar_diff=k_ar_diff)
    return result # This is a JohansenTestResult object

def perform_granger_causality_test(
    data: pd.DataFrame, # DataFrame with at least two series
    max_lag: int,
    variables_pair: Optional[tuple[str, str]] = None, # (caused_variable, causing_variable)
    verbose: bool = False # statsmodels grangercausalitytests prints a lot
) -> dict[str, Any]:
    """
    Performs Granger Causality tests for specified lags.
    H0: The lagged X series do not Granger-cause Y series.
    H1: The lagged X series do Granger-cause Y series.
    
    If variables_pair is None, tests causality for all pairs.
    Returns a dictionary summarizing test results.
    """
    if not isinstance(data, pd.DataFrame):
        raise TypeError("Input 'data' must be a pandas DataFrame.")
    if data.shape[1] < 2:
        raise ValueError("Data must contain at least two series for Granger causality.")
    if not isinstance(max_lag, int) or max_lag < 1:
        raise ValueError("max_lag must be a positive integer.")

    results_summary = {}

    if variables_pair:
        if not (isinstance(variables_pair, tuple) and len(variables_pair) == 2 and
                all(isinstance(v, str) for v in variables_pair) and
                all(v in data.columns for v in variables_pair)):
            raise ValueError("variables_pair must be a tuple of two valid column names from data.")
        
        caused_var, causing_var = variables_pair
        test_data = data[[caused_var, causing_var]].dropna()
        if len(test_data) < max_lag + 5: # Heuristic for enough data
             results_summary[f'{causing_var}_granger_causes_{caused_var}'] = {"error": "Not enough data after dropping NaNs for the specified max_lag."}
             return results_summary

        # Suppress print output from grangercausalitytests
        import io
        import sys
        old_stdout = sys.stdout
        sys.stdout = captured_output = io.StringIO()

        gc_results = grangercausalitytests(test_data, maxlag=[max_lag], verbose=False) # Pass max_lag as a list
        
        sys.stdout = old_stdout # Restore stdout
        # captured_output.getvalue() # Contains the printed table if verbose=True

        # Parse the result (it's a dict where keys are lags)
        # We are interested in the result for `max_lag`
        lag_result = gc_results.get(max_lag)
        if lag_result:
            # Each lag_result is a tuple of (test_dict, (params_tuple))
            # test_dict contains results for 'ssr_ftest', 'ssr_chi2test', 'lrtest', 'params_ftest'
            # We typically use the F-test ('ssr_ftest')
            f_test_result = lag_result[0]['ssr_ftest']
            results_summary[f'{causing_var}_granger_causes_{caused_var}'] = {
                'lag': max_lag,
                'F_statistic': f_test_result[0],
                'p_value': f_test_result[1],
                'df_denom': f_test_result[2],
                'df_num': f_test_result[3]
            }
        else:
            results_summary[f'{causing_var}_granger_causes_{caused_var}'] = {"error": f"No result for lag {max_lag}."}

    else: # Test all pairs
        from itertools import permutations
        for caused_var, causing_var in permutations(data.columns, 2):
            test_data = data[[caused_var, causing_var]].dropna()
            if len(test_data) < max_lag + 5:
                results_summary[f'{causing_var}_granger_causes_{caused_var}'] = {"error": "Not enough data after dropping NaNs."}
                continue

            old_stdout = sys.stdout
            sys.stdout = captured_output = io.StringIO()
            gc_results = grangercausalitytests(test_data, maxlag=[max_lag], verbose=False)
            sys.stdout = old_stdout
            
            lag_result = gc_results.get(max_lag)
            if lag_result:
                f_test_result = lag_result[0]['ssr_ftest']
                results_summary[f'{causing_var}_granger_causes_{caused_var}'] = {
                    'lag': max_lag,
                    'F_statistic': f_test_result[0],
                    'p_value': f_test_result[1],
                    'df_denom': f_test_result[2],
                    'df_num': f_test_result[3]
                }
            else:
                 results_summary[f'{causing_var}_granger_causes_{caused_var}'] = {"error": f"No result for lag {max_lag}."}
    return results_summary


def check_var_model_stability(fitted_var_model: VARResultsWrapper, t: Optional[dict] = None) -> dict[str, Any]:
    """
    Checks if all roots of the characteristic polynomial of a fitted VAR model
    are within the unit circle.
    Returns a dictionary with stability status and the roots.
    """
    if not isinstance(fitted_var_model, VARResultsWrapper):
        raise TypeError("Input must be a fitted VAR model (VARResultsWrapper).")
    
    # Use default translations if not provided
    if t is None:
        t = DEFAULT_TRANSLATIONS["en"]
    roots = fitted_var_model.roots
    is_stable = all(abs(root) < 1 for root in roots) # Strictly inside unit circle
    
    return {
        'is_stable': is_stable,
        'roots': roots,
        'interpretation': t.get("var_stable", "Model is stable.") if is_stable else t.get("var_unstable", "Model is unstable (some roots are on or outside the unit circle).")
    }