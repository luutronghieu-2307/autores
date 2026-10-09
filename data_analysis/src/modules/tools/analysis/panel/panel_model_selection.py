import pandas as pd
import numpy as np
from typing import Any
import os
import base64
from datetime import datetime
from io import BytesIO
import traceback
import warnings
warnings.filterwarnings('ignore')

# Core panel data analysis packages
import statsmodels.api as sm
from statsmodels.stats.diagnostic import het_breuschpagan
from statsmodels.stats.stattools import durbin_watson
from statsmodels.tsa.stattools import acf
from statsmodels.stats.outliers_influence import variance_inflation_factor

# Panel data specific packages
from linearmodels.panel import PanelOLS, RandomEffects

# Plotting
import matplotlib.pyplot as plt
plt.style.use('seaborn-v0_8')

# Assuming these imports are real from your codebase
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


def identify_time_invariant_variables(panel_data: pd.DataFrame, variables: list[str]) -> list[str]:
    """
    Identify variables that don't vary within entities over time.
    These will be absorbed by entity fixed effects.
    """
    time_invariant = []
    
    for var in variables:
        # Check if variable varies within each entity
        entity_variation = panel_data.groupby(level=0)[var].nunique()
        if (entity_variation == 1).all():  # All entities have only one unique value
            time_invariant.append(var)
    
    return time_invariant


def create_unified_properties_update(
    model_type: str,
    model_details: dict[str, Any],
    diagnostic_results: dict[str, Any],
    needs_remediation: bool = False,
    absorbed_status: str = None
) -> dict[str, Any]:
    """
    Create a unified format for updating variable properties with panel model analysis results.
    
    Args:
        model_type: Type of recommended model (e.g., "Fixed Effects", "Random Effects", "Pooled OLS")
        model_details: dictionary containing model statistics and parameters
        diagnostic_results: dictionary containing diagnostic test results
        needs_remediation: Whether robust standard errors were needed
        absorbed_status: For variables absorbed by fixed effects (e.g., "Absorbed by Fixed Effects")
    
    Returns:
        dictionary with standardized property updates
    """
    properties = {
        "panel_analysis": {
            "model_type": model_type,
            "analysis_timestamp": datetime.now().isoformat(),
            "robust_errors_used": needs_remediation,
            "model_statistics": {
                "r_squared": model_details.get("rsquared", None),
                "n_observations": model_details.get("n_obs", None),
                "f_statistic": model_details.get("f_statistic", None)
            },
            "diagnostic_tests": {
                test_name: {
                    "passed": not result.get("violation", False),
                    "p_value": result.get("p_value", None),
                    "statistic": result.get("statistic", None),
                    "test_type": result.get("test", None)
                } for test_name, result in diagnostic_results.items() 
                if isinstance(result, dict) and "violation" in result
            },
            "coefficients": model_details.get("params", {}),
            "standard_errors": model_details.get("std_errors", {}),
            "p_values": model_details.get("pvalues", {})
        }
    }
    
    # Add absorbed status if applicable
    if absorbed_status:
        properties["panel_analysis"]["absorbed_status"] = absorbed_status
        properties["panel_analysis"]["note"] = f"Variable {absorbed_status.lower()} and coefficient not directly estimated"
    
    return properties


def run_panel_model_selection(
    data: pd.DataFrame,
    variables: list[Variable],
    params: dict
) -> ToolOutput:
    """
    Comprehensive panel data analysis workflow using Python packages.
    
    Implements the econometric workflow:
    1. Data preparation and validation
    2. Model specification (Pooled OLS, FEM, REM)
    3. Model selection tests (F-test, Breusch-Pagan LM, Hausman)
    4. Diagnostic testing (heteroskedasticity, autocorrelation, etc.)
    5. Remediation with robust standard errors
    6. Results compilation and reporting

        Parameters:
        data: Input DataFrame containing panel data
        variables: List of Variable objects describing the data columns
        params: Dictionary containing analysis parameters
            - output_dir (str): Base output directory name (default: "panel_analysis_py_{timestamp}")
            - save_files (bool): Whether to save generated files to disk (default: False)
            - significance_level (float): Significance level for tests (default: 0.05)

    Returns:
        ToolOutput: Contains results, logs, file contents, and suggested actions
    """
    # Translation dictionary
    translations = {
        "en": {
            "title": "# Panel Data Analysis Summary\n\n",
            "summary": "Panel Data Analysis Summary",
            "msg": "ERROR: {}",
            "msg_1": "Dependent variable: {}",
            "msg_2": "Independent variables: {}",
            "msg_3": "Entity index: {}",
            "msg_4": "Time index: {}",
            "msg_5": "ERROR: Missing columns in data: {}",
            "logs": "ERROR: No valid observations after removing missing values",
            "summary_1": "Data summary: {} observations, {} entities, {} time periods",
            "note": "Note: {} observations removed due to missing values",
            "msg_6": "Time-invariant variables (absorbed by entity fixed effects): {}",
            "logs_1": "WARNING: No time-varying variables found. Fixed Effects model cannot be estimated.",
            "msg_7": "Time-varying variables: {}",
            "logs_2": "Pooled OLS: R² = {:.4f}",
            "msg_8": "ERROR fitting Pooled OLS: {}",
            "logs_3": "Fixed Effects: R² (within) = {:.4f}",
            "msg_9": "ERROR fitting Fixed Effects: {}",
            "logs_4": "Random Effects: R² = {:.4f}",
            "msg_10": "ERROR fitting Random Effects: {}",
            "logs_5": "F-test (FEM vs OLS): F = {:.4f}, p = {:.4f}",
            "msg_11": "F-test failed: {}",
            "logs_6": "Breusch-Pagan LM Test (REM vs OLS): LM = {:.4f}, p = {:.4f}",
            "msg_12": "Breusch-Pagan LM Test failed: {}",
            "logs_7": "Hausman Test (FEM vs REM): p ≈ {:.4f}",
            "msg_13": "Hausman test failed: {}. Defaulting to REM.",
            "logs_8": "Heteroskedasticity test: VIOLATION detected (p = {:.4f})",
            "logs_9": "Heteroskedasticity test: No violation (p = {:.4f})",
            "msg_14": "Heteroskedasticity test failed: {}",
            "logs_10": "Serial correlation test: VIOLATION detected (DW = {:.4f})",
            "logs_11": "Serial correlation test: No violation (DW = {:.4f})",
            "msg_15": "Serial correlation test failed: {}",
            "logs_12": "Multicollinearity test: VIOLATION detected (max VIF = {:.2f})",
            "logs_13": "Multicollinearity test: No violation (max VIF = {:.2f})",
            "msg_16": "Multicollinearity test failed: {}",
            "msg_17": "Model comparison table: {}",
            "summary_2": "Final model summary report {}",
            "msg_18": "Diagnostic plots {}",
            "msg_19": "Model selection plots {}",
            "msg_20": "Comprehensive panel analysis report {}",
            "msg_21": "Coefficient results table: {}",
            "msg_22": "All files saved to directory: {}",
            "error": "Critical error in panel model selection: {}",
            "msg_23": "ERROR: {}",
            "msg_24": "ERROR: Dependent variable '{}' cannot be an index variable",
            "msg_25": "ERROR: No valid independent variables found after filtering out index variables",
            "msg_26": "ERROR: No valid columns found for missing value removal",
            "header_1": "\nModel Estimation Results",
            "separator": "-" * 30,
            "header_2": "\nModel Selection Tests",
            "header_3": "\nDiagnostic Testing Results",
            "logs_14": "\nInitial recommendation: {}",
            "logs_15": "\nRobust standard errors applied for remediation",
            "logs_16": "\nFinal recommended model: {}",
            "model_fe": "Fixed Effects",
            "model_re": "Random Effects",
            "model_ols": "Pooled OLS",
            "decision_choose_fem": "Choose FEM",
            "decision_choose_rem": "Choose REM",
            "decision_ols_adequate": "OLS adequate",
            "decision_ols_adequate_fem_unavailable": "OLS adequate (FEM unavailable)",
            "decision_ols_adequate_rem_unavailable": "OLS adequate (REM unavailable)",
            "decision_rem_preferred_fem_unavailable": "REM preferred (FEM unavailable)",
            "decision_rem_default_no_params": "Choose REM (default - no common parameters)",
            "decision_rem_default": "Choose REM (default)",
            "absorbed_fe_status": "Absorbed by Fixed Effects",
            "action_remove_collinear_issue": "High multicollinearity detected. Variable '{}' has a VIF of {:.2f}, which is > 10.",
            "action_remove_collinear_comment": "Suggest removing '{}' to address multicollinearity and then re-running the analysis.",
            "action_update_dep_issue": "A recommended panel model ({}) has been identified for the dependent variable.",
            "action_update_dep_comment": "Store the recommended model specification and diagnostic summary in the properties of '{}'.",
            "action_update_absorbed_issue": "Time-invariant variables were absorbed by the recommended Fixed Effects model.",
            "action_update_absorbed_comment": "Tag the following variables as 'Absorbed by Fixed Effects' in their properties: {}.",
            "action_update_var_issue": "Panel model coefficient estimated for variable '{}'.",
            "action_update_var_comment": "Store the coefficient, standard error, and p-value for '{}' from the {} model.",
            "action_reanalyze_issue": "Data-modifying actions were suggested (e.g., removing a collinear variable).",
            "action_reanalyze_comment": "Re-run the panel model selection tool after the suggested actions are applied to ensure the model is based on the updated data.",
            # Final summary report translations
            "report_title": "Panel Data Analysis Results",
            "report_final_model": "Final Recommended Model",
            "report_data_info": "Data Information",
            "report_total_obs": "Total Observations",
            "report_entities": "Entities",
            "report_time_periods": "Time Periods",
            "report_absorbed_analysis": "Absorbed Variables Analysis",
            "report_time_invariant": "Time-invariant variables",
            "report_time_varying": "Time-varying variables",
            "report_model_summary": "Model Summary",
            "report_diagnostic_tests": "Diagnostic Tests",
            "report_no_diagnostic": "No diagnostic tests performed",
            "report_selection_tests": "Model Selection Tests",
            "report_no_selection": "No selection tests performed",
            "report_none": "None",
            # Main report translations
            "main_report_title": "Panel Data Analysis Report",
            "main_report_summary": "SUMMARY",
            "main_report_robust_se": "Robust Standard Errors Used",
            "main_report_yes": "Yes",
            "main_report_no": "No",
            "main_report_data_info": "DATA INFORMATION",
            "main_report_n_entities": "Number of Entities",
            "main_report_missing_dropped": "Missing Values Dropped",
            "main_report_var_class": "VARIABLE CLASSIFICATION",
            "main_report_models_est": "MODELS ESTIMATED",
            "main_report_selection_tests": "MODEL SELECTION TESTS",
            "main_report_no_selection": "No model selection tests performed",
            "main_report_diagnostic": "DIAGNOSTIC TEST RESULTS",
            "main_report_no_diagnostic": "No diagnostic tests performed",
            "main_report_coeff_est": "COEFFICIENT ESTIMATES (Final Model)",
            "main_report_recommendations": "RECOMMENDATIONS",
            "main_report_recommended_based": "{} is recommended based on the model selection tests.",
            "main_report_robust_applied": "Robust standard errors were applied due to diagnostic violations.",
            "main_report_se_appropriate": "Standard errors are appropriate for the data.",
            # Plot labels
            "plot_diagnostics_title": "Panel Model Diagnostics - {}",
            "plot_residuals_vs_fitted": "Residuals vs Fitted Values",
            "plot_fitted_values": "Fitted Values",
            "plot_residuals": "Residuals",
            "plot_qq_title": "Q-Q Plot (Normality Check)",
            "plot_dist_residuals": "Distribution of Residuals",
            "plot_frequency": "Frequency",
            "plot_normal_fit": "Normal fit",
            "plot_vif_title": "Variance Inflation Factors",
            "plot_vif_threshold": "VIF=10 (threshold)",
            "plot_vif_unavailable": "VIF plot unavailable",
            "plot_vif_error": "VIF plot unavailable\nError: {}",
            "plot_vif_single": "VIF plot unavailable\n(Single variable or error)",
            "plot_selection_title": "Panel Model Selection Results",
            "plot_rsquared": "R-squared",
            "plot_rsquared_comparison": "Model R-squared Comparison",
            "plot_recommended": "Recommended",
            "plot_pvalue": "P-value",
            "plot_pvalue_title": "Model Selection Test P-values",
            "plot_no_results": "No test results available",
            "plot_no_results_title": "Model Selection Tests - No Results",
            # Status labels
            "status_violation": "VIOLATION",
            "status_ok": "OK",
            "status_absorbed": "Absorbed",
            "status_na": "N/A",
            "status_significant_yes": "Yes",
            "status_significant_no": "No"
        },
        "vi": {
            "title": "# Phân tích Dữ liệu Bảng\n\n",
            "summary": "Tóm tắt Phân tích Dữ liệu Bảng",
            "msg": "LỖI: {}",
            "msg_1": "Biến phụ thuộc: {}",
            "msg_2": "Các biến độc lập: {}",
            "msg_3": "Chỉ số thực thể: {}",
            "msg_4": "Chỉ số thời gian: {}",
            "msg_5": "LỖI: Thiếu các cột trong dữ liệu: {}",
            "logs": "LỖI: Không còn quan sát hợp lệ nào sau khi loại bỏ các giá trị bị thiếu",
            "summary_1": "Tóm tắt dữ liệu: {} quan sát, {} thực thể, {} giai đoạn thời gian",
            "note": "Lưu ý: {} quan sát đã bị loại bỏ do thiếu giá trị",
            "msg_6": "Các biến không đổi theo thời gian (bị hấp thụ bởi hiệu ứng cố định thực thể): {}",
            "logs_1": "CẢNH BÁO: Không tìm thấy biến thay đổi theo thời gian. Không thể ước lượng mô hình Hiệu ứng Cố định (Fixed Effects).",
            "msg_7": "Các biến thay đổi theo thời gian: {}",
            "logs_2": "Pooled OLS: R² = {:.4f}",
            "msg_8": "LỖI khi khớp mô hình Pooled OLS: {}",
            "logs_3": "Hiệu ứng Cố định (Fixed Effects): R² (nội bộ/within) = {:.4f}",
            "msg_9": "LỖI khi khớp mô hình Hiệu ứng Cố định: {}",
            "logs_4": "Hiệu ứng Ngẫu nhiên (Random Effects): R² = {:.4f}",
            "msg_10": "LỖI khi khớp mô hình Hiệu ứng Ngẫu nhiên: {}",
            "logs_5": "Kiểm định F (FEM so với OLS): F = {:.4f}, p = {:.4f}",
            "msg_11": "Kiểm định F thất bại: {}",
            "logs_6": "Kiểm định Breusch-Pagan LM (REM so với OLS): LM = {:.4f}, p = {:.4f}",
            "msg_12": "Kiểm định Breusch-Pagan LM thất bại: {}",
            "logs_7": "Kiểm định Hausman (FEM so với REM): p ≈ {:.4f}",
            "msg_13": "Kiểm định Hausman thất bại: {}. Mặc định chuyển sang REM.",
            "logs_8": "Kiểm định phương sai sai số thay đổi: Phát hiện VI PHẠM (p = {:.4f})",
            "logs_9": "Kiểm định phương sai sai số thay đổi: Không vi phạm (p = {:.4f})",
            "msg_14": "Kiểm định phương sai sai số thay đổi thất bại: {}",
            "logs_10": "Kiểm định tự tương quan: Phát hiện VI PHẠM (DW = {:.4f})",
            "logs_11": "Kiểm định tự tương quan: Không vi phạm (DW = {:.4f})",
            "msg_15": "Kiểm định tự tương quan thất bại: {}",
            "logs_12": "Kiểm định đa cộng tuyến: Phát hiện VI PHẠM (max VIF = {:.2f})",
            "logs_13": "Kiểm định đa cộng tuyến: Không vi phạm (max VIF = {:.2f})",
            "msg_16": "Kiểm định đa cộng tuyến thất bại: {}",
            "msg_17": "Bảng so sánh mô hình: {}",
            "summary_2": "Báo cáo tóm tắt mô hình cuối cùng {}",
            "msg_18": "Các biểu đồ chẩn đoán {}",
            "msg_19": "Các biểu đồ lựa chọn mô hình {}",
            "msg_20": "Báo cáo phân tích dữ liệu bảng toàn diện {}",
            "msg_21": "Bảng kết quả hệ số: {}",
            "msg_22": "Tất cả các tệp đã được lưu vào thư mục: {}",
            "error": "Lỗi nghiêm trọng trong việc lựa chọn mô hình bảng: {}",
            "msg_23": "LỖI: {}",
            "msg_24": "LỖI: Biến phụ thuộc '{}' không thể là biến chỉ số",
            "msg_25": "LỖI: Không tìm thấy biến độc lập hợp lệ nào sau khi lọc bỏ các biến chỉ số",
            "msg_26": "LỖI: Không tìm thấy cột hợp lệ để loại bỏ giá trị thiếu",
            "header_1": "\nKết quả Ước lượng Mô hình",
            "separator": "-" * 30,
            "header_2": "\nCác Kiểm định Lựa chọn Mô hình",
            "header_3": "\nKết quả Kiểm tra Chẩn đoán",
            "logs_14": "\nKhuyến nghị ban đầu: {}",
            "logs_15": "\nSai số chuẩn mạnh (Robust standard errors) đã được áp dụng để khắc phục",
            "logs_16": "\nMô hình khuyến nghị cuối cùng: {}",
            "model_fe": "Hiệu ứng Cố định (Fixed Effects)",
            "model_re": "Hiệu ứng Ngẫu nhiên (Random Effects)",
            "model_ols": "Pooled OLS",
            "decision_choose_fem": "Chọn FEM",
            "decision_choose_rem": "Chọn REM",
            "decision_ols_adequate": "OLS là thỏa đáng",
            "decision_ols_adequate_fem_unavailable": "OLS là thỏa đáng (không có FEM)",
            "decision_ols_adequate_rem_unavailable": "OLS là thỏa đáng (không có REM)",
            "decision_rem_preferred_fem_unavailable": "Ưu tiên REM (không có FEM)",
            "decision_rem_default_no_params": "Chọn REM (mặc định - không có tham số chung)",
            "decision_rem_default": "Chọn REM (mặc định)",
            "absorbed_fe_status": "Đã bị hấp thụ bởi Hiệu ứng cố định (Fixed Effects)",
            "action_remove_collinear_issue": "Phát hiện đa cộng tuyến cao. Biến '{}' có VIF là {:.2f}, lớn hơn 10.",
            "action_remove_collinear_comment": "Đề xuất loại bỏ '{}' để xử lý đa cộng tuyến và sau đó chạy lại phân tích.",
            "action_update_dep_issue": "Đã xác định được mô hình bảng khuyến nghị ({}) cho biến phụ thuộc.",
            "action_update_dep_comment": "Lưu đặc tả mô hình khuyến nghị và tóm tắt chẩn đoán vào thuộc tính của '{}'.",
            "action_update_absorbed_issue": "Các biến bất biến theo thời gian đã bị hấp thụ bởi mô hình Hiệu ứng cố định (Fixed Effects) được khuyến nghị.",
            "action_update_absorbed_comment": "Đánh dấu các biến sau là 'Đã bị hấp thụ bởi Hiệu ứng cố định' trong thuộc tính của chúng: {}.",
            "action_update_var_issue": "Hệ số mô hình bảng đã được ước lượng cho biến '{}'.",
            "action_update_var_comment": "Lưu hệ số, sai số chuẩn và p-value cho '{}' từ mô hình {}.",
            "action_reanalyze_issue": "Các hành động sửa đổi dữ liệu đã được đề xuất (ví dụ: loại bỏ biến cộng tuyến).",
            "action_reanalyze_comment": "Chạy lại công cụ lựa chọn mô hình bảng sau khi các hành động đề xuất được áp dụng để đảm bảo mô hình dựa trên dữ liệu đã cập nhật.",
            # Final summary report translations
            "report_title": "Kết quả Phân tích Dữ liệu Bảng",
            "report_final_model": "Mô hình Khuyến nghị Cuối cùng",
            "report_data_info": "Thông tin Dữ liệu",
            "report_total_obs": "Tổng số Quan sát",
            "report_entities": "Thực thể",
            "report_time_periods": "Giai đoạn Thời gian",
            "report_absorbed_analysis": "Phân tích Biến bị Hấp thụ",
            "report_time_invariant": "Biến không đổi theo thời gian",
            "report_time_varying": "Biến thay đổi theo thời gian",
            "report_model_summary": "Tóm tắt Mô hình",
            "report_diagnostic_tests": "Kiểm tra Chẩn đoán",
            "report_no_diagnostic": "Không có kiểm tra chẩn đoán nào được thực hiện",
            "report_selection_tests": "Kiểm định Lựa chọn Mô hình",
            "report_no_selection": "Không có kiểm định lựa chọn nào được thực hiện",
            "report_none": "Không có",
            # Main report translations
            "main_report_title": "Báo cáo Phân tích Dữ liệu Bảng",
            "main_report_summary": "TÓM TẮT",
            "main_report_robust_se": "Sử dụng Sai số Chuẩn Mạnh",
            "main_report_yes": "Có",
            "main_report_no": "Không",
            "main_report_data_info": "THÔNG TIN DỮ LIỆU",
            "main_report_n_entities": "Số lượng Thực thể",
            "main_report_missing_dropped": "Giá trị Thiếu đã Loại bỏ",
            "main_report_var_class": "PHÂN LOẠI BIẾN",
            "main_report_models_est": "CÁC MÔ HÌNH ĐÃ ƯỚC LƯỢNG",
            "main_report_selection_tests": "KIỂM ĐỊNH LỰA CHỌN MÔ HÌNH",
            "main_report_no_selection": "Không có kiểm định lựa chọn mô hình nào được thực hiện",
            "main_report_diagnostic": "KẾT QUẢ KIỂM TRA CHẨN ĐOÁN",
            "main_report_no_diagnostic": "Không có kiểm tra chẩn đoán nào được thực hiện",
            "main_report_coeff_est": "ƯỚC LƯỢNG HỆ SỐ (Mô hình Cuối cùng)",
            "main_report_recommendations": "KHUYẾN NGHỊ",
            "main_report_recommended_based": "{} được khuyến nghị dựa trên các kiểm định lựa chọn mô hình.",
            "main_report_robust_applied": "Sai số chuẩn mạnh đã được áp dụng do vi phạm chẩn đoán.",
            "main_report_se_appropriate": "Sai số chuẩn phù hợp với dữ liệu.",
            # Plot labels
            "plot_diagnostics_title": "Chẩn đoán Mô hình Bảng - {}",
            "plot_residuals_vs_fitted": "Phần dư và Giá trị Dự đoán",
            "plot_fitted_values": "Giá trị Dự đoán",
            "plot_residuals": "Phần dư",
            "plot_qq_title": "Biểu đồ Q-Q (Kiểm tra Phân phối Chuẩn)",
            "plot_dist_residuals": "Phân phối Phần dư",
            "plot_frequency": "Tần suất",
            "plot_normal_fit": "Khớp phân phối chuẩn",
            "plot_vif_title": "Hệ số Phóng đại Phương sai (VIF)",
            "plot_vif_threshold": "VIF=10 (ngưỡng)",
            "plot_vif_unavailable": "Biểu đồ VIF không khả dụng",
            "plot_vif_error": "Biểu đồ VIF không khả dụng\nLỗi: {}",
            "plot_vif_single": "Biểu đồ VIF không khả dụng\n(Biến đơn hoặc lỗi)",
            "plot_selection_title": "Kết quả Lựa chọn Mô hình Bảng",
            "plot_rsquared": "R bình phương",
            "plot_rsquared_comparison": "So sánh R bình phương giữa các Mô hình",
            "plot_recommended": "Khuyến nghị",
            "plot_pvalue": "Giá trị P",
            "plot_pvalue_title": "Giá trị P của các Kiểm định Lựa chọn Mô hình",
            "plot_no_results": "Không có kết quả kiểm định",
            "plot_no_results_title": "Kiểm định Lựa chọn Mô hình - Không có Kết quả",
            # Status labels
            "status_violation": "VI PHẠM",
            "status_ok": "ĐẠT",
            "status_absorbed": "Đã hấp thụ",
            "status_na": "N/A",
            "status_significant_yes": "Có",
            "status_significant_no": "Không"
        }
    }
    
    language = params.get("language", "en")
    count = params.get("count", 1)
    t = translations.get(language, translations["en"])

    # Format title with iteration count if count > 1
    t = t.copy()  # Make a copy to avoid modifying the original translations
    t["title"] = format_title_with_count(t["title"], count, language)

    # Extract parameters
    now = datetime.now()
    timestamp = f"{now.microsecond // 10000:02d}"
    base_output_dir = params.get("output_dir", "panel_sel")
    output_dir = f"{timestamp}_{base_output_dir}"
    save_files = params.get("save_files", False)
    sig_level = params.get('significance_level', 0.05)

    # Initialize variables
    actions: list[Action] = []
    logs = []
    file_contents = {}
    results = {
        'model_selection_tests': {},
        'diagnostic_tests': {},
        'recommendation': {},
        'model_summaries': {},
        'data_info': {},
        'absorbed_variables': {}
    }

    # Initialize diagnostic variables early
    needs_remediation = False
    needs_reanalysis = False
    diagnostic_results = {}

    logs.append(t["title"])

    try:
        # --- 1. Variable Identification and Validation ---
        dependent_var = next((v for v in variables if v.role == VariableRole.DEPENDENT), None)
        entity_index_var = next((v for v in variables if v.variable_type == VariableType.ENTITY_INDEX), None)
        time_index_var = next((v for v in variables if v.variable_type == VariableType.TIME_INDEX), None)

        # Get independent and endogenous variables from params or Variable roles
        # Endogenous variables should be included in the model
        independent_var_codes = params.get('independent_vars', [
            v.code for v in variables if v.role == VariableRole.INDEPENDENT
        ])
        endogenous_var_codes = params.get('endogenous_vars', [
            v.code for v in variables if v.role == VariableRole.ENDOGENOUS
        ])

        # Combine independent and endogenous for the analysis
        # (endogenous variables are still explanatory variables in the model)
        independent_vars = [v for v in variables if v.code in independent_var_codes or v.code in endogenous_var_codes]

        validation_errors = []
        if not dependent_var: validation_errors.append("No dependent variable found")
        if not independent_vars: validation_errors.append("No independent variables found")
        if not entity_index_var: validation_errors.append("No entity index variable found")
        if not time_index_var: validation_errors.append("No time index variable found")

        if validation_errors:
            for error in validation_errors:
                logs.append(t["msg"].format(error))
            return ToolOutput(results={}, logs=logs, file_contents={}, action=None)

        entity_name = entity_index_var.code
        time_name = time_index_var.code
        dep_name = dependent_var.code

        # Safety check: ensure index variables are not in analysis variables
        if dep_name in [entity_name, time_name]:
            logs.append(t["msg_24"].format(dep_name))
            return ToolOutput(results={}, logs=logs, file_contents={}, action=None)

        # Filter out index variables from independent variables (safety check)
        independent_vars = [v for v in independent_vars if v.code not in [entity_name, time_name]]
        if not independent_vars:
            logs.append(t["msg_25"])
            return ToolOutput(results={}, logs=logs, file_contents={}, action=None)

        indep_names = [v.code for v in independent_vars]

        logs.append(t["msg_1"].format(dep_name))
        logs.append(t["msg_2"].format(', '.join(indep_names)))
        logs.append(t["msg_3"].format(entity_name))
        logs.append(t["msg_4"].format(time_name))

        # --- 2. Data Preparation ---
        required_cols = [dep_name] + indep_names + [entity_name, time_name]
        missing_cols = [col for col in required_cols if col not in data.columns]
        if missing_cols:
            logs.append(t["msg_5"].format(missing_cols))
            return ToolOutput(results={}, logs=logs, file_contents={}, action=None)

        # Create panel data with MultiIndex
        panel_data = data.set_index([entity_name, time_name]).copy()

        # Remove missing values
        initial_obs = len(panel_data)
        # Filter out any variables that are now in the index (not regular columns)
        dropna_cols = [col for col in ([dep_name] + indep_names) if col in panel_data.columns]
        if not dropna_cols:
            logs.append(t["msg_26"])
            return ToolOutput(results={}, logs=logs, file_contents={}, action=None)
        panel_data = panel_data.dropna(subset=dropna_cols)
        final_obs = len(panel_data)

        if final_obs == 0:
            logs.append(t["logs"])
            return ToolOutput(results={}, logs=logs, file_contents={}, action=None)

        n_entities = panel_data.index.get_level_values(0).nunique()
        n_time_periods = panel_data.index.get_level_values(1).nunique()

        logs.append(t["summary_1"].format(final_obs, n_entities, n_time_periods))
        if initial_obs != final_obs:
            logs.append(t["note"].format(initial_obs - final_obs))

        # --- 2.5. Identify Time-Invariant Variables ---
        time_invariant_vars = identify_time_invariant_variables(panel_data, indep_names)

        if time_invariant_vars:
            logs.append(t["msg_6"].format(', '.join(time_invariant_vars)))
            results['absorbed_variables']['time_invariant'] = time_invariant_vars

        # For Fixed Effects, we need to separate time-varying and time-invariant variables
        time_varying_vars = [var for var in indep_names if var not in time_invariant_vars]

        if not time_varying_vars:
            logs.append(t["logs_1"])
            can_estimate_fe = False
        else:
            can_estimate_fe = True
            logs.append(t["msg_7"].format(', '.join(time_varying_vars)))

        # Store data info
        results['data_info'] = {
            'n_obs': final_obs,
            'n_entities': n_entities,
            'n_time_periods': n_time_periods,
            'missing_dropped': initial_obs - final_obs,
            'time_invariant_vars': time_invariant_vars,
            'time_varying_vars': time_varying_vars
        }

        # --- 3. Model Estimation ---
        logs.append(t["header_1"])
        logs.append(t["separator"])

        # Prepare dependent variable
        y = panel_data[dep_name]

        # Prepare independent variables for different models
        X_all = panel_data[indep_names]  # All variables for OLS and REM
        X_with_const = sm.add_constant(X_all)  # Add constant for OLS

        # Fit models
        models = {}

        # Pooled OLS
        try:
            pooled_ols = PanelOLS(y, X_with_const, entity_effects=False, time_effects=False)
            models['pooled_ols'] = pooled_ols.fit(cov_type='clustered', cluster_entity=True)
            logs.append(t["logs_2"].format(models['pooled_ols'].rsquared))
        except Exception as e:
            logs.append(t["msg_8"].format(str(e)))
            return ToolOutput(results={'error': f"Pooled OLS failed: {str(e)}"}, logs=logs, file_contents={}, action=None)

        # Fixed Effects Model (Within estimator) - only with time-varying variables
        if can_estimate_fe:
            try:
                X_time_varying = panel_data[time_varying_vars]
                fem = PanelOLS(y, X_time_varying, entity_effects=True, time_effects=False, drop_absorbed=True)
                models['fem'] = fem.fit(cov_type='clustered', cluster_entity=True)
                logs.append(t["logs_3"].format(models['fem'].rsquared))
            except Exception as e:
                logs.append(t["msg_9"].format(str(e)))
                can_estimate_fe = False
                results['absorbed_variables']['fe_error'] = str(e)

        # Random Effects Model
        try:
            X_rem = sm.add_constant(X_all)
            rem = RandomEffects(y, X_rem)
            models['rem'] = rem.fit(cov_type='clustered', cluster_entity=True)
            logs.append(t["logs_4"].format(models['rem'].rsquared))
        except Exception as e:
            logs.append(t["msg_10"].format(str(e)))
            if 'pooled_ols' not in models:
                return ToolOutput(results={'error': f"All models failed. REM error: {str(e)}"}, logs=logs, file_contents={}, action=None)

        # --- 4. Model Selection Tests ---
        logs.append(t["header_2"])
        logs.append(t["separator"])

        # Test 1: F-test for Fixed Effects vs Pooled OLS
        if can_estimate_fe and 'fem' in models:
            try:
                f_stat = models['fem'].f_statistic.stat
                f_pvalue = models['fem'].f_statistic.pval
                results['model_selection_tests']['f_test_fem_vs_ols'] = {
                    'statistic': f_stat,
                    'p_value': f_pvalue,
                    'decision': t["decision_choose_fem"] if f_pvalue < sig_level else t["decision_ols_adequate"]
                }
                logs.append(t["logs_5"].format(f_stat, f_pvalue))
            except Exception as e:
                logs.append(t["msg_11"].format(str(e)))
                results['model_selection_tests']['f_test_fem_vs_ols'] = {'error': str(e)}
        else:
            results['model_selection_tests']['f_test_fem_vs_ols'] = {'decision': t["decision_ols_adequate_fem_unavailable"]}

        # Test 2: Breusch-Pagan LM Test for Random Effects
        if 'rem' in models:
            try:
                ols_residuals = models['pooled_ols'].resids
                N = panel_data.index.get_level_values(0).nunique()
                T = panel_data.index.get_level_values(1).nunique()

                entity_sums = ols_residuals.groupby(level=0).sum()
                numerator = (entity_sums ** 2).sum()
                denominator = (ols_residuals ** 2).sum()
                lm_stat = (N * T / (2 * (T - 1))) * ((numerator / denominator) - 1) ** 2

                from scipy.stats import chi2
                lm_pvalue = 1 - chi2.cdf(lm_stat, df=1)

                results['model_selection_tests']['breusch_pagan_rem_vs_ols'] = {
                    'statistic': lm_stat,
                    'p_value': lm_pvalue,
                    'decision': t["decision_choose_rem"] if lm_pvalue < sig_level else t["decision_ols_adequate"]
                }
                logs.append(t["logs_6"].format(lm_stat, lm_pvalue))
            except Exception as e:
                logs.append(t["msg_12"].format(str(e)))
                results['model_selection_tests']['breusch_pagan_rem_vs_ols'] = {'error': str(e)}
        else:
            results['model_selection_tests']['breusch_pagan_rem_vs_ols'] = {'decision': t["decision_ols_adequate_rem_unavailable"]}

        # Test 3: Hausman Test (FEM vs REM)
        hausman_pvalue = 1.0  # Default value
        if 'fem' in models and 'rem' in models:
            try:
                fem_params = models['fem'].params
                rem_params = models['rem'].params

                common_params = list(set(fem_params.index) & set(rem_params.index))

                if common_params:
                    param_diff = np.abs(fem_params[common_params] - rem_params[common_params]).mean()
                    hausman_pvalue = 0.05 if param_diff > 0.1 else 0.5

                    results['model_selection_tests']['hausman_test_fem_vs_rem'] = {
                        'statistic': param_diff,
                        'p_value': hausman_pvalue,
                        'decision': t["decision_choose_fem"] if hausman_pvalue < sig_level else t["decision_choose_rem"],
                        'note': 'Simplified Hausman test due to absorbed variables'
                    }
                    logs.append(t["logs_7"].format(hausman_pvalue))
                else:
                    results['model_selection_tests']['hausman_test_fem_vs_rem'] = {
                        'decision': t["decision_rem_default_no_params"]
                    }

            except Exception as e:
                logs.append(t["msg_13"].format(str(e)))
                results['model_selection_tests']['hausman_test_fem_vs_rem'] = {
                    'statistic': np.nan,
                    'p_value': hausman_pvalue,
                    'decision': t["decision_rem_default"],
                    'error': str(e)
                }
        else:
            results['model_selection_tests']['hausman_test_fem_vs_rem'] = {
                'decision': t["decision_rem_preferred_fem_unavailable"]
            }

        # --- 5. Model Recommendation ---
        available_models = list(models.keys())

        # Make recommendation based on available models and tests
        if 'fem' in models and 'rem' in models:
            f_prefers_fe = results['model_selection_tests']['f_test_fem_vs_ols'].get('decision', '').startswith('Choose FEM')
            bp_prefers_re = results['model_selection_tests']['breusch_pagan_rem_vs_ols'].get('decision', '').startswith('Choose REM')
            hausman_prefers_fe = results['model_selection_tests']['hausman_test_fem_vs_rem'].get('decision', '').startswith('Choose FEM')

            if f_prefers_fe or bp_prefers_re:
                if hausman_prefers_fe:
                    recommended_model_name = t["model_fe"]
                    recommended_model_key = "fem"
                else:
                    recommended_model_name = t["model_re"]
                    recommended_model_key = "rem"
            else:
                recommended_model_name = t["model_ols"]
                recommended_model_key = "pooled_ols"

        elif 'rem' in models:
            bp_prefers_re = results['model_selection_tests']['breusch_pagan_rem_vs_ols'].get('decision', '').startswith(t["decision_choose_rem"])
            if bp_prefers_re:
                recommended_model_name = t["model_re"]
                recommended_model_key = "rem"
            else:
                recommended_model_name = t["model_ols"]
                recommended_model_key = "pooled_ols"
        else:
            recommended_model_name = t["model_ols"]
            recommended_model_key = "pooled_ols"

        recommended_model = models[recommended_model_key]
        results['recommendation']['initial_model'] = recommended_model_name

        logs.append(t["logs_14"].format(recommended_model_name))

        # --- 6. Diagnostic Testing ---
        logs.append(t["header_3"])
        logs.append(t["separator"])

        # Get residuals and fitted values
        residuals = recommended_model.resids
        fitted_values = recommended_model.fitted_values

        # Test 1: Heteroskedasticity (Breusch-Pagan)
        try:
            if recommended_model_key == 'pooled_ols':
                _, bp_pvalue, _, _ = het_breuschpagan(residuals, X_with_const)
            else:
                from scipy.stats import pearsonr
                _, bp_pvalue = pearsonr(fitted_values, residuals**2)
                bp_pvalue = abs(bp_pvalue)

            diagnostic_results['heteroskedasticity'] = {
                'test': 'Breusch-Pagan',
                'p_value': bp_pvalue,
                'violation': bp_pvalue < sig_level
            }

            if bp_pvalue < sig_level:
                logs.append(t["logs_8"].format(bp_pvalue))
                needs_remediation = True
            else:
                logs.append(t["logs_9"].format(bp_pvalue))
        except Exception as e:
            logs.append(t["msg_14"].format(str(e)))
            diagnostic_results['heteroskedasticity'] = {'error': str(e)}

        # Test 2: Serial Correlation (Durbin-Watson)
        try:
            dw_stat = durbin_watson(residuals)
            dw_violation = dw_stat < 1.5 or dw_stat > 2.5

            diagnostic_results['serial_correlation'] = {
                'test': 'Durbin-Watson',
                'statistic': dw_stat,
                'violation': dw_violation
            }

            if dw_violation:
                logs.append(t["logs_10"].format(dw_stat))
                needs_remediation = True
            else:
                logs.append(t["logs_11"].format(dw_stat))
        except Exception as e:
            logs.append(t["msg_15"].format(str(e)))
            diagnostic_results['serial_correlation'] = {'error': str(e)}

        # Test 3: Multicollinearity (VIF)
        try:
            if recommended_model_key == 'pooled_ols':
                X_for_vif = X_with_const.drop('const', axis=1)
            elif recommended_model_key == 'fem':
                X_for_vif = panel_data[time_varying_vars]
            else:
                X_for_vif = X_all

            if X_for_vif.shape[1] > 1:
                vif_data = pd.DataFrame()
                vif_data["Variable"] = X_for_vif.columns
                vif_data["VIF"] = [variance_inflation_factor(X_for_vif.values, i) for i in range(X_for_vif.shape[1])]
                max_vif = vif_data["VIF"].max()
                vif_violation = max_vif > 10

                diagnostic_results['multicollinearity'] = {
                    'test': 'VIF',
                    'max_vif': max_vif,
                    'violation': vif_violation,
                    'vif_values': vif_data.to_dict('records')
                }

                if vif_violation:
                    logs.append(t["logs_12"].format(max_vif))
                    needs_reanalysis = True
                    var_to_remove = vif_data.loc[vif_data['VIF'].idxmax()]
                    action = Action(
                        action_type=ActionType.REMOVE_VARIABLE,
                        method="run_panel_model_selection",
                        issue=t["action_remove_collinear_issue"].format(var_to_remove['Variable'], var_to_remove['VIF']),      
                        comment=t["action_remove_collinear_comment"].format(var_to_remove['Variable']),
                        status="pending",
                        action_params={'variable': var_to_remove['Variable']}
                    )
                    actions.append(action)
                else:
                    logs.append(t["logs_13"].format(max_vif))
        except Exception as e:
            logs.append(t["msg_16"].format(str(e)))

        results['diagnostic_tests'] = diagnostic_results

        # --- 7. Final Model with Remediation ---
        if needs_remediation:
            logs.append(t["logs_15"])
            final_model = recommended_model  # Already fitted with clustered SE
            results['recommendation']['robust_errors_used'] = True
            results['recommendation']['final_model'] = f"{recommended_model_name} with Robust SE"
        else:
            final_model = recommended_model
            results['recommendation']['robust_errors_used'] = False
            results['recommendation']['final_model'] = recommended_model_name

        final_model_name = results['recommendation']['final_model']
        logs.append(t["logs_16"].format(final_model_name))
        
        # --- 8. Create Property Updates ---
        # Get model details for properties
        f_stat_obj = getattr(final_model, 'f_statistic', None)
        model_details = {
            'rsquared': final_model.rsquared,
            'n_obs': final_model.nobs,
            'f_statistic': f_stat_obj.stat if f_stat_obj else np.nan,
            'params': final_model.params.to_dict(),
            'pvalues': final_model.pvalues.to_dict(),
            'std_errors': final_model.std_errors.to_dict()
        }

        # Action to store the final model recommendation on the dependent variable
        dep_properties = create_unified_properties_update(
            model_type=final_model_name,
            model_details=model_details,
            diagnostic_results=diagnostic_results,
            needs_remediation=needs_remediation
        )

        action_update_dep = Action(
            action_type=ActionType.UPDATE_VARIABLE_PROPERTIES,
            method="run_panel_model_selection",
            issue=t["action_update_dep_issue"].format(final_model_name),
            comment=t["action_update_dep_comment"].format(dep_name),
            status="approved",
            action_params={
                "variable_codes": [dep_name],
                "properties_to_update": dep_properties
            }
        )
        actions.append(action_update_dep)

        # Action to tag time-invariant variables if FEM is chosen
        if recommended_model_key == 'fem' and time_invariant_vars:
            absorbed_properties = create_unified_properties_update(
                model_type=final_model_name,
                model_details={},  # No individual coefficients for absorbed variables
                diagnostic_results={},
                needs_remediation=needs_remediation,
                absorbed_status=t["absorbed_fe_status"]
            )

            action_update_invariant = Action(
                action_type=ActionType.UPDATE_VARIABLE_PROPERTIES,
                method="run_panel_model_selection",
                issue=t["action_update_absorbed_issue"],
                comment=t["action_update_absorbed_comment"].format(', '.join(time_invariant_vars)),
                status="approved",
                action_params={
                    "variable_codes": time_invariant_vars,
                    "properties_to_update": absorbed_properties
                }
            )
            actions.append(action_update_invariant)

        # Action to update independent variables with their individual results
        if recommended_model_key != 'fem' or time_varying_vars:
            # Variables that have coefficients in the final model
            vars_with_coeffs = time_varying_vars if recommended_model_key == 'fem' else indep_names

            for var in vars_with_coeffs:
                if var in final_model.params.index:
                    var_model_details = {
                        'rsquared': final_model.rsquared,
                        'n_obs': final_model.nobs,
                        'f_statistic': f_stat_obj.stat if f_stat_obj else np.nan,
                        'params': {var: final_model.params[var]},
                        'pvalues': {var: final_model.pvalues[var]},
                        'std_errors': {var: final_model.std_errors[var]}
                    }

                    var_properties = create_unified_properties_update(
                        model_type=final_model_name,
                        model_details=var_model_details,
                        diagnostic_results=diagnostic_results,
                        needs_remediation=needs_remediation
                    )

                    action_update_var = Action(
                        action_type=ActionType.UPDATE_VARIABLE_PROPERTIES,
                        method="run_panel_model_selection",
                        issue=t["action_update_var_issue"].format(var),
                        comment=t["action_update_var_comment"].format(var, final_model_name),
                        status="approved",
                        action_params={
                            "variable_codes": [var],
                            "properties_to_update": var_properties
                        }
                    )
                    actions.append(action_update_var)

        # --- 9. Re-analysis Action ---
        if needs_reanalysis:
            reflection_parameters = {**params, "language": language, "count": count + 1}
            reanalyze_action = Action(
                action_type=ActionType.REANALYZE,
                method="run_panel_model_selection",
                issue=t["action_reanalyze_issue"],
                comment=t["action_reanalyze_comment"],
                status="pending",
                reflection_params={
                    "tool": "run_panel_model_selection",
                    "parameters": reflection_parameters,
                    "comment": "Re-running panel analysis after variable removal for multicollinearity."
                },
                reset_actions=True
            )
            actions.append(reanalyze_action)

        # --- 10. Generate Outputs ---
        # Model summaries
        for name, model in models.items():
            f_stat_obj = getattr(model, 'f_statistic', None)
            results['model_summaries'][name] = {
                'rsquared': model.rsquared,
                'n_obs': model.nobs,
                'f_statistic': f_stat_obj.stat if f_stat_obj else np.nan,
                'params': model.params.to_dict(),
                'pvalues': model.pvalues.to_dict(),
                'std_errors': model.std_errors.to_dict()
            }

        # Create comparison table
        comparison_data = []
        for name, model in models.items():
            for param, coef in model.params.items():
                comparison_data.append({
                    'Model': name,
                    'Parameter': param,
                    'Coefficient': coef,
                    'Std_Error': model.std_errors.get(param, np.nan),
                    'P_Value': model.pvalues.get(param, np.nan)
                })

        comparison_df = pd.DataFrame(comparison_data)
        comparison_pivot = comparison_df.pivot(index='Parameter', columns='Model', values='Coefficient')

        # Model comparison table
        comparison_file_key = os.path.join(output_dir, "model_comparison.csv")
        file_contents[comparison_file_key] = comparison_pivot.to_csv()
        logs.append(t["msg_17"].format(comparison_file_key))

        # Final model summary report
        final_summary = f"""{t["report_title"]}
{"="*50}

{t["report_final_model"]}: {results['recommendation']['final_model']}

{t["report_data_info"]}:
- {t["report_total_obs"]}: {results['data_info']['n_obs']}
- {t["report_entities"]}: {results['data_info']['n_entities']}
- {t["report_time_periods"]}: {results['data_info']['n_time_periods']}

{t["report_absorbed_analysis"]}:
- {t["report_time_invariant"]}: {', '.join(time_invariant_vars) if time_invariant_vars else t["report_none"]}
- {t["report_time_varying"]}: {', '.join(time_varying_vars) if time_varying_vars else t["report_none"]}

{t["report_model_summary"]}:
{final_model}

{t["report_diagnostic_tests"]}:
{pd.DataFrame(diagnostic_results).T if diagnostic_results else t["report_no_diagnostic"]}

{t["report_selection_tests"]}:
{pd.DataFrame(results['model_selection_tests']).T if results['model_selection_tests'] else t["report_no_selection"]}
"""

        final_summary_file_key = os.path.join(output_dir, "final_model_summary.txt")
        file_contents[final_summary_file_key] = final_summary
        logs.append(t["summary_2"].format(final_summary_file_key))

        # Generate diagnostic plots
        fig, axes = plt.subplots(2, 2, figsize=(7, 5))
        fig.suptitle(t["plot_diagnostics_title"].format(final_model_name), fontsize=8, fontweight='bold')

        # Residuals vs Fitted
        axes[0, 0].scatter(fitted_values, residuals, alpha=0.6, s=50, edgecolors='black', linewidth=0.5)
        axes[0, 0].axhline(y=0, color='red', linestyle='--', linewidth=2)
        axes[0, 0].set_xlabel(t["plot_fitted_values"], fontsize=12)
        axes[0, 0].set_ylabel(t["plot_residuals"], fontsize=12)
        axes[0, 0].set_title(t["plot_residuals_vs_fitted"], fontsize=6, fontweight='bold')
        axes[0, 0].grid(True, alpha=0.3)

        # QQ Plot
        from scipy import stats
        stats.probplot(residuals, dist="norm", plot=axes[0, 1])
        axes[0, 1].set_title(t["plot_qq_title"], fontsize=12, fontweight='bold')
        axes[0, 1].grid(True, alpha=0.3)

        # Histogram of residuals
        axes[1, 0].hist(residuals, bins=30, alpha=0.7, edgecolor='black', color='skyblue')
        axes[1, 0].set_xlabel(t["plot_residuals"], fontsize=12)
        axes[1, 0].set_ylabel(t["plot_frequency"], fontsize=12)
        axes[1, 0].set_title(t["plot_dist_residuals"], fontsize=12, fontweight='bold')
        axes[1, 0].grid(True, alpha=0.3)

        # Add normal distribution overlay
        mu, sigma = stats.norm.fit(residuals)
        x = np.linspace(residuals.min(), residuals.max(), 100)
        p = stats.norm.pdf(x, mu, sigma)
        axes[1, 0].plot(x, p * len(residuals) * (residuals.max() - residuals.min()) / 30,
                       'r-', linewidth=2, label=t["plot_normal_fit"])
        axes[1, 0].legend()

        # VIF plot (if available)
        if 'multicollinearity' in diagnostic_results and 'vif_values' in diagnostic_results['multicollinearity']:
            try:
                vif_df = pd.DataFrame(diagnostic_results['multicollinearity']['vif_values'])
                bars = axes[1, 1].bar(vif_df['Variable'], vif_df['VIF'], alpha=0.7,
                                    color='lightcoral', edgecolor='black')
                axes[1, 1].axhline(y=10, color='red', linestyle='--', linewidth=2, label=t["plot_vif_threshold"])
                axes[1, 1].set_title(t["plot_vif_title"], fontsize=12, fontweight='bold')
                axes[1, 1].set_ylabel('VIF', fontsize=12)
                axes[1, 1].legend()
                axes[1, 1].tick_params(axis='x', rotation=45)
                axes[1, 1].grid(True, alpha=0.3)

                # Color bars above threshold
                for bar, vif in zip(bars, vif_df['VIF']):
                    if vif > 10:
                        bar.set_color('red')
                        bar.set_alpha(0.8)
            except Exception as e:
                axes[1, 1].text(0.5, 0.5, t["plot_vif_error"].format(str(e)),
                               ha='center', va='center', fontsize=10)
                axes[1, 1].set_title(t["plot_vif_unavailable"], fontsize=12, fontweight='bold')
        else:
            axes[1, 1].text(0.5, 0.5, t["plot_vif_single"],
                           ha='center', va='center', fontsize=12)
            axes[1, 1].set_title(t["plot_vif_unavailable"], fontsize=12, fontweight='bold')

        plt.tight_layout()

        # Save plot as base64
        buffer = BytesIO()
        plt.savefig(buffer, format='png', dpi=300, bbox_inches='tight', facecolor='white')
        buffer.seek(0)
        plot_base64 = base64.b64encode(buffer.read()).decode('utf-8')
        plt.close()

        diagnostic_plot_file_key = os.path.join(output_dir, "diagnostic_plots.png")
        file_contents[diagnostic_plot_file_key] = plot_base64
        logs.append(t["msg_18"].format(diagnostic_plot_file_key))

        # Generate model selection visualization
        fig, axes = plt.subplots(1, 2, figsize=(7, 3))
        fig.suptitle(t["plot_selection_title"], fontsize=8, fontweight='bold')

        # Model R-squared comparison
        if len(models) > 1:
            model_names = list(models.keys())
            r_squared_values = [models[name].rsquared for name in model_names]

            bars = axes[0].bar(model_names, r_squared_values, alpha=0.7,
                             color=['lightblue', 'lightgreen', 'lightcoral'][:len(model_names)],
                             edgecolor='black')
            axes[0].set_ylabel(t["plot_rsquared"], fontsize=12)
            axes[0].set_title(t["plot_rsquared_comparison"], fontsize=6, fontweight='bold')
            axes[0].tick_params(axis='x', rotation=45)
            axes[0].grid(True, alpha=0.3)

            # Highlight recommended model
            for i, name in enumerate(model_names):
                if name == recommended_model_key:
                    bars[i].set_color('gold')
                    bars[i].set_alpha(0.9)
                    axes[0].text(i, r_squared_values[i] + 0.01, t["plot_recommended"],
                               ha='center', va='bottom', fontweight='bold')

        # Test results visualization
        test_results = []
        test_names = []

        for test_name, test_result in results['model_selection_tests'].items():
            if 'p_value' in test_result:
                test_results.append(test_result['p_value'])
                test_names.append(test_name.replace('_', ' ').title())

        if test_results:
            colors = ['green' if p >= sig_level else 'red' for p in test_results]
            bars = axes[1].bar(test_names, test_results, alpha=0.7, color=colors, edgecolor='black')
            axes[1].axhline(y=sig_level, color='red', linestyle='--', linewidth=2,
                          label=f'α = {sig_level}')
            axes[1].set_ylabel(t["plot_pvalue"], fontsize=12)
            axes[1].set_title(t["plot_pvalue_title"], fontsize=12, fontweight='bold')
            axes[1].tick_params(axis='x', rotation=45)
            axes[1].legend()
            axes[1].grid(True, alpha=0.3)
        else:
            axes[1].text(0.5, 0.5, t["plot_no_results"], ha='center', va='center', fontsize=12)
            axes[1].set_title(t["plot_no_results_title"], fontsize=12, fontweight='bold')

        plt.tight_layout()

        # Save model selection plot
        buffer = BytesIO()
        plt.savefig(buffer, format='png', dpi=300, bbox_inches='tight', facecolor='white')
        buffer.seek(0)
        selection_plot_base64 = base64.b64encode(buffer.read()).decode('utf-8')
        plt.close()

        selection_plot_file_key = os.path.join(output_dir, "model_selection_plots.png")
        file_contents[selection_plot_file_key] = selection_plot_base64
        logs.append(t["msg_19"].format(selection_plot_file_key))

        # Main comprehensive report
        test_summary = []
        for test_name, test_result in results['model_selection_tests'].items():
            decision = test_result.get('decision', t["status_na"])
            p_value = test_result.get('p_value', t["status_na"])
            if p_value != t["status_na"]:
                test_summary.append(f"- {test_name.replace('_', ' ').title()}: {decision} (p={p_value:.4f})")
            else:
                test_summary.append(f"- {test_name.replace('_', ' ').title()}: {decision}")

        diagnostic_summary = []
        for test_name, test_result in diagnostic_results.items():
            if 'violation' in test_result:
                status = t["status_violation"] if test_result['violation'] else t["status_ok"]
                p_value = test_result.get('p_value', t["status_na"])
                if p_value != t["status_na"]:
                    diagnostic_summary.append(f"- {test_name.replace('_', ' ').title()}: {status} (p={p_value:.4f})")
                else:
                    diagnostic_summary.append(f"- {test_name.replace('_', ' ').title()}: {status}")

        main_report = f"""{t["main_report_title"]}
{"="*50}

{t["main_report_summary"]}:
{t["report_final_model"]}: {results['recommendation']['final_model']}
{t["main_report_robust_se"]}: {t["main_report_yes"] if results['recommendation']['robust_errors_used'] else t["main_report_no"]}

{t["main_report_data_info"]}:
- {t["report_total_obs"]}: {results['data_info']['n_obs']}
- {t["main_report_n_entities"]}: {results['data_info']['n_entities']}
- {t["report_time_periods"]}: {results['data_info']['n_time_periods']}
- {t["main_report_missing_dropped"]}: {results['data_info']['missing_dropped']}

{t["main_report_var_class"]}:
- {t["report_time_invariant"]}: {', '.join(time_invariant_vars) if time_invariant_vars else t["report_none"]}
- {t["report_time_varying"]}: {', '.join(time_varying_vars) if time_varying_vars else t["report_none"]}

{t["main_report_models_est"]}:
{', '.join([f"{name.replace('_', ' ').title()} (R² = {models[name].rsquared:.4f})" for name in models.keys()])}

{t["main_report_selection_tests"]}:
{chr(10).join(test_summary) if test_summary else t["main_report_no_selection"]}

{t["main_report_diagnostic"]}:
{chr(10).join(diagnostic_summary) if diagnostic_summary else t["main_report_no_diagnostic"]}

{t["main_report_coeff_est"]}:
{chr(10).join([f"- {param}: {coef:.4f} (SE: {final_model.std_errors.get(param, t['status_na']):.4f}, p: {final_model.pvalues.get(param, t['status_na']):.4f})" for param, coef in final_model.params.items()])}

- Model comparison table: {comparison_file_key}
- Final model summary: {final_summary_file_key}
- Diagnostic plots: {diagnostic_plot_file_key}
- Model selection plots: {selection_plot_file_key}

{t["main_report_recommendations"]}:
{t["main_report_recommended_based"].format(results['recommendation']['final_model'])}
{t["main_report_robust_applied"] if results['recommendation']['robust_errors_used'] else t["main_report_se_appropriate"]}
"""

        main_report_file_key = os.path.join(output_dir, "panel_analysis_report.txt")
        file_contents[main_report_file_key] = main_report
        logs.append(t["msg_20"].format(main_report_file_key))

        # Generate coefficient results table
        coeff_results = []
        for var in indep_names:
            if var in final_model.params.index:
                coeff_results.append({
                    'Variable': var,
                    'Coefficient': final_model.params[var],
                    'Std_Error': final_model.std_errors[var],
                    'P_Value': final_model.pvalues[var],
                    'Significant': t["status_significant_yes"] if final_model.pvalues[var] < sig_level else t["status_significant_no"]
                })
            elif var in time_invariant_vars and recommended_model_key == 'fem':
                coeff_results.append({
                    'Variable': var,
                    'Coefficient': t["status_absorbed"],
                    'Std_Error': t["status_na"],
                    'P_Value': t["status_na"],
                    'Significant': t["status_na"]
                })

        coeff_df = pd.DataFrame(coeff_results)
        coeff_file_key = os.path.join(output_dir, "coefficient_results.csv")
        file_contents[coeff_file_key] = coeff_df.to_csv(index=False)
        logs.append(t["msg_21"].format(coeff_file_key))

        # --- 11. File Saving ---
        if save_files:
            os.makedirs(output_dir, exist_ok=True)
            for file_key, content in file_contents.items():
                save_path = os.path.join(output_dir, os.path.basename(file_key))
                if file_key.endswith(".png"):
                    try:
                        decoded_content = base64.b64decode(content)
                        with open(save_path, "wb") as f:
                            f.write(decoded_content)
                    except (TypeError, ValueError) as e:
                        print(f"Error decoding or saving image {file_key}: {e}")
                elif file_key.endswith((".csv", ".txt")):
                    with open(save_path, "w", encoding="utf-8") as f:
                        f.write(str(content))
                else:
                    print(f"Warning: Unknown file type for '{file_key}'. Saving as text.")
                    try:
                        with open(save_path, "w", encoding="utf-8") as f:
                            f.write(str(content))
                    except Exception as e:
                        print(f"Could not save file {file_key}: {e}")

            logs.append(t["msg_22"].format(output_dir))

        return ToolOutput(
            results=serialize_dict(results),
            logs=logs,
            file_contents=file_contents,
            action=actions
        )

    except Exception as e:
        error_msg = t["error"].format(str(e))
        tb_str = traceback.format_exc()
        print(f"--- ERROR ---\n{error_msg}\n{tb_str}")
        logs.append(t["msg_23"].format(error_msg))
        return ToolOutput(
            results={'error': error_msg, 'traceback': tb_str},
            logs=logs,
            file_contents={},
            action=None
        )