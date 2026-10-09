import pandas as pd
from typing import Optional
import io
import base64
import os
import matplotlib.pyplot as plt
import statsmodels.api as sm # For ACF/PACF plots
from datetime import datetime

from data_analysis.src.schemas.analyzer_states import (
    Variable, 
    Action, 
    ActionType, 
    ToolOutput, 
    VariableType, 
    VariableRole
)
from data_analysis.src.modules.tools.analysis.time.utils.statistical_tests import run_adf_test, run_kpss_test
from data_analysis.src.modules.tools.analysis.time.utils.transformations import apply_differencing
from data_analysis.src.modules.utils import serialize_dict
from data_analysis.src.modules.tools.analysis.cross_section.pipeline_utils import format_title_with_count

def fig_to_base64(fig: plt.Figure) -> str:
    """Converts a matplotlib Figure to a base64 encoded PNG string."""
    buf = io.BytesIO()
    try:
        fig.savefig(buf, format='png', bbox_inches='tight', dpi=300)
    except Exception as e:
        print(f"Error saving figure to buffer: {e}")
        return ""
    finally:
        plt.close(fig)
    buf.seek(0)
    img_str = base64.b64encode(buf.getvalue()).decode('utf-8')
    return img_str


def _determine_stationarity_from_tests(
    var_code: str,
    series: pd.Series,
    tests_to_run: list[str],
    sig_level: float,
    adf_params: dict,
    kpss_params: dict,
    logs: list[str],
    t: dict
) -> tuple[bool, dict]:
    """Helper to run stationarity tests and determine overall stationarity."""
    test_results_summary = {}
    is_stationary_overall = True

    # ADF Test
    if "adf" in tests_to_run:
        try:
            adf_result = run_adf_test(series, **adf_params, significance_level=sig_level, t=t)
            test_results_summary['adf'] = adf_result
            logs.append(t["test_adf"].format(
                var_code=var_code, p_value=adf_result['p_value'], interpretation=adf_result['interpretation']
            ))
            if adf_result['p_value'] > sig_level:
                is_stationary_overall = False
        except Exception as e:
            logs.append(t["test_adf_failed"].format(var_code=var_code, error=str(e)))
            test_results_summary['adf'] = {'error': str(e)}
            is_stationary_overall = False

    # KPSS Test
    if "kpss" in tests_to_run:
        try:
            kpss_result = run_kpss_test(series, **kpss_params, significance_level=sig_level, t=t)
            test_results_summary['kpss'] = kpss_result
            logs.append(t["test_kpss"].format(
                var_code=var_code, p_value=kpss_result['p_value_reported'], interpretation=kpss_result['interpretation']
            ))
            if kpss_result['p_value_numeric_for_decision'] is not None and kpss_result['p_value_numeric_for_decision'] < sig_level:
                is_stationary_overall = False
            elif kpss_result['p_value_numeric_for_decision'] is None and isinstance(kpss_result['p_value_reported'], str) and '<' in kpss_result['p_value_reported']:
                is_stationary_overall = False
        except Exception as e:
            logs.append(t["test_kpss_failed"].format(var_code=var_code, error=str(e)))
            test_results_summary['kpss'] = {'error': str(e)}
            is_stationary_overall = False

    return is_stationary_overall, test_results_summary

def _find_differencing_order_iterative(
    input_series: pd.Series,
    max_order: int,
    diff_type: str,
    m_period: int,
    tests_to_run: list[str],
    sig_level: float,
    adf_params: dict,
    kpss_params: dict,
    logs: list[str],
    var_code_logging: str,
    t: dict
) -> tuple[int, Optional[pd.Series], bool]:
    """Iteratively applies differencing and tests for stationarity."""
    series_being_differenced = input_series.copy()

    for current_order in range(1, max_order + 1):
        diff_type_key = "diff_type_seasonal" if diff_type == 'seasonal' else "diff_type_regular"
        diff_type_log = t[diff_type_key]

        try:
            if diff_type == 'seasonal':
                series_after_one_more_diff, _ = apply_differencing(series_being_differenced, d=0, D=1, m=m_period)
            elif diff_type == 'regular':
                series_after_one_more_diff, _ = apply_differencing(series_being_differenced, d=1, D=0, m=0)
            else:
                logs.append(t["error_invalid_diff_type"].format(diff_type=diff_type, var_code=var_code_logging))
                return current_order - 1, series_being_differenced, False

            series_after_one_more_diff = series_after_one_more_diff.dropna()

            min_data_points = max(len(tests_to_run) * 5, 10)
            if len(series_after_one_more_diff) < min_data_points:
                logs.append(t["error_insufficient_data_diff"].format(
                    count=len(series_after_one_more_diff), diff_type=diff_type, order=current_order, var_code=var_code_logging
                ))
                return current_order - 1, series_being_differenced, False

            is_stat_now, _ = _determine_stationarity_from_tests(
                f"{var_code_logging}_{diff_type}{current_order}",
                series_after_one_more_diff, tests_to_run, sig_level, adf_params, kpss_params, logs, t
            )

            if is_stat_now:
                logs.append(t["diff_achieved_stationarity"].format(
                    diff_type=diff_type_log, order=current_order, var_code=var_code_logging
                ))
                return current_order, series_after_one_more_diff, True

            series_being_differenced = series_after_one_more_diff

        except Exception as e:
            logs.append(t["error_diff_failed"].format(
                diff_type=diff_type, order=current_order, var_code=var_code_logging, error=str(e)
            ))
            return current_order - 1, series_being_differenced, False

    logs.append(t["warning_max_diff_reached"].format(
        diff_type=diff_type, max_order=max_order, var_code=var_code_logging
    ))
    return max_order, series_being_differenced, False


def _create_enhanced_plots(series: pd.Series, var_code: str, series_type: str, output_dir_id: str,
                         acf_pacf_lags: Optional[int], file_contents: dict[str, str],
                         logs: list[str], t: dict, d: int = 0, D: int = 0, m: int = 0) -> None:
    """Create enhanced time series, ACF, and PACF plots."""
    try:
        # Time series plot with enhanced styling
        fig_ts, ax_ts = plt.subplots(figsize=(6, 3))
        ax_ts.plot(series.index, series.values, linewidth=1.5, color='steelblue', alpha=0.8)
        ax_ts.set_title(t["plot_title_ts"].format(var_code=var_code, series_type=series_type), fontsize=14, fontweight='bold', pad=20)
        ax_ts.set_xlabel(t.get("time", "Time"), fontsize=6)
        ax_ts.set_ylabel(t.get("value", "Value"), fontsize=6)
        ax_ts.grid(True, alpha=0.3, linestyle='--')
        ax_ts.spines['top'].set_visible(False)
        ax_ts.spines['right'].set_visible(False)
        plt.tight_layout()

        suffix = f"_d{d}_D{D}" if d > 0 or D > 0 else "_original"
        ts_plot_path = f"{output_dir_id}/{var_code}{suffix}_timeseries.png"
        file_contents[ts_plot_path] = fig_to_base64(fig_ts)
        logs.append(t["plot_timeseries"].format(var_code=var_code, series_type=series_type, path=ts_plot_path))

        # ACF Plot with enhanced styling
        fig_acf, ax_acf = plt.subplots(figsize=(6, 3))
        sm.graphics.tsa.plot_acf(series, ax=ax_acf, lags=acf_pacf_lags, zero=False, alpha=0.05)
        ax_acf.set_title(t["plot_title_acf"].format(var_code=var_code, series_type=series_type), fontsize=7, fontweight='bold', pad=20)
        ax_acf.grid(True, alpha=0.3, linestyle='--')
        ax_acf.spines['top'].set_visible(False)
        ax_acf.spines['right'].set_visible(False)
        plt.tight_layout()

        acf_plot_path = f"{output_dir_id}/{var_code}{suffix}_acf.png"
        file_contents[acf_plot_path] = fig_to_base64(fig_acf)
        logs.append(t["plot_acf"].format(var_code=var_code, series_type=series_type, path=acf_plot_path))

        # PACF Plot with enhanced styling
        fig_pacf, ax_pacf = plt.subplots(figsize=(6, 3))
        sm.graphics.tsa.plot_pacf(series, ax=ax_pacf, lags=acf_pacf_lags, zero=False, method='ywm', alpha=0.05)
        ax_pacf.set_title(t["plot_title_pacf"].format(var_code=var_code, series_type=series_type), fontsize=7, fontweight='bold', pad=20)
        ax_pacf.grid(True, alpha=0.3, linestyle='--')
        ax_pacf.spines['top'].set_visible(False)
        ax_pacf.spines['right'].set_visible(False)
        plt.tight_layout()

        pacf_plot_path = f"{output_dir_id}/{var_code}{suffix}_pacf.png"
        file_contents[pacf_plot_path] = fig_to_base64(fig_pacf)
        logs.append(t["plot_pacf"].format(var_code=var_code, series_type=series_type, path=pacf_plot_path))

    except Exception as e:
        logs.append(t["error_plot_failed"].format(var_code=var_code, series_type=series_type, error=str(e)))


def run_stationarity_assessment(
    data: pd.DataFrame,
    variables: list[Variable],
    params: dict
) -> ToolOutput:
    """
    Perform stationarity assessment and suggest differencing transformations if needed.
    
    This tool tests time series for stationarity using statistical tests (ADF, KPSS) and
    automatically determines appropriate differencing orders to achieve stationarity.
    
    Parameters:
        data: Input DataFrame containing the time series data
        variables: list of Variable objects describing the data columns
        params: dictionary containing analysis parameters:
            - target_variables (list[str]): variables to test for stationarity (default: dependent/endogenous variables)
            - tests_to_run (list[str]): statistical tests to perform ['adf', 'kpss'] (default: ['adf', 'kpss'])
            - significance_level (float): significance level for tests (default: 0.05)
            - adf_params (dict): parameters for ADF test (default: {'regression': 'ct', 'autolag': 'AIC'})
            - kpss_params (dict): parameters for KPSS test (default: {'regression': 'c', 'nlags': 'auto'})
            - acf_pacf_lags (int): number of lags for ACF/PACF plots (default: None)
            - max_d (int): maximum regular differencing order (default: 2)
            - max_D (int): maximum seasonal differencing order (default: 1)
            - auto_apply_differencing (bool): whether to automatically apply differencing (default: True)
            - seasonal_period (int): seasonal period for differencing (default: inferred from frequency)
            - output_dir (str): base output directory name (default: 'stationarity_assessment')
            - save_files (bool): whether to save generated files to disk (default: False)
    
    Returns:
        ToolOutput: Contains stationarity test results, differencing recommendations, 
                   diagnostic plots, and suggested transformation actions
    """
    
    # Parameter extraction and initialization
    target_variable_codes = params.get('target_variables', [
        var.code for var in variables
        if var.role in [VariableRole.DEPENDENT, VariableRole.ENDOGENOUS]
    ])
    tests_to_run = params.get('tests_to_run', ['adf', 'kpss'])
    sig_level = params.get('significance_level', 0.05)
    adf_params = params.get('adf_params', {'regression': 'ct', 'autolag': 'AIC'})
    kpss_params = params.get('kpss_params', {'regression': 'c', 'nlags': 'auto'})
    acf_pacf_lags = params.get('acf_pacf_lags', None)
    max_d = params.get('max_d', 2)
    max_D = params.get('max_D', 1)
    auto_apply_diff = params.get('auto_apply_differencing', True)
    seasonal_period_param = params.get('seasonal_period', None)
    base_output_dir = params.get("output_dir", "stationarity")
    save_files = params.get("save_files", False)

    # Translation dictionary
    translations = {
        "en": {
            "title": "# Stationarity Assessment Analysis\n\n",
            "test_adf": "ADF Test for {var_code}: p-value={p_value:.4f}, {interpretation}",
            "test_adf_failed": "ADF test failed for {var_code}: {error}",
            "test_kpss": "KPSS Test for {var_code}: p-value={p_value}, {interpretation}",
            "test_kpss_failed": "KPSS test failed for {var_code}: {error}",
            "error_invalid_diff_type": "Invalid differencing type '{diff_type}' for {var_code}",
            "error_insufficient_data_diff": "Insufficient data points ({count}) for {diff_type} differencing order {order} on {var_code}",
            "diff_achieved_stationarity": "{diff_type} differencing order {order} achieved stationarity for {var_code}",
            "error_diff_failed": "Error in {diff_type} differencing order {order} for {var_code}: {error}",
            "warning_max_diff_reached": "Maximum {diff_type} differencing order {max_order} reached for {var_code}, series remains non-stationary",
            "plot_timeseries": "Time series plot for {var_code} ({series_type}): {path}",
            "plot_acf": "ACF plot for {var_code} ({series_type}): {path}",
            "plot_pacf": "PACF plot for {var_code} ({series_type}): {path}",
            "error_plot_failed": "Error creating plots for {var_code} ({series_type}): {error}",
            "plot_title_ts": "Time Series: {var_code} ({series_type})",
            "plot_title_acf": "Autocorrelation Function: {var_code} ({series_type})",
            "plot_title_pacf": "Partial Autocorrelation Function: {var_code} ({series_type})",
            "error_no_target_vars": "No target variables specified for stationarity assessment",
            "error_time_index_not_found": "Time index column '{time_col}' not found in data",
            "status_freq_detected": "Time index frequency detected and set: {freq}",
            "status_freq_not_inferred": "Could not infer regular frequency from time index, proceeding without frequency constraint",
            "error_time_index_processing": "Error processing time index '{time_col}': {error}",
            "status_starting": "Starting stationarity assessment for time series variables",
            "error_var_not_found": "Variable '{var_code}' not found in data",
            "error_var_empty": "Variable '{var_code}' contains no valid data after removing missing values",
            "status_seasonal_from_properties": "Using seasonal period m={m} from variable properties for {var_code}",
            "status_seasonal_from_params": "Using seasonal period m={m} from parameters for {var_code}",
            "status_seasonal_inferred": "Inferred seasonal period m={m} from frequency {freq} for {var_code}",
            "status_no_seasonal": "No seasonal period detected for {var_code}, proceeding without seasonal differencing",
            "status_analyzing_var": "Analyzing stationarity for variable: {var_code} (seasonal period m={m})",
            "error_insufficient_data_test": "Insufficient data points ({count}) for reliable stationarity testing of {var_code}",
            "status_non_stationary": "Variable {var_code} is non-stationary, searching for appropriate differencing orders",
            "status_attempting_seasonal_diff": "Attempting seasonal differencing for {var_code} (m={m}, max_D={max_D})",
            "status_attempting_regular_diff": "Attempting regular differencing for {var_code} on {context} series (max_d={max_d})",
            "status_diff_solution_found": "Differencing solution found for {var_code}: d={d}, D={D}, m={m}",
            "warning_diff_no_stationarity": "Differencing attempts for {var_code} (d={d}, D={D}) did not achieve stationarity",
            "warning_no_diff_found": "No effective differencing orders found for non-stationary {var_code}",
            "warning_auto_diff_disabled": "Variable {var_code} is non-stationary but automatic differencing is disabled",
            "status_var_stationary": "Variable {var_code} is stationary, no transformation required",
            "status_summary_report": "Stationarity assessment summary report: {path}",
            "error_summary_failed": "Error generating summary report: {error}",
            "status_completed": "Stationarity assessment completed for {count} variables",
            "context_seasonally_differenced": "seasonally differenced (D={D})",
            "context_original": "original",
            "diff_type_seasonal": "Seasonal",
            "diff_type_regular": "Regular",
            "adf_stationary": "Reject H0 at {sig}% significance. Series is likely stationary (p-value: {p:.4f}).",
            "adf_non_stationary": "Fail to reject H0 at {sig}% significance. Series is likely non-stationary (p-value: {p:.4f}).",
            "kpss_stationary": "Fail to reject H0 at {sig}% significance. Series is likely stationary (p-value: {p}).",
            "kpss_non_stationary": "Reject H0 at {sig}% significance. Series is likely non-stationary (p-value: {p}).",
            "time": "Time",
            "value": "Value",
            "action_non_stat_issue": "Series {var_code} is non-stationary (requires differencing for stationarity)",
            "action_transform_diff_comment": "Apply differencing transformation (d={d}, D={D}, m={m}) to {var_code}",
            "action_remains_non_stat_issue": "Series {var_code} remains non-stationary after differencing attempts (d={d}, D={D})",
            "action_remains_non_stat_comment": "Manual review required for {var_code} stationarity - consider alternative transformations",
            "action_no_diff_issue": "Series {var_code} is non-stationary and no differencing solution was found",
            "action_no_diff_comment": "Manual review required for {var_code} - consider alternative transformations or adjust parameters",
            "action_auto_diff_disabled_issue": "Series {var_code} is non-stationary and automatic differencing is disabled",
            "action_auto_diff_disabled_comment": "Manual intervention required for {var_code} stationarity transformation",
            "action_reanalyze_transformed_issue": "Stationarity verification needed for transformed variables",
            "action_reanalyze_transformed_comment": "Re-assess stationarity for transformed variables: {vars_list}",
            "action_reanalyze_transformed_reflection": "Verify stationarity of {vars_list} after differencing"
        },
        "vi": {
            "title": "# Phân Tích Đánh Giá Tính Dừng\n\n",
            "test_adf": "Kiểm Định ADF cho {var_code}: p-value={p_value:.4f}, {interpretation}",
            "test_adf_failed": "Kiểm định ADF thất bại cho {var_code}: {error}",
            "test_kpss": "Kiểm Định KPSS cho {var_code}: p-value={p_value}, {interpretation}",
            "test_kpss_failed": "Kiểm định KPSS thất bại cho {var_code}: {error}",
            "error_invalid_diff_type": "Loại sai phân không hợp lệ '{diff_type}' cho {var_code}",
            "error_insufficient_data_diff": "Không đủ điểm dữ liệu ({count}) cho sai phân {diff_type} bậc {order} trên {var_code}",
            "diff_achieved_stationarity": "Sai phân {diff_type} bậc {order} đạt được tính dừng cho {var_code}",
            "error_diff_failed": "Lỗi trong sai phân {diff_type} bậc {order} cho {var_code}: {error}",
            "warning_max_diff_reached": "Đạt bậc sai phân {diff_type} tối đa {max_order} cho {var_code}, chuỗi vẫn không dừng",
            "plot_timeseries": "Biểu đồ chuỗi thời gian cho {var_code} ({series_type}): {path}",
            "plot_acf": "Biểu đồ ACF cho {var_code} ({series_type}): {path}",
            "plot_pacf": "Biểu đồ PACF cho {var_code} ({series_type}): {path}",
            "error_plot_failed": "Lỗi tạo biểu đồ cho {var_code} ({series_type}): {error}",
            "plot_title_ts": "Biểu đồ chuỗi thời gian: {var_code} ({series_type})",
            "plot_title_acf": "Hàm tự tương quan: {var_code} ({series_type})",
            "plot_title_pacf": "Hàm tự tương quan riêng: {var_code} ({series_type})",
            "error_no_target_vars": "Không có biến mục tiêu nào được chỉ định để đánh giá tính dừng",
            "error_time_index_not_found": "Không tìm thấy cột chỉ số thời gian '{time_col}' trong dữ liệu",
            "status_freq_detected": "Tần số chỉ số thời gian được phát hiện và thiết lập: {freq}",
            "status_freq_not_inferred": "Không thể suy ra tần số đều từ chỉ số thời gian, tiếp tục mà không có ràng buộc tần số",
            "error_time_index_processing": "Lỗi xử lý chỉ số thời gian '{time_col}': {error}",
            "status_starting": "Bắt đầu đánh giá tính dừng cho các biến chuỗi thời gian",
            "error_var_not_found": "Không tìm thấy biến '{var_code}' trong dữ liệu",
            "error_var_empty": "Biến '{var_code}' không chứa dữ liệu hợp lệ sau khi loại bỏ giá trị thiếu",
            "status_seasonal_from_properties": "Sử dụng chu kỳ mùa vụ m={m} từ thuộc tính biến cho {var_code}",
            "status_seasonal_from_params": "Sử dụng chu kỳ mùa vụ m={m} từ tham số cho {var_code}",
            "status_seasonal_inferred": "Suy ra chu kỳ mùa vụ m={m} từ tần số {freq} cho {var_code}",
            "status_no_seasonal": "Không phát hiện chu kỳ mùa vụ cho {var_code}, tiếp tục mà không có sai phân mùa vụ",
            "status_analyzing_var": "Phân tích tính dừng cho biến: {var_code} (chu kỳ mùa vụ m={m})",
            "error_insufficient_data_test": "Không đủ điểm dữ liệu ({count}) để kiểm định tính dừng đáng tin cậy của {var_code}",
            "status_non_stationary": "Biến {var_code} không dừng, đang tìm kiếm bậc sai phân phù hợp",
            "status_attempting_seasonal_diff": "Đang thử sai phân mùa vụ cho {var_code} (m={m}, max_D={max_D})",
            "status_attempting_regular_diff": "Đang thử sai phân thường cho {var_code} trên chuỗi {context} (max_d={max_d})",
            "status_diff_solution_found": "Tìm thấy giải pháp sai phân cho {var_code}: d={d}, D={D}, m={m}",
            "warning_diff_no_stationarity": "Các nỗ lực sai phân cho {var_code} (d={d}, D={D}) không đạt được tính dừng",
            "warning_no_diff_found": "Không tìm thấy bậc sai phân hiệu quả cho {var_code} không dừng",
            "warning_auto_diff_disabled": "Biến {var_code} không dừng nhưng sai phân tự động bị vô hiệu hóa",
            "status_var_stationary": "Biến {var_code} dừng, không cần biến đổi",
            "status_summary_report": "Báo cáo tóm tắt đánh giá tính dừng: {path}",
            "error_summary_failed": "Lỗi tạo báo cáo tóm tắt: {error}",
            "status_completed": "Đánh giá tính dừng hoàn tất cho {count} biến",
            "context_seasonally_differenced": "sai phân theo mùa (D={D})",
            "context_original": "gốc",
            "diff_type_seasonal": "Mùa vụ",
            "diff_type_regular": "Thường",
            "adf_stationary": "Bác bỏ H0 ở mức ý nghĩa {sig}%. Chuỗi có khả năng là chuỗi dừng (p-value: {p:.4f}).",
            "adf_non_stationary": "Chưa đủ cơ sở bác bỏ H0 ở mức ý nghĩa {sig}%. Chuỗi có khả năng là chuỗi không dừng (p-value: {p:.4f}).",
            "kpss_stationary": "Chưa đủ cơ sở bác bỏ H0 ở mức ý nghĩa {sig}%. Chuỗi có khả năng là chuỗi dừng (p-value: {p}).",
            "kpss_non_stationary": "Bác bỏ H0 ở mức ý nghĩa {sig}%. Chuỗi có khả năng là chuỗi không dừng (p-value: {p}).",
            "time": "Thời gian",
            "value": "Giá trị",
            "action_non_stat_issue": "Chuỗi {var_code} không dừng (cần sai phân để dừng)",
            "action_transform_diff_comment": "Áp dụng biến đổi sai phân (d={d}, D={D}, m={m}) cho {var_code}",
            "action_remains_non_stat_issue": "Chuỗi {var_code} vẫn không dừng sau thử sai phân (d={d}, D={D})",
            "action_remains_non_stat_comment": "Cần xem xét thủ công tính dừng của {var_code} - xem xét biến đổi thay thế",
            "action_no_diff_issue": "Chuỗi {var_code} không dừng và không tìm thấy giải pháp sai phân",
            "action_no_diff_comment": "Cần xem xét thủ công {var_code} - xem xét biến đổi thay thế hoặc điều chỉnh tham số",
            "action_auto_diff_disabled_issue": "Chuỗi {var_code} không dừng và sai phân tự động bị tắt",
            "action_auto_diff_disabled_comment": "Cần can thiệp thủ công cho biến đổi dừng của {var_code}",
            "action_reanalyze_transformed_issue": "Cần xác minh tính dừng cho biến đã biến đổi",
            "action_reanalyze_transformed_comment": "Đánh giá lại tính dừng cho các biến đã biến đổi: {vars_list}",
            "action_reanalyze_transformed_reflection": "Xác minh tính dừng của {vars_list} sau khi lấy sai phân"
        }
    }
    language = params.get("language", "en")
    count = params.get("count", 1)
    t = translations.get(language, translations["en"])

    # Format title with iteration count if count > 1
    t = t.copy()  # Make a copy to avoid modifying the original translations
    t["title"] = format_title_with_count(t["title"], count, language)

    # Initialize output containers
    logs = []
    file_contents = {}
    actions = []
    overall_summary_data = []

    # Generate timestamped output directory
    now = datetime.now()
    timestamp = f"{now.microsecond // 10000:02d}"
    output_dir_id = f"{timestamp}_{base_output_dir}"
    output_dir = os.path.join(os.path.dirname(base_output_dir) or ".", f"{timestamp}_{os.path.basename(base_output_dir)}")
    
    # Input validation
    if not target_variable_codes:
        logs.append(t["error_no_target_vars"])
        return ToolOutput(results={}, logs=logs, file_contents=file_contents, action=None)

    # Identify and process time index
    time_index_col_name = None
    time_index_var_meta: Optional[Variable] = None
    for var_meta in variables:
        if var_meta.variable_type == VariableType.TIME_INDEX:
            time_index_col_name = var_meta.code
            time_index_var_meta = var_meta
            break

    if not time_index_col_name or time_index_col_name not in data.columns:
        logs.append(t["error_time_index_not_found"].format(time_col=time_index_col_name))
        return ToolOutput(results={}, logs=logs, file_contents=file_contents, action=None)

    try:
        processed_data = data.copy()
        processed_data[time_index_col_name] = pd.to_datetime(processed_data[time_index_col_name])
        processed_data = processed_data.set_index(time_index_col_name).sort_index()

        inferred_freq = pd.infer_freq(processed_data.index)
        if inferred_freq:
            processed_data.index.freq = inferred_freq
            logs.append(t["status_freq_detected"].format(freq=inferred_freq))
        else:
            logs.append(t["status_freq_not_inferred"])

    except Exception as e:
        logs.append(t["error_time_index_processing"].format(time_col=time_index_col_name, error=str(e)))
        return ToolOutput(results={}, logs=logs, file_contents=file_contents, action=None)

    transformed_vars_for_reflection = []

    logs.append(t["title"])
    logs.append(t["status_starting"])
    
    # Main analysis loop for each target variable
    for var_code in target_variable_codes:
        if var_code not in processed_data.columns:
            logs.append(t["error_var_not_found"].format(var_code=var_code))
            overall_summary_data.append({'Variable': var_code, 'Error': 'Not found in data'})
            continue

        current_series = processed_data[var_code].dropna()
        if current_series.empty:
            logs.append(t["error_var_empty"].format(var_code=var_code))
            overall_summary_data.append({'Variable': var_code, 'Error': 'Empty series after NaN removal'})
            continue

        # Determine seasonal period
        variable_meta = next((v for v in variables if v.code == var_code), None)
        m_period_from_properties = 0
        if variable_meta and variable_meta.properties:
            m_period_from_properties = variable_meta.properties.get('seasonal_period', 0)

        if m_period_from_properties > 0:
            m_period = m_period_from_properties
            logs.append(t["status_seasonal_from_properties"].format(m=m_period, var_code=var_code))
        elif seasonal_period_param is not None and seasonal_period_param > 0:
            m_period = seasonal_period_param
            logs.append(t["status_seasonal_from_params"].format(m=m_period, var_code=var_code))
        else:
            m_period = 0
            if inferred_freq:
                try:
                    freq_map = {'A': 1, 'Q': 4, 'M': 12, 'W': 52, 'D': 7}
                    base_freq = inferred_freq[0]
                    inferred_m = freq_map.get(base_freq, 0)
                    if inferred_m > 1:
                        m_period = inferred_m
                        logs.append(t["status_seasonal_inferred"].format(m=m_period, freq=inferred_freq, var_code=var_code))
                except Exception:
                    pass
            if m_period <= 1:
                m_period = 0
                logs.append(t["status_no_seasonal"].format(var_code=var_code))

        logs.append(t["status_analyzing_var"].format(var_code=var_code, m=m_period))
        var_summary_row = {'Variable': var_code, 'Seasonal Period (m)': m_period}

        # Create original series plots
        _create_enhanced_plots(current_series, var_code, "Original", output_dir_id,
                             acf_pacf_lags, file_contents, logs, t)

        # Perform initial stationarity tests
        min_test_points = max(len(tests_to_run) * 5, 10)
        if len(current_series) < min_test_points:
            logs.append(t["error_insufficient_data_test"].format(count=len(current_series), var_code=var_code))
            var_summary_row['Is Stationary (Initial)'] = 'Insufficient Data'
            var_summary_row['Suggested d'] = 0
            var_summary_row['Suggested D'] = 0
            var_summary_row['Error'] = 'Insufficient Data'
            overall_summary_data.append(var_summary_row)
            continue

        is_stationary, test_results = _determine_stationarity_from_tests(
            var_code, current_series, tests_to_run, sig_level, adf_params, kpss_params, logs, t
        )
        
        var_summary_row['Is Stationary (Initial)'] = is_stationary
        if 'adf' in test_results:
            var_summary_row['ADF Stat (Initial)'] = test_results['adf'].get('test_statistic')
            var_summary_row['ADF p-val (Initial)'] = test_results['adf'].get('p_value')
        if 'kpss' in test_results:
            var_summary_row['KPSS Stat (Initial)'] = test_results['kpss'].get('test_statistic')
            var_summary_row['KPSS p-val (Initial)'] = test_results['kpss'].get('p_value_reported')

        d_final, D_final = 0, 0
        series_after_diff_for_plots = None

        if not is_stationary:
            logs.append(t["status_non_stationary"].format(var_code=var_code))

            if auto_apply_diff:
                series_for_diff_process = current_series.copy()
                current_d, current_D = 0, 0
                is_stat_after_diff = False

                # Seasonal differencing first
                if m_period > 1 and max_D > 0:
                    logs.append(t["status_attempting_seasonal_diff"].format(var_code=var_code, m=m_period, max_D=max_D))
                    D_found, s_diff_series, s_is_stat = _find_differencing_order_iterative(
                        series_for_diff_process, max_D, 'seasonal', m_period, tests_to_run,
                        sig_level, adf_params, kpss_params, logs, var_code, t
                    )
                    current_D = D_found
                    if s_diff_series is not None:
                        series_for_diff_process = s_diff_series
                        is_stat_after_diff = s_is_stat
                        series_after_diff_for_plots = s_diff_series

                # Regular differencing
                if not is_stat_after_diff and max_d > 0:
                    if current_D > 0:
                        diff_context = t["context_seasonally_differenced"].format(D=current_D)
                    else:
                        diff_context = t["context_original"]
                    logs.append(t["status_attempting_regular_diff"].format(var_code=var_code, context=diff_context, max_d=max_d))
                    d_found, r_diff_series, r_is_stat = _find_differencing_order_iterative(
                        series_for_diff_process, max_d, 'regular', 0, tests_to_run,
                        sig_level, adf_params, kpss_params, logs, var_code, t
                    )
                    current_d = d_found
                    if r_diff_series is not None:
                        series_for_diff_process = r_diff_series
                        is_stat_after_diff = r_is_stat
                        series_after_diff_for_plots = r_diff_series

                d_final, D_final = current_d, current_D
                var_summary_row['Suggested d'] = d_final
                var_summary_row['Suggested D'] = D_final
                var_summary_row['Is Stationary (After Suggested Diff)'] = is_stat_after_diff

                if d_final > 0 or D_final > 0:
                    if is_stat_after_diff:
                        logs.append(t["status_diff_solution_found"].format(var_code=var_code, d=d_final, D=D_final, m=m_period))

                        # Create plots for differenced series
                        if series_after_diff_for_plots is not None and not series_after_diff_for_plots.empty:
                            _create_enhanced_plots(series_after_diff_for_plots, var_code,
                                                 f"Differenced (d={d_final}, D={D_final})",
                                                 output_dir_id, acf_pacf_lags, file_contents, logs, t,
                                                 d_final, D_final, m_period)

                        # Create transformation action
                        action = Action(
                            action_type=ActionType.TRANSFORM_VARIABLES,
                            method="run_stationarity_assessment",
                            issue=t["action_non_stat_issue"].format(var_code=var_code),
                            comment=t["action_transform_diff_comment"].format(d=d_final, D=D_final, m=m_period, var_code=var_code),
                            status="pending",
                            action_params={
                                'variable': var_code,
                                'transform_type': 'differencing',
                                'transform_params': {'d': d_final, 'D': D_final, 'm': m_period}
                            }
                        )
                        actions.append(action)
                        transformed_vars_for_reflection.append(var_code)

                    else:
                        logs.append(t["warning_diff_no_stationarity"].format(var_code=var_code, d=d_final, D=D_final))
                        action = Action(
                            action_type=ActionType.RECHECK_DATA,
                            method="run_stationarity_assessment",
                            issue=t["action_remains_non_stat_issue"].format(var_code=var_code, d=d_final, D=D_final),
                            comment=t["action_remains_non_stat_comment"].format(var_code=var_code),
                            status="pending",
                            action_params={'variable_to_check': var_code}
                        )
                        actions.append(action)

                else:
                    logs.append(t["warning_no_diff_found"].format(var_code=var_code))
                    action = Action(
                        action_type=ActionType.RECHECK_DATA,
                        method="run_stationarity_assessment",
                        issue=t["action_no_diff_issue"].format(var_code=var_code),
                        comment=t["action_no_diff_comment"].format(var_code=var_code),
                        status="pending",
                        action_params={'variable_to_check': var_code}
                    )
                    actions.append(action)

            else:
                logs.append(t["warning_auto_diff_disabled"].format(var_code=var_code))
                var_summary_row['Suggested d'] = 0
                var_summary_row['Suggested D'] = 0
                var_summary_row['Is Stationary (After Suggested Diff)'] = False
                action = Action(
                    action_type=ActionType.RECHECK_DATA,
                    method="run_stationarity_assessment",
                    issue=t["action_auto_diff_disabled_issue"].format(var_code=var_code),
                    comment=t["action_auto_diff_disabled_comment"].format(var_code=var_code),
                    status="pending",
                    action_params={'variable_to_check': var_code}
                )
                actions.append(action)

        else:
            logs.append(t["status_var_stationary"].format(var_code=var_code))
            var_summary_row['Suggested d'] = 0
            var_summary_row['Suggested D'] = 0
            var_summary_row['Is Stationary (After Suggested Diff)'] = True

        overall_summary_data.append(var_summary_row)

    # Create re-analysis action for transformed variables
    if transformed_vars_for_reflection:
        vars_list_str = ', '.join(transformed_vars_for_reflection)
        reanalyze_action = Action(
            action_type=ActionType.REANALYZE,
            method="run_stationarity_assessment",
            issue=t["action_reanalyze_transformed_issue"],
            comment=t["action_reanalyze_transformed_comment"].format(vars_list=vars_list_str),
            status="pending",
            reflection_params={
                'tool': 'run_stationarity_assessment',
                'parameters': {
                    'target_variables': transformed_vars_for_reflection,
                    'tests_to_run': tests_to_run,
                    'significance_level': sig_level,
                    'adf_params': adf_params,
                    'kpss_params': kpss_params,
                    'auto_apply_differencing': False,
                    'save_files': save_files,
                    'output_dir': base_output_dir,
                    'language': language,
                    'count': count + 1
                },
                'comment': t["action_reanalyze_transformed_reflection"].format(vars_list=vars_list_str)
            },
            reset_actions=True
        )
        actions.append(reanalyze_action)

    # Generate summary report
    if overall_summary_data:
        summary_df = pd.DataFrame(overall_summary_data)
        summary_cols = ['Variable', 'Seasonal Period (m)', 'Is Stationary (Initial)']
        if 'adf' in tests_to_run:
            summary_cols.extend(['ADF Stat (Initial)', 'ADF p-val (Initial)'])
        if 'kpss' in tests_to_run:
            summary_cols.extend(['KPSS Stat (Initial)', 'KPSS p-val (Initial)'])
        summary_cols.extend(['Suggested d', 'Suggested D', 'Is Stationary (After Suggested Diff)', 'Error'])

        for col in summary_cols:
            if col not in summary_df.columns:
                summary_df[col] = None

        summary_df = summary_df.reindex(columns=[col for col in summary_cols if col in summary_df.columns])

        try:
            summary_table_csv = summary_df.to_csv(index=False)
            summary_csv_path = f"{output_dir_id}/stationarity_summary_report.csv"
            file_contents[summary_csv_path] = summary_table_csv
            logs.append(t["status_summary_report"].format(path=summary_csv_path))
        except Exception as e:
            logs.append(t["error_summary_failed"].format(error=str(e)))

    logs.append(t["status_completed"].format(count=len(target_variable_codes)))

    # Save files if requested
    if save_files:
        os.makedirs(output_dir, exist_ok=True)
        
        for filename, content in file_contents.items():
            save_path = os.path.join(output_dir, os.path.basename(filename))
            
            if filename.endswith(".png"):
                try:
                    decoded_content = base64.b64decode(content)
                    with open(save_path, "wb") as f:
                        f.write(decoded_content)
                except (TypeError, ValueError) as e:
                    print(f"Error decoding or saving image {filename}: {e}")
            
            elif filename.endswith((".csv", ".txt")):
                with open(save_path, "w", encoding="utf-8") as f:
                    f.write(str(content))
            
            else:
                print(f"Warning: Unknown file type for '{filename}'. Saving as text.")
                try:
                    with open(save_path, "w", encoding="utf-8") as f:
                        f.write(str(content))
                except Exception as e:
                    print(f"Could not save file {filename}: {e}")

    # Prepare final results
    tool_results = {
        row['Variable']: {k: v for k, v in row.items() if k != 'Variable' and pd.notna(v)}
        for row in overall_summary_data
    }
    
    return ToolOutput(
        results=serialize_dict(tool_results),
        logs=logs,
        file_contents=file_contents,
        action=actions if actions else None
    )