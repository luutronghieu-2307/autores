import pandas as pd
import numpy as np
from typing import Any
from datetime import datetime
import os
import warnings
warnings.filterwarnings('ignore')
import base64
import traceback
from statsmodels.tsa.stattools import adfuller
from statsmodels.stats.diagnostic import het_breuschpagan
from statsmodels.stats.stattools import durbin_watson
from statsmodels.regression.linear_model import OLS
from statsmodels.sandbox.regression.gmm import IV2SLS as SM_IV2SLS

from sklearn.preprocessing import PolynomialFeatures, StandardScaler
from patsy import dmatrix
from scipy import stats
from scipy.stats import jarque_bera, normaltest
import seaborn as sns
# Core panel analysis packages
import statsmodels.api as sm
# Linear models for panel data
from linearmodels.panel import PanelOLS, RandomEffects, PooledOLS
from linearmodels.iv import IV2SLS
from linearmodels.system import SUR
from pydynpd import regression

# Plotting
import matplotlib.pyplot as plt
plt.style.use('seaborn-v0_8')

# Assuming these imports are from your codebase
from data_analysis.src.schemas.analyzer_states import (
    Variable, 
    Action, 
    ActionType, 
    ToolOutput, 
    VariableType, 
    VariableRole
)
from data_analysis.src.modules.utils import serialize_dict
from data_analysis.src.modules.tools.analysis.cross_section.pipeline_utils import format_title_with_count


def _extract_panel_recommendation(variables: list[Variable]) -> dict[str, Any]:
    """
    Extract panel model recommendations from variable properties.
    
    This function extracts the unified properties format from the dependent variable
    to get panel model recommendations, model details, and diagnostic results.
    
    Args:
        variables: list of Variable objects
        
    Returns:
        dict containing:
        - model_type: Recommended panel model type
        - robust_errors_used: Whether robust errors were used
        - needs_remediation: Whether the model needs remediation
        - model_details: Detailed model information
        - diagnostic_results: Results from diagnostic tests
        - absorbed_variables: Variables absorbed by fixed effects
    """
    dep_var = next((v for v in variables if v.role == VariableRole.DEPENDENT), None)
    if not dep_var:
        return {
            'model_type': 'Pooled OLS',
            'robust_errors_used': False,
            'needs_remediation': False,
            'model_details': {},
            'diagnostic_results': {},
            'absorbed_variables': []
        }

    
    # Extract the unified properties format
    properties = dep_var.properties
    
    # Get panel model recommendation with defaults
    panel_rec = properties.get('panel_model_recommendation', {})
    
    # Extract model details
    model_details = properties.get('model_details', {})
    
    # Extract diagnostic results
    diagnostic_results = properties.get('diagnostic_results', {})
    
    return {
        'model_type': panel_rec.get('model_type', 'Pooled OLS'),
        'robust_errors_used': panel_rec.get('robust_errors_used', False),
        'needs_remediation': panel_rec.get('needs_remediation', False),
        'model_details': model_details,
        'diagnostic_results': diagnostic_results,
        'absorbed_variables': []
    }


def _get_absorbed_variables(variables: list[Variable]) -> list[str]:
    """
    Get variables that were absorbed by fixed effects.
    
    Variables are considered absorbed if their panel_model_recommendation
    contains 'absorbed_status' == 'Absorbed by Fixed Effects'.
    
    Args:
        variables: List of Variable objects
        
    Returns:
        List of variable codes that were absorbed by fixed effects
    """
    absorbed = []
    for var in variables:
        panel_rec = var.properties.get('panel_model_recommendation', {})
        if panel_rec.get('absorbed_status') == 'Absorbed by Fixed Effects':
            absorbed.append(var.code)
    return absorbed


def _get_time_invariant_variables(variables: list[Variable]) -> list[str]:
    """
    Get time-invariant variables from diagnostic results.
    
    Variables are considered time-invariant if their diagnostic_results
    contains 'time_invariant' == True.
    
    Args:
        variables: List of Variable objects
        
    Returns:
        List of variable codes that are time-invariant
    """
    time_invariant = []
    for var in variables:
        diagnostic_results = var.properties.get('diagnostic_results', {})
        if diagnostic_results.get('time_invariant', False):
            time_invariant.append(var.code)
    return time_invariant


def _format_model_results(model_results: Any, model_name: str) -> str:
    """
    Format model results into a readable string with proper header.
    
    Args:
        model_results: Model results object (should have summary method)
        model_name: Name of the model for the header
        
    Returns:
        Formatted string with header and model summary
    """
    try:
        # Try to get summary if available
        if hasattr(model_results, 'summary'):
            summary_str = str(model_results.summary)
        else:
            summary_str = str(model_results)
        # Create centered header with equal signs
        header = f"\n{'='*80}\n{model_name.center(80)}\n{'='*80}\n"
        return header + summary_str
    except Exception as e:
        return f"Error generating summary for {model_name}: {str(e)}"


def _build_pydynpd_command(dep_var: str, indep_vars: list[str], 
                          lag_dep_reg: int = 1, gmm_lags: tuple[int, int] = (2, 4)) -> str:
    """
    Build command string for pydynpd GMM estimation.
    
    Creates a command string following pydynpd syntax for dynamic panel GMM estimation.
    The command includes lagged dependent variables and GMM instruments.
    
    Args:
        dep_var: Name of dependent variable
        indep_vars: List of independent variable names
        lag_dep_reg: Number of lags for dependent variable (default: 1)
        gmm_lags: Tuple of (min_lag, max_lag) for GMM instruments (default: (2, 4))
        
    Returns:
        Command string in pydynpd format
    """
    # Build lagged dependent variable string
    lag_str = f"L(1:{lag_dep_reg}).{dep_var}" if lag_dep_reg > 0 else ""
    
    # Combine lagged dependent and independent variables
    regressors = f"{lag_str} {' '.join(indep_vars)}".strip()
    
    # Build GMM instruments
    gmm_lag_str = f"({gmm_lags[0]},{gmm_lags[1]})"
    dep_instr = f"gmm({dep_var}, {gmm_lag_str})"
    indep_instrs = " ".join([f"gmm({v}, {gmm_lag_str})" for v in indep_vars])
    
    # Combine into final command: "dep_var regressors | instruments"
    command = f"{dep_var} {regressors} | {dep_instr} {indep_instrs}"
    return command


def _perform_ramsey_reset_test(y: pd.Series, X: pd.DataFrame, 
                              entity_effects: bool = False, t: dict = None) -> dict[str, Any]:
    """
    Perform Ramsey RESET test for non-linearity in panel data models.
    
    The RESET test checks for omitted variables by testing whether powers of 
    fitted values are significant when added to the original regression.
    
    Args:
        y: Dependent variable series
        X: Independent variables DataFrame
        entity_effects: Whether to include entity effects in base model
        
    Returns:
        Dict containing:
            - test: Test name
            - statistic: F-statistic value
            - p_value: P-value of the test
            - df_num: Numerator degrees of freedom
            - df_denom: Denominator degrees of freedom
            - significant: Whether test is significant at 5% level
            - error: Error message if test failed

    """
    try:
        # Fit base model depending on panel structure
        if entity_effects and hasattr(y.index, 'levels'):
            # Panel data with entity effects
            base_model = PanelOLS(y, X, entity_effects=True).fit()
            fitted_values = base_model.fitted_values
        else:
            # Pooled OLS with constant term
            X_const = sm.add_constant(X)
            base_model = sm.OLS(y, X_const).fit()
            fitted_values = base_model.fittedvalues
        
         # Create powers of fitted values for RESET test (squared and cubed)
        fitted_powers = np.column_stack([
            np.power(fitted_values, 2), 
            np.power(fitted_values, 3)
        ])
        
        # Augmented regression with original variables plus powers
        X_augmented = np.column_stack([X, fitted_powers])
        X_augmented = sm.add_constant(X_augmented)
        # Fit augmented model
        augmented_model = sm.OLS(y, X_augmented).fit()
        
        # F-test for joint significance of the power terms
        # Create restriction matrix for the last two coefficients (powers)
        n_vars = X_augmented.shape[1]
        r_matrix = np.zeros((2, n_vars))
        r_matrix[0, -2] = 1  # coefficient of fitted^2
        r_matrix[1, -1] = 1  # coefficient of fitted^3
        
        f_test = augmented_model.f_test(r_matrix)
        
        return {
            'test': 'Ramsey RESET',
            'statistic': f_test.fvalue,
            'p_value': f_test.pvalue,
            'df_num': f_test.df_num,
            'df_denom': f_test.df_denom,
            'significant': f_test.pvalue < 0.05,
            'interpretation': t.get("reset_linear_rejected", "Reject H0: Model is linear") if f_test.pvalue < 0.05 else t.get("reset_linear_failed", "Fail to reject H0: Model is linear")
        }

        
    except Exception as e:
        return {
            'test': 'Ramsey RESET',
            'error': str(e)
        }


def _run_iv_analysis(y: pd.Series, X_exog: pd.DataFrame, X_endog: pd.DataFrame, 
                    Z_instr: pd.DataFrame, base_model_type: str = 'Fixed Effects', t: dict = None) -> dict[str, Any]:
    """
    Run comprehensive IV/2SLS analysis with proper diagnostics.
    
    Performs two-stage least squares estimation with appropriate covariance matrix
    and comprehensive diagnostic testing including endogeneity, instrument validity,
    and instrument strength tests.
    
    Args:
        y: Dependent variable series (should have panel index)
        X_exog: DataFrame of exogenous variables
        X_endog: DataFrame of endogenous variables
        Z_instr: DataFrame of instrument variables
        base_model_type: Type of base model ('Fixed Effects', 'Random Effects', 'Pooled')
        
    Returns:
        Dict containing:
            - model_fit: Fitted IV model object
            - summary: Formatted model summary string
            - model_details: Key model statistics and parameters
            - diagnostics: Comprehensive diagnostic test results
            - error: Error message if estimation failed
    """
    results = {}
    
    try:
        # Set up IV model based on base model type
        if base_model_type == 'Fixed Effects':
            # Use entity effects for panel data
            iv_model = IV2SLS(y, X_exog, X_endog, Z_instr, entity_effects=True)
        else:
            # Random effects or pooled specification
            iv_model = IV2SLS(y, X_exog, X_endog, Z_instr)
        
        # Fit model with appropriate covariance matrix
        # Check for panel structure to determine clustering
        if hasattr(y.index, 'levels') and len(y.index.levels) >= 2:
            # Panel data - use entity-clustered standard errors
            iv_fit = iv_model.fit(cov_type='clustered', clusters=y.index.get_level_values(0))
        else:
            # Non-panel data - use robust standard errors
            iv_fit = iv_model.fit(cov_type='robust')
        # Store model fit and summary
        results['model_fit'] = iv_fit
        results['summary'] = _format_model_results(iv_fit, t.get("model_iv_title", "IV/2SLS Model"))
        
        # Extract key model details
        f_stat_obj = getattr(iv_fit, 'f_statistic', None)
        results['model_details'] = {
            'rsquared': getattr(iv_fit, 'rsquared', np.nan),
            'n_obs': getattr(iv_fit, 'nobs', np.nan),
            'f_statistic': f_stat_obj.stat if f_stat_obj else np.nan,
            'params': iv_fit.params.to_dict() if hasattr(iv_fit, 'params') else {},
            'pvalues': iv_fit.pvalues.to_dict() if hasattr(iv_fit, 'pvalues') else {},
            'std_errors': iv_fit.std_errors.to_dict() if hasattr(iv_fit, 'std_errors') else {}
        }
        
        # Comprehensive diagnostic testing
        diagnostics = {}
        
        # 1. Endogeneity test (Wu-Hausman test)
        try:
            wu_hausman = iv_fit.wu_hausman()
            diagnostics['wu_hausman_test'] = {
                'test': 'Wu-Hausman Endogeneity Test',
                'statistic': wu_hausman.stat,
                'p_value': wu_hausman.pval,
                'significant': wu_hausman.pval < 0.05,
                'interpretation': (t.get("wu_hausman_endog_confirmed", 'Reject H0: Variables are exogenous (endogeneity confirmed)') 
                                if wu_hausman.pval < 0.05 
                                else t.get("wu_hausman_exog_failed", 'Fail to reject H0: Variables are exogenous'))
            }
        except Exception as e:
            diagnostics['wu_hausman_test'] = {
                'test': 'Wu-Hausman Endogeneity Test',
                'error': str(e)
            }
        
        # 2. Instrument validity test (Sargan test)
        try:
            if Z_instr.shape[1] > X_endog.shape[1]:  # Overidentified case
                sargan = iv_fit.sargan()
                diagnostics['sargan_test'] = {
                    'test': 'Sargan Overidentification Test',
                    'statistic': sargan.stat,
                    'p_value': sargan.pval,
                    'significant': sargan.pval < 0.05,
                    'interpretation': ('Reject H0: Instruments are valid (instrument validity questioned)' 
                                    if sargan.pval < 0.05 
                                    else 'Fail to reject H0: Instruments are valid')
                }
            else:
                diagnostics['sargan_test'] = {
                    'test': 'Sargan Overidentification Test',
                    'note': 'Exactly identified model - overidentification test not applicable'
                }
        except Exception as e:
            diagnostics['sargan_test'] = {'error': str(e)}
        
        # 3. Instrument strength test (First-stage F-statistics)
        try:
            first_stage = iv_fit.first_stage
            f_statistics = {}
            
            # Extract F-statistics from first stage results
            if hasattr(first_stage, 'f_statistics'):
                f_statistics = first_stage.f_statistics
            elif hasattr(first_stage, 'results'):
                # Handle case where first_stage has individual results
                for var, result in first_stage.results.items():
                    if hasattr(result, 'f_statistic'):
                        f_statistics[var] = result.f_statistic.stat
            
            if f_statistics:
                min_f_stat = min(f_statistics.values())
                diagnostics['first_stage_f'] = {
                    'test': 'First-Stage F-Test',
                    'f_statistics': f_statistics,
                    'min_f_statistic': min_f_stat,
                    'significant': min_f_stat < 10,
                    'interpretation': (t.get("first_stage_strong", 'Strong instruments (F > 10)') if min_f_stat > 10 
                                    else t.get("first_stage_weak", 'Weak instruments detected (F < 10)'))
                }
            else:
                diagnostics['first_stage_f'] = {
                    'min_f_statistic': 0,
                    'weak_instruments': True,
                    'interpretation': t.get("first_stage_error", 'Could not compute F-statistics')
                }
                
        except Exception as e:
            diagnostics['first_stage_f'] = {
                'test': 'First-Stage F-Test',
                'error': str(e)
            }
        
        results['diagnostics'] = diagnostics
        
    except Exception as e:
        results['error'] = f"IV estimation failed: {str(e)}"
    
    return results

def _run_gmm_analysis(data: pd.DataFrame, dep_var: str, indep_vars: list[str],
                     entity_col: str, time_col: str, t: dict = None) -> dict[str, Any]:
    """
    Run GMM analysis using pydynpd for dynamic panel data models.
    
    Performs Generalized Method of Moments estimation using the Arellano-Bond
    approach for dynamic panel data. Includes comprehensive diagnostic testing
    for instrument validity and serial correlation.
    
    Args:
        data: Panel data DataFrame
        dep_var: Name of dependent variable
        indep_vars: List of independent variable names
        entity_col: Name of entity identifier column
        time_col: Name of time identifier column
        
    Returns:
       Dict containing:
            - model_fit: Fitted GMM model object
            - command: Command string used for estimation
            - summary: Formatted model summary
            - model_details: Key model statistics
            - diagnostics: Hansen test and AR tests results
            - error: Error message if estimation failed
    """
    results = {}
    
    try:
        # Build command string for GMM estimation
        command = _build_pydynpd_command(dep_var, indep_vars)
        
        # Run Arellano-Bond GMM estimation
        mydpd = regression.abond(command, data, [entity_col, time_col])
        
        if not mydpd.models:
            results['error'] = "GMM estimation failed. Check data structure and variable specification."
            return results
        
        # Get the fitted model (first model in the list)
        gmm_fit = mydpd.models[0]
        
        results['model_fit'] = gmm_fit
        results['command'] = command
        
        # Extract model components
        reg_table = gmm_fit.regression_table
        hansen = gmm_fit.hansen
        ar_tests = gmm_fit.AR_list
        
        # Extract model details
        results['model_details'] = {
            'n_obs': len(data),
            'n_groups': data[entity_col].nunique(),
            'time_periods': data[time_col].nunique(),
            'params': reg_table['coef'].to_dict() if hasattr(reg_table, 'coef') else {},
            'pvalues': reg_table['P>|z|'].to_dict() if hasattr(reg_table, 'P>|z|') else {},
            'std_errors': reg_table['std err'].to_dict() if hasattr(reg_table, 'std err') else {}
        }
        
        # Create comprehensive summary
        summary_parts = [
            t.get("gmm_header", "GMM Dynamic Panel Data Results"),
            t.get("gmm_command_label", "Estimation Command: {}").format(command),
            t.get("gmm_sample_label", "Sample: {} observations, {} entities, {} time periods").format(len(data), data[entity_col].nunique(), data[time_col].nunique()),
            "",
            t.get("gmm_coefficient_label", "Coefficient Estimates:"),
            reg_table.to_string(),
            "",
            f"Hansen J-Test: chi2({hansen.df}) = {hansen.test_value:.4f}, p-value = {hansen.p_value:.4f}",
            f"AR(1) Test: z = {ar_tests[0].AR:.3f}, p-value = {ar_tests[0].P_value:.4f}",
            f"AR(2) Test: z = {ar_tests[1].AR:.3f}, p-value = {ar_tests[1].P_value:.4f}"
        ]
        
        results['summary'] = "\n".join(summary_parts)
        
        # Comprehensive diagnostic testing
        diagnostics = {}
        
        # Hansen test for instrument validity
        diagnostics['hansen_test'] = {
            'test': 'Hansen J-Test',
            'statistic': hansen.test_value,
            'p_value': hansen.p_value,
            'df': hansen.df,
            'significant': hansen.p_value < 0.05,
            'interpretation': (t.get("hansen_invalid", 'Reject H0: Instruments are valid (overidentifying restrictions violated)') 
                            if hansen.p_value < 0.05 
                            else t.get("hansen_valid", 'Fail to reject H0: Instruments are valid'))
        }
        
        # Serial correlation tests
        diagnostics['ar_tests'] = {
            'ar1': {
                'test': 'AR(1) Test',
                'statistic': ar_tests[0].AR,
                'p_value': ar_tests[0].P_value,
                'significant': ar_tests[0].P_value < 0.05,
                'interpretation': (t.get("ar1_detected", 'Expected result: First-order serial correlation detected') 
                                if ar_tests[0].P_value < 0.05 
                                else t.get("ar1_not_detected", 'Unexpected: No first-order serial correlation'))
            },
            'ar2': {
                'test': 'AR(2) Test',
                'statistic': ar_tests[1].AR,
                'p_value': ar_tests[1].P_value,
                'significant': ar_tests[1].P_value < 0.05,
                'interpretation': (t.get("ar2_detected", 'Concerning: Second-order serial correlation detected') 
                                if ar_tests[1].P_value < 0.05 
                                else t.get("ar2_not_detected", 'Expected result: No second-order serial correlation'))
            }
        }
        
        results['diagnostics'] = diagnostics
        
    except Exception as e:
        results['error'] = f"GMM estimation failed: {str(e)}"
    
    return results


def run_advanced_panel_analysis(
    data: pd.DataFrame,
    variables: list[Variable],
    params: dict
) -> ToolOutput:
    """
    Perform advanced panel data analysis with proper integration of initial recommendations.
    
    This tool builds upon the initial panel model selection and performs:
    1. IV/2SLS analysis for endogeneity
    2. GMM analysis for dynamic panels
    3. Non-linearity testing and remediation
    4. Integration with previous recommendations

    Parameters:
    - data: Panel dataset
    - variables: List of Variable objects
    - params: Dict with keys:
        - analysis_type (str): Type of analysis ('IV' or 'GMM') (default: 'IV')
        - output_dir (str): Output directory (default: 'SS_advanced_panel')
        - save_files (bool): Save files to disk (default: False)
        - significance_level (float): Significance level for tests (default: 0.05)
        - endogenous_vars (List[str]): Endogenous variables for IV analysis (default: all endogenous vars)
        - instrument_vars (List[str]): Instrument variables for IV analysis (default: all independent vars)
        - test_non_linearity (bool): Whether to test for non-linearity (default: False)


    Returns:
        - ToolOutput: Results, logs, file contents, and actions
    """
    # Translation dictionary
    translations = {
        "en": {
            "title": "# Advanced Panel Data Analysis Report\n\n",
            "logs": "Advanced Panel Data Analysis Report",
            "msg": "Analysis Type: {}",
            "msg_1": "Timestamp: {}",
            "msg_2": "Initial model recommendation: {}",
            "msg_3": "Remediation needed: {}",
            "msg_4": "Variables absorbed by fixed effects: {}",
            "msg_5": "Time-invariant variables identified: {}",
            "logs_1": "Previous diagnostic test results:",
            "msg_6": "  {}: p-value = {:.4f}",
            "errormsg": "Missing required variables (dependent, entity_index, time_index)",
            "msg_7": "ERROR: {}",
            "msg_8": "Panel data prepared with shape: {}",
            "msg_9": "Dependent variable: {}",
            "msg_10": "Entity index: {}",
            "msg_11": "Time index: {}",
            "logs_2": "Starting IV/2SLS Analysis",
            "errormsg_1": "endogenous_vars and instrument_vars required for IV analysis",
            "msg_12": "ERROR: {}",
            "msg_13": "Endogenous variables: {}",
            "msg_14": "Instrument variables: {}",
            "msg_15": "Exogenous variables: {}",
            "msg_16": "Missing instruments in data: {}",
            "msg_17": "ERROR: {}",
            "msg_18": "WARNING: Overlap between instruments and exogenous vars: {}",
            "msg_19": "WARNING: Removing overlapping variables from exogenous list: {}",
            "msg_20": "Data matrices prepared - Y: {}, X_exog: {}, X_endog: {}, Z_instr: {}",
            "msg_21": "Instrument matrix rank: {}/{}",
            "logs_3": "WARNING: Instrument matrix does not have full rank",
            "msg_22": "Combined instrument matrix rank: {}/{}",
            "logs_4": "WARNING: Combined instrument matrix does not have full rank",
            "msg_23": "High correlation pairs detected: {} pairs",
            "msg_24": "Matrix rank check failed: {}",
            "msg_25": "IV analysis failed: {}",
            "logs_5": "Attempting alternative IV specification...",
            "msg_26": "Trying with cleaned instruments: {}",
            "logs_6": "Alternative IV specification successful",
            "msg_27": "Alternative IV specification also failed: {}",
            "logs_7": "No clean instruments available for alternative specification",
            "logs_8": "IV analysis completed successfully",
            "msg_28": "  {}: {}",
            "logs_9": "Weak instruments detected (F-statistic: {:.2f})",
            "logs_10": "Endogeneity confirmed - IV approach justified",
            "logs_11": "No evidence of endogeneity - OLS may be sufficient",
            "logs_12": "Starting GMM Analysis",
            "msg_29": "Independent variables: {}",
            "msg_30": "GMM analysis failed: {}",
            "logs_13": "GMM analysis completed successfully",
            "msg_31": "Hansen test: {}",
            "msg_32": "AR(1) test: {}",
            "msg_33": "AR(2) test: {}",
            "logs_14": "Hansen test failure detected (p-value: {:.4f})",
            "logs_15": "AR(2) test failure detected (p-value: {:.4f})",
            "msg_34": "Unknown analysis_type: {}",
            "msg_35": "ERROR: {}",
            "logs_16": "Starting Non-linearity Testing",
            "logs_17": "Ramsey RESET test completed: p-value = {:.4f}",
            "logs_18": "Evidence of non-linearity detected",
            "msg_36": "Non-linearity remediation suggested for variable: {}",
            "logs_19": "No evidence of non-linearity detected",
            "msg_37": "RESET test failed: {}",
            "logs_20": "No variables available for non-linearity testing",
            "msg_38": "IV diagnostics report: {}",
            "msg_39": "GMM diagnostics report generated: {}",
            "summary": "Summary statistics: {}",
            "msg_40": "Main analysis: {}",
            "msg_41": "Analysis completed successfully - {} model",
            "msg_42": "Remediation actions identified: {}",
            "msg_43": "Model requires remediation: {}",
            "error": "Error decoding or saving image {}: {}",
            "warning": "Warning: Unknown file type for '{}'. Saving as text.",
            "msg_44": "Could not save file {}: {}",
            "msg_45": "Failed to save {}: {}",
            "msg_46": "Advanced panel analysis failed: {}",
            "error_1": "Error occurred at: {}",
            "error_2": "Error log generated: {}",
            "error_3": "Failed to save error log: {}",
            "error_4": "Failed to generate error log: {}",
            # IV Details section
            "iv_details_header": "IV/2SLS Diagnostic Details",
            "iv_first_stage": "First Stage Results:",
            "iv_endogeneity_test": "Endogeneity Test (Wu-Hausman):",
            "iv_statistic": "- Statistic: {}",
            "iv_p_value": "- P-value: {}",
            "iv_significant": "- Significant: {}",
            "iv_instrument_validity": "Instrument Validity (Sargan/Hansen):",
            "iv_test": "- Test: {}",
            "iv_weak_instruments": "Weak Instruments Check:",
            "iv_min_f_stat": "- Minimum F-statistic: {}",
            "iv_weak_instr_status": "- Weak Instruments: {}",
            "iv_recommendation": "- Recommendation: {}",
            "iv_use_stronger": "Use stronger instruments",
            "iv_adequate": "Instruments appear adequate",
            # GMM Details section
            "gmm_details_header": "GMM Diagnostic Details",
            "gmm_hansen_test": "Hansen Test (Instrument Validity):",
            "gmm_degrees_freedom": "- Degrees of Freedom: {}",
            "gmm_interpretation": "- Interpretation: {}",
            "gmm_ar1_test": "AR(1) Test (Expected: Significant):",
            "gmm_ar2_test": "AR(2) Test (Expected: Not Significant):",
            "gmm_model_command": "Model Command:",
            "gmm_overall_validity": "Overall Model Validity:",
            "gmm_hansen_passed": "- Hansen Test Passed: {}",
            "gmm_ar2_passed": "- AR(2) Test Passed: {}",
            "gmm_model_valid": "- Model is Valid: {}",
            # Summary Stats section
            "summary_header": "Panel Data Summary Statistics",
            "summary_dataset_info": "Dataset Information:",
            "summary_total_obs": "- Total Observations: {}",
            "summary_num_vars": "- Number of Variables: {}",
            "summary_num_entities": "- Number of Entities: {}",
            "summary_num_periods": "- Number of Time Periods: {}",
            "summary_balanced": "- Balanced Panel: {}",
            "summary_var_summary": "Variable Summary:",
            "summary_missing": "Missing Values:",
            "summary_correlation": "Correlation Matrix (Top 10 variables):",
            # Report Content section
            "report_header": "Advanced Panel Data Analysis Report",
            "report_analysis_config": "Analysis Configuration:",
            "report_analysis_type": "- Analysis Type: {}",
            "report_timestamp": "- Timestamp: {}",
            "report_sig_level": "- Significance Level: {}",
            "report_panel_shape": "- Panel Data Shape: {}",
            "report_initial_model": "Initial Model Recommendation:",
            "report_model_type": "- Model Type: {}",
            "report_robust_errors": "- Robust Errors Used: {}",
            "report_needs_remediation": "- Needs Remediation: {}",
            "report_var_config": "Variable Configuration:",
            "report_dep_var": "- Dependent Variable: {}",
            "report_entity_idx": "- Entity Index: {}",
            "report_time_idx": "- Time Index: {}",
            "report_absorbed_vars": "- Absorbed Variables: {}",
            "report_time_invariant": "- Time-Invariant Variables: {}",
            "report_model_spec": "Model Specification:",
            "report_diagnostic_results": "Diagnostic Test Results:",
            "report_remediation_actions": "Remediation Actions Required:",
            "report_no_summary": "No model summary available",
            "report_no_diagnostics": "No diagnostic tests performed",
            "report_no_remediation": "No remediation actions needed",
            # Error Log section
            "error_log_header": "Advanced Panel Analysis Error Log",
            "error_log_message": "Error Message: {}",
            "error_log_timestamp": "Timestamp: {}",
            "error_log_analysis_type": "Analysis Type: {}",
            "error_log_parameters": "Parameters:",
            "error_log_sig_level": "- Significance Level: {}",
            "error_log_endogenous": "- Endogenous Variables: {}",
            "error_log_instruments": "- Instrument Variables: {}",
            "error_log_test_nonlin": "- Test Non-linearity: {}",
            "error_log_var_config": "Variables Configuration:",
            "error_log_traceback": "Full Traceback:",
            "error_log_data_shape": "Data Shape: {}",
            "error_log_panel_shape": "Panel Data Shape: {}",
            "not_available": "Not available",
            "not_applicable": "N/A",
            "none": "None",
            "ar2_not_detected": "Expected result: No second-order serial correlation",
            "model_iv_title": "IV/2SLS Model",
            "action_non_linearity_comment": "Consider adding polynomial terms or logarithmic transformation for variable '{}'",
            "summary_weak_instr": "- Weak instruments: Current F-statistic = {:.2f}",
            "summary_weak_instr_rec": "  Recommendation: Find stronger instruments",
            "summary_invalid_instr": "- Invalid instruments: Hansen p-value = {:.4f}",
            "summary_invalid_instr_rec": "  Recommendation: Reduce instrument count or check for heteroscedasticity",
            "summary_serial_corr": "- Serial correlation: AR(2) p-value = {:.4f}",
            "summary_serial_corr_rec": "  Recommendation: Use deeper lags or different GMM specification",
            "summary_non_linearity": "- Non-linearity: RESET p-value = {:.4f}",
            "summary_non_linearity_rec": "  Recommendation: Add polynomial terms for '{}'"
        },
        "vi": {
            "title": "# Phân Tích Dữ Liệu Bảng Chuyên Sâu\n\n",
            "logs": "Báo Cáo Phân Tích Dữ Liệu Bảng Nâng Cao",
            "msg": "Loại Phân Tích: {}",
            "msg_1": "Thời gian: {}",
            "msg_2": "Đề xuất mô hình ban đầu: {}",
            "msg_3": "Cần khắc phục: {}",
            "msg_4": "Biến được hấp thụ bởi fixed effects: {}",
            "msg_5": "Biến bất biến theo thời gian được xác định: {}",
            "logs_1": "Kết quả kiểm định chẩn đoán trước đó:",
            "msg_6": "  {}: p-value = {:.4f}",
            "errormsg": "Thiếu biến bắt buộc (dependent, entity_index, time_index)",
            "msg_7": "LỖI: {}",
            "msg_8": "Dữ liệu bảng đã chuẩn bị với kích thước: {}",
            "msg_9": "Biến phụ thuộc: {}",
            "msg_10": "Chỉ số thực thể: {}",
            "msg_11": "Chỉ số thời gian: {}",
            "logs_2": "Bắt đầu Phân Tích IV/2SLS",
            "errormsg_1": "Yêu cầu endogenous_vars và instrument_vars cho phân tích IV",
            "msg_12": "LỖI: {}",
            "msg_13": "Biến nội sinh: {}",
            "msg_14": "Biến công cụ: {}",
            "msg_15": "Biến ngoại sinh: {}",
            "msg_16": "Biến công cụ thiếu trong dữ liệu: {}",
            "msg_17": "LỖI: {}",
            "msg_18": "CẢNH BÁO: Trùng lặp giữa biến công cụ và biến ngoại sinh: {}",
            "msg_19": "CẢNH BÁO: Loại bỏ biến trùng lặp khỏi danh sách ngoại sinh: {}",
            "msg_20": "Ma trận dữ liệu đã chuẩn bị - Y: {}, X_exog: {}, X_endog: {}, Z_instr: {}",
            "msg_21": "Hạng ma trận công cụ: {}/{}",
            "logs_3": "CẢNH BÁO: Ma trận công cụ không có hạng đầy đủ",
            "msg_22": "Hạng ma trận công cụ kết hợp: {}/{}",
            "logs_4": "CẢNH BÁO: Ma trận công cụ kết hợp không có hạng đầy đủ",
            "msg_23": "Phát hiện cặp tương quan cao: {} cặp",
            "msg_24": "Kiểm tra hạng ma trận thất bại: {}",
            "msg_25": "Phân tích IV thất bại: {}",
            "logs_5": "Đang thử đặc tả IV thay thế...",
            "msg_26": "Thử với biến công cụ đã làm sạch: {}",
            "logs_6": "Đặc tả IV thay thế thành công",
            "msg_27": "Đặc tả IV thay thế cũng thất bại: {}",
            "logs_7": "Không có biến công cụ sạch cho đặc tả thay thế",
            "logs_8": "Phân tích IV hoàn thành thành công",
            "msg_28": "  {}: {}",
            "logs_9": "Phát hiện biến công cụ yếu (F-statistic: {:.2f})",
            "logs_10": "Xác nhận nội sinh - Phương pháp IV được chứng minh",
            "logs_11": "Không có bằng chứng nội sinh - OLS có thể đủ",
            "logs_12": "Bắt đầu Phân Tích GMM",
            "msg_29": "Biến độc lập: {}",
            "msg_30": "Phân tích GMM thất bại: {}",
            "logs_13": "Phân tích GMM hoàn thành thành công",
            "msg_31": "Kiểm định Hansen: {}",
            "msg_32": "Kiểm định AR(1): {}",
            "msg_33": "Kiểm định AR(2): {}",
            "logs_14": "Phát hiện thất bại kiểm định Hansen (p-value: {:.4f})",
            "logs_15": "Phát hiện thất bại kiểm định AR(2) (p-value: {:.4f})",
            "msg_34": "analysis_type không xác định: {}",
            "msg_35": "LỖI: {}",
            "logs_16": "Bắt đầu Kiểm Định Phi Tuyến",
            "logs_17": "Kiểm định Ramsey RESET hoàn thành: p-value = {:.4f}",
            "logs_18": "Phát hiện bằng chứng phi tuyến",
            "msg_36": "Đề xuất khắc phục phi tuyến cho biến: {}",
            "logs_19": "Không phát hiện bằng chứng phi tuyến",
            "msg_37": "Kiểm định RESET thất bại: {}",
            "logs_20": "Không có biến khả dụng để kiểm định phi tuyến",
            "msg_38": "Báo cáo chẩn đoán IV: {}",
            "msg_39": "Báo cáo chẩn đoán GMM đã tạo: {}",
            "summary": "Thống kê tóm tắt: {}",
            "msg_40": "Phân tích chính: {}",
            "msg_41": "Phân tích hoàn thành thành công - mô hình {}",
            "msg_42": "Hành động khắc phục được xác định: {}",
            "msg_43": "Mô hình yêu cầu khắc phục: {}",
            "error": "Lỗi giải mã hoặc lưu hình ảnh {}: {}",
            "warning": "Cảnh báo: Loại tệp không xác định cho '{}'. Lưu dưới dạng văn bản.",
            "msg_44": "Không thể lưu tệp {}: {}",
            "msg_45": "Lưu {} thất bại: {}",
            "msg_46": "Phân tích bảng nâng cao thất bại: {}",
            "error_1": "Lỗi xảy ra tại: {}",
            "error_2": "Nhật ký lỗi đã tạo: {}",
            "error_3": "Lưu nhật ký lỗi thất bại: {}",
            "error_4": "Tạo nhật ký lỗi thất bại: {}",
            # IV Details section
            "iv_details_header": "Chi Tiết Chẩn Đoán IV/2SLS",
            "iv_first_stage": "Kết Quả Giai Đoạn Đầu:",
            "iv_endogeneity_test": "Kiểm Định Nội Sinh (Wu-Hausman):",
            "iv_statistic": "- Thống kê: {}",
            "iv_p_value": "- P-value: {}",
            "iv_significant": "- Có ý nghĩa: {}",
            "iv_instrument_validity": "Tính Hợp Lệ Biến Công Cụ (Sargan/Hansen):",
            "iv_test": "- Kiểm định: {}",
            "iv_weak_instruments": "Kiểm Tra Biến Công Cụ Yếu:",
            "iv_min_f_stat": "- F-statistic tối thiểu: {}",
            "iv_weak_instr_status": "- Biến công cụ yếu: {}",
            "iv_recommendation": "- Khuyến nghị: {}",
            "iv_use_stronger": "Sử dụng biến công cụ mạnh hơn",
            "iv_adequate": "Biến công cụ có vẻ phù hợp",
            # GMM Details section
            "gmm_details_header": "Chi Tiết Chẩn Đoán GMM",
            "gmm_hansen_test": "Kiểm Định Hansen (Tính Hợp Lệ Biến Công Cụ):",
            "gmm_degrees_freedom": "- Bậc tự do: {}",
            "gmm_interpretation": "- Giải thích: {}",
            "gmm_ar1_test": "Kiểm Định AR(1) (Kỳ vọng: Có ý nghĩa):",
            "gmm_ar2_test": "Kiểm Định AR(2) (Kỳ vọng: Không có ý nghĩa):",
            "gmm_model_command": "Lệnh Mô Hình:",
            "gmm_overall_validity": "Tính Hợp Lệ Tổng Thể Mô Hình:",
            "gmm_hansen_passed": "- Kiểm định Hansen đạt: {}",
            "gmm_ar2_passed": "- Kiểm định AR(2) đạt: {}",
            "gmm_model_valid": "- Mô hình hợp lệ: {}",
            # Summary Stats section
            "summary_header": "Thống Kê Tóm Tắt Dữ Liệu Bảng",
            "summary_dataset_info": "Thông Tin Tập Dữ Liệu:",
            "summary_total_obs": "- Tổng số quan sát: {}",
            "summary_num_vars": "- Số lượng biến: {}",
            "summary_num_entities": "- Số lượng thực thể: {}",
            "summary_num_periods": "- Số kỳ thời gian: {}",
            "summary_balanced": "- Bảng cân bằng: {}",
            "summary_var_summary": "Tóm Tắt Biến:",
            "summary_missing": "Giá Trị Thiếu:",
            "summary_correlation": "Ma Trận Tương Quan (Top 10 biến):",
            # Report Content section
            "report_header": "Báo Cáo Phân Tích Dữ Liệu Bảng Nâng Cao",
            "report_analysis_config": "Cấu Hình Phân Tích:",
            "report_analysis_type": "- Loại phân tích: {}",
            "report_timestamp": "- Thời gian: {}",
            "report_sig_level": "- Mức ý nghĩa: {}",
            "report_panel_shape": "- Kích thước dữ liệu bảng: {}",
            "report_initial_model": "Đề Xuất Mô Hình Ban Đầu:",
            "report_model_type": "- Loại mô hình: {}",
            "report_robust_errors": "- Sai số robust được sử dụng: {}",
            "report_needs_remediation": "- Cần khắc phục: {}",
            "report_var_config": "Cấu Hình Biến:",
            "report_dep_var": "- Biến phụ thuộc: {}",
            "report_entity_idx": "- Chỉ số thực thể: {}",
            "report_time_idx": "- Chỉ số thời gian: {}",
            "report_absorbed_vars": "- Biến đã hấp thụ: {}",
            "report_time_invariant": "- Biến bất biến theo thời gian: {}",
            "report_model_spec": "Đặc Tả Mô Hình:",
            "report_diagnostic_results": "Kết Quả Kiểm Định Chẩn Đoán:",
            "report_remediation_actions": "Hành Động Khắc Phục Yêu Cầu:",
            "report_no_summary": "Không có tóm tắt mô hình",
            "report_no_diagnostics": "Không thực hiện kiểm định chẩn đoán",
            "report_no_remediation": "Không cần hành động khắc phục",
            # Error Log section
            "error_log_header": "Nhật Ký Lỗi Phân Tích Bảng Nâng Cao",
            "error_log_message": "Thông báo lỗi: {}",
            "error_log_timestamp": "Thời gian: {}",
            "error_log_analysis_type": "Loại phân tích: {}",
            "error_log_parameters": "Tham số:",
            "error_log_sig_level": "- Mức ý nghĩa: {}",
            "error_log_endogenous": "- Biến nội sinh: {}",
            "error_log_instruments": "- Biến công cụ: {}",
            "error_log_test_nonlin": "- Kiểm định phi tuyến: {}",
            "error_log_var_config": "Cấu Hình Biến:",
            "error_log_traceback": "Traceback Đầy Đủ:",
            "error_log_data_shape": "Kích thước dữ liệu: {}",
            "error_log_panel_shape": "Kích thước dữ liệu bảng: {}",
            "reset_linear_rejected": "Bác bỏ H0: Mô hình là tuyến tính (có bằng chứng của tính phi tuyến)",
            "reset_linear_failed": "Chưa đủ cơ sở bác bỏ H0: Mô hình là tuyến tính",
            "wu_hausman_endog_confirmed": "Bác bỏ H0: Các biến là ngoại sinh (xác nhận nội sinh)",
            "wu_hausman_exog_failed": "Chưa đủ cơ sở bác bỏ H0: Các biến là ngoại sinh",
            "sargan_invalid": "Bác bỏ H0: Các biến công cụ là hợp lệ (nghi ngờ tính hợp lệ của biến công cụ)",
            "sargan_valid": "Chưa đủ cơ sở bác bỏ H0: Các biến công cụ là hợp lệ",
            "sargan_exact_identified": "Mô hình xác định vừa đủ - kiểm định quá định danh không áp dụng",
            "first_stage_strong": "Biến công cụ mạnh (F > 10)",
            "first_stage_weak": "Phát hiện biến công cụ yếu (F < 10)",
            "first_stage_error": "Không thể tính toán thống kê F",
            "gmm_header": "Kết quả Dữ liệu Bảng Động GMM",
            "gmm_command_label": "Lệnh Ước lượng: {}",
            "gmm_sample_label": "Mẫu: {} quan sát, {} thực thể, {} giai đoạn thời gian",
            "gmm_coefficient_label": "Ước lượng Hệ số:",
            "hansen_invalid": "Bác bỏ H0: Các biến công cụ là hợp lệ (vi phạm các ràng buộc quá định danh)",
            "hansen_valid": "Chưa đủ cơ sở bác bỏ H0: Các biến công cụ là hợp lệ",
            "ar1_detected": "Kết quả mong đợi: Phát hiện tự tương quan bậc nhất",
            "ar1_not_detected": "Không mong đợi: Không có tự tương quan bậc nhất",
            "ar2_detected": "Đáng lo ngại: Phát hiện tự tương quan bậc hai",
            "ar2_not_detected": "Kết quả mong đợi: Không có tự tương quan bậc hai",
            "model_iv_title": "Mô hình IV/2SLS",
            "action_weak_instr_issue": "Phát hiện biến công cụ yếu",
            "action_weak_instr_comment": "Xem xét tìm các biến công cụ mạnh hơn. Thống kê F tối thiểu hiện tại: {:.2f}",
            "action_invalid_instr_issue": "Kiểm định Hansen bác bỏ tính hợp lệ của biến công cụ",
            "action_invalid_instr_comment": "Xem xét giảm số lượng biến công cụ hoặc kiểm tra phương sai sai số thay đổi. Hansen p-value: {:.4f}",
            "action_serial_corr_issue": "Kiểm định AR(2) cho thấy vẫn còn tự tương quan",
            "action_serial_corr_comment": "Xem xét sử dụng các độ trễ sâu hơn hoặc đặc tả GMM khác. AR(2) p-value: {:.4f}",
            "action_non_linearity_issue": "Phát hiện tính phi tuyến (p={:.4f})",
            "action_non_linearity_comment": "Xem xét thêm các số hạng đa thức hoặc biến đổi logarit cho biến '{}'",
            "summary_weak_instr": "- Biến công cụ yếu: Thống kê F hiện tại = {:.2f}",
            "summary_weak_instr_rec": "  Khuyến nghị: Tìm các biến công cụ mạnh hơn",
            "summary_invalid_instr": "- Biến công cụ không hợp lệ: Hansen p-value = {:.4f}",
            "summary_invalid_instr_rec": "  Khuyến nghị: Giảm số lượng biến công cụ hoặc kiểm tra phương sai sai số thay đổi",
            "summary_serial_corr": "- Tự tương quan: AR(2) p-value = {:.4f}",
            "summary_serial_corr_rec": "  Khuyến nghị: Sử dụng các độ trễ sâu hơn hoặc đặc tả GMM khác",
            "summary_non_linearity": "- Tính phi tuyến: RESET p-value = {:.4f}",
            "summary_non_linearity_rec": "  Khuyến nghị: Thêm các số hạng đa thức cho '{}'",
            "not_available": "Không có sẵn",
            "not_applicable": "Không áp dụng",
            "none": "Không có",
        }
    }

    language = params.get("language", "en")
    count = params.get("count", 1)
    t = translations.get(language, translations["en"])

    # Format title with iteration count if count > 1
    t = t.copy()  # Make a copy to avoid modifying the original translations
    t["title"] = format_title_with_count(t["title"], count, language)

    # Extract all parameters at the start
    now = datetime.now()
    timestamp = f"{now.microsecond // 10000:02d}"

    analysis_type = params.get('analysis_type', 'IV')

    output_dir = params.get('output_dir', f'{timestamp}_ad_panel')
    save_files = params.get('save_files', False)
    sig_level = params.get('significance_level', 0.05)
    endogenous_vars = params.get('endogenous_vars', [
        v.code for v in variables if v.role == VariableRole.ENDOGENOUS
    ])

    instrument_vars = params.get('instrument_vars', [
        v.code for v in variables if v.role == VariableRole.INDEPENDENT
    ])
    test_non_linearity = params.get('test_non_linearity', False)

    # Initialize outputs
    logs = []
    actions = []
    file_contents = {}
    results = {
        'initial_recommendation': {},
        'model_specification': {},
        'model_details': {},
        'diagnostics': {},
        'final_model': {},
        'remediation_actions': []
    }

    logs.append(t["title"])
    logs.append(t["msg"].format(analysis_type))
    logs.append(t["msg_1"].format(timestamp))

    try:
        # --- 1. Extract Initial Recommendations ---
        initial_rec = _extract_panel_recommendation(variables)
        absorbed_vars = _get_absorbed_variables(variables)
        time_invariant_vars = _get_time_invariant_variables(variables)

        results['initial_recommendation'] = initial_rec
        results['absorbed_variables'] = absorbed_vars
        results['time_invariant_variables'] = time_invariant_vars

        logs.append(t["msg_2"].format(initial_rec.get('model_type', 'None found')))
        logs.append(t["msg_3"].format(initial_rec.get('needs_remediation', False)))

        if absorbed_vars:
            logs.append(t["msg_4"].format(', '.join(absorbed_vars)))
        if time_invariant_vars:
            logs.append(t["msg_5"].format(', '.join(time_invariant_vars)))

        # Extract existing diagnostics
        existing_diagnostics = initial_rec.get('diagnostic_results', {})
        if existing_diagnostics:
            logs.append(t["logs_1"])
            for test, result in existing_diagnostics.items():
                if isinstance(result, dict) and 'p_value' in result:
                    logs.append(t["msg_6"].format(test, result['p_value']))

        # --- 2. Variable Identification ---
        dependent_var = next((v for v in variables if v.role == VariableRole.DEPENDENT), None)
        entity_index_var = next((v for v in variables if v.variable_type == VariableType.ENTITY_INDEX), None)
        time_index_var = next((v for v in variables if v.variable_type == VariableType.TIME_INDEX), None)

        if not all([dependent_var, entity_index_var, time_index_var]):
            error_msg = t["errormsg"]
            logs.append(t["msg_7"].format(error_msg))
            return ToolOutput(results={'error': error_msg}, logs=logs, file_contents={}, action=None)

        dep_name = dependent_var.code
        entity_name = entity_index_var.code
        time_name = time_index_var.code

        # --- 3. Data Preparation ---
        panel_data = data.set_index([entity_name, time_name]).copy()
        y = panel_data[dep_name]

        logs.append(t["msg_8"].format(panel_data.shape))
        logs.append(t["msg_9"].format(dep_name))
        logs.append(t["msg_10"].format(entity_name))
        logs.append(t["msg_11"].format(time_name))

        # --- 4. Model-Specific Analysis ---
        if analysis_type == 'IV':
            logs.append(t["logs_2"])

            if not endogenous_vars or not instrument_vars:
                error_msg = t["errormsg_1"]
                logs.append(t["msg_12"].format(error_msg))
                return ToolOutput(results={'error': error_msg}, logs=logs, file_contents={}, action=None)

            # Get exogenous variables - EXCLUDE instruments to avoid rank deficiency
            exog_vars = [v.code for v in variables
                        if v.role == VariableRole.INDEPENDENT
                        and v.code not in endogenous_vars
                        and v.code not in instrument_vars  # KEY FIX: Exclude instruments
                        and v.code not in absorbed_vars]

            logs.append(t["msg_13"].format(', '.join(endogenous_vars)))
            logs.append(t["msg_14"].format(', '.join(instrument_vars)))
            logs.append(t["msg_15"].format(', '.join(exog_vars)))

            # Check if instruments are available in data
            missing_instruments = [var for var in instrument_vars  if var not in panel_data.columns]
            if missing_instruments:
                error_msg = t["msg_16"].format(', '.join(missing_instruments))
                logs.append(t["msg_17"].format(error_msg))
                return ToolOutput(results={'error': error_msg}, logs=logs, file_contents={}, action=None)

            # Check for instrument-exogenous overlap (should be empty after fix)
            overlap = set(instrument_vars) & set(exog_vars)
            if overlap:
                logs.append(t["msg_18"].format(', '.join(overlap)))
                logs.append(t["msg_19"].format(', '.join(overlap)))
                exog_vars = [v for v in exog_vars if v not in overlap]

            # Prepare data matrices
            X_exog = panel_data[exog_vars] if exog_vars else pd.DataFrame(index=panel_data.index)
            X_endog = panel_data[endogenous_vars]
            Z_instr = panel_data[instrument_vars]

            logs.append(t["msg_20"].format(y.shape, X_exog.shape, X_endog.shape, Z_instr.shape))

            # Check for rank deficiency before running IV
            try:
                # Check instrument matrix rank
                Z_rank = np.linalg.matrix_rank(Z_instr.values)
                logs.append(t["msg_21"].format(Z_rank, Z_instr.shape[1]))

                if Z_rank < Z_instr.shape[1]:
                    logs.append(t["logs_3"])

                # Check combined exogenous + instrument matrix rank
                if X_exog.shape[1] > 0:
                    combined_instr = np.column_stack([X_exog.values, Z_instr.values])
                    combined_rank = np.linalg.matrix_rank(combined_instr)
                    logs.append(t["msg_22"].format(combined_rank, combined_instr.shape[1]))

                    if combined_rank < combined_instr.shape[1]:
                        logs.append(t["logs_4"])

                        # Try to identify problematic instruments
                        corr_matrix = pd.DataFrame(combined_instr).corr()
                        high_corr_pairs = []
                        for i in range(len(corr_matrix.columns)):
                            for j in range(i+1, len(corr_matrix.columns)):
                                if abs(corr_matrix.iloc[i, j]) > 0.95:
                                    high_corr_pairs.append((i, j, corr_matrix.iloc[i, j]))

                        if high_corr_pairs:
                            logs.append(t["msg_23"].format(len(high_corr_pairs)))

            except Exception as rank_error:
                logs.append(t["msg_24"].format(str(rank_error)))

            # Run IV analysis
            iv_results = _run_iv_analysis(y, X_exog, X_endog, Z_instr,
                                        initial_rec.get('model_type', 'Fixed Effects'), t=t)

            if 'error' in iv_results:
                logs.append(t["msg_25"].format(iv_results['error']))

                # Try alternative approach - use only instruments that are not in other matrices
                logs.append(t["logs_5"])

                # Remove any instruments that might be causing issues
                clean_instr_vars = [v for v in instrument_vars if v not in exog_vars and v not in endogenous_vars]

                if clean_instr_vars:
                    logs.append(t["msg_26"].format(', '.join(clean_instr_vars)))
                    Z_instr_clean = panel_data[clean_instr_vars]

                    iv_results_clean = _run_iv_analysis(y, X_exog, X_endog, Z_instr_clean,
                                                      initial_rec.get('model_type', 'Fixed Effects'), t=t)

                    if 'error' not in iv_results_clean:
                        iv_results = iv_results_clean
                        logs.append(t["logs_6"])
                    else:
                        logs.append(t["msg_27"].format(iv_results_clean['error']))
                        return ToolOutput(results={'error': iv_results['error']}, logs=logs, file_contents={}, action=None)
                else:
                    logs.append(t["logs_7"])
                    return ToolOutput(results={'error': iv_results['error']}, logs=logs, file_contents={}, action=None)

            results['final_model'] = iv_results
            results['model_details'] = iv_results.get('model_details', {})
            results['diagnostics'].update(iv_results.get('diagnostics', {}))

            logs.append(t["logs_8"])

            # Report diagnostics
            diagnostics = iv_results.get('diagnostics', {})
            for test_name, test_result in diagnostics.items():
                if 'error' not in test_result:
                    logs.append(t["msg_28"].format(test_name, test_result.get('interpretation', 'N/A')))

            # Check for remediation needs
            needs_remediation = False

            # Check for weak instruments
            first_stage = diagnostics.get('first_stage_f', {})
            if first_stage.get('weak_instruments', False):
                needs_remediation = True
                min_f_stat = first_stage.get('min_f_statistic', 0)
                action = Action(
                    action_type=ActionType.TRANSFORM_VARIABLES,
                    method="run_advanced_panel_analysis",
                    issue=t["action_weak_instr_issue"],
                    comment=t["action_weak_instr_comment"].format(min_f_stat),
                    status="pending",
                    action_params={
                        'issue_type': 'weak_instruments',
                        'current_f_stat': min_f_stat,
                        'instruments': instrument_vars
                    }
                )
                actions.append(action)
                results['remediation_actions'].append(action.action_params)
                logs.append(t["logs_9"].format(min_f_stat))

            # Check endogeneity test
            wu_hausman = diagnostics.get('wu_hausman_test', {})
            if wu_hausman.get('significant', False):
                logs.append(t["logs_10"])
            else:
                logs.append(t["logs_11"])

            results['needs_remediation'] = needs_remediation

        elif analysis_type == 'GMM':
            logs.append(t["logs_12"])

            indep_vars = [v.code for v in variables
                         if v.role == VariableRole.INDEPENDENT
                         and v.code not in absorbed_vars]

            logs.append(t["msg_29"].format(', '.join(indep_vars)))

            # Run GMM analysis
            gmm_results = _run_gmm_analysis(data, dep_name, indep_vars, entity_name, time_name, t=t)

            if 'error' in gmm_results:
                logs.append(t["msg_30"].format(gmm_results['error']))
                return ToolOutput(results={'error': gmm_results['error']}, logs=logs, file_contents={}, action=None)

            results['final_model'] = gmm_results
            results['model_details'] = gmm_results.get('model_details', {})
            results['diagnostics'].update(gmm_results.get('diagnostics', {}))

            logs.append(t["logs_13"])

            # Report diagnostics
            diagnostics = gmm_results.get('diagnostics', {})
            hansen = diagnostics.get('hansen_test', {})
            ar_tests = diagnostics.get('ar_tests', {})

            logs.append(t["msg_31"].format(hansen.get('interpretation', 'N/A')))
            logs.append(t["msg_32"].format(ar_tests.get('ar1', {}).get('interpretation', 'N/A')))
            logs.append(t["msg_33"].format(ar_tests.get('ar2', {}).get('interpretation', 'N/A')))

            # Check for remediation needs
            needs_remediation = False

            # Check Hansen test
            if hansen.get('significant', False):
                needs_remediation = True
                hansen_p_value = hansen.get('p_value', 0)
                action = Action(
                    action_type=ActionType.TRANSFORM_VARIABLES,
                    method="run_advanced_panel_analysis",
                    issue=t["action_invalid_instr_issue"],
                    comment=t["action_invalid_instr_comment"].format(hansen_p_value),
                    status="pending",
                    action_params={
                        'issue_type': 'invalid_instruments',
                        'hansen_p_value': hansen_p_value
                    }
                )
                actions.append(action)
                results['remediation_actions'].append(action.action_params)
                logs.append(t["logs_14"].format(hansen_p_value))

            # Check AR(2) test
            ar2_result = ar_tests.get('ar2', {})
            if ar2_result.get('significant', False):
                needs_remediation = True
                ar2_p_value = ar2_result.get('p_value', 0)
                action = Action(
                    action_type=ActionType.TRANSFORM_VARIABLES,
                    method="run_advanced_panel_analysis",
                    issue=t["action_serial_corr_issue"],
                    comment=t["action_serial_corr_comment"].format(ar2_p_value),
                    status="pending",
                    action_params={
                        'issue_type': 'serial_correlation',
                        'ar2_p_value': ar2_p_value
                    }
                )
                actions.append(action)
                results['remediation_actions'].append(action.action_params)
                logs.append(t["logs_15"].format(ar2_p_value))

            results['needs_remediation'] = needs_remediation

        else:
            error_msg = t["msg_34"].format(analysis_type)
            logs.append(t["msg_35"].format(error_msg))
            return ToolOutput(results={'error': error_msg}, logs=logs, file_contents={}, action=None)

        # --- 5. Non-linearity Testing ---
        if test_non_linearity:
            logs.append(t["logs_16"])

            # Get variables for testing (exclude absorbed ones)
            test_vars = [v.code for v in variables
                        if v.role == VariableRole.INDEPENDENT
                        and v.code not in absorbed_vars]

            if test_vars:
                X_test = panel_data[test_vars]

                # Perform RESET test
                reset_results = _perform_ramsey_reset_test(
                    y, X_test,
                    entity_effects=(initial_rec.get('model_type') == 'Fixed Effects'),
                    t=t
                )

                results['diagnostics']['non_linearity_test'] = reset_results

                if 'error' not in reset_results:
                    p_val = reset_results.get('p_value', 1.0)
                    logs.append(t["logs_17"].format(p_val))

                    if reset_results.get('significant', False):
                        logs.append(t["logs_18"])

                        # Suggest transformation
                        if test_vars:
                            action = Action(
                                action_type=ActionType.TRANSFORM_VARIABLES,
                                method="run_advanced_panel_analysis",
                                issue=t["action_non_linearity_issue"].format(p_val),
                                comment=t["action_non_linearity_comment"].format(test_vars[0]),
                                status="pending",
                                action_params={
                                    'issue_type': 'non_linearity',
                                    'variable': test_vars[0],
                                    'transform_type': 'polynomial',
                                    'degree': 2,
                                    'reset_p_value': p_val
                                }
                            )
                            actions.append(action)
                            results['remediation_actions'].append(action.action_params)
                            logs.append(t["msg_36"].format(test_vars[0]))
                    else:
                        logs.append(t["logs_19"])
                else:
                    logs.append(t["msg_37"].format(reset_results['error']))
            else:
                logs.append(t["logs_20"])

        # --- 6. Generate Reports ---
        # Create detailed diagnostic summary
        diagnostic_summary = []
        for test_name, test_result in results['diagnostics'].items():
            if isinstance(test_result, dict) and 'error' not in test_result:
                if 'p_value' in test_result:
                    diagnostic_summary.append(f"- {test_name}: p-value = {test_result['p_value']:.4f}")
                    if 'interpretation' in test_result:
                        diagnostic_summary.append(f"  {test_result['interpretation']}")
                else:
                    diagnostic_summary.append(f"- {test_name}: {test_result}")
            elif isinstance(test_result, dict) and 'error' in test_result:
                diagnostic_summary.append(f"- {test_name}: ERROR - {test_result['error']}")

        # Create remediation summary
        remediation_summary = []
        for action in results.get('remediation_actions', []):
            issue_type = action.get('issue_type', 'Unknown')
            if issue_type == 'weak_instruments':
                remediation_summary.append(t["summary_weak_instr"].format(action.get('current_f_stat', 0.0)))
                remediation_summary.append(t["summary_weak_instr_rec"])
            elif issue_type == 'invalid_instruments':
                remediation_summary.append(t["summary_invalid_instr"].format(action.get('hansen_p_value', 0.0)))
                remediation_summary.append(t["summary_invalid_instr_rec"])
            elif issue_type == 'serial_correlation':
                remediation_summary.append(t["summary_serial_corr"].format(action.get('ar2_p_value', 0.0)))
                remediation_summary.append(t["summary_serial_corr_rec"])
            elif issue_type == 'non_linearity':
                remediation_summary.append(t["summary_non_linearity"].format(action.get('reset_p_value', 0.0)))
                remediation_summary.append(t["summary_non_linearity_rec"].format(action.get('variable', 'N/A')))

        # Generate comprehensive report
        report_content = f"""{t["report_header"]}
{"="*80}

{t["report_analysis_config"]}
{t["report_analysis_type"].format(analysis_type)}
{t["report_timestamp"].format(timestamp)}
{t["report_sig_level"].format(sig_level)}
{t["report_panel_shape"].format(panel_data.shape)}

{t["report_initial_model"]}
{t["report_model_type"].format(initial_rec.get('model_type', t["not_applicable"]))}
{t["report_robust_errors"].format(initial_rec.get('robust_errors_used', t["not_applicable"]))}
{t["report_needs_remediation"].format(initial_rec.get('needs_remediation', t["not_applicable"]))}

{t["report_var_config"]}
{t["report_dep_var"].format(dep_name)}
{t["report_entity_idx"].format(entity_name)}
{t["report_time_idx"].format(time_name)}
{t["report_absorbed_vars"].format(', '.join(absorbed_vars) if absorbed_vars else t["none"])}
{t["report_time_invariant"].format(', '.join(time_invariant_vars) if time_invariant_vars else t["none"])}

{t["report_model_spec"]}
{results['final_model'].get('summary', t["report_no_summary"])}

{t["report_diagnostic_results"]}
{chr(10).join(diagnostic_summary) if diagnostic_summary else t["report_no_diagnostics"]}

{t["report_remediation_actions"]}
{chr(10).join(remediation_summary) if remediation_summary else t["report_no_remediation"]}
"""

        # Create model-specific detailed outputs
        if analysis_type == 'IV':
            # IV-specific diagnostics file
            iv_diagnostics = results['final_model'].get('diagnostics', {})
            iv_recommendation = t["iv_use_stronger"] if iv_diagnostics.get('first_stage_f', {}).get('weak_instruments', False) else t["iv_adequate"]
            iv_details = f"""{t["iv_details_header"]}
{"="*40}

{t["iv_first_stage"]}
{iv_diagnostics.get('first_stage_f', {}).get('details', t["not_available"])}

{t["iv_endogeneity_test"]}
{t["iv_statistic"].format(iv_diagnostics.get('wu_hausman_test', {}).get('statistic', t["not_applicable"]))}
{t["iv_p_value"].format(iv_diagnostics.get('wu_hausman_test', {}).get('p_value', t["not_applicable"]))}
{t["iv_significant"].format(iv_diagnostics.get('wu_hausman_test', {}).get('significant', t["not_applicable"]))}

{t["iv_instrument_validity"]}
{t["iv_test"].format(iv_diagnostics.get('sargan_test', {}).get('test', t["not_applicable"]))}
{t["iv_statistic"].format(iv_diagnostics.get('sargan_test', {}).get('statistic', t["not_applicable"]))}
{t["iv_p_value"].format(iv_diagnostics.get('sargan_test', {}).get('p_value', t["not_applicable"]))}

{t["iv_weak_instruments"]}
{t["iv_min_f_stat"].format(iv_diagnostics.get('first_stage_f', {}).get('min_f_statistic', t["not_applicable"]))}
{t["iv_weak_instr_status"].format(iv_diagnostics.get('first_stage_f', {}).get('weak_instruments', t["not_applicable"]))}
{t["iv_recommendation"].format(iv_recommendation)}
"""
            iv_file_key = os.path.join(output_dir, f"iv_diagnostics.txt")
            file_contents[iv_file_key] = iv_details
            logs.append(t["msg_38"].format(iv_file_key))

        elif analysis_type == 'GMM':
            # GMM-specific diagnostics file
            gmm_diagnostics = results['final_model'].get('diagnostics', {})
            gmm_details = f"""{t["gmm_details_header"]}
{"="*40}

{t["gmm_hansen_test"]}
{t["iv_statistic"].format(gmm_diagnostics.get('hansen_test', {}).get('statistic', t["not_applicable"]))}
{t["iv_p_value"].format(gmm_diagnostics.get('hansen_test', {}).get('p_value', t["not_applicable"]))}
{t["gmm_degrees_freedom"].format(gmm_diagnostics.get('hansen_test', {}).get('df', t["not_applicable"]))}
{t["gmm_interpretation"].format(gmm_diagnostics.get('hansen_test', {}).get('interpretation', t["not_applicable"]))}

{t["gmm_ar1_test"]}
{t["iv_statistic"].format(gmm_diagnostics.get('ar_tests', {}).get('ar1', {}).get('statistic', t["not_applicable"]))}
{t["iv_p_value"].format(gmm_diagnostics.get('ar_tests', {}).get('ar1', {}).get('p_value', t["not_applicable"]))}
{t["gmm_interpretation"].format(gmm_diagnostics.get('ar_tests', {}).get('ar1', {}).get('interpretation', t["not_applicable"]))}

{t["gmm_ar2_test"]}
{t["iv_statistic"].format(gmm_diagnostics.get('ar_tests', {}).get('ar2', {}).get('statistic', t["not_applicable"]))}
{t["iv_p_value"].format(gmm_diagnostics.get('ar_tests', {}).get('ar2', {}).get('p_value', t["not_applicable"]))}
{t["gmm_interpretation"].format(gmm_diagnostics.get('ar_tests', {}).get('ar2', {}).get('interpretation', t["not_applicable"]))}

{t["gmm_model_command"]}
{results['final_model'].get('command', t["not_applicable"])}

{t["gmm_overall_validity"]}
{t["gmm_hansen_passed"].format(not gmm_diagnostics.get('hansen_test', {}).get('significant', True))}
{t["gmm_ar2_passed"].format(not gmm_diagnostics.get('ar_tests', {}).get('ar2', {}).get('significant', True))}
{t["gmm_model_valid"].format(not gmm_diagnostics.get('hansen_test', {}).get('significant', True) and not gmm_diagnostics.get('ar_tests', {}).get('ar2', {}).get('significant', True))}
"""
            gmm_file_key = os.path.join(output_dir, f"gmm_diagnostics.txt")
            file_contents[gmm_file_key] = gmm_details
            logs.append(t["msg_39"].format(gmm_file_key))

        # Create summary statistics file
        summary_stats = f"""{t["summary_header"]}
{"="*40}

{t["summary_dataset_info"]}
{t["summary_total_obs"].format(panel_data.shape[0])}
{t["summary_num_vars"].format(panel_data.shape[1])}
{t["summary_num_entities"].format(panel_data.index.get_level_values(0).nunique())}
{t["summary_num_periods"].format(panel_data.index.get_level_values(1).nunique())}
{t["summary_balanced"].format(panel_data.groupby(level=0).size().nunique() == 1)}

{t["summary_var_summary"]}
{panel_data.describe().to_string()}

{t["summary_missing"]}
{panel_data.isnull().sum().to_string()}

{t["summary_correlation"]}
{panel_data.select_dtypes(include=[np.number]).iloc[:, :10].corr().to_string()}
"""

        summary_file_key = os.path.join(output_dir, f"summary_statistics.txt")
        file_contents[summary_file_key] = summary_stats
        logs.append(t["summary"].format(summary_file_key))

        # Save main report
        report_file_key = os.path.join(output_dir, f"advanced_panel_report_{analysis_type}.txt")
        file_contents[report_file_key] = report_content
        logs.append(t["msg_40"].format(report_file_key))

        # Final summary logs
        logs.append(t["msg_41"].format(analysis_type))
        logs.append(t["msg_42"].format(len(results.get('remediation_actions', []))))
        logs.append(t["msg_43"].format(results.get('needs_remediation', False)))

        # Set model specification details
        results['model_specification'] = {
            'analysis_type': analysis_type,
            'dependent_variable': dep_name,
            'entity_index': entity_name,
            'time_index': time_name,
            'absorbed_variables': absorbed_vars,
            'time_invariant_variables': time_invariant_vars,
            'panel_shape': panel_data.shape,
            'balanced_panel': panel_data.groupby(level=0).size().nunique() == 1
        }

        if analysis_type == 'IV':
            results['model_specification'].update({
                'endogenous_vars': endogenous_vars,
                'instrument_vars': instrument_vars,
                'exogenous_vars': exog_vars if 'exog_vars' in locals() else []
            })
        elif analysis_type == 'GMM':
            results['model_specification'].update({
                'independent_vars': indep_vars if 'indep_vars' in locals() else [],
                'gmm_command': results['final_model'].get('command', 'N/A')
            })

        # Consolidate file saving at the end
        if save_files:
            os.makedirs(output_dir, exist_ok=True)
            for filename, content in file_contents.items():
                save_path = os.path.join(output_dir, os.path.basename(filename))
                try:
                    if filename.endswith(".png"):
                        try:
                            decoded_content = base64.b64decode(content)
                            with open(save_path, "wb") as f:
                                f.write(decoded_content)
                        except (TypeError, ValueError) as e:
                            logs.append(t["error"].format(filename, e))
                    elif filename.endswith((".csv", ".txt")):
                        with open(save_path, "w", encoding="utf-8") as f:
                            f.write(str(content))
                    else:
                        logs.append(t["warning"].format(filename))
                        try:
                            with open(save_path, "w", encoding="utf-8") as f:
                                f.write(str(content))
                        except Exception as e:
                            logs.append(t["msg_44"].format(filename, e))
                except Exception as e:
                    logs.append(t["msg_45"].format(filename, str(e)))

        return ToolOutput(
            results=serialize_dict(results),
            logs=logs,
            file_contents=file_contents,
            action=actions if actions else None
        )

    except Exception as e:
        error_msg = t["msg_46"].format(str(e))
        logs.append(error_msg)
        logs.append(t["error_1"].format(datetime.now().strftime('%Y-%m-%d %H:%M:%S')))

        # Generate error log file
        try:
            error_file_key = os.path.join(output_dir, f"error_log.txt")
            error_content = f"""{t["error_log_header"]}
{"="*50}

{t["error_log_message"].format(error_msg)}
{t["error_log_timestamp"].format(datetime.now().strftime('%Y-%m-%d %H:%M:%S'))}
{t["error_log_analysis_type"].format(analysis_type)}

{t["error_log_parameters"]}
{t["error_log_sig_level"].format(sig_level)}
{t["error_log_endogenous"].format(endogenous_vars)}
{t["error_log_instruments"].format(instrument_vars)}
{t["error_log_test_nonlin"].format(test_non_linearity)}

{t["error_log_var_config"]}
{chr(10).join([f"- {v.code} ({v.role.value if hasattr(v.role, 'value') else v.role})" for v in variables])}

{t["error_log_traceback"]}
{traceback.format_exc()}

{t["error_log_data_shape"].format(data.shape if 'data' in locals() else t["not_applicable"])}
{t["error_log_panel_shape"].format(panel_data.shape if 'panel_data' in locals() else t["not_applicable"])}
"""
            file_contents[error_file_key] = error_content
            logs.append(t["error_2"].format(error_file_key))

            # Save error log if file saving is enabled
            if save_files:
                os.makedirs(output_dir, exist_ok=True)
                try:
                    with open(error_file_key, 'w', encoding='utf-8') as f:
                        f.write(error_content)
                except Exception as save_error:
                    logs.append(t["error_3"].format(str(save_error)))

        except Exception as log_error:
            logs.append(t["error_4"].format(str(log_error)))

        return ToolOutput(
            results={'error': error_msg, 'timestamp': timestamp, 'analysis_type': analysis_type},
            logs=logs,
            file_contents=file_contents,
            action=None
        )