import base64
import io
from datetime import datetime
import os
import pandas as pd
import numpy as np
import matplotlib
import traceback
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import statsmodels.api as sm

from data_analysis.src.schemas.analyzer_states import (
    Variable, 
    Action, 
    ActionType, 
    ToolOutput, 
    VariableType, 
    VariableRole
)
from data_analysis.src.modules.tools.analysis.time.utils import plotting as ts_plotting
from data_analysis.src.modules.tools.analysis.time.utils import statistical_tests as ts_stat_tests
from data_analysis.src.modules.tools.analysis.time.utils import model_helpers as ts_model_helpers
from data_analysis.src.modules.utils import serialize_dict
from data_analysis.src.modules.tools.analysis.cross_section.pipeline_utils import format_title_with_count, get_iteration_suffix


# --- Helper Functions ---
def fig_to_base64(fig: plt.Figure) -> str:
    """Converts a matplotlib Figure to a base64 encoded string."""
    img_buf = io.BytesIO()
    fig.savefig(img_buf, format='png', bbox_inches='tight', dpi=150, facecolor='white')
    img_buf.seek(0)
    base64_string = base64.b64encode(img_buf.getvalue()).decode('utf-8')
    plt.close(fig)
    return base64_string


def df_to_csv_string(df: pd.DataFrame, index: bool = False) -> str:
    """Converts a pandas DataFrame to a CSV string."""
    return df.to_csv(index=index)


def _apply_simple_differencing(series: pd.Series, d: int = 0, D: int = 0, m: int = 0) -> pd.Series:
    """Applies seasonal and regular differencing to a series. Simplified version."""
    temp_series = series.copy()
    if m > 0 and D > 0:
        for _ in range(D):
            temp_series = temp_series.diff(m)
    if d > 0:
        for _ in range(d):
            temp_series = temp_series.diff(1)
    return temp_series.dropna()


def _determine_cointegrating_rank(johansen_result, significance_level: float = 0.05) -> int:
    """
    Determines the cointegrating rank from Johansen test results using the trace statistic.

    Args:
        johansen_result: The result object from statsmodels' run_johansen_cointegration_test.
        significance_level: The significance level to use for critical values (0.1, 0.05, 0.01).

    Returns:
        The estimated number of cointegrating relationships (rank).
    """
    crit_value_map = {0.10: 0, 0.05: 1, 0.01: 2}
    if significance_level not in crit_value_map:
        raise ValueError("Significance level must be one of 0.1, 0.05, or 0.01")
    crit_col_index = crit_value_map[significance_level]

    trace_stats = johansen_result.lr1
    crit_values = johansen_result.cvt[:, crit_col_index]

    rank = 0
    for i in range(len(trace_stats)):
        if trace_stats[i] > crit_values[i]:
            rank = i + 1
        else:
            break
    return rank


def _create_professional_plot_style():
    """Apply professional styling to matplotlib plots."""
    plt.style.use('seaborn-v0_8-whitegrid')
    plt.rcParams.update({
        'figure.facecolor': 'white',
        'axes.facecolor': 'white',
        'axes.edgecolor': 'black',
        'axes.linewidth': 0.8,
        'grid.alpha': 0.5,
        'grid.linewidth': 0.5,
        'font.size': 10,
        'axes.titlesize': 12,
        'axes.labelsize': 10,
        'xtick.labelsize': 9,
        'ytick.labelsize': 9,
        'legend.fontsize': 9,
        'figure.dpi': 150
    })


def run_model_structure_identification(
    data: pd.DataFrame,
    variables: list[Variable],
    params: dict
) -> ToolOutput:
    """
    Identify potential model structures and parameters based on data characteristics.

    This tool analyzes time series data to suggest optimal model specifications for various
    model families including ARIMA, SARIMA, ETS, VAR, VECM, and Granger causality tests.

    Parameters:
        data: Input DataFrame containing the time series data.
        variables: list of Variable objects describing the data columns.
        params: dictionary containing analysis parameters:
            - model_family (str): Type of model to analyze - 'ARIMA', 'SARIMA', 'ARIMAX', 'SARIMAX', 'ETS', 'VAR', 'VECM', 'GRANGER'.
            - target_variables (List[str]): List of target variable codes to analyze. (default: all endogenous and dependent variables)
            - exogenous_variables (List[str]): List of exogenous variable codes for ARIMAX/SARIMAX (default: all indepenedent vars).
            - differencing_orders (dict): Differencing orders for each variable {var_code: {'d': int, 'D': int, 'm': int}}.
            - seasonal_periods (dict): Seasonal periods for each variable {var_code: int}.
            - output_dir (str): Base output directory name (default: 'model_structure_identification').
            - save_files (bool): Whether to save generated files to disk (default: False).
            - acf_pacf_lags (int): Number of lags for ACF/PACF plots.
            - significance_level_vif (float): VIF threshold for multicollinearity detection (default: 5.0).
            - info_criterion (str): Information criterion for model selection - 'AIC', 'BIC', 'HQIC' (default: 'AIC').
            - significance_level_johansen (float): Significance level for Johansen test (default: 0.05).
            - language (str): language for output messages - "en" or "vi" (default: "en").
            
            ARIMA-specific parameters (arima_params):
                - p_max (int): Maximum AR order to test (default: 3).
                - q_max (int): Maximum MA order to test (default: 3).
                - P_max (int): Maximum seasonal AR order to test (default: 2).
                - Q_max (int): Maximum seasonal MA order to test (default: 2).
                - auto_select_orders (bool): Whether to automatically select orders (default: True).
                - trend (str): Trend component - 'c', 'ct', 'ctt', 'n' (default: 'c').
                
            ETS-specific parameters (ets_params):
                - auto_select_model (bool): Whether to automatically select ETS model (default: True).
                - error_types (list[str]): Error types to test - ['add', 'mul'] (default: ['add', 'mul']).
                - trend_types (list): Trend types to test - ['add', 'mul', None] (default: ['add', 'mul', None]).
                - seasonal_types (list): Seasonal types to test - ['add', 'mul', None] (default: ['add', 'mul', None]).
                - damped_trends (list[bool]): Whether to test damped trends (default: [False, True]).
                - force_seasonal (bool): Force seasonal component in model selection (default: False).
                
            VAR-specific parameters (var_params):
                - max_lags (int): Maximum lags to test for VAR (default: 10).
                - trend (str): Trend specification for VAR (default: 'c').
                
            VECM-specific parameters (vecm_params):
                - det_order_johansen (int): Deterministic order for Johansen test (default: 0).
                
            Granger-specific parameters (granger_params):
                - max_lags_for_var (int): Maximum lags for VAR underlying Granger test (default: 10).
                - trend_for_var (str): Trend specification for VAR underlying Granger test (default: 'c').
    
    Returns:
        ToolOutput: Contains analysis results, logs, file contents, and suggested actions.
    """
    # --- Parameter Extraction ---
    now = datetime.now()
    timestamp = f"{now.microsecond // 10000:02d}"
    base_output_dir = params.get("output_dir", "time_model_struc")
    save_files = params.get("save_files", False)
    output_dir_id = f"{timestamp}_{base_output_dir}"
    output_dir = os.path.join(os.path.dirname(base_output_dir) or ".", output_dir_id)
    
    # Target and exogenous variables
    target_variable_codes = params.get('target_variables', [
        var.code for var in variables 
        if var.role in [VariableRole.DEPENDENT, VariableRole.ENDOGENOUS]
    ])
    exogenous_variable_codes = params.get('exogenous_variables', [
        var.code for var in variables if var.role == VariableRole.INDEPENDENT
    ])
    
    # Model configuration
    model_family = params.get('model_family', '').upper()
    differencing_orders_map = params.get('differencing_orders', {})
    seasonal_periods_map = params.get('seasonal_periods', {})
    acf_pacf_lags = params.get('acf_pacf_lags', None)
    significance_level_vif = params.get('significance_level_vif', 5.0)
    info_criterion = params.get('info_criterion', 'AIC')
    significance_level_johansen = params.get('significance_level_johansen', 0.05)
    
    # Model-specific parameters
    arima_params = params.get('arima_params', {})
    p_max_user = arima_params.get('p_max', 3)
    q_max_user = arima_params.get('q_max', 3)
    P_max_user = arima_params.get('P_max', 2)
    Q_max_user = arima_params.get('Q_max', 2)
    auto_select_orders = arima_params.get('auto_select_orders', True)
    arima_trend = arima_params.get('trend', 'c')
    
    ets_params = params.get('ets_params', {})
    auto_select_model = ets_params.get('auto_select_model', True)
    force_seasonal = ets_params.get('force_seasonal', False)
    error_types = ets_params.get('error_types', ["add", "mul"])
    trend_types = ets_params.get('trend_types', ["add", "mul", None])
    seasonal_types = ets_params.get('seasonal_types', ["add", "mul", None])
    damped_trends = ets_params.get('damped_trends', [False, True])
    
    var_params = params.get('var_params', {})
    max_lags_var = var_params.get('max_lags', 10)
    var_trend = var_params.get('trend', 'c')
    
    vecm_params = params.get('vecm_params', {})
    det_order_johansen = vecm_params.get('det_order_johansen', 0)
    
    granger_params = params.get('granger_params', {})
    max_lags_granger = granger_params.get('max_lags_for_var', 10)
    granger_trend = granger_params.get('trend_for_var', 'c')

    language = params.get("language", "en")
    count = params.get("count", 1)

    # Define translations dictionary
    translations = {
        "en": {
            "title": "# Model Structure Identification Analysis ({})\n\n",
            "error_no_target": "**ERROR**: No target variables specified for analysis.\n",
            "error_no_model": "**ERROR**: Model family not specified.\n",
            "freq_inferred": "Data frequency inferred and set to: {}\n",
            "warn_no_freq": "**Warning**: Could not infer data frequency.\n",
            "error_time_index": "**Error** processing time index '{}': {}\n",
            "error_no_datetime": "**ERROR**: Data does not have a proper DatetimeIndex.\n",
            "using_diff_orders": "Using suggested differencing orders for '{}': {}\n",
            "analyzing_var": "\n### Analyzing {} for {} model specification\n",
            "error_var_not_found": "**ERROR**: Target variable '{}' not found in data.\n",
            "error_no_data": "**ERROR**: No data available for '{}' after removing missing values.\n",
            "diff_config": "Differencing configuration for {}: d={}, D={}, m={}\n",
            "error_insufficient_data": "**ERROR**: Insufficient data for {} ({} effective observations). Minimum 30 required.\n",
            "data_summary": "Data summary for {}: {} total observations, {} effective observations.\n",
            "reduced_search": "Reduced search space for {} due to sample size: p_max={}, q_max={}, P_max={}, Q_max={}.\n",
            "error_empty_series": "**ERROR**: Series for '{}' became empty after differencing.\n",
            "acf_plot": "The ACF plot for {} (stationarized): `{}`\n",
            "pacf_plot": "The PACF plot for {} (stationarized): `{}`\n",
            "warn_acf_pacf_error": "**Warning**: Error generating ACF/PACF plots for {}: {}\n",
            "auto_order_selection": "Performing automated order selection for {} using {}.\n",
            "ic_table": "The information criteria table for {}: `{}`\n",
            "warn_auto_failed": "**Warning**: Automated order selection for {} failed. All model combinations resulted in errors.\n",
            "optimal_model": "Optimal model for {} based on {}: {}.\n",
            "error_auto_selection": "**Error** during automated order selection for {}: {}\n",
            "manual_required": "Manual order selection required for {}. Please analyze ACF/PACF plots.\n",
            "multicol_analysis": "Performing multicollinearity analysis for exogenous variables: {}.\n",
            "vif_table": "The VIF analysis table for {} is available at: `{}`\n",
            "warn_high_vif": "**Warning**: High multicollinearity detected (VIF > {}) for: {}.\n",
            "no_multicol": "No significant multicollinearity detected among exogenous variables.\n",
            "error_vif": "**Error** calculating VIF: {}\n",
            "analyzing_ets": "\n### Analyzing {} for ETS model specification\n",
            "seasonal_inferred": "Seasonal period for {} inferred from data frequency: m={}.\n",
            "auto_ets_selection": "Performing automated ETS model selection for {} using {}.\n",
            "warn_force_seasonal": "**Warning**: `force_seasonal` is True but no seasonal period (m>1) is defined for {}. Ignoring this setting.\n",
            "enforce_seasonal": "Enforcing seasonal component in model selection.\n",
            "ets_comparison_table": "The ETS model comparison table for {}: `{}`\n",
            "note_nonseasonal_best": "**Note**: The best overall model for {} is non-seasonal ({}: {:.2f}). The best seasonal model has a higher {} of {:.2f}, suggesting weak seasonal patterns.\n",
            "suggested_ets": "Suggested ETS model for {}: {}\n",
            "warn_no_best_ets": "**Warning**: Could not determine best ETS model for {} using {}.\n",
            "auto_ets_disabled": "Automated ETS model selection disabled for {}. Manual specification required.\n",
            "error_requires_2vars": "**ERROR**: {} requires at least 2 target variables.\n",
            "vecm_prereq_check": "\n### Performing prerequisite check for VECM: All series should be non-stationary.\n",
            "error_vecm_stationary": "**ERROR**: VECM prerequisite failed. Variable '{}' is stationary. VECM is for cointegrated non-stationary series. Consider using a VAR model.\n",
            "warn_unknown_stationarity": "**Warning**: Stationarity status for '{}' is unknown. Run stationarity assessment first for reliable VECM analysis.\n",
            "error_not_enough_data": "**ERROR**: Not enough data points for {} analysis after dropping NaNs.\n",
            "determining_lag": "Determining optimal lag order for {} using up to {} lags.\n",
            "var_lag_summary": "The VAR Lag Order Selection summary is available at: `{}`\n",
            "suggested_var_lag": "Suggested VAR lag order p = {} based on {}.\n",
            "warn_no_optimal_lag": "**Warning**: Could not determine optimal lag using {}. Manual selection is needed.\n",
            "error_lag_selection": "**Error** during VAR lag order selection: {}\n",
            "johansen_test": "Performing Johansen cointegration test with lag order k_ar_diff={}.\n",
            "johansen_plot": "The Johansen cointegration test plot is available at: `{}`\n",
            "coint_rank_auto": "Automatically determined cointegrating rank r = {} at {}% significance.\n",
            "error_johansen": "**Error** during Johansen cointegration test: {}\n",
            "error_granger_2vars": "**ERROR**: Granger causality analysis requires at least 2 target variables.\n",
            "error_granger_data": "**ERROR**: Not enough data for Granger causality lag selection.\n",
            "granger_lag_det": "\n### Determining optimal lag length for Granger causality test (via VAR lag selection on {}).\n",
            "var_summary_granger": "The VAR Lag Order Selection summary (for Granger) is available at: `{}`\n",
            "suggested_granger_lag": "Suggested lag length for Granger causality tests: {} based on {}.\n",
            "warn_no_granger_lag": "**Warning**: Could not determine optimal lag for Granger using {}. Manual selection is needed.\n",
            "error_granger_lag": "**Error** during lag selection for Granger causality: {}\n",
            "error_unknown_model": "**ERROR**: Unknown or unsupported model family '{}'.\n",
            "complete": "\n**Model Structure Identification analysis complete.**\n",
            "time": "Time",
            "value": "Value",
            "action_sarimax_opt_issue": "Optimal SARIMAX parameters identified for '{var_code}' using {ic}.",
            "action_sarimax_opt_comment": "Store optimal SARIMAX parameters in variable properties for model estimation.",
            "action_ets_opt_issue": "Optimal ETS parameters identified for '{var_code}' based on {ic}.",
            "action_ets_opt_comment": "Store optimal ETS parameters in variable properties for model estimation.",
            "action_var_lag_issue": "Suggested VAR lag order for variables {vars} based on {ic}.",
            "action_var_lag_comment": "Store optimal VAR lag order (p={p}) in properties of all target variables.",
            "action_vecm_params_issue": "Suggested VECM parameters for variables {vars}.",
            "action_vecm_params_comment": "Store VECM parameters (k_ar_diff={k}, coint_rank={r}) in properties."
        },
        "vi": {
            "title": "# Phân Tích Xác Định Cấu Trúc Mô Hình ({})\n\n",
            "error_no_target": "**LỖI**: Không có biến mục tiêu nào được chỉ định cho phân tích.\n",
            "error_no_model": "**LỖI**: Loại mô hình không được chỉ định.\n",
            "freq_inferred": "Tần số dữ liệu được suy ra và đặt thành: {}\n",
            "warn_no_freq": "**Cảnh báo**: Không thể suy ra tần số dữ liệu.\n",
            "error_time_index": "**Lỗi** xử lý chỉ số thời gian '{}': {}\n",
            "error_no_datetime": "**LỖI**: Dữ liệu không có DatetimeIndex phù hợp.\n",
            "using_diff_orders": "Sử dụng bậc sai phân được đề xuất cho '{}': {}\n",
            "analyzing_var": "\n### Phân tích {} cho đặc tả mô hình {}\n",
            "error_var_not_found": "**LỖI**: Biến mục tiêu '{}' không tìm thấy trong dữ liệu.\n",
            "error_no_data": "**LỖI**: Không có dữ liệu nào cho '{}' sau khi loại bỏ giá trị thiếu.\n",
            "diff_config": "Cấu hình sai phân cho {}: d={}, D={}, m={}\n",
            "error_insufficient_data": "**LỖI**: Dữ liệu không đủ cho {} ({} quan sát hiệu quả). Tối thiểu 30 quan sát cần thiết.\n",
            "data_summary": "Tóm tắt dữ liệu cho {}: {} tổng quan sát, {} quan sát hiệu quả.\n",
            "reduced_search": "Giảm không gian tìm kiếm cho {} do kích thước mẫu: p_max={}, q_max={}, P_max={}, Q_max={}.\n",
            "error_empty_series": "**LỖI**: Chuỗi cho '{}' trở nên rỗng sau khi sai phân.\n",
            "acf_plot": "Biểu đồ ACF cho {} (đã tĩnh hóa): `{}`\n",
            "pacf_plot": "Biểu đồ PACF cho {} (đã tĩnh hóa): `{}`\n",
            "warn_acf_pacf_error": "**Cảnh báo**: Lỗi tạo biểu đồ ACF/PACF cho {}: {}\n",
            "auto_order_selection": "Thực hiện lựa chọn bậc tự động cho {} bằng {}.\n",
            "ic_table": "Bảng tiêu chí thông tin cho {}: `{}`\n",
            "warn_auto_failed": "**Cảnh báo**: Lựa chọn bậc tự động cho {} thất bại. Tất cả các tổ hợp mô hình đều gặp lỗi.\n",
            "optimal_model": "Mô hình tối ưu cho {} dựa trên {}: {}.\n",
            "error_auto_selection": "**Lỗi** trong quá trình lựa chọn bậc tự động cho {}: {}\n",
            "manual_required": "Yêu cầu lựa chọn bậc thủ công cho {}. Vui lòng phân tích biểu đồ ACF/PACF.\n",
            "multicol_analysis": "Thực hiện phân tích đa cộng tuyến cho biến ngoại sinh: {}.\n",
            "vif_table": "Bảng phân tích VIF cho {} có sẵn tại: `{}`\n",
            "warn_high_vif": "**Cảnh báo**: Phát hiện đa cộng tuyến cao (VIF > {}) cho: {}.\n",
            "no_multicol": "Không phát hiện đa cộng tuyến có ý nghĩa giữa các biến ngoại sinh.\n",
            "error_vif": "**Lỗi** tính VIF: {}\n",
            "analyzing_ets": "\n### Phân tích {} cho đặc tả mô hình ETS\n",
            "seasonal_inferred": "Chu kỳ theo mùa cho {} được suy ra từ tần số dữ liệu: m={}.\n",
            "auto_ets_selection": "Thực hiện lựa chọn mô hình ETS tự động cho {} bằng {}.\n",
            "warn_force_seasonal": "**Cảnh báo**: `force_seasonal` là True nhưng không có chu kỳ theo mùa (m>1) được định nghĩa cho {}. Bỏ qua cài đặt này.\n",
            "enforce_seasonal": "Bắt buộc thành phần theo mùa trong lựa chọn mô hình.\n",
            "ets_comparison_table": "Bảng so sánh mô hình ETS cho {}: `{}`\n",
            "note_nonseasonal_best": "**Lưu ý**: Mô hình tốt nhất tổng thể cho {} là không theo mùa ({}: {:.2f}). Mô hình theo mùa tốt nhất có {} cao hơn là {:.2f}, cho thấy mô hình theo mùa yếu.\n",
            "suggested_ets": "Mô hình ETS đề xuất cho {}: {}\n",
            "warn_no_best_ets": "**Cảnh báo**: Không thể xác định mô hình ETS tốt nhất cho {} bằng {}.\n",
            "auto_ets_disabled": "Lựa chọn mô hình ETS tự động bị vô hiệu hóa cho {}. Yêu cầu chỉ định thủ công.\n",
            "error_requires_2vars": "**LỖI**: {} yêu cầu ít nhất 2 biến mục tiêu.\n",
            "vecm_prereq_check": "\n### Thực hiện kiểm tra điều kiện tiên quyết cho VECM: Tất cả chuỗi nên là không dừng.\n",
            "error_vecm_stationary": "**LỖI**: Điều kiện tiên quyết VECM thất bại. Biến '{}' là dừng. VECM dành cho chuỗi không dừng có đồng tích hợp. Xem xét sử dụng mô hình VAR.\n",
            "warn_unknown_stationarity": "**Cảnh báo**: Trạng thái tính dừng cho '{}' không xác định. Chạy đánh giá tính dừng trước để phân tích VECM đáng tin cậy.\n",
            "error_not_enough_data": "**LỖI**: Không đủ điểm dữ liệu cho phân tích {} sau khi loại bỏ NaN.\n",
            "determining_lag": "Xác định bậc trễ tối ưu cho {} sử dụng tối đa {} bậc trễ.\n",
            "var_lag_summary": "Tóm tắt lựa chọn bậc trễ VAR có sẵn tại: `{}`\n",
            "suggested_var_lag": "Bậc trễ VAR đề xuất p = {} dựa trên {}.\n",
            "warn_no_optimal_lag": "**Cảnh báo**: Không thể xác định bậc trễ tối ưu bằng {}. Cần lựa chọn thủ công.\n",
            "error_lag_selection": "**Lỗi** trong quá trình lựa chọn bậc trễ VAR: {}\n",
            "johansen_test": "Thực hiện kiểm định đồng tích hợp Johansen với bậc trễ k_ar_diff={}.\n",
            "johansen_plot": "Biểu đồ kiểm định đồng tích hợp Johansen có sẵn tại: `{}`\n",
            "coint_rank_auto": "Xếp hạng đồng tích hợp được xác định tự động r = {} tại mức ý nghĩa {}%.\n",
            "error_johansen": "**Lỗi** trong quá trình kiểm định đồng tích hợp Johansen: {}\n",
            "error_granger_2vars": "**LỖI**: Phân tích nhân quả Granger yêu cầu ít nhất 2 biến mục tiêu.\n",
            "error_granger_data": "**LỖI**: Không đủ dữ liệu cho lựa chọn bậc trễ nhân quả Granger.\n",
            "granger_lag_det": "\n### Xác định độ dài bậc trễ tối ưu cho kiểm định nhân quả Granger (qua lựa chọn bậc trễ VAR trên {}).\n",
            "var_summary_granger": "Tóm tắt lựa chọn bậc trễ VAR (cho Granger) có sẵn tại: `{}`\n",
            "suggested_granger_lag": "Độ dài bậc trễ đề xuất cho kiểm định nhân quả Granger: {} dựa trên {}.\n",
            "warn_no_granger_lag": "**Cảnh báo**: Không thể xác định bậc trễ tối ưu cho Granger bằng {}. Cần lựa chọn thủ công.\n",
            "error_granger_lag": "**Lỗi** trong quá trình lựa chọn bậc trễ cho nhân quả Granger: {}\n",
            "error_unknown_model": "**LỖI**: Loại mô hình không xác định hoặc không được hỗ trợ '{}'.\n",
            "complete": "\n**Phân tích xác định cấu trúc mô hình hoàn tất.**\n",
            "time": "Thời gian",
            "value": "Giá trị",
            "action_sarimax_opt_issue": "Tham số SARIMAX tối ưu được xác định cho '{var_code}' sử dụng {ic}.",
            "action_sarimax_opt_comment": "Lưu tham số SARIMAX tối ưu vào thuộc tính biến để ước lượng mô hình.",
            "action_ets_opt_issue": "Tham số ETS tối ưu được xác định cho '{var_code}' dựa trên {ic}.",
            "action_ets_opt_comment": "Lưu tham số ETS tối ưu vào thuộc tính biến để ước lượng mô hình.",
            "action_var_lag_issue": "Đề xuất bậc trễ VAR cho các biến {vars} dựa trên {ic}.",
            "action_var_lag_comment": "Lưu bậc trễ VAR tối ưu (p={p}) vào thuộc tính của tất cả biến mục tiêu.",
            "action_vecm_params_issue": "Đề xuất tham số VECM cho các biến {vars}.",
            "action_vecm_params_comment": "Lưu tham số VECM (k_ar_diff={k}, coint_rank={r}) vào thuộc tính."
        }
    }

    # Get translations for selected language
    t = translations.get(language, translations["en"])

    # --- Initialization ---
    logs = []
    file_contents = {}
    actions = []
    tool_results = {"suggested_parameters": {}, "supporting_analysis": {}}

    _create_professional_plot_style()

    # Format title with iteration count if count > 1
    title = t["title"].format(model_family)
    title = format_title_with_count(title, count, language)
    logs.append(title)

    # Input validation
    if not target_variable_codes:
        logs.append(t["error_no_target"])
        return ToolOutput(results={}, logs=logs, file_contents=file_contents, action=actions)

    if not model_family:
        logs.append(t["error_no_model"])
        return ToolOutput(results={}, logs=logs, file_contents=file_contents, action=actions)

    # --- Data Processing ---
    time_index_col_name = next((var.code for var in variables if var.variable_type == VariableType.TIME_INDEX), None)
    
    processed_data = data.copy()
    if time_index_col_name and time_index_col_name in processed_data.columns:
        try:
            if not pd.api.types.is_datetime64_any_dtype(processed_data[time_index_col_name]):
                processed_data[time_index_col_name] = pd.to_datetime(processed_data[time_index_col_name])
            if processed_data.index.name != time_index_col_name:
                processed_data = processed_data.set_index(time_index_col_name)
            processed_data = processed_data.sort_index()
            if processed_data.index.freq is None:
                inferred_freq = pd.infer_freq(processed_data.index)
                if inferred_freq:
                    processed_data = processed_data.asfreq(inferred_freq)
                    logs.append(t["freq_inferred"].format(inferred_freq))
                else:
                    logs.append(t["warn_no_freq"])
        except Exception as e:
            logs.append(t["error_time_index"].format(time_index_col_name, e))
    elif not isinstance(processed_data.index, pd.DatetimeIndex):
        logs.append(t["error_no_datetime"])
        return ToolOutput(results={}, logs=logs, file_contents=file_contents, action=actions)

    # Infer differencing orders from variable properties if not provided
    if not differencing_orders_map:
        inferred_orders = {}
        for var in variables:
            if var.properties and 'differencing_orders_suggested' in var.properties:
                orders = var.properties['differencing_orders_suggested']
                if isinstance(orders, dict) and all(k in orders for k in ['d', 'D', 'm']):
                    inferred_orders[var.code] = orders
                    logs.append(t["using_diff_orders"].format(var.code, orders))
        if inferred_orders:
            differencing_orders_map = inferred_orders

    # --- Model Family Specific Analysis ---
    # (All logs below now use t["key"] – only the string parts changed)

    if model_family in ["ARIMA", "SARIMA", "ARIMAX", "SARIMAX"]:
        ic_for_selection = info_criterion.upper()

        for var_code in target_variable_codes:
            logs.append(t["analyzing_var"].format(var_code, model_family))
            tool_results["suggested_parameters"][var_code] = {}
            tool_results["supporting_analysis"][var_code] = {}

            if var_code not in processed_data.columns:
                logs.append(t["error_var_not_found"].format(var_code))
                continue

            all_vars_for_model = [var_code] + exogenous_variable_codes
            model_data = processed_data[all_vars_for_model].copy().dropna()

            if model_data.empty:
                logs.append(t["error_no_data"].format(var_code))
                continue

            series_original = model_data[var_code]
            exog_df = model_data[exogenous_variable_codes] if exogenous_variable_codes else None
            
            # Get differencing parameters
            diff_orders = differencing_orders_map.get(var_code, {'d': 0, 'D': 0, 'm': 0})
            d_known, D_known = diff_orders.get('d', 0), diff_orders.get('D', 0)
            m_known = diff_orders.get('m', seasonal_periods_map.get(var_code, 0))
            m_for_model = m_known if model_family in ["SARIMA", "SARIMAX"] else 0
            
            logs.append(t["diff_config"].format(var_code, d_known, D_known, m_for_model))
            
            # Data sufficiency check
            n_obs = len(series_original)
            n_effective_obs = n_obs - d_known - (D_known * m_for_model)
            
            if n_effective_obs < 30:
                logs.append(t["error_insufficient_data"].format(var_code, n_effective_obs))
                continue
            
            logs.append(t["data_summary"].format(var_code, n_obs, n_effective_obs))

            # Adjust search space based on data availability
            p_max, q_max, P_max, Q_max = p_max_user, q_max_user, P_max_user, Q_max_user
            if m_for_model > 1 and n_effective_obs < 250 or n_effective_obs < 50:
                p_max = min(p_max_user, 2); q_max = min(q_max_user, 2)
                P_max = min(P_max_user, 1); Q_max = min(Q_max_user, 1)
                logs.append(t["reduced_search"].format(var_code, p_max, q_max, P_max, Q_max))

            p_range = range(p_max + 1); q_range = range(q_max + 1)
            P_range = range(P_max + 1) if m_for_model > 1 else [0]
            Q_range = range(Q_max + 1) if m_for_model > 1 else [0]

            stationarized_series = _apply_simple_differencing(series_original, d=d_known, D=D_known, m=m_for_model)
            if stationarized_series.empty:
                logs.append(t["error_empty_series"].format(var_code))
                continue
            
            # Generate ACF/PACF plots
            try:
                fig_acf_pacf = ts_plotting.plot_acf_pacf(
                    stationarized_series, 
                    lags=acf_pacf_lags, 
                    title_suffix=f" - {var_code} (Stationarized)",
                    t=t
                )
                acf_plot_path = f"{output_dir_id}/{var_code}_stationarized_acf_pacf.png"
                file_contents[acf_plot_path] = fig_to_base64(fig_acf_pacf)
                logs.append(t["acf_plot"].format(var_code, acf_plot_path))
            except Exception as e:
                logs.append(t["warn_acf_pacf_error"].format(var_code, e))

            # Automated order selection
            if auto_select_orders:
                logs.append(t["auto_order_selection"].format(var_code, ic_for_selection))
                try:
                    ic_results_df = ts_model_helpers.get_information_criteria_for_arima_orders(
                        series=series_original, p_range=p_range, d_range=[d_known], q_range=q_range,
                        P_range=P_range, D_range=[D_known] if m_for_model > 1 else [0], Q_range=Q_range,
                        m=m_for_model, exog=exog_df, trend=arima_trend)

                    ic_results_df.sort_values(by=ic_for_selection, ascending=True, inplace=True)
                    
                    ic_table_path = f"{output_dir_id}/{var_code}_arima_ic_table.csv"
                    file_contents[ic_table_path] = df_to_csv_string(ic_results_df, index=False)
                    logs.append(t["ic_table"].format(var_code, ic_table_path))
                    
                    valid_results_df = ic_results_df.dropna(subset=[ic_for_selection])

                    if valid_results_df.empty:
                        logs.append(t["warn_auto_failed"].format(var_code))
                        tool_results["suggested_parameters"][var_code]['order'] = (None, d_known, None)
                        if m_for_model > 1: tool_results["suggested_parameters"][var_code]['seasonal_order'] = (None, D_known, None, m_for_model)
                    else:
                        best_order_row = valid_results_df.iloc[0]
                        suggested_p = int(best_order_row['p']); suggested_q = int(best_order_row['q'])
                        suggested_P = int(best_order_row['P']) if m_for_model > 1 else 0
                        suggested_Q = int(best_order_row['Q']) if m_for_model > 1 else 0
                        
                        final_suggested_params = {'model_order': (suggested_p, d_known, suggested_q), 'exogenous_variables': exogenous_variable_codes}
                        if m_for_model > 1: final_suggested_params['seasonal_order'] = (suggested_P, D_known, suggested_Q, m_for_model)
                        
                        tool_results["suggested_parameters"][var_code] = final_suggested_params
                        
                        order_desc = f"p={suggested_p}, d={d_known}, q={suggested_q}"
                        if m_for_model > 1: order_desc += f", P={suggested_P}, D={D_known}, Q={suggested_Q}, m={m_for_model}"
                        logs.append(t["optimal_model"].format(var_code, ic_for_selection, order_desc))
                        
                        actions.append(Action(
                            action_type=ActionType.UPDATE_VARIABLE_PROPERTIES,
                            method="run_model_structure_identification",
                            issue=t["action_sarimax_opt_issue"].format(var_code=var_code, ic=ic_for_selection),
                            comment=t["action_sarimax_opt_comment"],
                            status="approved",
                            action_params={"variable_code": var_code, "properties_to_update": {"model_specifications": {"SARIMAX": final_suggested_params}}}
                        ))
                except Exception as e:
                    logs.append(t["error_auto_selection"].format(var_code, e))
            else:
                tool_results["suggested_parameters"][var_code]['order'] = (None, d_known, None)
                if m_for_model > 1: tool_results["suggested_parameters"][var_code]['seasonal_order'] = (None, D_known, None, m_for_model)
                logs.append(t["manual_required"].format(var_code))

            if exog_df is not None and not exog_df.empty and exog_df.shape[1] > 1:
                logs.append(t["multicol_analysis"].format(exogenous_variable_codes))
                try:
                    vif_df = ts_model_helpers.calculate_vif(exog_df)
                    vif_table_path = f"{output_dir_id}/{var_code}_exog_vif_table.csv"
                    file_contents[vif_table_path] = df_to_csv_string(vif_df, index=True)
                    logs.append(t["vif_table"].format(var_code, vif_table_path))
                    tool_results["supporting_analysis"][var_code]["vif_values"] = vif_df.to_dict()
                    
                    high_vif_vars = vif_df[vif_df['VIF'] > significance_level_vif]
                    if not high_vif_vars.empty:
                        logs.append(t["warn_high_vif"].format(significance_level_vif, list(high_vif_vars.index)))
                    else:
                        logs.append(t["no_multicol"])
                except Exception as e:
                    logs.append(t["error_vif"].format(e))
            
            tool_results["suggested_parameters"][var_code]["exogenous_variables"] = exogenous_variable_codes
    
    # ETS Analysis
    elif model_family == "ETS":
        ic_for_selection = info_criterion.upper()

        for var_code in target_variable_codes:
            logs.append(t["analyzing_ets"].format(var_code))
            tool_results["suggested_parameters"][var_code] = {}

            if var_code not in processed_data.columns:
                logs.append(t["error_var_not_found"].format(var_code))
                continue
            
            series_original = processed_data[var_code].dropna()
            if series_original.empty:
                logs.append(t["error_no_data"].format(var_code))
                continue
            
            # Determine seasonal period
            m_known = seasonal_periods_map.get(var_code, 0)
            if m_known <= 1 and processed_data.index.freqstr:
                freq_str = processed_data.index.freqstr.upper()
                if 'A' in freq_str: m_known = 1
                elif 'Q' in freq_str: m_known = 4
                elif 'M' in freq_str: m_known = 12
                elif 'W' in freq_str: m_known = 52
                elif 'D' in freq_str: m_known = 7
                if m_known > 1: logs.append(t["seasonal_inferred"].format(var_code, m_known))

            if auto_select_model:
                logs.append(t["auto_ets_selection"].format(var_code, ic_for_selection))
                
                current_force_seasonal = force_seasonal
                if current_force_seasonal and m_known <= 1:
                    logs.append(t["warn_force_seasonal"].format(var_code))
                    current_force_seasonal = False
                
                if current_force_seasonal: logs.append(t["enforce_seasonal"])

                try:
                    ic_results_df = ts_model_helpers.get_information_criteria_for_ets(
                        series=series_original, error_types=error_types, trend_types=trend_types,
                        seasonal_types=seasonal_types, seasonal_periods=m_known if m_known > 1 else None,
                        damped_trends=damped_trends, force_seasonal=current_force_seasonal)
                    
                    ic_table_path = f"{output_dir_id}/{var_code}_ets_ic_table.csv"
                    file_contents[ic_table_path] = df_to_csv_string(ic_results_df, index=False)
                    logs.append(t["ets_comparison_table"].format(var_code, ic_table_path))

                    valid_results_df = ic_results_df.dropna(subset=[ic_for_selection])

                    if not valid_results_df.empty:
                        best_model_row = valid_results_df.loc[valid_results_df[ic_for_selection].idxmin()]
                        
                        best_model_is_seasonal = pd.notna(best_model_row['Seasonal'])
                        if m_known > 1 and not best_model_is_seasonal and not current_force_seasonal:
                            seasonal_models_df = valid_results_df[pd.notna(valid_results_df['Seasonal'])]
                            if not seasonal_models_df.empty:
                                best_seasonal_model_row = seasonal_models_df.loc[seasonal_models_df[ic_for_selection].idxmin()]
                                logs.append(t["note_nonseasonal_best"].format(
                                    var_code, ic_for_selection, best_model_row[ic_for_selection],
                                    ic_for_selection, best_seasonal_model_row[ic_for_selection]))

                        suggested_ets_params = {
                            'error': best_model_row['Error'], 'trend': best_model_row['Trend'],
                            'seasonal': best_model_row['Seasonal'], 'damped_trend': best_model_row['Damped'],
                            'seasonal_periods': m_known if pd.notna(best_model_row['Seasonal']) and m_known > 1 else None
                        }
                        tool_results["suggested_parameters"][var_code]['ets_model'] = suggested_ets_params
                        logs.append(t["suggested_ets"].format(var_code, suggested_ets_params))

                        actions.append(Action(
                            action_type=ActionType.UPDATE_VARIABLE_PROPERTIES,
                            method="run_model_structure_identification",
                            issue=t["action_ets_opt_issue"].format(var_code=var_code, ic=ic_for_selection),
                            comment=t["action_ets_opt_comment"],
                            status="approved",
                            action_params={"variable_code": var_code, "properties_to_update": {"model_specifications": {"ETS": suggested_ets_params}}}
                        ))
                    else:
                        logs.append(t["warn_no_best_ets"].format(var_code, ic_for_selection))
                except Exception as e:
                    print(f"Error during automated ETS model selection for {var_code}: {e}\n{traceback.format_exc()}")
            else:
                logs.append(t["auto_ets_disabled"].format(var_code))
                tool_results["suggested_parameters"][var_code]['ets_model'] = {'error': None, 'trend': None, 'seasonal': None, 'damped_trend': None, 'seasonal_periods': m_known if m_known > 1 else None}

    elif model_family in ["VAR", "VECM"]:
        if len(target_variable_codes) < 2:
            logs.append(t["error_requires_2vars"].format(model_family))
            return ToolOutput(results=tool_results, logs=logs, file_contents=file_contents, action=actions)

        if model_family == "VECM":
            logs.append(t["vecm_prereq_check"])
            all_series_non_stationary = True
            for var_code in target_variable_codes:
                var_meta = next((v for v in variables if v.code == var_code), None)
                is_stationary = var_meta.properties.get('stationarity_analysis', {}).get('is_stationary') if var_meta else None
                if is_stationary is True:
                    logs.append(t["error_vecm_stationary"].format(var_code))
                    all_series_non_stationary = False
                elif is_stationary is None:
                    logs.append(t["warn_unknown_stationarity"].format(var_code))
            if not all_series_non_stationary:
                 return ToolOutput(results=tool_results, logs=logs, file_contents=file_contents, action=actions)

        var_data = processed_data[target_variable_codes].dropna()
        max_lags_to_test = min(max_lags_var, (len(var_data) - 1) // 2)
        if var_data.empty or len(var_data) < max_lags_to_test + 5:
            logs.append(t["error_not_enough_data"].format(model_family))
            return ToolOutput(results=tool_results, logs=logs, file_contents=file_contents, action=actions)

        ic_for_lag_sel_var = info_criterion.lower()
        logs.append(t["determining_lag"].format(model_family, max_lags_to_test))
        selected_lag_p = None
        try:
            lag_selection_results = ts_model_helpers.get_var_lag_order_selection(data=var_data, maxlags=max_lags_to_test, trend=var_trend)
            summary_path = f"{output_dir_id}/var_lag_selection_summary.txt"
            file_contents[summary_path] = lag_selection_results["full_selection_summary"]
            logs.append(t["var_lag_summary"].format(summary_path))
            tool_results["supporting_analysis"]["var_lag_selection_summary_file"] = summary_path

            lag_val = lag_selection_results["selected_lags_by_criterion"].get(ic_for_lag_sel_var)
            if lag_val is not None:
                selected_lag_p = int(lag_val)
                logs.append(t["suggested_var_lag"].format(selected_lag_p, ic_for_lag_sel_var.upper()))
            else:
                logs.append(t["warn_no_optimal_lag"].format(ic_for_lag_sel_var.upper()))
        except Exception as e:
            logs.append(t["error_lag_selection"].format(e))

        if selected_lag_p is not None:
            if model_family == "VAR":
                final_suggested_params = {'var_lags': selected_lag_p}
                tool_results["suggested_parameters"]['var_lags'] = selected_lag_p
                actions.append(Action(
                    action_type=ActionType.UPDATE_VARIABLE_PROPERTIES, 
                    method="run_model_structure_identification",
                    issue=t["action_var_lag_issue"].format(vars=target_variable_codes, ic=ic_for_lag_sel_var.upper()),
                    comment=t["action_var_lag_comment"].format(p=selected_lag_p),
                    status="pending",
                    action_params={"variable_codes": target_variable_codes, "properties_to_update": {"model_specifications": {"VAR": final_suggested_params}}}
                ))

            elif model_family == "VECM":
                k_ar_diff_johansen = selected_lag_p - 1 if selected_lag_p > 0 else 0
                logs.append(t["johansen_test"].format(k_ar_diff_johansen))
                try:
                    johansen_result_obj = ts_stat_tests.run_johansen_cointegration_test(data=var_data, det_order=det_order_johansen, k_ar_diff=k_ar_diff_johansen)
                    
                    fig_johansen = ts_plotting.plot_johansen_test_results(johansen_result_obj, target_variable_codes, t=t)
                    johansen_plot_path = f"{output_dir_id}/johansen_test_plot.png"
                    file_contents[johansen_plot_path] = fig_to_base64(fig_johansen)
                    logs.append(t["johansen_plot"].format(johansen_plot_path))
                    
                    coint_rank_r = _determine_cointegrating_rank(johansen_result_obj, significance_level=significance_level_johansen)
                    logs.append(t["coint_rank_auto"].format(coint_rank_r, significance_level_johansen*100))
                    
                    vecm_params_to_store = {'k_ar_diff': k_ar_diff_johansen, 'coint_rank': coint_rank_r}
                    tool_results["suggested_parameters"] = {'vecm_params': vecm_params_to_store}

                    actions.append(Action(
                        action_type=ActionType.UPDATE_VARIABLE_PROPERTIES, method="run_model_structure_identification",
                        issue=f"Suggested VECM parameters for variables {target_variable_codes}.",
                        comment=f"Store VECM parameters (k_ar_diff={k_ar_diff_johansen}, coint_rank={coint_rank_r}) in properties.", status="approved",
                        action_params={"variable_codes": target_variable_codes, "properties_to_update": {"model_specifications": {"VECM": vecm_params_to_store}}}
                    ))
                except Exception as e:
                    logs.append(t["error_johansen"].format(e))
        
        if exogenous_variable_codes:
            tool_results["suggested_parameters"]["exogenous_variables"] = exogenous_variable_codes

    # Granger Causality Lag Selection
    elif model_family == "GRANGER":
        if len(target_variable_codes) < 2:
            logs.append(t["error_granger_2vars"])
        else:
            granger_data = processed_data[target_variable_codes].dropna()
            max_lags_to_test = min(max_lags_granger, (len(granger_data) - 1) // 2)
            if granger_data.empty or len(granger_data) < max_lags_to_test + 5:
                logs.append(t["error_granger_data"])
            else:
                ic_for_lag_sel_granger = info_criterion.lower()
                logs.append(t["granger_lag_det"].format(target_variable_codes))
                try:
                    lag_selection_results = ts_model_helpers.get_var_lag_order_selection(data=granger_data, maxlags=max_lags_to_test, trend=granger_trend)
                    summary_path = f"{output_dir_id}/granger_lag_selection_summary.txt"
                    file_contents[summary_path] = lag_selection_results["full_selection_summary"]
                    logs.append(t["var_summary_granger"].format(summary_path))
                    tool_results["supporting_analysis"]["granger_lag_selection_summary_file"] = summary_path

                    selected_lag_granger = lag_selection_results["selected_lags_by_criterion"].get(ic_for_lag_sel_granger)
                    if selected_lag_granger is not None:
                        selected_lag_granger = int(selected_lag_granger)
                        logs.append(t["suggested_granger_lag"].format(selected_lag_granger, ic_for_lag_sel_granger.upper()))
                        tool_results["suggested_parameters"]['granger_lags'] = selected_lag_granger
                    else:
                        logs.append(t["warn_no_granger_lag"].format(ic_for_lag_sel_granger.upper()))
                except Exception as e:
                    logs.append(t["error_granger_lag"].format(e))
    else:
        logs.append(t["error_unknown_model"].format(model_family))

    logs.append(t["complete"])

    if save_files:
        os.makedirs(output_dir, exist_ok=True)
        for filename, content in file_contents.items():
            save_path = os.path.join(output_dir, os.path.basename(filename))
            if filename.endswith(".png"):
                try:
                    decoded_content = base64.b64decode(content)
                    with open(save_path, "wb") as f: f.write(decoded_content)
                except (TypeError, ValueError) as e:
                    print(f"Error decoding or saving image {filename}: {e}")
            elif filename.endswith((".csv", ".txt")):
                with open(save_path, "w", encoding="utf-8") as f: f.write(str(content))
            else:
                print(f"Warning: Unknown file type for '{filename}'. Saving as text.")
                try:
                    with open(save_path, "w", encoding="utf-8") as f: f.write(str(content))
                except Exception as e:
                    print(f"Could not save file {filename}: {e}")

    return ToolOutput(
        results=serialize_dict(tool_results),
        logs=logs,
        file_contents=file_contents,
        action=actions if actions else None
    )