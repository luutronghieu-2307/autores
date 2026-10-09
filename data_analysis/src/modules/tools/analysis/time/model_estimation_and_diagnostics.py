import base64
import io
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from datetime import datetime
import os
from statsmodels.tsa.statespace.sarimax import SARIMAX
from statsmodels.tsa.exponential_smoothing.ets import ETSModel
from statsmodels.tsa.api import VAR
from statsmodels.tsa.vector_ar.vecm import VECM

from typing import Optional, Any, Union
from data_analysis.src.schemas.analyzer_states import (
    Variable, 
    Action, 
    ActionType, 
    ToolOutput, 
    VariableType, 
    VariableRole
)

from data_analysis.src.modules.tools.analysis.time.utils import plotting as plotting_util
from data_analysis.src.modules.tools.analysis.time.utils import statistical_tests as statistical_tests_util
from data_analysis.src.modules.utils import serialize_dict
from data_analysis.src.modules.tools.analysis.cross_section.pipeline_utils import format_title_with_count

from data_analysis.src.modules.tools.analysis.time.model_application import _run_model_application_step

# --- Helper Functions ---
def fig_to_base64(fig: Figure) -> str:
    """Converts a matplotlib Figure to a base64 encoded string."""
    buf = io.BytesIO()
    fig.savefig(buf, format='png', bbox_inches='tight', dpi=300, facecolor='white')
    plt.close(fig)
    buf.seek(0)
    return base64.b64encode(buf.getvalue()).decode('utf-8')

def df_to_csv_string(df: pd.DataFrame, index: bool = False) -> str:
    """Converts a pandas DataFrame to a CSV string."""
    return df.to_csv(index=index)

def run_model_estimation_and_diagnostics(
    data: pd.DataFrame,
    variables: list[Variable],
    params: dict
) -> ToolOutput:
    """
    Combined Tool: Fits the specified model, performs initial evaluation,
    and then runs diagnostics on the fitted model.

    Parameters:
        data: Input DataFrame containing the time series data
        variables: List of Variable objects describing the data columns
        params: Dictionary containing analysis parameters
            - model_family (str): Model type -  'ARIMA', 'SARIMA', 'ARIMAX', 'SARIMAX', 'ETS', 'VAR', 'VECM'
            - target_variables_codes (List[str]): List of target variable codes (default: dependent var if not provided in both target params)
            - target_variable_code (str): Single target variable code (alternative to above)
            - exogenous_variables (List[str]): List of exogenous variable codes (default: all independent variables)
            - model_order (Tuple): ARIMA order (p, d, q) for SARIMAX (prioritize model specs (from model structure function) over this one, default (1.0.0))
            - seasonal_order (Tuple): Seasonal order (P, D, Q, s) for SARIMAX ( same as above)
            - trend (str): Trend component ('c', 'ct', 'n') for SARIMAX
            - ets_params (dict): Parameters for ETS model
            - var_lags (int): Number of lags for VAR model (default: 1)
            - vecm_params (dict): Parameters for VECM model
            - significance_level_ljung_box (float): P-value threshold for Ljung-Box test (default: 0.05)
            - significance_level_shapiro_wilk (float): P-value threshold for Shapiro-Wilk test (default: 0.05)
            - significance_level_breusch_pagan (float): P-value threshold for Breusch-Pagan test (default: 0.05)
            - ljung_box_lags (int): Number of lags for Ljung-Box test
            - acf_pacf_lags (int): Number of lags for ACF/PACF plots
            - irf_periods (int): Number of periods for Impulse Response Functions (default: 10)
            - fevd_steps (int): Number of steps for Forecast Error Variance Decomposition
            - application_params (dict): Parameters for model application step
            - output_dir (str): Base output directory name
            - save_files (bool): Whether to save generated files to disk
            - language (str): Language for output messages - "en" or "vi" (default: "en")

    Returns:
        ToolOutput: Contains results, logs, file contents, and suggested actions
    """

    # Translation dictionary
    translations = {
        "en": {
            "title": "# Model Estimation & Diagnostics Analysis\n\n",
            "model_type_not_specified": "Model type not specified in parameters.",
            "model_type_handled_by_sarimax": "Model type '{}' will be handled by the general SARIMAX implementation.",
            "auto_selecting_dependent": "No target variables specified. Auto-selecting dependent variables: {}",
            "no_target_and_no_dependent": "No target variables specified and no dependent variables found. Use 'target_variables_codes' or 'target_variable_code' parameter.",
            "no_target_specified": "No target variables specified. Use 'target_variables_codes' or 'target_variable_code' parameter.",
            "starting_estimation": "Starting Model Estimation & Diagnostics: {}",
            "time_index_not_found": "Time index variable not found in metadata.",
            "time_index_column_not_found": "Time index column '{}' not found in data.",
            "error_setting_time_index": "Error setting time index '{}': {}",
            "index_not_datetime": "Index '{}' is not a DatetimeIndex after processing.",
            "data_sorted": "Data sorted by time index.",
            "frequency_inferred": "Inferred and set frequency: {}",
            "frequency_not_inferred": "Warning: Could not infer frequency for the time series index.",
            "exog_vars_not_found": "One or more exogenous variables not found in data.",
            "exog_vars_handled": "Exogenous variables: {} (NaN values handled).",
            "exog_vars_still_nan": "Exogenous variables still contain NaN values after handling.",
            "exog_vars": "Exogenous variables: {}",
            "processing_sarimax": "Processing SARIMAX for target variable: {}",
            "target_var_not_found": "Target variable '{}' not found in data.",
            "target_series_empty": "Target series for '{}' is empty after dropping NaN values.",
            "sarimax_specs_found": "Found SARIMAX specifications for '{}' in variable properties.",
            "sarimax_parameters": "SARIMAX parameters: order={}, seasonal_order={}, trend='{}'",
            "sarimax_fitted": "SARIMAX model for '{}' fitted successfully.",
            "processing_ets": "Processing ETS for target variable: {}",
            "ets_specs_found": "Found ETS specifications for '{}' in variable properties.",
            "ets_parameters": "ETS parameters: {}",
            "ets_fitted": "ETS model for '{}' fitted successfully.",
            "target_vars_for_model": "Target variables for {}: {}",
            "model_specs_found": "Found {} specifications in properties of '{}'.",
            "var_lags_required": "'var_lags' parameter is required for VAR models but was not specified.",
            "var_parameters": "VAR parameters: lags={}, trend='{}'",
            "var_fitted": "VAR model fitted with {} lags, trend='{}'.",
            "vecm_parameters": "VECM parameters: k_ar_diff={}, coint_rank={}, deterministic='{}'",
            "vecm_fitted": "VECM model fitted successfully.",
            "checking_application": "Checking conditions for model application...",
            "skip_application_failed": "Skipping application: Model fitting failed.",
            "skip_application_actions": "Skipping application: Diagnostics suggested critical actions. Please resolve them first.",
            "no_application_params": "No application parameters provided. Skipping model application step.",
            "error_fitting_model": "Error fitting {} model: {}",
            "model_meets_assumptions": "Model diagnostics indicate the model meets key assumptions based on the tests performed.",
            "model_not_supported": "Model type '{}' not supported"
        },
        "vi": {
            "title": "# Phân Tích Ước Lượng & Chẩn Đoán Mô Hình Time Series\n\n",
            "model_type_not_specified": "Loại mô hình không được chỉ định trong tham số.",
            "model_type_handled_by_sarimax": "Loại mô hình '{}' sẽ được xử lý bởi triển khai SARIMAX chung.",
            "auto_selecting_dependent": "Không có biến mục tiêu được chỉ định. Tự động chọn các biến phụ thuộc: {}",
            "no_target_and_no_dependent": "Không có biến mục tiêu được chỉ định và không tìm thấy biến phụ thuộc. Sử dụng tham số 'target_variables_codes' hoặc 'target_variable_code'.",
            "no_target_specified": "Không có biến mục tiêu được chỉ định. Sử dụng tham số 'target_variables_codes' hoặc 'target_variable_code'.",
            "starting_estimation": "Bắt đầu Ước lượng & Chẩn đoán Mô hình: {}",
            "time_index_not_found": "Không tìm thấy biến chỉ số thời gian trong siêu dữ liệu.",
            "time_index_column_not_found": "Không tìm thấy cột chỉ số thời gian '{}' trong dữ liệu.",
            "error_setting_time_index": "Lỗi khi thiết lập chỉ số thời gian '{}': {}",
            "index_not_datetime": "Chỉ số '{}' không phải là DatetimeIndex sau khi xử lý.",
            "data_sorted": "Dữ liệu đã được sắp xếp theo chỉ số thời gian.",
            "frequency_inferred": "Đã suy luận và thiết lập tần suất: {}",
            "frequency_not_inferred": "Cảnh báo: Không thể suy luận tần suất cho chỉ số chuỗi thời gian.",
            "exog_vars_not_found": "Một hoặc nhiều biến ngoại sinh không được tìm thấy trong dữ liệu.",
            "exog_vars_handled": "Các biến ngoại sinh: {} (Các giá trị NaN đã được xử lý).",
            "exog_vars_still_nan": "Các biến ngoại sinh vẫn chứa giá trị NaN sau khi xử lý.",
            "exog_vars": "Các biến ngoại sinh: {}",
            "processing_sarimax": "Đang xử lý SARIMAX cho biến mục tiêu: {}",
            "target_var_not_found": "Không tìm thấy biến mục tiêu '{}' trong dữ liệu.",
            "target_series_empty": "Chuỗi mục tiêu cho '{}' trống sau khi loại bỏ các giá trị NaN.",
            "sarimax_specs_found": "Đã tìm thấy đặc tả SARIMAX cho '{}' trong thuộc tính biến.",
            "sarimax_parameters": "Tham số SARIMAX: order={}, seasonal_order={}, trend='{}'",
            "sarimax_fitted": "Mô hình SARIMAX cho '{}' đã được khớp thành công.",
            "processing_ets": "Đang xử lý ETS cho biến mục tiêu: {}",
            "ets_specs_found": "Đã tìm thấy đặc tả ETS cho '{}' trong thuộc tính biến.",
            "ets_parameters": "Tham số ETS: {}",
            "ets_fitted": "Mô hình ETS cho '{}' đã được khớp thành công.",
            "target_vars_for_model": "Các biến mục tiêu cho {}: {}",
            "model_specs_found": "Đã tìm thấy đặc tả {} trong thuộc tính của '{}'.",
            "var_lags_required": "Tham số 'var_lags' là bắt buộc cho các mô hình VAR nhưng không được chỉ định.",
            "var_parameters": "Tham số VAR: lags={}, trend='{}'",
            "var_fitted": "Mô hình VAR đã được khớp với {} độ trễ, trend='{}'.",
            "vecm_parameters": "Tham số VECM: k_ar_diff={}, coint_rank={}, deterministic='{}'",
            "vecm_fitted": "Mô hình VECM đã được khớp thành công.",
            "checking_application": "Đang kiểm tra điều kiện để áp dụng mô hình...",
            "skip_application_failed": "Bỏ qua áp dụng: Khớp mô hình thất bại.",
            "skip_application_actions": "Bỏ qua áp dụng: Chẩn đoán đề xuất các hành động quan trọng. Vui lòng giải quyết chúng trước.",
            "no_application_params": "Không có tham số áp dụng được cung cấp. Bỏ qua bước áp dụng mô hình.",
            "error_fitting_model": "Lỗi khi khớp mô hình {}: {}",
            "model_meets_assumptions": "Chẩn đoán mô hình cho thấy mô hình đáp ứng các giả định chính dựa trên các kiểm tra đã thực hiện.",
            "model_not_supported": "Loại mô hình '{}' không được hỗ trợ"
        }
    }
    
    # --- Parameter Extraction ---
    model_type = params.get('model_family', '').upper()
    target_variables_codes = params.get('target_variables_codes', [])
    single_target = params.get('target_variable_code')
    exog_variable_codes = params.get('exogenous_variables', [var.code for var in variables if var.role == VariableRole.INDEPENDENT])

    # Model-specific parameters
    model_order = tuple(params.get('model_order', (1, 0, 0)))
    seasonal_order = tuple(params.get('seasonal_order', (0, 0, 0, 0)))
    trend = params.get('trend', 'c')
    ets_params = params.get('ets_params', {})
    var_lags = params.get('var_lags', 1)
    vecm_params = params.get('vecm_params', {})

    # Diagnostic parameters
    sig_level_ljung_box = params.get('significance_level_ljung_box', 0.05)
    sig_level_shapiro_wilk = params.get('significance_level_shapiro_wilk', 0.05)
    sig_level_breusch_pagan = params.get('significance_level_breusch_pagan', 0.05)
    ljung_box_lags = params.get('ljung_box_lags', None)
    acf_pacf_lags = params.get('acf_pacf_lags', None)
    irf_periods = params.get('irf_periods', 10)
    fevd_steps = params.get('fevd_steps', irf_periods)

    # Application parameters
    application_params = params.get('application_params', None)

    # Output parameters
    base_output_dir = params.get("output_dir", "time_est_diag")
    save_files = params.get("save_files", False)
    language = params.get("language", "en")
    count = params.get("count", 1)

    # Get translations for selected language
    t = translations.get(language, translations["en"])

    # Format title with iteration count if count > 1
    t = t.copy()  # Make a copy to avoid modifying the original translations
    t["title"] = format_title_with_count(t["title"], count, language)

    # --- Initialization ---
    logs = []
    file_contents = {}
    tool_results = {'diagnostics_summary': {}}
    actions: list[Action] = []
    fitted_model = None
    
    # Generate unique output directory
    now = datetime.now()
    timestamp = f"{now.microsecond // 10000:02d}"
    output_dir_id = f"{timestamp}_{base_output_dir}"
    output_dir = os.path.join(os.path.dirname(base_output_dir) or ".", output_dir_id)
    
    # Validate model type
    if not model_type:
        logs.append(t["model_type_not_specified"])
        return ToolOutput(results={"error": "model_type not specified"}, logs=logs, file_contents=file_contents, action=actions)

    if model_type in ["ARIMA", "ARIMAX", "SARIMA"]:
        logs.append(t["model_type_handled_by_sarimax"].format(model_type))
        model_type = "SARIMAX"

    # Handle target variables
    if not target_variables_codes:
        if single_target:
            target_variables_codes = [single_target]
        else:
            # Default to dependent variables if no targets specified
            dependent_vars = [var.code for var in variables if var.role == VariableRole.DEPENDENT]
            if dependent_vars:
                target_variables_codes = dependent_vars
                logs.append(t["auto_selecting_dependent"].format(dependent_vars))
            else:
                logs.append(t["no_target_and_no_dependent"])
                return ToolOutput(results={"error": "No target variables specified and no dependent variables available"}, logs=logs, file_contents=file_contents, action=actions)

    if not target_variables_codes:
        logs.append(t["no_target_specified"])
        return ToolOutput(results={"error": "No target variables specified"}, logs=logs, file_contents=file_contents, action=actions)

    logs.append(t["title"])
    logs.append(t["starting_estimation"].format(model_type))
    
    # --- Data Preparation ---
    time_index_var = next((v for v in variables if v.variable_type == VariableType.TIME_INDEX), None)
    if not time_index_var:
        logs.append(t["time_index_not_found"])
        return ToolOutput(results={"error": "Time index variable not found"}, logs=logs, file_contents=file_contents, action=actions)

    time_index_col_name = time_index_var.code
    current_data = data.copy()

    if time_index_col_name not in current_data.columns and current_data.index.name != time_index_col_name:
        logs.append(t["time_index_column_not_found"].format(time_index_col_name))
        return ToolOutput(results={"error": f"Time index column '{time_index_col_name}' not found"}, logs=logs, file_contents=file_contents, action=actions)

    # Set time index
    if time_index_col_name in current_data.columns and current_data.index.name != time_index_col_name:
        try:
            current_data[time_index_col_name] = pd.to_datetime(current_data[time_index_col_name])
            current_data = current_data.set_index(time_index_col_name)
        except Exception as e:
            logs.append(t["error_setting_time_index"].format(time_index_col_name, e))
            return ToolOutput(results={"error": f"Error setting time index: {e}"}, logs=logs, file_contents=file_contents, action=actions)

    if not isinstance(current_data.index, pd.DatetimeIndex):
        logs.append(t["index_not_datetime"].format(current_data.index.name))
        return ToolOutput(results={"error": "Index is not DatetimeIndex"}, logs=logs, file_contents=file_contents, action=actions)

    # Sort and set frequency
    if not current_data.index.is_monotonic_increasing:
        current_data = current_data.sort_index()
        logs.append(t["data_sorted"])

    if current_data.index.freq is None:
        inferred_freq = pd.infer_freq(current_data.index)
        if inferred_freq:
            current_data = current_data.asfreq(inferred_freq)
            logs.append(t["frequency_inferred"].format(inferred_freq))
        else:
            logs.append(t["frequency_not_inferred"])
    
    # Prepare exogenous variables
    exog_df_full = None
    if exog_variable_codes:
        if not all(c in current_data.columns for c in exog_variable_codes):
            logs.append(t["exog_vars_not_found"])
            return ToolOutput(results={"error": "Exogenous variables not found"}, logs=logs, file_contents=file_contents, action=actions)

        exog_df_full = current_data[exog_variable_codes].copy()
        if exog_df_full.isnull().any().any():
            exog_df_full.fillna(method='ffill', inplace=True)
            exog_df_full.fillna(method='bfill', inplace=True)
            logs.append(t["exog_vars_handled"].format(', '.join(exog_variable_codes)))
            if exog_df_full.isnull().any().any():
                logs.append(t["exog_vars_still_nan"])
                return ToolOutput(results={"error": "Exogenous variables have NaNs"}, logs=logs, file_contents=file_contents, action=actions)
        else:
            logs.append(t["exog_vars"].format(', '.join(exog_variable_codes)))
    
    # --- Model Fitting ---
    try:
        if model_type == "SARIMAX":
            for target_variable_code in target_variables_codes:
                logs.append(t["processing_sarimax"].format(target_variable_code))
                tool_results[target_variable_code] = {'diagnostics_summary': {}}

                if target_variable_code not in current_data.columns:
                    logs.append(t["target_var_not_found"].format(target_variable_code))
                    tool_results[target_variable_code]['error'] = 'Target variable not found'
                    continue

                target_series_data = current_data[target_variable_code].dropna()
                if target_series_data.empty:
                    logs.append(t["target_series_empty"].format(target_variable_code))
                    tool_results[target_variable_code]['error'] = 'Target series is empty'
                    continue

                exog_df = exog_df_full.loc[target_series_data.index] if exog_df_full is not None else None

                # Get model specifications from variable properties
                target_var_meta = next((v for v in variables if v.code == target_variable_code), None)
                model_specs = {}
                if target_var_meta and target_var_meta.properties:
                    model_specs = target_var_meta.properties.get('model_specifications', {}).get('SARIMAX', {})
                    if model_specs:
                        logs.append(t["sarimax_specs_found"].format(target_variable_code))

                # Use variable properties first, then params
                final_order = tuple(model_specs.get('model_order', model_order))
                final_seasonal_order = tuple(model_specs.get('seasonal_order', seasonal_order))
                final_trend = model_specs.get('trend', trend)

                logs.append(t["sarimax_parameters"].format(final_order, final_seasonal_order, final_trend))

                model = SARIMAX(target_series_data, exog=exog_df, order=final_order,
                               seasonal_order=final_seasonal_order, trend=final_trend,
                               freq=target_series_data.index.freqstr)
                fitted_model = model.fit(disp=False)
                logs.append(t["sarimax_fitted"].format(target_variable_code))

                run_evaluation_and_diagnostics_for_model(
                    fitted_model, target_series_data, logs, file_contents,
                    tool_results[target_variable_code], actions, output_dir_id,
                    target_variable_code, sig_level_ljung_box, sig_level_shapiro_wilk,
                    sig_level_breusch_pagan, ljung_box_lags, acf_pacf_lags,
                    irf_periods, fevd_steps, language
                )
        
        elif model_type == "ETS":
            for target_variable_code in target_variables_codes:
                logs.append(t["processing_ets"].format(target_variable_code))
                tool_results[target_variable_code] = {'diagnostics_summary': {}}

                if target_variable_code not in current_data.columns:
                    logs.append(t["target_var_not_found"].format(target_variable_code))
                    tool_results[target_variable_code]['error'] = 'Target variable not found'
                    continue

                target_series_data = current_data[target_variable_code].dropna()
                if target_series_data.empty:
                    logs.append(t["target_series_empty"].format(target_variable_code))
                    tool_results[target_variable_code]['error'] = 'Target series is empty'
                    continue

                # Get model specifications from variable properties
                target_var_meta = next((v for v in variables if v.code == target_variable_code), None)
                model_specs = {}
                if target_var_meta and target_var_meta.properties:
                    model_specs = target_var_meta.properties.get('model_specifications', {}).get('ETS', {})
                    if model_specs:
                        logs.append(t["ets_specs_found"].format(target_variable_code))

                final_ets_params = {**model_specs, **ets_params}
                logs.append(t["ets_parameters"].format(final_ets_params))

                model = ETSModel(target_series_data, **final_ets_params, freq=target_series_data.index.freqstr)
                fitted_model = model.fit(disp=False)
                logs.append(t["ets_fitted"].format(target_variable_code))

                run_evaluation_and_diagnostics_for_model(
                    fitted_model, target_series_data, logs, file_contents,
                    tool_results[target_variable_code], actions, output_dir_id,
                    target_variable_code, sig_level_ljung_box, sig_level_shapiro_wilk,
                    sig_level_breusch_pagan, ljung_box_lags, acf_pacf_lags,
                    irf_periods, fevd_steps, language
                )
        
        elif model_type in ["VAR", "VECM"]:
            if not target_variables_codes or not all(c in current_data.columns for c in target_variables_codes):
                return ToolOutput(results={"error": f"Target variables for {model_type} not found"}, logs=logs, file_contents=file_contents, action=actions)

            target_series_data = current_data[target_variables_codes].dropna()
            logs.append(t["target_vars_for_model"].format(model_type, ', '.join(target_variables_codes)))

            if target_series_data.empty:
                return ToolOutput(results={"error": "Target data is empty"}, logs=logs, file_contents=file_contents, action=actions)

            exog_df = exog_df_full.loc[target_series_data.index] if exog_df_full is not None else None

            # Get model specifications from first variable's properties
            first_var_meta = next((v for v in variables if v.code == target_variables_codes[0]), None)
            model_specs = {}
            if first_var_meta and first_var_meta.properties:
                model_specs = first_var_meta.properties.get('model_specifications', {}).get(model_type, {})
                if model_specs:
                    logs.append(t["model_specs_found"].format(model_type, first_var_meta.code))

            if model_type == "VAR":
                final_lags = model_specs.get('var_lags', var_lags)
                final_trend = model_specs.get('trend', trend)

                if final_lags is None:
                    logs.append(t["var_lags_required"])
                    return ToolOutput(results={"error": "'var_lags' not specified"}, logs=logs, file_contents=file_contents, action=actions)

                logs.append(t["var_parameters"].format(final_lags, final_trend))

                model = VAR(target_series_data, exog=exog_df, dates=target_series_data.index,
                           freq=target_series_data.index.freqstr)
                fitted_model = model.fit(maxlags=final_lags, trend=final_trend, ic=None)
                logs.append(t["var_fitted"].format(fitted_model.k_ar, final_trend))

            elif model_type == "VECM":
                final_vecm_params = {**model_specs, **vecm_params}
                k_ar_diff = final_vecm_params.get('k_ar_diff')
                coint_rank = final_vecm_params.get('coint_rank')
                deterministic = final_vecm_params.get('deterministic', 'ci')

                if k_ar_diff is None:
                    return ToolOutput(results={"error": "VECM 'k_ar_diff' not specified"}, logs=logs)
                if coint_rank is None:
                    return ToolOutput(results={"error": "VECM 'coint_rank' not specified"}, logs=logs)

                logs.append(t["vecm_parameters"].format(k_ar_diff, coint_rank, deterministic))

                model = VECM(target_series_data, exog=exog_df, dates=target_series_data.index,
                            freq=target_series_data.index.freqstr, k_ar_diff=k_ar_diff,
                            coint_rank=coint_rank, deterministic=deterministic)
                fitted_model = model.fit()
                logs.append(t["vecm_fitted"])

            run_evaluation_and_diagnostics_for_model(
                fitted_model, target_series_data, logs, file_contents,
                tool_results, actions, output_dir_id, model_type.lower(),
                sig_level_ljung_box, sig_level_shapiro_wilk, sig_level_breusch_pagan,
                ljung_box_lags, acf_pacf_lags, irf_periods, fevd_steps, language
            )

        else:
            return ToolOutput(results={"error": t["model_not_supported"].format(model_type)}, logs=logs)
        
        # --- Integrated Application Step ---
        if application_params:
            model_prefix = model_type.lower()
            logs.append(t["checking_application"])

            if fitted_model is None:
                logs.append(t["skip_application_failed"])
                return ToolOutput(results=serialize_dict(tool_results), logs=logs, file_contents=file_contents, action=actions)

            has_critical_actions = any(
                a.action_type == ActionType.MODIFY_MODEL_SPECIFICATION for a in actions
            )
            if has_critical_actions:
                logs.append(t["skip_application_actions"])
            else:
                _run_model_application_step(
                    fitted_model=fitted_model,
                    target_series_data=target_series_data,
                    variables=variables,
                    params=application_params,
                    logs=logs,
                    file_contents=file_contents,
                    tool_results=tool_results.get(model_prefix, tool_results),
                    actions=actions,
                    output_dir_id=output_dir_id,
                    model_prefix=model_prefix
                )
        else:
            logs.append(t["no_application_params"])

    except Exception as e:
        logs.append(t["error_fitting_model"].format(model_type, e))
        return ToolOutput(results={"error": f"Error fitting model: {e}"}, logs=logs, file_contents=file_contents, action=actions)

    # --- Finalization ---
    if not actions:
        logs.append(t["model_meets_assumptions"])
    
    plt.close('all')
    
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
    
    return ToolOutput(results=serialize_dict(tool_results), logs=logs, file_contents=file_contents, action=actions if actions else None)

def run_evaluation_and_diagnostics_for_model(
    fitted_model: Any,
    target_series_data: Union[pd.Series, pd.DataFrame],
    logs: list[str],
    file_contents: dict[str, str],
    tool_results: dict[str, Any],
    actions: list[Action],
    output_dir_id: str,
    model_prefix: str,
    sig_level_ljung_box: float,
    sig_level_shapiro_wilk: float,
    sig_level_breusch_pagan: float,
    ljung_box_lags: Optional[int],
    acf_pacf_lags: Optional[int],
    irf_periods: int,
    fevd_steps: int,
    language: str = "en"
):
    """
    A helper to run evaluation and diagnostics on a single fitted model.
    This is used to avoid code duplication for univariate models in a loop.

    Parameters:
        fitted_model: The fitted time series model
        target_series_data: The target time series data (Series or DataFrame)
        logs: list to append log messages for reporting
        file_contents: dictionary to store generated file contents
        tool_results: dictionary to store analysis results
        actions: list to append suggested actions
        output_dir_id: Unique output directory identifier
        model_prefix: Prefix for file naming (e.g., 'sarimax', 'ets')
        sig_level_ljung_box: Significance level for Ljung-Box test
        sig_level_shapiro_wilk: Significance level for Shapiro-Wilk test
        sig_level_breusch_pagan: Significance level for Breusch-Pagan test
        ljung_box_lags: Number of lags for Ljung-Box test
        acf_pacf_lags: Number of lags for ACF/PACF plots
        irf_periods: Number of periods for Impulse Response Functions
        fevd_steps: Number of steps for Forecast Error Variance Decomposition
        language: Language for output messages - "en" or "vi" (default: "en")
    """

    # Translation dictionary
    translations = {
        "en": {
            "model_failed": "Model fitting failed for {}. Skipping evaluation and diagnostics.",
            "model_success": "Model fitting successful for {}. Generating comprehensive model summary.",
            "summary_complete": "Complete model summary for {}: {}",
            "table_saved": "Model {} table for {}: {}",
            "summary_saved": "Model summary for {}: {}",
            "params_extracted": "Model parameters for {}: {}",
            "summary_error": "Error generating model summary for {}: {}",
            "diagnostics_start": "Starting comprehensive diagnostic tests for {} model",
            "residuals_empty": "Residuals are empty for {}. Skipping diagnostics.",
            "residuals_plot": "Residuals analysis plot for {} ({}): {}",
            "residuals_plot_single": "Residuals analysis plot for {}: {}",
            "running_tests": "Running diagnostic tests for {} residuals ({})",
            "ljung_box_saved": "Ljung-Box test results for {} ({}): {}",
            "ljung_box_failed": "Ljung-Box test indicates significant autocorrelation in {} ({}) at lags: {}",
            "ljung_box_passed": "Ljung-Box test passed for {} ({}) - no significant autocorrelation detected",
            "ljung_box_error": "Error running Ljung-Box test for {} ({}): {}",
            "ljung_box_issue": "Residual autocorrelation detected in {} ({}) at lags {}",
            "ljung_box_comment": "Consider adjusting model specification (e.g., modify AR/MA terms or seasonal components)",
            "shapiro_test": "Shapiro-Wilk normality test for {} ({}): Statistic={:.4f}, P-value={:.4f}, {}",
            "shapiro_failed": "Shapiro-Wilk test indicates non-normal residuals for {} ({})",
            "shapiro_passed": "Shapiro-Wilk test passed for {} ({}) - residuals appear normally distributed",
            "shapiro_error": "Error running Shapiro-Wilk test for {} ({}): {}",
            "breusch_test": "Breusch-Pagan heteroscedasticity test for {} ({}): F-statistic={:.4f}, P-value={:.4f}, {}",
            "breusch_failed": "Breusch-Pagan test indicates heteroscedasticity in {} ({})",
            "breusch_passed": "Breusch-Pagan test passed for {} ({}) - homoscedasticity maintained",
            "breusch_error": "Error running Breusch-Pagan test for {} ({}): {}",
            "breusch_issue": "Heteroscedasticity detected in {} ({})",
            "breusch_comment": "Consider using robust standard errors, data transformation (e.g., log), or GARCH modeling",
            "stability_check": "Model stability check for {}: {}",
            "stability_issue": "Model stability issue detected for {}",
            "stability_confirmed": "Model stability confirmed for {}",
            "stability_plot": "Model stability plot for {}: {}",
            "stability_error": "Error checking model stability for {}: {}",
            "stability_comment": "Consider reducing the number of lags or re-specifying the model",
            "var_issue": "VAR/VECM model {} is unstable",
            "var_diagnostics": "Running VAR-specific diagnostic tests for {}",
            "irf_generating": "Generating Impulse Response Functions for {} ({} periods)",
            "irf_saved": "Impulse Response Functions plot for {}: {}",
            "irf_error": "Error generating Impulse Response Functions for {}: {}",
            "fevd_generating": "Generating Forecast Error Variance Decomposition for {} ({} steps)",
            "fevd_saved": "Forecast Error Variance Decomposition plot for {}: {}",
            "fevd_error": "Error generating Forecast Error Variance Decomposition for {}: {}",
            "granger_running": "Running Granger Causality tests for {}",
            "granger_saved": "Granger Causality test results for {}: {}",
            "granger_error": "Error running Granger Causality tests for {}: {}",
            "diagnostics_error": "Critical error during diagnostic tests for {}: {}",
            "granger_causes": "All other variables jointly Granger-cause {}",
            "granger_not_causes": "All other variables jointly do NOT Granger-cause {}",
            "granger_effect": "Effect of ALL OTHERS on {}",
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
            "model_failed": "Việc khớp mô hình thất bại cho {}. Bỏ qua đánh giá và chẩn đoán.",
            "model_success": "Việc khớp mô hình thành công cho {}. Đang tạo bản tóm tắt mô hình toàn diện.",
            "summary_complete": "Bản tóm tắt mô hình hoàn chỉnh cho {}: {}",
            "table_saved": "Bảng {} mô hình cho {}: {}",
            "summary_saved": "Bản tóm tắt mô hình cho {}: {}",
            "params_extracted": "Các tham số mô hình cho {}: {}",
            "summary_error": "Lỗi khi tạo bản tóm tắt mô hình cho {}: {}",
            "diagnostics_start": "Bắt đầu các kiểm tra chẩn đoán toàn diện cho mô hình {}",
            "residuals_empty": "Phần dư trống cho {}. Bỏ qua chẩn đoán.",
            "residuals_plot": "Biểu đồ phân tích phần dư cho {} ({}): {}",
            "residuals_plot_single": "Biểu đồ phân tích phần dư cho {}: {}",
            "running_tests": "Đang chạy các kiểm tra chẩn đoán cho phần dư {} ({})",
            "ljung_box_saved": "Kết quả kiểm tra Ljung-Box cho {} ({}): {}",
            "ljung_box_failed": "Kiểm tra Ljung-Box cho thấy có tự tương quan đáng kể trong {} ({}) tại các độ trễ: {}",
            "ljung_box_passed": "Kiểm tra Ljung-Box đạt cho {} ({}) - không phát hiện tự tương quan đáng kể",
            "ljung_box_error": "Lỗi khi chạy kiểm tra Ljung-Box cho {} ({}): {}",
            "ljung_box_issue": "Phát hiện tự tương quan phần dư trong {} ({}) tại các độ trễ {}",
            "ljung_box_comment": "Xem xét điều chỉnh đặc tả mô hình (ví dụ: sửa đổi các thành phần AR/MA hoặc thành phần mùa vụ)",
            "shapiro_test": "Kiểm tra phân phối chuẩn Shapiro-Wilk cho {} ({}): Thống kê={:.4f}, Giá trị P={:.4f}, {}",
            "shapiro_failed": "Kiểm tra Shapiro-Wilk cho thấy phần dư không phân phối chuẩn cho {} ({})",
            "shapiro_passed": "Kiểm tra Shapiro-Wilk đạt cho {} ({}) - phần dư có vẻ phân phối chuẩn",
            "shapiro_error": "Lỗi khi chạy kiểm tra Shapiro-Wilk cho {} ({}): {}",
            "breusch_test": "Kiểm tra phương sai thay đổi Breusch-Pagan cho {} ({}): F-statistic={:.4f}, Giá trị P={:.4f}, {}",
            "breusch_failed": "Kiểm tra Breusch-Pagan cho thấy có phương sai thay đổi trong {} ({})",
            "breusch_passed": "Kiểm tra Breusch-Pagan đạt cho {} ({}) - duy trì phương sai đồng nhất",
            "breusch_error": "Lỗi khi chạy kiểm tra Breusch-Pagan cho {} ({}): {}",
            "breusch_issue": "Phát hiện phương sai thay đổi trong {} ({})",
            "breusch_comment": "Xem xét sử dụng sai số chuẩn vững, chuyển đổi dữ liệu (ví dụ: log), hoặc mô hình hóa GARCH",
            "stability_check": "Kiểm tra ổn định mô hình cho {}: {}",
            "stability_issue": "Phát hiện vấn đề về ổn định mô hình cho {}",
            "stability_confirmed": "Đã xác nhận tính ổn định của mô hình cho {}",
            "stability_plot": "Biểu đồ ổn định mô hình cho {}: {}",
            "stability_error": "Lỗi khi kiểm tra tính ổn định mô hình cho {}: {}",
            "stability_comment": "Xem xét giảm số lượng độ trễ hoặc xác định lại mô hình",
            "var_issue": "Mô hình VAR/VECM {} không ổn định",
            "var_diagnostics": "Đang chạy các kiểm tra chẩn đoán đặc trưng cho VAR cho {}",
            "irf_generating": "Đang tạo Hàm Phản ứng Xung cho {} ({} chu kỳ)",
            "irf_saved": "Biểu đồ Hàm Phản ứng Xung cho {}: {}",
            "irf_error": "Lỗi khi tạo Hàm Phản ứng Xung cho {}: {}",
            "fevd_generating": "Đang tạo Phân rã Phương sai Sai số Dự báo cho {} ({} bước)",
            "fevd_saved": "Biểu đồ Phân rã Phương sai Sai số Dự báo cho {}: {}",
            "fevd_error": "Lỗi khi tạo Phân rã Phương sai Sai số Dự báo cho {}: {}",
            "granger_running": "Đang chạy các kiểm tra Nhân Quả Granger cho {}",
            "granger_saved": "Kết quả kiểm tra Nhân Quả Granger cho {}: {}",
            "granger_error": "Lỗi khi chạy các kiểm tra Nhân Quả Granger cho {}: {}",
            "diagnostics_error": "Lỗi nghiêm trọng trong quá trình kiểm tra chẩn đoán cho {}: {}",
            "granger_causes": "Tất cả các biến khác cùng tác động Granger-cause lên {}",
            "granger_not_causes": "Tất cả các biến khác cùng KHÔNG tác động Granger-cause lên {}",
            "granger_effect": "Tác động của TẤT CẢ CÁC BIẾN KHÁC lên {}",
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

    # Get translations for selected language
    t = translations.get(language, translations["en"])

    if not fitted_model:
        logs.append(t["model_failed"].format(model_prefix))
        return
    
    # --- Model Summary Generation ---
    logs.append(t["model_success"].format(model_prefix))

    try:
        summary_obj = fitted_model.summary()
        summary_path = f"{output_dir_id}/{model_prefix}_model_summary.txt"

        if hasattr(summary_obj, 'as_text') and hasattr(summary_obj, 'tables'):
            file_contents[summary_path] = summary_obj.as_text()
            logs.append(t["summary_complete"].format(model_prefix, summary_path))

            tool_results['parsed_summary'] = {}
            for i, table in enumerate(summary_obj.tables):
                table_title = "coefficients" if i == 1 else (table.title or f"summary_table_{i}")
                clean_title = table_title.replace(':', '').replace(' ', '_').lower()

                try:
                    df = pd.read_csv(io.StringIO(table.as_csv()), index_col=0)
                    csv_str = df_to_csv_string(df, index=True)
                    table_path = f"{output_dir_id}/{model_prefix}_{clean_title}.csv"
                    file_contents[table_path] = csv_str
                    logs.append(t["table_saved"].format(clean_title, model_prefix, table_path))
                    tool_results['parsed_summary'][clean_title] = df.to_dict(orient='split')
                except Exception:
                    tool_results['parsed_summary'][clean_title] = table.as_html()
        else:
            summary_text = str(summary_obj)
            file_contents[summary_path] = summary_text
            logs.append(t["summary_saved"].format(model_prefix, summary_path))
            tool_results['parsed_summary'] = {'raw_summary': summary_text}

        # Extract and report model parameters
        extracted_params = {}
        model_class_name = type(fitted_model).__name__
        if "SARIMAXResults" in model_class_name:
            extracted_params = {
                'order': fitted_model.model.order,
                'seasonal_order': fitted_model.model.seasonal_order,
                'trend': fitted_model.model.trend
            }
        elif "ETSResults" in model_class_name:
            extracted_params = {
                'error': fitted_model.model.error,
                'trend': fitted_model.model.trend,
                'seasonal': fitted_model.model.seasonal,
                'damped_trend': fitted_model.model.damped_trend
            }
        elif "VARResultsWrapper" in model_class_name:
            extracted_params = {'lags': fitted_model.k_ar}
        elif "VECMResultsWrapper" in model_class_name:
            extracted_params = {
                'k_ar_diff': fitted_model.model.k_ar_diff,
                'coint_rank': fitted_model.model.coint_rank,
                'deterministic': fitted_model.model.deterministic
            }

        tool_results['model_parameters'] = extracted_params
        logs.append(t["params_extracted"].format(model_prefix, extracted_params))

    except Exception as e:
        logs.append(t["summary_error"].format(model_prefix, e))
        tool_results['reporting_error'] = str(e)
        return
    
    # --- Diagnostic Tests ---
    logs.append(t["diagnostics_start"].format(model_prefix))
    
    try:
        # Extract residuals
        residuals = fitted_model.resid
        if isinstance(residuals, np.ndarray):
            ts_data_df = target_series_data if isinstance(target_series_data, pd.DataFrame) else target_series_data.to_frame()
            if len(residuals) == fitted_model.nobs and len(ts_data_df.index[-fitted_model.nobs:]) == fitted_model.nobs:
                columns = ts_data_df.columns if residuals.ndim > 1 else [ts_data_df.columns[0]]
                residuals = pd.DataFrame(residuals, index=ts_data_df.index[-fitted_model.nobs:], columns=columns)
                if residuals.shape[1] == 1:
                    residuals = residuals.iloc[:, 0]
            else:
                residuals = pd.DataFrame(residuals)
        
        if residuals.empty:
            logs.append(t["residuals_empty"].format(model_prefix))
            return
        
        # Generate residuals overview plots with improved styling
        if isinstance(residuals, pd.DataFrame):
            for col in residuals.columns:
                fig_resid_overview = plotting_util.plot_residuals_overview(
                    residuals[col], 
                    title=f"Residuals Analysis - {model_prefix} ({col})",
                    t=t
                )
                # Enhance plot styling
                for ax in fig_resid_overview.get_axes():
                    ax.grid(True, alpha=0.3)
                    ax.set_facecolor('#fafafa')
                
                plot_path = f"{output_dir_id}/{model_prefix}_residuals_overview_{col}.png"
                file_contents[plot_path] = fig_to_base64(fig_resid_overview)
                logs.append(t["residuals_plot"].format(model_prefix, col, plot_path))
        else:
            fig_resid_overview = plotting_util.plot_residuals_overview(
                residuals, 
                title=f"Residuals Analysis - {model_prefix}",
                t=t
            )
            # Enhance plot styling
            for ax in fig_resid_overview.get_axes():
                ax.grid(True, alpha=0.3)
                ax.set_facecolor('#fafafa')
            
            plot_path = f"{output_dir_id}/{model_prefix}_residuals_overview.png"
            file_contents[plot_path] = fig_to_base64(fig_resid_overview)
            logs.append(t["residuals_plot_single"].format(model_prefix, plot_path))
        
        # Run diagnostic tests for each residual series
        residuals_to_test = residuals.to_frame() if isinstance(residuals, pd.Series) else residuals
        
        for col_name in residuals_to_test.columns:
            resid_series = residuals_to_test[col_name].dropna()
            if resid_series.empty:
                continue
            
            logs.append(t["running_tests"].format(model_prefix, col_name))
            
            # Ljung-Box Test for Serial Correlation
            try:
                model_df_lb = len(fitted_model.params) // len(residuals_to_test.columns) if hasattr(fitted_model, 'params') else 0
                lb_results_df = statistical_tests_util.run_ljung_box_test(
                    resid_series, 
                    lags=ljung_box_lags, 
                    model_df=max(0, int(model_df_lb))
                )
                lb_path = f"{output_dir_id}/{model_prefix}_{col_name}_ljung_box_test.csv"
                file_contents[lb_path] = df_to_csv_string(lb_results_df, index=True)
                logs.append(t["ljung_box_saved"].format(model_prefix, col_name, lb_path))
                
                # Check for autocorrelation
                if (lb_results_df['lb_pvalue'] < sig_level_ljung_box).any():
                    failed_lags = lb_results_df[lb_results_df['lb_pvalue'] < sig_level_ljung_box].index.tolist()
                    logs.append(t["ljung_box_failed"].format(model_prefix, col_name, failed_lags))
                    actions.append(Action(
                        action_type=ActionType.MODIFY_MODEL_SPECIFICATION,
                        method="run_model_estimation_and_diagnostics",
                        issue=t["ljung_box_issue"].format(model_prefix, col_name, failed_lags),
                        comment=t["ljung_box_comment"],
                        status="pending"
                    ))
                else:
                    logs.append(t["ljung_box_passed"].format(model_prefix, col_name))
            except Exception as e:
                logs.append(t["ljung_box_error"].format(model_prefix, col_name, e))
            
            # Shapiro-Wilk Test for Normality
            try:
                sw_results = statistical_tests_util.run_shapiro_wilk_test(
                    resid_series, 
                    significance_level=sig_level_shapiro_wilk,
                    t=t
                )
                test_stat = sw_results.get('test_statistic', 'N/A')
                p_value = sw_results.get('p_value', 'N/A')
                interpretation = sw_results.get('interpretation', 'N/A')

                logs.append(t["shapiro_test"].format(model_prefix, col_name, test_stat, p_value, interpretation))

                if sw_results.get('p_value', 1.0) < sig_level_shapiro_wilk:
                    logs.append(t["shapiro_failed"].format(model_prefix, col_name))
                else:
                    logs.append(t["shapiro_passed"].format(model_prefix, col_name))
            except Exception as e:
                logs.append(t["shapiro_error"].format(model_prefix, col_name, e))
            
            # Breusch-Pagan Test for Heteroscedasticity
            try:
                exog_for_bp = None
                if hasattr(fitted_model.model, 'exog') and fitted_model.model.exog is not None:
                    exog_for_bp = pd.DataFrame(fitted_model.model.exog, index=target_series_data.index).loc[resid_series.index]
                else:
                    fitted_vals = fitted_model.fittedvalues
                    if isinstance(fitted_vals, pd.DataFrame):
                        exog_for_bp = pd.DataFrame({'fitted_values': fitted_vals[col_name]}, index=resid_series.index)
                    else:
                        exog_for_bp = pd.DataFrame({'fitted_values': fitted_vals}, index=resid_series.index)
                
                if not exog_for_bp.empty:
                    bp_results = statistical_tests_util.run_breusch_pagan_test(
                        resid_series, 
                        exog_for_bp, 
                        significance_level=sig_level_breusch_pagan,
                        t=t
                    )
                    f_stat = bp_results.get('f_statistic', 'N/A')
                    f_p_value = bp_results.get('f_p_value', 'N/A')
                    interpretation = bp_results.get('interpretation', 'N/A')

                    logs.append(t["breusch_test"].format(model_prefix, col_name, f_stat, f_p_value, interpretation))

                    if bp_results.get('f_p_value', 1.0) < sig_level_breusch_pagan:
                        logs.append(t["breusch_failed"].format(model_prefix, col_name))
                        actions.append(Action(
                            action_type=ActionType.MODIFY_MODEL_SPECIFICATION,
                            method="run_model_estimation_and_diagnostics",
                            issue=t["breusch_issue"].format(model_prefix, col_name),
                            comment=t["breusch_comment"],
                            status="pending"
                        ))
                    else:
                        logs.append(t["breusch_passed"].format(model_prefix, col_name))
            except Exception as e:
                logs.append(t["breusch_error"].format(model_prefix, col_name, e))
        
        # Additional diagnostics for VAR/VECM models
        if "VARResultsWrapper" in type(fitted_model).__name__ or "VECMResultsWrapper" in type(fitted_model).__name__:
            
            # Model Stability Check
            try:
                stability_results = statistical_tests_util.check_var_model_stability(fitted_model, t=t)
                stability_interpretation = stability_results.get('interpretation', 'N/A')
                logs.append(t["stability_check"].format(model_prefix, stability_interpretation))

                if not stability_results.get('is_stable', True):
                    logs.append(t["stability_issue"].format(model_prefix))
                    actions.append(Action(
                        action_type=ActionType.MODIFY_MODEL_SPECIFICATION,
                        method="run_model_estimation_and_diagnostics",
                        issue=t["var_issue"].format(model_prefix),
                        comment=t["stability_comment"],
                        status="pending"
                    ))
                else:
                    logs.append(t["stability_confirmed"].format(model_prefix))
                
                # Generate stability plot
                fig_stability = plotting_util.plot_var_stability(fitted_model, t=t)
                # Enhance plot styling
                for ax in fig_stability.get_axes():
                    ax.grid(True, alpha=0.3)
                    ax.set_facecolor('#fafafa')
                
                stability_path = f"{output_dir_id}/{model_prefix}_model_stability_roots.png"
                file_contents[stability_path] = fig_to_base64(fig_stability)
                logs.append(t["stability_plot"].format(model_prefix, stability_path))
            except Exception as e:
                logs.append(t["stability_error"].format(model_prefix, e))
            
            # VAR-specific diagnostics
            if "VARResultsWrapper" in type(fitted_model).__name__:
                logs.append(t["var_diagnostics"].format(model_prefix))
                
                # Impulse Response Functions
                try:
                    logs.append(t["irf_generating"].format(model_prefix, irf_periods))
                    irf_results = fitted_model.irf(irf_periods)
                    fig_irf = plotting_util.plot_impulse_response_functions(irf_results, t=t)

                    # Enhance plot styling
                    for ax in fig_irf.get_axes():
                        ax.grid(True, alpha=0.3)
                        ax.set_facecolor('#fafafa')

                    irf_path = f"{output_dir_id}/{model_prefix}_impulse_response_functions.png"
                    file_contents[irf_path] = fig_to_base64(fig_irf)
                    logs.append(t["irf_saved"].format(model_prefix, irf_path))
                except Exception as e:
                    logs.append(t["irf_error"].format(model_prefix, e))
                
                # Forecast Error Variance Decomposition
                try:
                    logs.append(t["fevd_generating"].format(model_prefix, fevd_steps))
                    fig_fevd = plotting_util.plot_forecast_error_variance_decomposition(fitted_model, periods=fevd_steps, t=t)

                    # Enhance plot styling
                    for ax in fig_fevd.get_axes():
                        ax.grid(True, alpha=0.3)
                        ax.set_facecolor('#fafafa')

                    fevd_path = f"{output_dir_id}/{model_prefix}_fevd.png"
                    file_contents[fevd_path] = fig_to_base64(fig_fevd)
                    logs.append(t["fevd_saved"].format(model_prefix, fevd_path))
                except Exception as e:
                    logs.append(t["fevd_error"].format(model_prefix, e))
                
                # Granger Causality Tests
                try:
                    logs.append(t["granger_running"].format(model_prefix))
                    variables = fitted_model.model.endog_names
                    causality_results = {}

                    for caused_var in variables:
                        causing_vars = [v for v in variables if v != caused_var]
                        test_result = fitted_model.test_causality(caused=caused_var, causing=causing_vars, kind='f')
                        causality_results[t["granger_effect"].format(caused_var)] = {
                            'f_statistic': test_result.test_statistic,
                            'p_value': test_result.pvalue,
                            'df': test_result.df,
                            'conclusion': t["granger_causes"].format(caused_var) if test_result.pvalue < 0.05 else t["granger_not_causes"].format(caused_var)
                        }

                    causality_df = pd.DataFrame.from_dict(causality_results, orient='index')
                    causality_path = f"{output_dir_id}/{model_prefix}_granger_causality.csv"
                    file_contents[causality_path] = df_to_csv_string(causality_df, index=True)
                    logs.append(t["granger_saved"].format(model_prefix, causality_path))
                    tool_results['diagnostics_summary']['granger_causality'] = causality_df.to_dict(orient='index')
                except Exception as e:
                    logs.append(t["granger_error"].format(model_prefix, e))
    
    except Exception as e:
        logs.append(t["diagnostics_error"].format(model_prefix, e))
        tool_results['diagnostics_error'] = str(e)