import base64
import io
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from datetime import datetime
import statsmodels.api as sm

from typing import Any

from data_analysis.src.schemas.analyzer_states import Variable, Action, ActionType, ToolOutput
from data_analysis.src.modules.tools.analysis.time.utils import plotting as plotting_util
from data_analysis.src.modules.tools.analysis.time.utils import statistical_tests as statistical_tests_util

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

# --- Tool 6: Model Diagnostics & Refinement ---
def run_model_diagnostics(
    data: pd.DataFrame, # Original data (or data used for fitting)
    variables: list[Variable],
    params: dict,
    fitted_model: Any # The actual fitted model object from Tool 5
) -> ToolOutput:
    """
    Tool 6: Perform model diagnostics and suggest refinements.

    Parameters:
        data: Original data (or data used for fitting)
        variables: list of Variable objects
        params: dictionary containing analysis parameters
            - language (str): language for output messages - "en" or "vi" (default: "en")
        fitted_model: The actual fitted model object from Tool 5

    Returns:
        ToolOutput: Contains diagnostics results, logs, and suggested actions
    """
    language = params.get("language", "en")

    # Define translations dictionary
    translations = {
        "en": {
            "error_no_model": "Error: No fitted model provided for diagnostics.",
            "starting_diagnostics": "--- Starting Model Diagnostics for: {} ---",
            "warn_no_time_index": "Warning: Could not reliably assign time index to residuals. Using default numeric index.",
            "warn_empty_index": "Warning: Residuals index is empty. Using default numeric index.",
            "error_empty_residuals": "Error: Residuals are empty.",
            "error_extract_residuals": "Error extracting residuals: {}",
            "resid_overview_plot": "Residuals overview plot: `{}`",
            "error_plot_overview": "Error plotting residuals overview: {}",
            "acf_resid_plot": "ACF of residuals plot: `{}`",
            "pacf_resid_plot": "PACF of residuals plot: `{}`",
            "error_plot_acf_pacf": "Error plotting ACF/PACF of residuals: {}",
            "ljung_box_results": "Ljung-Box test results: `{}`",
            "warn_ljung_box": "Warning: Ljung-Box test indicates significant autocorrelation in residuals at lags: {} (p < {}).",
            "error_ljung_box": "Error running Ljung-Box test: {}",
            "shapiro_wilk_results": "Shapiro-Wilk normality test: Statistic={:.4f}, P-value={:.4f}. Interpretation: {}",
            "warn_shapiro_wilk": "Warning: Shapiro-Wilk test indicates residuals may not be normally distributed (p < {}).",
            "error_shapiro_wilk": "Error running Shapiro-Wilk test: {}",
            "breusch_pagan_results": "Breusch-Pagan homoscedasticity test: F-statistic={:.4f}, P-value={:.4f}. Interpretation: {}",
            "warn_breusch_pagan": "Warning: Breusch-Pagan test indicates heteroscedasticity in residuals (p < {}).",
            "skip_breusch_pagan": "Skipping Breusch-Pagan test: No suitable exogenous variables or fitted values for the test.",
            "error_breusch_pagan": "Error running Breusch-Pagan test: {}",
            "stability_check": "Model Stability Check: {}",
            "warn_unstable": "Warning: Model is UNSTABLE. Roots of characteristic polynomial are outside the unit circle.",
            "stability_plot": "Model stability roots plot: `{}`",
            "error_stability": "Error performing/plotting model stability check: {}",
            "diagnostics_ok": "\nModel diagnostics suggest the model meets key assumptions based on the tests performed.",
            "diagnostics_issues": "\nModel diagnostics identified potential issues. See suggested actions.",
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
            "var_unstable": "Model is unstable (some roots are on or outside the unit circle).",
            "ljung_box_issue": "Residual autocorrelation detected by Ljung-Box test at lags {model} {col} {lags}.",
            "ljung_box_comment": "Consider re-specifying model (e.g., different AR/MA orders, seasonal components).",
            "breusch_issue": "Heteroscedasticity detected by Breusch-Pagan test. {model} {col}",
            "breusch_comment": "Consider transformations (e.g., log, Box-Cox), using robust standard errors, or models that handle heteroscedasticity (e.g., GARCH).",
            "var_issue": "VAR/VECM model is unstable. {model}",
            "stability_comment": "Re-specify model (e.g., different lag order, ensure series are appropriately differenced/cointegrated)."
        },
        "vi": {
            "error_no_model": "Lỗi: Không có mô hình được cung cấp cho chẩn đoán.",
            "starting_diagnostics": "--- Bắt Đầu Chẩn Đoán Mô Hình cho: {} ---",
            "warn_no_time_index": "Cảnh báo: Không thể gán chỉ số thời gian cho phần dư một cách đáng tin cậy. Sử dụng chỉ số số mặc định.",
            "warn_empty_index": "Cảnh báo: Chỉ số phần dư trống. Sử dụng chỉ số số mặc định.",
            "error_empty_residuals": "Lỗi: Phần dư trống.",
            "error_extract_residuals": "Lỗi trích xuất phần dư: {}",
            "resid_overview_plot": "Biểu đồ tổng quan phần dư: `{}`",
            "error_plot_overview": "Lỗi vẽ biểu đồ tổng quan phần dư: {}",
            "acf_resid_plot": "Biểu đồ ACF của phần dư: `{}`",
            "pacf_resid_plot": "Biểu đồ PACF của phần dư: `{}`",
            "error_plot_acf_pacf": "Lỗi vẽ biểu đồ ACF/PACF của phần dư: {}",
            "ljung_box_results": "Kết quả kiểm định Ljung-Box: `{}`",
            "warn_ljung_box": "Cảnh báo: Kiểm định Ljung-Box cho thấy tự tương quan có ý nghĩa trong phần dư tại độ trễ: {} (p < {}).",
            "error_ljung_box": "Lỗi chạy kiểm định Ljung-Box: {}",
            "shapiro_wilk_results": "Kiểm định phân phối chuẩn Shapiro-Wilk: Thống kê={:.4f}, P-value={:.4f}. Giải thích: {}",
            "warn_shapiro_wilk": "Cảnh báo: Kiểm định Shapiro-Wilk cho thấy phần dư có thể không phân phối chuẩn (p < {}).",
            "error_shapiro_wilk": "Lỗi chạy kiểm định Shapiro-Wilk: {}",
            "breusch_pagan_results": "Kiểm định phương sai đồng nhất Breusch-Pagan: F-statistic={:.4f}, P-value={:.4f}. Giải thích: {}",
            "warn_breusch_pagan": "Cảnh báo: Kiểm định Breusch-Pagan cho thấy phương sai không đồng nhất trong phần dư (p < {}).",
            "skip_breusch_pagan": "Bỏ qua kiểm định Breusch-Pagan: Không có biến ngoại sinh hoặc giá trị khớp phù hợp cho kiểm định.",
            "error_breusch_pagan": "Lỗi chạy kiểm định Breusch-Pagan: {}",
            "stability_check": "Kiểm Tra Tính Ổn Định Mô Hình: {}",
            "warn_unstable": "Cảnh báo: Mô hình KHÔNG ỔN ĐỊNH. Nghiệm của đa thức đặc trưng nằm ngoài vòng tròn đơn vị.",
            "stability_plot": "Biểu đồ nghiệm tính ổn định mô hình: `{}`",
            "error_stability": "Lỗi thực hiện/vẽ biểu đồ kiểm tra tính ổn định mô hình: {}",
            "diagnostics_ok": "\nChẩn đoán mô hình cho thấy mô hình đáp ứng các giả định chính dựa trên các kiểm định đã thực hiện.",
            "diagnostics_issues": "\nChẩn đoán mô hình xác định các vấn đề tiềm ẩn. Xem các hành động được đề xuất.",
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
            "var_unstable": "Mô hình không ổn định (một số nghiệm nằm trên hoặc ngoài vòng tròn đơn vị).",
            "ljung_box_issue": "Phát hiện tự tương quan phần dư bởi kiểm định Ljung-Box tại độ trễ {model} {col} {lags}.",
            "ljung_box_comment": "Xem xét tái đặc tả mô hình (ví dụ: bậc AR/MA khác, thành phần mùa vụ).",
            "breusch_issue": "Phát hiện phương sai thay đổi bởi kiểm định Breusch-Pagan. {model} {col}",
            "breusch_comment": "Xem xét biến đổi (ví dụ: log, Box-Cox), sử dụng sai số chuẩn vững, hoặc mô hình xử lý phương sai thay đổi (ví dụ: GARCH).",
            "var_issue": "Mô hình VAR/VECM không ổn định. {model}",
            "stability_comment": "Tái đặc tả mô hình (ví dụ: bậc trễ khác, đảm bảo chuỗi sai phân/đồng tích hợp phù hợp)."
        }
    }

    # Get translations for selected language
    t = translations.get(language, translations["en"])

    logs = []
    file_contents = {}
    tool_results = {'diagnostics_summary': {}}
    actions = []

    # --- 1. Initialization and Parameter Extraction ---
    now = datetime.now()
    timestamp = f"{now.microsecond // 10000:02d}"
    base_output_name = params.get("output_name", "model_diagnostics")
    output_dir_id = f"{timestamp}_{base_output_name}"

    if fitted_model is None:
        logs.append(t["error_no_model"])
        return ToolOutput(results={"error": "No fitted model provided"}, logs=logs, file_contents=file_contents)

    model_type_from_object = type(fitted_model).__name__ # e.g. ARIMAResultsWrapper
    # model_type_param = params.get('model_type') # Could be used to confirm or guide
    logs.append(t["starting_diagnostics"].format(model_type_from_object))

    sig_level_ljung_box = params.get('significance_level_ljung_box', 0.05)
    sig_level_shapiro_wilk = params.get('significance_level_shapiro_wilk', 0.05)
    sig_level_breusch_pagan = params.get('significance_level_breusch_pagan', 0.05)
    ljung_box_lags = params.get('ljung_box_lags', None) # e.g., [10, 20] or int
    acf_pacf_lags = params.get('acf_pacf_lags', None) # Lags for ACF/PACF plots of residuals

    # --- 2. Residual Extraction and Basic Plots ---
    try:
        residuals = pd.Series(fitted_model.resid)
        if residuals.index.empty and hasattr(fitted_model, 'data') and hasattr(fitted_model.data, 'dates'):
             # For some models like VAR, residuals might not have a proper time index directly
             # Try to align with original data's index if possible
             # This needs careful handling based on how statsmodels returns residuals for each model type
             # For VAR, fitted_model.resid is usually a numpy array.
             # We need to get the original data's index that corresponds to these residuals.
             # This typically means skipping initial observations if differencing or lags were involved.
            if hasattr(fitted_model, 'nobs') and hasattr(data, 'index'):
                if len(residuals) == fitted_model.nobs and len(data.index[-fitted_model.nobs:]) == fitted_model.nobs:
                    residuals.index = data.index[-fitted_model.nobs:]
                else:
                    logs.append(t["warn_no_time_index"])
            else:
                 logs.append(t["warn_empty_index"])

        if residuals.empty:
            logs.append(t["error_empty_residuals"])
            return ToolOutput(results={"error": "Residuals are empty"}, logs=logs, file_contents=file_contents)
        tool_results['residuals_mean'] = residuals.mean()
        tool_results['residuals_std'] = residuals.std()
    except Exception as e:
        logs.append(t["error_extract_residuals"].format(e))
        return ToolOutput(results={"error": f"Error extracting residuals: {e}"}, logs=logs, file_contents=file_contents)

    # Plot: Residuals Overview (Time series, Histogram, Q-Q plot)
    try:
        fig_resid_overview = plotting_util.plot_residuals_overview(residuals, title="Residuals Analysis", t=t)
        resid_overview_path = f"{output_dir_id}/residuals_overview.png"
        file_contents[resid_overview_path] = fig_to_base64(fig_resid_overview)
        logs.append(t["resid_overview_plot"].format(resid_overview_path))
    except Exception as e:
        logs.append(t["error_plot_overview"].format(e))

    # Plot: ACF and PACF of Residuals (Separate figures as per Tool 3 example style)
    try:
        # ACF of Residuals
        fig_acf_resid = plt.figure(figsize=(5,2))
        ax_acf = fig_acf_resid.add_subplot(111)
        sm.graphics.tsa.plot_acf(residuals.dropna(), ax=ax_acf, lags=acf_pacf_lags, zero=False)
        ax_acf.set_title("ACF of Residuals")
        acf_resid_path = f"{output_dir_id}/residuals_acf.png"
        file_contents[acf_resid_path] = fig_to_base64(fig_acf_resid)
        logs.append(t["acf_resid_plot"].format(acf_resid_path))

        # PACF of Residuals
        fig_pacf_resid = plt.figure(figsize=(5,2))
        ax_pacf = fig_pacf_resid.add_subplot(111)
        sm.graphics.tsa.plot_pacf(residuals.dropna(), ax=ax_pacf, lags=acf_pacf_lags, method='ywm', zero=False)
        ax_pacf.set_title("PACF of Residuals")
        pacf_resid_path = f"{output_dir_id}/residuals_pacf.png"
        file_contents[pacf_resid_path] = fig_to_base64(fig_pacf_resid)
        logs.append(t["pacf_resid_plot"].format(pacf_resid_path))
    except Exception as e:
        logs.append(t["error_plot_acf_pacf"].format(e))


    # --- 3. Statistical Tests on Residuals ---
    # Ljung-Box Test (Autocorrelation)
    try:
        # model_df for Ljung-Box: number of estimated parameters in the model
        # This can be len(fitted_model.params) excluding intercept if model has one,
        # or more complex for VAR/VECM. For simplicity, can start with 0 if unsure,
        # or try to infer. A common heuristic is p+q for ARIMA(p,d,q) or P+Q for seasonal.
        # If model_df is too high, it can lead to issues.
        # Let's try to get it from fitted_model.df_model (degrees of freedom used by model)
        # or len(fitted_model.params).
        model_degrees_freedom = 0
        if hasattr(fitted_model, 'params'):
            model_degrees_freedom = len(fitted_model.params)
            # Adjust if an intercept/trend is implicitly included but not a "dynamic" parameter
            if hasattr(fitted_model, 'k_trend') and fitted_model.k_trend > 0:
                 model_degrees_freedom -= fitted_model.k_trend
            if hasattr(fitted_model, 'k_exog') and fitted_model.k_exog > 0: # Exog params
                 model_degrees_freedom -= fitted_model.k_exog


        lb_results_df = statistical_tests_util.run_ljung_box_test(residuals.dropna(), lags=ljung_box_lags, model_df=max(0, model_degrees_freedom))
        lb_csv_path = f"{output_dir_id}/ljung_box_test.csv"
        file_contents[lb_csv_path] = df_to_csv_string(lb_results_df, index=True)
        logs.append(t["ljung_box_results"].format(lb_csv_path))
        tool_results['diagnostics_summary']['ljung_box'] = lb_results_df.to_dict(orient='split')
        # Check significance
        if (lb_results_df['lb_pvalue'] < sig_level_ljung_box).any():
            failed_lags = lb_results_df[lb_results_df['lb_pvalue'] < sig_level_ljung_box].index.tolist()
            logs.append(t["warn_ljung_box"].format(failed_lags, sig_level_ljung_box))
            actions.append(Action(
                action_type=ActionType.MODIFY_MODEL_SPECIFICATION,
                method="run_model_diagnostics",
                issue=t["ljung_box_issue"].format(model_prefix=model_type_from_object, col='', failed_lags=failed_lags),
                comment=t["ljung_box_comment"],
                status="pending",
                reflection_params={'tool_name': 'Tool 4: Model Structure Identification'} # Or specific tool name
            ))
    except Exception as e:
        logs.append(t["error_ljung_box"].format(e))
        tool_results['diagnostics_summary']['ljung_box_error'] = str(e)

    # Shapiro-Wilk Test (Normality)
    try:
        sw_results = statistical_tests_util.run_shapiro_wilk_test(residuals.dropna(), significance_level=sig_level_shapiro_wilk, t=t)
        logs.append(t["shapiro_wilk_results"].format(sw_results.get('test_statistic', 'N/A'), sw_results.get('p_value', 'N/A'), sw_results.get('interpretation', 'N/A')))
        tool_results['diagnostics_summary']['shapiro_wilk'] = sw_results
        if sw_results.get('p_value', 1.0) < sig_level_shapiro_wilk:
            logs.append(t["warn_shapiro_wilk"].format(sig_level_shapiro_wilk))
            # This is often a weaker assumption, so action might be less direct
            # actions.append(Action(... consider transformations ...))
    except Exception as e:
        logs.append(t["error_shapiro_wilk"].format(e))
        tool_results['diagnostics_summary']['shapiro_wilk_error'] = str(e)

    # Breusch-Pagan Test (Homoscedasticity)
    try:
        exog_for_bp_test = None
        if hasattr(fitted_model.model, 'exog') and fitted_model.model.exog is not None:
            # Need to ensure it's aligned with residuals
            # This can be complex if there was pre-sample data or differencing.
            # For simplicity, if exog exists, try to use it.
            # A safer bet is often fitted_model.fittedvalues
            num_resid = len(residuals.dropna())
            exog_model = pd.DataFrame(fitted_model.model.exog) # Convert to DataFrame
            if len(exog_model) > num_resid: # Model exog might include pre-sample
                exog_for_bp_test = exog_model.iloc[-num_resid:].copy()
            elif len(exog_model) == num_resid:
                exog_for_bp_test = exog_model.copy()
            else: # Fallback to fitted values if alignment is tricky
                 exog_for_bp_test = pd.DataFrame({'fitted_values': fitted_model.fittedvalues})

            # Ensure exog_for_bp_test has same index as residuals for the test function
            exog_for_bp_test.index = residuals.dropna().index

        else: # No explicit exog, use fitted values
            exog_for_bp_test = pd.DataFrame({'fitted_values': fitted_model.fittedvalues}, index=residuals.dropna().index)

        if not exog_for_bp_test.empty:
            bp_results = statistical_tests_util.run_breusch_pagan_test(residuals.dropna(), exog_for_bp_test, significance_level=sig_level_breusch_pagan, t=t)
            logs.append(t["breusch_pagan_results"].format(bp_results.get('f_statistic', 'N/A'), bp_results.get('f_p_value', 'N/A'), bp_results.get('interpretation', 'N/A')))
            tool_results['diagnostics_summary']['breusch_pagan'] = bp_results
            if bp_results.get('f_p_value', 1.0) < sig_level_breusch_pagan:
                logs.append(t["warn_breusch_pagan"].format(sig_level_breusch_pagan))
                # Action could be to use robust standard errors, transform data, or use GARCH-type models
                actions.append(Action(
                    action_type=ActionType.MODIFY_MODEL_SPECIFICATION, # Or a new ActionType like "CONSIDER_ROBUST_ERRORS"
                    method="run_model_diagnostics",
                    issue=t["breusch_issue"].format(model_prefix=model_type_from_object, col=''),
                    comment=t["breusch_comment"],
                    status="pending",
                    reflection_params={'tool_name': 'Tool 2: Data Preprocessing'} # if transformation is chosen
                ))
        else:
            logs.append(t["skip_breusch_pagan"])

    except Exception as e:
        logs.append(t["error_breusch_pagan"].format(e))
        tool_results['diagnostics_summary']['breusch_pagan_error'] = str(e)

    # --- 4. Model-Specific Diagnostics (e.g., VAR/VECM Stability) ---
    if "VARResultsWrapper" in model_type_from_object or "VECMResultsWrapper" in model_type_from_object :
        try:
            stability_results = statistical_tests_util.check_var_model_stability(fitted_model, t=t)
            logs.append(t["stability_check"].format(stability_results.get('interpretation', 'N/A')))
            tool_results['diagnostics_summary']['model_stability'] = stability_results
            if not stability_results.get('is_stable', True):
                logs.append(t["warn_unstable"])
                actions.append(Action(
                    action_type=ActionType.MODIFY_MODEL_SPECIFICATION,
                    method="run_model_diagnostics",
                    issue="VAR/VECM model is unstable.",
                    comment="Re-specify model (e.g., different lag order, ensure series are appropriately differenced/cointegrated).",
                    status="pending",
                    reflection_params={'tool_name': 'Tool 4: Model Structure Identification'}
                ))

            # Plot VAR/VECM stability roots
            fig_stability = plotting_util.plot_var_stability(fitted_model, t=t) # Assumes VECM also has .plot_roots() or similar
            stability_plot_path = f"{output_dir_id}/model_stability_roots.png"
            file_contents[stability_plot_path] = fig_to_base64(fig_stability)
            logs.append(t["stability_plot"].format(stability_plot_path))

        except Exception as e:
            logs.append(t["error_stability"].format(e))
            tool_results['diagnostics_summary']['model_stability_error'] = str(e)

    # --- 5. Outlier Adjustment in Residuals (Cautious - Suggestion) ---
    # This is a placeholder for more advanced outlier detection in residuals.
    # For now, if residuals look problematic (e.g., very large spikes in overview plot),
    # a generic RECHECK_DATA action might be suggested.
    # A more specific action would involve identifying outlier timestamps and suggesting
    # dummy variables in Tool 2.

    # --- 6. Final Interpretation and Refinement Suggestions ---
    if not actions:
        logs.append(t["diagnostics_ok"])
    else:
        logs.append(t["diagnostics_issues"])

    # Close all matplotlib figures that might have been created by statsmodels internal plotting
    plt.close('all')

    return ToolOutput(
        results=tool_results,
        logs=logs,
        file_contents=file_contents,
        action=actions if actions else None
    )