import pandas as pd
import numpy as np
import os
import statsmodels.api as sm
from scipy import stats
from io import BytesIO
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from sklearn.metrics import roc_curve, auc, confusion_matrix
from statsmodels.stats.outliers_influence import variance_inflation_factor
import seaborn as sns
from sklearn.metrics import classification_report
from sklearn.calibration import CalibrationDisplay

import base64
from datetime import datetime
from scipy.stats import shapiro
import numpy as np
from statsmodels.stats.diagnostic import het_breuschpagan
from sklearn.metrics import mean_squared_error, mean_absolute_error
import logging
import os
import pandas as pd
import numpy as np
from datetime import datetime
import matplotlib.pyplot as plt
from io import BytesIO
import base64
import seaborn as sns

logger = logging.getLogger(__name__)

from data_analysis.src.schemas.analyzer_states import (
    Variable, 
    Action, 
    ToolOutput, 
    ActionType, 
    VariableRole, 
    VariableType
)

# Import Actual Utility Functions
from data_analysis.src.modules.tools.analysis.cross_section.utils import durbin_watson_test, fisher_f_test
from data_analysis.src.modules.tools.analysis.cross_section.pipeline_utils import (
    compute_coefficients_table, evaluate_model_fit, get_t_dict, format_title_with_count
)

from data_analysis.src.modules.utils import serialize_dict, parse_variable_values

######################################################
################# LINEAR REGRESSION ##################
######################################################

def shapiro_wilk_test(residuals: np.ndarray) -> dict:
    """Perform Shapiro-Wilk test for normality of residuals."""
    stat, p_value = shapiro(residuals)
    return {"statistic": stat, "p_value": p_value}

def breusch_pagan_test(data: pd.DataFrame, dependent_var: str, independent_vars: list[str]) -> dict:
    """Perform Breusch-Pagan test for heteroscedasticity."""
    X = sm.add_constant(data[independent_vars])
    model = sm.OLS(data[dependent_var], X).fit()
    bp_test = het_breuschpagan(model.resid, X)
    return {
        "lm_statistic": bp_test[0],
        "lm_p_value": bp_test[1],
        "f_statistic": bp_test[2],
        "f_p_value": bp_test[3]
    }

def compute_rmse_mae(data: pd.DataFrame, dependent_var: str, independent_vars: list[str]) -> dict:
    """Compute RMSE and MAE for the regression model."""
    X = sm.add_constant(data[independent_vars])
    model = sm.OLS(data[dependent_var], X).fit()
    predictions = model.predict(X)
    rmse = np.sqrt(mean_squared_error(data[dependent_var], predictions))
    mae = mean_absolute_error(data[dependent_var], predictions)
    return {"RMSE": rmse, "MAE": mae}

def create_residual_plot(residuals: np.ndarray, predicted_values: np.ndarray, t: dict = None) -> str:
    """Create a professional residual plot."""
    t_dict = t or {
        "residual_plot_xlabel": "Predicted Values",
        "residual_plot_ylabel": "Residuals",
        "residual_plot_title": "Residuals vs Predicted Values"
    }
    plt.figure(figsize=(5, 4))
    plt.scatter(predicted_values, residuals, alpha=0.6, edgecolors='steelblue', facecolors='none', s=50)
    plt.axhline(y=0, color='red', linestyle='--', linewidth=1)
    plt.xlabel(t_dict.get("residual_plot_xlabel", "Predicted Values"), fontsize=6)
    plt.ylabel(t_dict.get("residual_plot_ylabel", "Residuals"), fontsize=6)
    plt.title(t_dict.get("residual_plot_title", "Residuals vs Predicted Values"), fontsize=7, fontweight='bold')
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    
    buffer = BytesIO()
    plt.savefig(buffer, format="png", dpi=300, bbox_inches='tight')
    buffer.seek(0)
    image_png = buffer.getvalue()
    base64_string = base64.b64encode(image_png).decode("utf-8")
    plt.close()
    return base64_string

def create_qq_plot(residuals: np.ndarray, t: dict = None) -> str:
    """Create a professional Q-Q plot."""
    t_dict = t or {
        "qq_plot_title": "Q-Q Plot of Residuals",
        "qq_plot_xlabel": "Theoretical Quantiles",
        "qq_plot_ylabel": "Sample Quantiles"
    }
    plt.figure(figsize=(4, 3))
    sm.qqplot(residuals, line='45', fit=True)
    plt.title(t_dict.get("qq_plot_title", "Q-Q Plot of Residuals"), fontsize=7, fontweight='bold')
    plt.xlabel(t_dict.get("qq_plot_xlabel", "Theoretical Quantiles"), fontsize=6)
    plt.ylabel(t_dict.get("qq_plot_ylabel", "Sample Quantiles"), fontsize=6)
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    
    buffer = BytesIO()
    plt.savefig(buffer, format="png", dpi=300, bbox_inches='tight')
    buffer.seek(0)
    base64_string = base64.b64encode(buffer.getvalue()).decode("utf-8")
    plt.close()
    return base64_string

def create_histogram(residuals: np.ndarray, t: dict = None) -> str:
    """Create a professional histogram of residuals."""
    t_dict = t or {
        "hist_plot_xlabel": "Residuals",
        "hist_plot_ylabel": "Frequency",
        "hist_plot_title": "Histogram of Residuals"
    }
    plt.figure(figsize=(4, 3))
    plt.hist(residuals, bins=30, edgecolor='black', alpha=0.7, color='skyblue')
    plt.xlabel(t_dict.get("hist_plot_xlabel", "Residuals"), fontsize=6)
    plt.ylabel(t_dict.get("hist_plot_ylabel", "Frequency"), fontsize=6)
    plt.title(t_dict.get("hist_plot_title", "Histogram of Residuals"), fontsize=7, fontweight='bold')
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    
    buffer = BytesIO()
    plt.savefig(buffer, format="png", dpi=300, bbox_inches='tight')
    buffer.seek(0)
    base64_string = base64.b64encode(buffer.getvalue()).decode("utf-8")
    plt.close()
    return base64_string

def create_actual_vs_predicted_plot(actual: np.ndarray, predicted: np.ndarray, dependent_name: str, t: dict = None) -> str:
    """Create a professional actual vs predicted plot."""
    t_dict = t or {
        "actual_vs_pred_xlabel": "Actual",
        "actual_vs_pred_ylabel": "Predicted",
        "actual_vs_pred_title": "Actual vs Predicted Values",
        "perfect_prediction": "Perfect Prediction"
    }
    plt.figure(figsize=(4, 3))
    plt.scatter(actual, predicted, alpha=0.6, s=50, edgecolors='steelblue', facecolors='none')
    plt.plot([actual.min(), actual.max()], [actual.min(), actual.max()], 'r--', lw=2, label=t_dict.get("perfect_prediction", "Perfect Prediction"))
    plt.xlabel(f'{t_dict.get("actual_vs_pred_xlabel", "Actual")} {dependent_name}', fontsize=6)
    plt.ylabel(f'{t_dict.get("actual_vs_pred_ylabel", "Predicted")} {dependent_name}', fontsize=6)
    plt.title(t_dict.get("actual_vs_pred_title", "Actual vs Predicted Values"), fontsize=7, fontweight='bold')
    plt.grid(True, alpha=0.3)
    plt.legend()
    plt.tight_layout()
    
    buffer = BytesIO()
    plt.savefig(buffer, format="png", dpi=300, bbox_inches='tight')
    buffer.seek(0)
    base64_string = base64.b64encode(buffer.getvalue()).decode("utf-8")
    plt.close()
    return base64_string

def run_regression_analysis(
    data: pd.DataFrame,
    variables: list[Variable],
    params: dict
) -> ToolOutput:
    """
    Perform multiple regression analysis and model evaluation, generating comprehensive reports.

    This function groups observed variables by parent code for latent variables, computes their mean,
    and uses them in regression analysis. It provides detailed coefficient analysis, model diagnostics,
    and generates visualizations for model validation.

    Parameters:
        data: Input DataFrame containing observed variables
        variables: list of Variable objects (dependent and independent, including latent and observed)
        params: dictionary containing analysis parameters
            - output_dir (str): base output directory name (default: "regression_analysis")
            - save_files (bool): whether to save generated files to disk (default: False)
            - variable_names (dict): mapping of variable codes to display names (optional)
            - language (str): language for output messages - "en" or "vi" (default: "en")

    Returns:
        ToolOutput: Contains results, logs, file contents, and suggested actions
    """
    # Extract parameters
    base_output_dir = params.get("output_dir", "regress")
    save_files = params.get("save_files", False)
    variable_names = params.get("variable_names", {v.code: v.name for v in variables})
    language = params.get("language", "en")
    count = params.get("count", 1)

    # Define translations dictionary
    translations = {
        "en": {
            "title": "# Multiple Regression Analysis Report\n\n",
            "section_title": "## Multiple Regression Analysis\n\n",
            "error_dep_var": "**ERROR**: Exactly one dependent group (latent or single observed) required, found {}.\n",
            "error_indep_var": "**ERROR**: No valid independent variables found in the data.\n",
            "intro": "Multiple regression analysis was performed using Ordinary Least Squares (OLS) method to assess the impact of independent variables on the dependent variable `{}`.\n\n",
            "coeff_section": "### Regression Coefficients\n\n",
            "coeff_table": "The coefficients table: `{}`\n\n",
            "interpretation": "**Interpretation**:\n",
            "analysis_results": "**Analysis Results**:\n",
            "no_significance": "**Analysis Results**: No independent variables show statistical significance.",
            "sig_effect": "- Variable `{}` ({}) has significant statistical effect on `{}` (p = {:.3f}).",
            "no_sig_effect": "- Variable `{}` ({}) has no significant statistical effect on `{}` (p = {:.3f}).",
            "unstd_equation": "\n**Unstandardized Regression Equation**:\n{}\n\n",
            "std_equation": "**Standardized Regression Equation**:\n{}",
            "model_eval_section": "### Model Evaluation\n\n",
            "model_eval_desc": "This section evaluates the goodness of fit of the regression model using adjusted R² and related metrics.\n\n",
            "model_fit_table_section": "#### Model Fit Summary Table\n\n",
            "model_summary_file": "The model summary table: `{}`\n\n",
            "assessment": "**Assessment**:\n",
            "model_fit_msg": "The adjusted R² coefficient is {:.3f}. The independent variables explain {:.1f}% of the variation in `{}`. {}\nDurbin-Watson coefficient: {:.3f} (ideal range ~1–3, optimal ~2 indicates no autocorrelation).",
            "model_suitable": "The model is suitable for research as adjusted R² ≥ 0.50.",
            "model_not_suitable": "The model may not be suitable as adjusted R² < 0.50.",
            "model_testing_section": "## Model Testing\n\n",
            "t_test_section": "### Testing Independent Variables Xi (Student's t-test)\n",
            "t_test_desc": "Based on regression analysis results to test component variables:\n",
            "t_test_intercept": "Intercept significance (p-value) is {:.3f} {}, {}",
            "t_test_intercept_sig": "< 0.05",
            "t_test_intercept_not_sig": ">= 0.05",
            "t_test_intercept_conclusion_sig": "so the intercept is statistically significant at 5% level.",
            "t_test_intercept_conclusion_not_sig": "so the intercept is not statistically significant.",
            "t_test_var": "- Variable `{}` ({}): p-value = {:.3f} {}, {} `{}` with coefficient β = {:.3f}.",
            "reject_h0": "< 0.05",
            "not_reject_h0": ">= 0.05",
            "affects": "reject H0, affects",
            "no_affect": "fail to reject H0, does not affect",
            "f_test_section": "### Testing Overall Model (Fisher's F-test)\n",
            "f_formula": "F-statistic calculated using formula: F = (R²(n-k-1))/(1-R²)k = ({:.3f} x ({}-{}-1))/((1-{:.3f}) x {}) = {:.3f}\n\n",
            "f_table_title": "**Fisher's F-test Table**:\n",
            "f_table_file": "The F-test table: `{}`\n\n",
            "f_conclusion": "**Conclusion**: {}",
            "f_interpretation": "F-statistic = {:.3f}, p-value = {:.3f}. Since p-value {}, {}",
            "f_p_less": "< 0.05",
            "f_p_more": ">= 0.05",
            "f_reject": "reject H0; conclude that independent variables significantly explain the variation in the dependent variable.",
            "f_not_reject": "fail to reject H0; the model is not statistically significant.",
            "autocorr_section": "### Autocorrelation Test (Durbin-Watson)\n",
            "autocorr_rule": "Durbin-Watson test rule of thumb:\n- If 1 < DW < 3: no autocorrelation\n- If 0 < DW < 1: positive autocorrelation\n- If 3 < DW < 4: negative autocorrelation\n",
            "dw_interpretation": "Durbin-Watson statistic = {:.3f}. Conclusion: {}.",
            "dw_no_autocorr": "no first-order autocorrelation",
            "dw_pos_autocorr": "positive autocorrelation",
            "dw_neg_autocorr": "negative autocorrelation",
            "normality_section": "### Normality Test of Residuals\n",
            "normality_interpretation": "Shapiro-Wilk test for normality of residuals: p-value = {:.3f}. {}.\n",
            "normality_not_normal": "Residuals do not follow normal distribution (p < 0.05)",
            "normality_normal": "Residuals follow normal distribution (p ≥ 0.05)",
            "qq_plot": "Q-Q plot: `{}`\n",
            "residual_hist": "Residual histogram: `{}`\n\n",
            "hetero_section": "### Heteroscedasticity Test\n",
            "hetero_interpretation": "Breusch-Pagan test for homoscedasticity: p-value = {:.3f}. {}.\n",
            "hetero_met": "Homoscedasticity assumption met (p ≥ 0.05)",
            "hetero_detected": "Heteroscedasticity detected (p < 0.05)",
            "residual_plot": "Residual scatter plot: `{}`\n\n",
            "multicol_section": "### Multicollinearity\n",
            "multicol_interpretation": "Variance Inflation Factor (VIF) of independent variables: {}. VIF {}, {}\n- R² = {:.3f} {}. - F-statistic = {:.3f} {}. - t-statistics: {} (t ≥ 2). {}",
            "vif_less": "< 10",
            "vif_more": ">= 10",
            "no_multicol": "no multicollinearity detected.",
            "multicol_detected": "multicollinearity detected.",
            "r2_not_large": "is not large",
            "r2_large": "is large",
            "f_small": "is small",
            "f_moderate": "is moderately large",
            "f_large": "is large",
            "t_large": "relatively large",
            "t_not_large": "not all large",
            "no_signs_multicol": "No signs of multicollinearity.",
            "possible_multicol": "Possible signs of multicollinearity.",
            "actual_vs_pred": "Actual vs Predicted values plot: `{}`\n\n",
            "action_non_sig_factor_issue": "Sig. = {} >= 0.05",
            "action_non_sig_factor_comment": "Remove factor `{}` due to non-significance",
            "action_non_sig_var_issue": "Sig. = {} >= 0.05",
            "action_non_sig_var_comment": "Remove variable `{}` due to non-significance",
            "action_no_sig_vars_issue": "No independent variables show statistical significance",
            "action_no_sig_vars_comment": "Review data or model specification",
            "action_reanalyze_regression_issue": "Non-significant variables or factors detected",
            "action_reanalyze_regression_comment": "Re-run regression analysis after removing non-significant variables or factors"
        },
        "vi": {
            "title": "# Báo Cáo Phân Tích Hồi Quy Bội\n\n",
            "section_title": "## Phân Tích Hồi Quy Bội\n\n",
            "error_dep_var": "**LỖI**: Yêu cầu chính xác một nhóm biến phụ thuộc (tiềm ẩn hoặc quan sát đơn lẻ), tìm thấy {}.\n",
            "error_indep_var": "**LỖI**: Không tìm thấy biến độc lập hợp lệ trong dữ liệu.\n",
            "intro": "Phân tích hồi quy bội được thực hiện bằng phương pháp Ordinary Least Squares (OLS) để đánh giá tác động của các biến độc lập lên biến phụ thuộc `{}`.\n\n",
            "coeff_section": "### Hệ Số Hồi Quy\n\n",
            "coeff_table": "Bảng hệ số: `{}`\n\n",
            "interpretation": "**Diễn Giải**:\n",
            "analysis_results": "**Kết Quả Phân Tích**:\n",
            "no_significance": "**Kết Quả Phân Tích**: Không có biến độc lập nào có ý nghĩa thống kê.",
            "sig_effect": "- Biến `{}` ({}) có tác động thống kê có ý nghĩa lên `{}` (p = {:.3f}).",
            "no_sig_effect": "- Biến `{}` ({}) không có tác động thống kê có ý nghĩa lên `{}` (p = {:.3f}).",
            "unstd_equation": "\n**Phương Trình Hồi Quy Chưa Chuẩn Hóa**:\n{}\n\n",
            "std_equation": "**Phương Trình Hồi Quy Chuẩn Hóa**:\n{}",
            "model_eval_section": "### Đánh Giá Mô Hình\n\n",
            "model_eval_desc": "Phần này đánh giá độ phù hợp của mô hình hồi quy sử dụng R² điều chỉnh và các chỉ số liên quan.\n\n",
            "model_fit_table_section": "#### Bảng Tóm Tắt Độ Phù Hợp Mô Hình\n\n",
            "model_summary_file": "Bảng tóm tắt mô hình: `{}`\n\n",
            "assessment": "**Đánh Giá**:\n",
            "model_fit_msg": "Hệ số R² điều chỉnh là {:.3f}. Các biến độc lập giải thích {:.1f}% sự biến thiên trong `{}`. {}\nHệ số Durbin-Watson: {:.3f} (khoảng lý tưởng ~1–3, tối ưu ~2 cho thấy không có tự tương quan).",
            "model_suitable": "Mô hình phù hợp cho nghiên cứu vì R² điều chỉnh ≥ 0.50.",
            "model_not_suitable": "Mô hình có thể không phù hợp vì R² điều chỉnh < 0.50.",
            "model_testing_section": "## Kiểm Định Mô Hình\n\n",
            "t_test_section": "### Kiểm Định Các Biến Độc Lập Xi (Student's t-test)\n",
            "t_test_desc": "Dựa trên kết quả phân tích hồi quy để kiểm định các biến thành phần:\n",
            "t_test_intercept": "Ý nghĩa hệ số chặn (p-value) là {:.3f} {}, {}",
            "t_test_intercept_sig": "< 0.05",
            "t_test_intercept_not_sig": ">= 0.05",
            "t_test_intercept_conclusion_sig": "nên hệ số chặn có ý nghĩa thống kê ở mức 5%.",
            "t_test_intercept_conclusion_not_sig": "nên hệ số chặn không có ý nghĩa thống kê.",
            "t_test_var": "- Biến `{}` ({}): p-value = {:.3f} {}, {} `{}` với hệ số β = {:.3f}.",
            "reject_h0": "< 0.05",
            "not_reject_h0": ">= 0.05",
            "affects": "bác bỏ H0, có tác động lên",
            "no_affect": "không bác bỏ H0, không tác động lên",
            "f_test_section": "### Kiểm Định Tổng Thể Mô Hình (Fisher's F-test)\n",
            "f_formula": "F-statistic được tính theo công thức: F = (R²(n-k-1))/(1-R²)k = ({:.3f} x ({}-{}-1))/((1-{:.3f}) x {}) = {:.3f}\n\n",
            "f_table_title": "**Bảng Fisher's F-test**:\n",
            "f_table_file": "Bảng F-test: `{}`\n\n",
            "f_conclusion": "**Kết Luận**: {}",
            "f_interpretation": "F-statistic = {:.3f}, p-value = {:.3f}. Vì p-value {}, {}",
            "f_p_less": "< 0.05",
            "f_p_more": ">= 0.05",
            "f_reject": "bác bỏ H0; kết luận rằng các biến độc lập giải thích đáng kể sự biến thiên trong biến phụ thuộc.",
            "f_not_reject": "không bác bỏ H0; mô hình không có ý nghĩa thống kê.",
            "autocorr_section": "### Kiểm Định Tự Tương Quan (Durbin-Watson)\n",
            "autocorr_rule": "Quy tắc kiểm định Durbin-Watson:\n- Nếu 1 < DW < 3: không có tự tương quan\n- Nếu 0 < DW < 1: tự tương quan dương\n- Nếu 3 < DW < 4: tự tương quan âm\n",
            "dw_interpretation": "Durbin-Watson statistic = {:.3f}. Kết luận: {}.",
            "dw_no_autocorr": "không có tự tương quan bậc nhất",
            "dw_pos_autocorr": "tự tương quan dương",
            "dw_neg_autocorr": "tự tương quan âm",
            "normality_section": "### Kiểm Định Phân Phối Chuẩn Của Phần Dư\n",
            "normality_interpretation": "Kiểm định Shapiro-Wilk cho phân phối chuẩn của phần dư: p-value = {:.3f}. {}.\n",
            "normality_not_normal": "Phần dư không tuân theo phân phối chuẩn (p < 0.05)",
            "normality_normal": "Phần dư tuân theo phân phối chuẩn (p ≥ 0.05)",
            "qq_plot": "Biểu đồ Q-Q: `{}`\n",
            "residual_hist": "Biểu đồ phân phối phần dư: `{}`\n\n",
            "hetero_section": "### Kiểm Định Phương Sai Thay Đổi\n",
            "hetero_interpretation": "Kiểm định Breusch-Pagan cho phương sai đồng nhất: p-value = {:.3f}. {}.\n",
            "hetero_met": "Giả định phương sai đồng nhất được thỏa mãn (p ≥ 0.05)",
            "hetero_detected": "Phát hiện phương sai thay đổi (p < 0.05)",
            "residual_plot": "Biểu đồ phân tán phần dư: `{}`\n\n",
            "multicol_section": "### Đa Cộng Tuyến\n",
            "multicol_interpretation": "Variance Inflation Factor (VIF) của các biến độc lập: {}. VIF {}, {}\n- R² = {:.3f} {}. - F-statistic = {:.3f} {}. - t-statistics: {} (t ≥ 2). {}",
            "vif_less": "< 10",
            "vif_more": ">= 10",
            "no_multicol": "không phát hiện đa cộng tuyến.",
            "multicol_detected": "phát hiện đa cộng tuyến.",
            "r2_not_large": "không lớn",
            "r2_large": "lớn",
            "f_small": "nhỏ",
            "f_moderate": "tương đối lớn",
            "f_large": "lớn",
            "t_large": "tương đối lớn",
            "t_not_large": "không phải tất cả đều lớn",
            "no_signs_multicol": "Không có dấu hiệu đa cộng tuyến.",
            "possible_multicol": "Có thể có dấu hiệu đa cộng tuyến.",
            "actual_vs_pred": "Biểu đồ giá trị thực tế so với dự đoán: `{}`\n\n",
            "action_non_sig_factor_issue": "Sig. = {} >= 0.05",
            "action_non_sig_factor_comment": "Loại bỏ nhân tố `{}` do không có ý nghĩa",
            "action_non_sig_var_issue": "Sig. = {} >= 0.05",
            "action_non_sig_var_comment": "Loại bỏ biến `{}` do không có ý nghĩa",
            "action_no_sig_vars_issue": "Không có biến độc lập nào có ý nghĩa thống kê",
            "action_no_sig_vars_comment": "Kiểm tra lại dữ liệu hoặc đặc tả mô hình",
            "action_reanalyze_regression_issue": "Phát hiện biến hoặc nhân tố không có ý nghĩa",
            "action_reanalyze_regression_comment": "Chạy lại phân tích hồi quy sau khi loại bỏ biến/nhân tố không ý nghĩa"
        }
    }

    # Get translations for selected language
    t = get_t_dict(translations.get(language, translations["en"]), language=language)

    # Format title with iteration count if count > 1
    t["title"] = format_title_with_count(t["title"], count, language)

    # Generate timestamped output directory
    now = datetime.now()
    timestamp = f"{now.microsecond // 10000:02d}"
    output_dir = os.path.join(os.path.dirname(base_output_dir) or ".", f"{timestamp}_{os.path.basename(base_output_dir)}")

    # Initialize outputs
    rel_output_dir = os.path.relpath(output_dir, start=os.path.dirname(base_output_dir) or ".")
    file_contents = {}
    logs = []

    # MODIFIED: Validate and process dependent variable (handle latent via mean of indicators)
    dependent_groups = {}
    dependent_observed_vars = [
        var for var in variables 
        if var.role == "dependent" and var.variable_type == "observed" and var.code in data.columns
    ]
    
    for var in dependent_observed_vars:
        parent_code = var.parent_code if var.parent_code else var.code
        if parent_code not in dependent_groups:
            dependent_groups[parent_code] = []
        dependent_groups[parent_code].append(var.code)
    
    if len(dependent_groups) != 1:
        report = f"""{t["title"]}{t["section_title"]}{t["error_dep_var"].format(len(dependent_groups))}"""

        return ToolOutput(
            results={},
            logs=[report],
            file_contents=file_contents,
            action=None
        )
    
    dependent_key = list(dependent_groups.keys())[0]
    dep_var_codes = dependent_groups[dependent_key]
    if len(dep_var_codes) > 1:  # Latent dependent: compute mean of indicators
        group_mean = data[dep_var_codes].mean(axis=1)
        data[dependent_key] = group_mean
        dependent_var = dependent_key
    else:  # Single observed dependent
        dependent_var = dep_var_codes[0]

    dependent_name = variable_names.get(dependent_var, dependent_var)
    
    # Group independent variables by parent code for latent variables
    latent_groups = {}
    independent_observed_vars = [
        var for var in variables 
        if var.role == "independent" and var.variable_type == "observed" and var.code in data.columns
    ]
    
    for var in independent_observed_vars:
        parent_code = var.parent_code
        if parent_code:
            if parent_code not in latent_groups:
                latent_groups[parent_code] = []
            latent_groups[parent_code].append(var.code)
        else:
            latent_groups[var.code] = [var.code]
    
    # Compute means for latent variables
    regression_vars = {}
    for group_key, var_codes in latent_groups.items():
        if len(var_codes) > 1:  # Latent variable (multiple observed variables)
            group_mean = data[var_codes].mean(axis=1)
            data[group_key] = group_mean
            regression_vars[group_key] = variable_names.get(group_key, group_key)
        else:  # Single observed variable
            regression_vars[var_codes[0]] = variable_names.get(var_codes[0], var_codes[0])
    
    independent_vars = list(regression_vars.keys())
    if not independent_vars:
        report = f"""{t["title"]}{t["section_title"]}{t["error_indep_var"]}"""
        return ToolOutput(
            results={},
            logs=[report],
            file_contents=file_contents,
            action=None
        )
    
    # Perform regression analysis
    coeff_table = compute_coefficients_table(
        data=data,
        dependent_var=dependent_var,
        independent_vars=independent_vars,
        save_results=False,
        t=t
    )
    
    # Fit the model for diagnostics
    X_sm = sm.add_constant(data[independent_vars])
    model = sm.OLS(data[dependent_var], X_sm).fit()
    predicted_values = model.fittedvalues
    residuals = model.resid
    
    # Generate coefficient interpretations and actions
    actions = []
    significant_vars = []
    coefficients_interpretation = []
    
    for _, row in coeff_table.iterrows():
        var = row[t["independent_variable"]]
        if var == t["constant"]:
            continue
        p_value = float(row[t["sig"]])
        var_name = regression_vars.get(var, var)
        
        if p_value < 0.05:
            significant_vars.append(var)
            coefficients_interpretation.append(
                t["sig_effect"].format(var, var_name, dependent_var, p_value)
            )
        else:
            coefficients_interpretation.append(
                t["no_sig_effect"].format(var, var_name, dependent_var, p_value)
            )
            if var in latent_groups and len(latent_groups[var]) > 1:
                actions.append(
                    Action(
                        action_type=ActionType.DISCARD_FACTOR,
                        method="run_regression_analysis",
                        issue=t["action_non_sig_factor_issue"].format(f"{p_value:.3f}"),
                        comment=t["action_non_sig_factor_comment"].format(var),
                        status="pending",
                        action_params={"factor": var}
                    )
                )
            else:
                actions.append(
                    Action(
                        action_type=ActionType.REMOVE_VARIABLE,
                        method="run_regression_analysis",
                        issue=t["action_non_sig_var_issue"].format(f"{p_value:.3f}"),
                        comment=t["action_non_sig_var_comment"].format(var),
                        status="pending",
                        action_params={"variable": var}
                    )
                )
    
    if significant_vars:
        coefficients_interpretation.insert(0, t["analysis_results"] + "\n")
    else:
        coefficients_interpretation.insert(0, t["no_significance"])
        actions.append(
            Action(
                action_type=ActionType.RECHECK_DATA,
                method="run_regression_analysis",
                issue=t["action_no_sig_vars_issue"],
                comment=t["action_no_sig_vars_comment"],
                status="pending",
                action_params=None
            )
        )
    
    # Add REANALYZE action if needed
    if any(action.action_type in [ActionType.DISCARD_FACTOR, ActionType.REMOVE_VARIABLE] for action in actions):
        actions.append(
            Action(
                action_type=ActionType.REANALYZE,
                method="run_regression_analysis",
                issue=t["action_reanalyze_regression_issue"],
                comment=t["action_reanalyze_regression_comment"],
                status="pending",
                action_params=None,
                reflection_params={
                    "tool": "run_regression_analysis",
                    "parameters": {
                        "factor_key": dependent_var,
                        "independent_vars": significant_vars,
                        "save_files": save_files,
                        "output_dir": base_output_dir,
                        "language": language,
                        "count": count + 1
                    },
                    "comment": "Re-run regression analysis with significant variables"
                },
                reset_actions=True
            )
        )

    # Compute model diagnostics
    model_summary = evaluate_model_fit(
        data=data,
        dependent_var=dependent_var,
        independent_vars=independent_vars,
        save_results=False,
        t=t
    )
    
    error_metrics = compute_rmse_mae(data, dependent_var, independent_vars)
    model_summary.update(error_metrics)
    
    dw_results = durbin_watson_test(
        data=data,
        dependent_var=dependent_var,
        independent_vars=independent_vars
    )
    dw_statistic = dw_results["DW_statistic"]
    
    f_test_results = fisher_f_test(
        data=data,
        dependent_var=dependent_var,
        independent_vars=independent_vars
    )
    f_statistic = f_test_results["F_statistic"]
    f_pvalue = f_test_results["p_value"]
    f_diagnostics = f_test_results["diagnostics"]
    
    # Additional diagnostic tests
    bp_results = breusch_pagan_test(data, dependent_var, independent_vars)
    bp_p_value = bp_results["f_p_value"]
    
    sw_results = shapiro_wilk_test(residuals)
    sw_p_value = sw_results["p_value"]
    
    # Create visualizations
    residual_plot_filename = os.path.join(rel_output_dir, "residual_plot.png")
    file_contents[residual_plot_filename] = create_residual_plot(residuals, predicted_values, t=t)
    
    qq_plot_filename = os.path.join(rel_output_dir, "qq_plot.png")
    file_contents[qq_plot_filename] = create_qq_plot(residuals, t=t)
    
    histogram_filename = os.path.join(rel_output_dir, "residual_histogram.png")
    file_contents[histogram_filename] = create_histogram(residuals, t=t)
    
    actual_pred_filename = os.path.join(rel_output_dir, "actual_vs_predicted.png")
    file_contents[actual_pred_filename] = create_actual_vs_predicted_plot(
        data[dependent_var], predicted_values, dependent_name, t=t
    )
    
    # Create data tables
    coeff_table_filename = os.path.join(rel_output_dir, "coefficients_table.csv")
    file_contents[coeff_table_filename] = coeff_table.to_csv(index=False)
    
    model_fit_df = pd.DataFrame([{
        "R": model_summary["R"],
        "R²": model_summary["R Square"],
        "Adjusted R²": model_summary["Adjusted R Square"],
        "Std. Error of Estimate": model_summary["Std. Error of the Estimate"],
        "RMSE": model_summary["RMSE"],
        "MAE": model_summary["MAE"],
        "Durbin-Watson": round(float(dw_statistic), 3)
    }])
    model_fit_filename = os.path.join(rel_output_dir, "model_summary.csv")
    file_contents[model_fit_filename] = model_fit_df.to_csv(index=False)
    
    # Model fit interpretation
    adjusted_r2 = float(model_summary["Adjusted R Square"])
    model_suitability = t["model_suitable"] if adjusted_r2 >= 0.50 else t["model_not_suitable"]
    model_fit_interpretation = t["model_fit_msg"].format(
        adjusted_r2,
        adjusted_r2*100,
        dependent_var,
        model_suitability,
        dw_statistic
    )
    
    # Generate regression equations
    equations_text = ""
    if not any(action.action_type in [ActionType.DISCARD_FACTOR, ActionType.REMOVE_VARIABLE, ActionType.RECHECK_DATA] for action in actions):
        unstd_terms = []
        intercept_mask = coeff_table[t["independent_variable"]] == t["constant"]
        intercept = float(coeff_table[intercept_mask][t["unstandardized_b"]].iloc[0])
        unstd_terms.append(f"{intercept:.3f}")
        
        for var in independent_vars:
            var_mask = coeff_table[t["independent_variable"]] == var
            b = float(coeff_table[var_mask][t["unstandardized_b"]].iloc[0])
            unstd_terms.append(f"{b:+.3f} x {var}")
        unstd_equation = f"{dependent_var} = {' '.join(unstd_terms)}"
        
        std_terms = []
        for var in significant_vars:
            var_mask = coeff_table[t["independent_variable"]] == var
            beta = float(coeff_table[var_mask][t["standardized_beta"]].iloc[0])
            std_terms.append(f"{beta:+.3f} x {var}")
        std_equation = f"{dependent_var} = {' '.join(std_terms)}" if std_terms else f"{dependent_var} = 0"

        equations_text = t["unstd_equation"].format(unstd_equation) + t["std_equation"].format(std_equation)
    
    # Generate detailed analysis if model is acceptable
    additional_report = ""
    if not any(action.action_type in [ActionType.DISCARD_FACTOR, ActionType.REMOVE_VARIABLE, ActionType.RECHECK_DATA] for action in actions):
        # Student's t-test interpretation
        t_test_interpretation = []
        intercept_row = coeff_table[coeff_table[t["independent_variable"]] == t["constant"]]
        intercept_pvalue = float(intercept_row[t["sig"]].iloc[0]) if not intercept_row.empty else 1.0
        
        p_comparison = t["t_test_intercept_sig"] if intercept_pvalue < 0.05 else t["t_test_intercept_not_sig"]
        conclusion = t["t_test_intercept_conclusion_sig"] if intercept_pvalue < 0.05 else t["t_test_intercept_conclusion_not_sig"]
        t_test_interpretation.append(
            t["t_test_intercept"].format(intercept_pvalue, p_comparison, conclusion)
        )
        
        for _, row in coeff_table.iterrows():
            var = row[t["independent_variable"]]
            if var == t["constant"]:
                continue
            p_value = float(row[t["sig"]])
            beta = float(row[t["unstandardized_b"]])
            var_name = regression_vars.get(var, var)
            
            p_comp = t["reject_h0"] if p_value < 0.05 else t["not_reject_h0"]
            effect = t["affects"] if p_value < 0.05 else t["no_affect"]
            t_test_interpretation.append(
                t["t_test_var"].format(var, var_name, p_value, p_comp, effect, dependent_var, beta)
            )
        
        # Fisher's F-test table
        n = f_diagnostics["sample_size"]
        k = f_diagnostics["num_predictors"]
        ssr = model_summary.get("SSR", 0)
        sse = model_summary.get("SSE", 0)
        df_regression = k
        df_residual = n - k - 1
        msr = ssr / df_regression if df_regression > 0 else 0
        mse = sse / df_residual if df_residual > 0 else 0
        
        f_table = pd.DataFrame([
            {"": "Regression", "Sum of Squares": ssr, "df": df_regression, "Mean Square": msr, "F": f_statistic, "Sig.": f_pvalue},
            {"": "Residual", "Sum of Squares": sse, "df": df_residual, "Mean Square": mse, "F": "", "Sig.": ""},
            {"": "Total", "Sum of Squares": ssr + sse, "df": n - 1, "Mean Square": "", "F": "", "Sig.": ""}
        ])
        f_table_filename = os.path.join(rel_output_dir, "f_test_table.csv")
        file_contents[f_table_filename] = f_table.to_csv(index=False)
        
        f_p_comp = t["f_p_less"] if f_pvalue < 0.05 else t["f_p_more"]
        f_concl = t["f_reject"] if f_pvalue < 0.05 else t["f_not_reject"]
        f_test_interpretation = t["f_interpretation"].format(f_statistic, f_pvalue, f_p_comp, f_concl)
        
        if 1 < dw_statistic < 3:
            dw_concl = t["dw_no_autocorr"]
        elif 0 < dw_statistic < 1:
            dw_concl = t["dw_pos_autocorr"]
        else:
            dw_concl = t["dw_neg_autocorr"]
        dw_interpretation = t["dw_interpretation"].format(dw_statistic, dw_concl)
        
        norm_concl = t["normality_not_normal"] if sw_p_value < 0.05 else t["normality_normal"]
        normality_interpretation = t["normality_interpretation"].format(sw_p_value, norm_concl)

        hetero_concl = t["hetero_met"] if bp_p_value >= 0.05 else t["hetero_detected"]
        heteroscedasticity_interpretation = t["hetero_interpretation"].format(bp_p_value, hetero_concl)
        
        # Multicollinearity check
        vif_values = [float(row.get(t["vif"], 1)) for _, row in coeff_table.iterrows() if row[t["independent_variable"]] != t["constant"]]
        max_vif = max(vif_values) if vif_values else 1
        t_stats = [float(row.get(t["t_stat"], 0)) for _, row in coeff_table.iterrows() if row[t["independent_variable"]] != t["constant"]]
        
        vif_str = ' ≈ '.join([f'{vif:.1f}' for vif in vif_values])
        vif_comp = t["vif_less"] if max_vif < 10 else t["vif_more"]
        vif_concl = t["no_multicol"] if max_vif < 10 else t["multicol_detected"]
        r2_size = t["r2_not_large"] if adjusted_r2 < 0.7 else t["r2_large"]
        if f_statistic < 10:
            f_size = t["f_small"]
        elif 10 <= f_statistic < 100:
            f_size = t["f_moderate"]
        else:
            f_size = t["f_large"]
        t_size = t["t_large"] if all(abs(t) >= 2 for t in t_stats) else t["t_not_large"]
        overall_concl = t["no_signs_multicol"] if (max_vif < 10 and adjusted_r2 < 0.7 and all(abs(t) >= 2 for t in t_stats)) else t["possible_multicol"]
        multicollinearity_interpretation = t["multicol_interpretation"].format(
            vif_str, vif_comp, vif_concl, adjusted_r2, r2_size, f_statistic, f_size, t_size, overall_concl
        )
        
        t_test_text = '\n'.join(t_test_interpretation)
        
        additional_report = f"""
{t["model_eval_section"]}{t["model_eval_desc"]}{t["model_fit_table_section"]}{t["model_summary_file"].format(model_fit_filename)}{t["assessment"]}{model_fit_interpretation}

{t["model_testing_section"]}{t["t_test_section"]}{t["t_test_desc"]}{t_test_text}

{t["f_test_section"]}{t["f_formula"].format(adjusted_r2, n, k, adjusted_r2, k, f_statistic)}{t["f_table_title"]}{t["f_table_file"].format(f_table_filename)}{t["f_conclusion"].format(f_test_interpretation)}

{t["autocorr_section"]}{t["autocorr_rule"]}{dw_interpretation}

{t["normality_section"]}{normality_interpretation}{t["qq_plot"].format(qq_plot_filename)}{t["residual_hist"].format(histogram_filename)}
{t["hetero_section"]}{heteroscedasticity_interpretation}{t["residual_plot"].format(residual_plot_filename)}
{t["multicol_section"]}{multicollinearity_interpretation}

{t["actual_vs_pred"].format(actual_pred_filename)}
"""
    
    # Create main report
    coeff_text = '\n'.join(coefficients_interpretation)
    report = f"""{t["title"]}{t["section_title"]}{t["intro"].format(dependent_name)}{t["coeff_section"]}{t["coeff_table"].format(coeff_table_filename)}{t["interpretation"]}{coeff_text}
{equations_text}

{additional_report}
"""
    
    logs.append(report)
    
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
                    logger.error(f"Error decoding or saving image {filename}: {e}")
            elif filename.endswith((".csv", ".txt", ".md")):
                with open(save_path, "w", encoding="utf-8") as f:
                    f.write(str(content))
            else:
                logger.warning(f"Unknown file type for '{filename}'. Saving as text.")
                try:
                    with open(save_path, "w", encoding="utf-8") as f:
                        f.write(str(content))
                except Exception as e:
                    logger.error(f"Could not save file {filename}: {e}")
    
    # Prepare results
    results = {
        "dependent_variable": dependent_var,
        "independent_variables": list(regression_vars.keys()),
        "significant_variables": significant_vars,
        "coefficients_table": coeff_table.to_dict(),
        "model_summary": model_summary,
        "durbin_watson": float(dw_statistic),
        "f_statistic": float(f_statistic),
        "f_pvalue": float(f_pvalue),
        "breusch_pagan_pvalue": float(bp_p_value),
        "shapiro_wilk_pvalue": float(sw_p_value),
        "adjusted_r2": float(adjusted_r2)
    }

    return ToolOutput(
        results=serialize_dict(results),
        logs=logs,
        file_contents=file_contents,
        action=actions if actions else None
    )
    

######################################################
################ LOGISTIC REGRESSION #################
######################################################

def hosmer_lemeshow_test(y_true: np.ndarray, y_pred_probs: np.ndarray, n_groups: int = 10) -> dict:
    """
    Performs the Hosmer-Lemeshow goodness of fit test for a binary classifier.

    A non-significant p-value (e.g., > 0.05) is desired, as it suggests that the model's
    predicted probabilities are well-calibrated (i.e., there is no significant difference
    between observed and expected frequencies).

    Args:
        y_true: True binary labels (0 or 1).
        y_pred_probs: Predicted probabilities for the positive class (class 1).
        n_groups: Number of groups to bin the data into (typically 10).

    Returns:
        A dictionary containing the chi-squared statistic and the p-value.
    """
    y_true = np.asarray(y_true)
    y_pred_probs = np.asarray(y_pred_probs)

    # Create a DataFrame for easier manipulation
    data = pd.DataFrame({'y_true': y_true, 'y_pred_probs': y_pred_probs})
    data = data.sort_values('y_pred_probs')
    
    # Create bins of approximately equal size based on predicted probabilities
    try:
        # Use qcut to create deciles (or other quantiles)
        data['group'] = pd.qcut(data['y_pred_probs'], q=n_groups, duplicates='raise')
    except ValueError:
        # If qcut fails due to non-unique bin edges (common with poorly discriminating models),
        # use rank-based grouping as a fallback to ensure n_groups are created.
        data['group'] = pd.qcut(data['y_pred_probs'].rank(method='first'), q=n_groups, labels=False)

    # Calculate observed and expected frequencies for each group
    summary = data.groupby('group', observed=False).agg(
        total_count=('y_true', 'count'),
        observed_1=('y_true', 'sum'),
        expected_1=('y_pred_probs', 'sum')
    )

    summary['observed_0'] = summary['total_count'] - summary['observed_1']
    summary['expected_0'] = summary['total_count'] - summary['expected_1']

    # The test is valid only if all expected counts are > 5. We'll check but proceed anyway,
    # as this is for reporting purposes. A warning could be logged if needed.
    
    # Calculate the Hosmer-Lemeshow chi-squared statistic
    h_stat = (
        ((summary['observed_0'] - summary['expected_0'])**2 / summary['expected_0']) +
        ((summary['observed_1'] - summary['expected_1'])**2 / summary['expected_1'])
    ).sum()

    # Degrees of freedom is n_groups - 2
    df = n_groups - 2
    p_value = 1 - stats.chi2.cdf(h_stat, df)

    return {"statistic": h_stat, "p_value": p_value}

def compute_pseudo_r2(model, data, dependent_var):
    """Compute McFadden Pseudo R² for logistic regression."""
    llf = model.llf  # Log-likelihood of fitted model
    ll_null = sm.Logit(data[dependent_var], np.ones(len(data))).fit(disp=0).llf  # Log-likelihood of null model
    pseudo_r2 = 1 - (llf / ll_null)
    return pseudo_r2

def compute_roc_auc(data, dependent_var, predicted_probs):
    """Compute ROC curve and AUC."""
    fpr, tpr, _ = roc_curve(data[dependent_var], predicted_probs)
    roc_auc = auc(fpr, tpr)
    return fpr, tpr, roc_auc

def compute_confusion_matrix(data, dependent_var, predicted_probs, threshold=0.5):
    """Compute confusion matrix metrics."""
    predicted_labels = (predicted_probs >= threshold).astype(int)
    cm = confusion_matrix(data[dependent_var], predicted_labels)
    tn, fp, fn, tp = cm.ravel()
    sensitivity = tp / (tp + fn) if (tp + fn) > 0 else 0
    specificity = tn / (tn + fp) if (tn + fp) > 0 else 0
    accuracy = (tp + tn) / (tp + tn + fp + fn)
    return cm, sensitivity, specificity, accuracy

def check_log_odds_linearity(data, dependent_var, independent_vars):
    """Check linearity of log-odds using Box-Tidwell approach (simplified)."""
    # Simplified check: Add interaction terms (X * log(X)) and test significance
    results = []
    for var in independent_vars:
        if data[var].min() <= 0:  # Avoid log(0) or negative
            continue
        data[f"{var}_log"] = data[var] * np.log(data[var] + 1e-10)
        X = sm.add_constant(data[[var, f"{var}_log"]])
        try:
            model = sm.Logit(data[dependent_var], X).fit(disp=0)
            p_value = model.pvalues[f"{var}_log"]
            results.append({"variable": var, "p_value": p_value})
        except:
            results.append({"variable": var, "p_value": None})
        data = data.drop(columns=[f"{var}_log"])
    return results

def run_logistic_regression_analysis(
    data: pd.DataFrame,
    variables: list[Variable],
    params: dict
) -> ToolOutput:
    """
    Perform logistic regression analysis and model evaluation, generating a comprehensive report
    with coefficients, odds ratios, fit metrics, and diagnostics.

    Parameters:
        data: Input DataFrame containing the data
        variables: list of Variable objects (dependent and independent, including latent and observed)
        params: dictionary containing analysis parameters
            - output_dir (str): base output directory name (default: 'logistic_regression_analysis')
            - save_files (bool): whether to save generated files to disk (default: False)
            - variable_names (dict): mapping of variable codes to display names (optional)
            - language (str): language for output messages - "en" or "vi" (default: "en")

    Returns:
        ToolOutput: Contains results, logs, file contents, and suggested actions
    """
    # Extract parameters at the start
    base_output_dir = params.get("output_dir", "logit_regress")
    save_files = params.get("save_files", False)
    variable_names = params.get("variable_names", {v.code: v.name for v in variables})
    language = params.get("language", "en")
    count = params.get("count", 1)

    # Define translations dictionary
    translations = {
        "en": {
            "title": "# Logistic Regression Analysis Report\n\n",
            "section_title": "## Logistic Regression Analysis\n\n",
            "analysis_of": "## Analysis of: `{}`\n\n",
            "error_dep_count": "**Error**: Exactly one dependent variable is required, found {}.\n",
            "error_binary": "**Error**: Dependent variable `{}` must be binary (0/1), found values: {}.\n",
            "error_no_indep": "**Error**: No valid independent variables found in the data.\n",
            "error_fit": "**Error**: Failed to fit logistic regression model: {}.\n",
            "intro": "Logistic regression analysis was performed to evaluate the relationship between independent variables and the binary outcome `{}`.\n\n",
            "coeff_section": "### Coefficients and Odds Ratios\n",
            "coeff_table": "**Coefficients Table**: `{}`\n\n",
            "interpretation": "**Interpretation**:\n",
            "sig_effect": "- **`{}` ({})**: Statistically significant effect (p={:.3f}). For each one-unit increase in `{}`, the odds of `{}` being 1 {} by {:.1f}% (Odds Ratio = {:.3f}).",
            "no_sig_effect": "- **`{}` ({})**: No statistically significant effect (p={:.3f}).",
            "increase": "increase",
            "decrease": "decrease",
            "equation_title": "**Logistic Regression Equation**:\n",
            "model_fit_section": "### Model Fit and Performance\n\n",
            "overall_fit_section": "#### Overall Model Fit\n",
            "model_summary": "**Model Summary**: `{}`\n\n",
            "model_fit_interp": "The model's overall significance is evaluated using the Likelihood Ratio (LLR) test. With a p-value of {:.3f}, the model is {} as a whole. McFadden's Pseudo R² is {:.3f}, indicating the model explains {:.1f}% of the variance, which suggests a {} model fit.",
            "stat_sig": "statistically significant",
            "not_stat_sig": "not statistically significant",
            "fit_good": "good",
            "fit_moderate": "moderate",
            "fit_poor": "poor",
            "goodness_fit_section": "#### Goodness-of-Fit Test\n",
            "hl_test_title": "**Hosmer-Lemeshow Test Results**:\n",
            "hl_interp": "The Hosmer-Lemeshow test yields a p-value of {:.3f}. {}",
            "hl_good": "Since p > 0.05, the null hypothesis is not rejected, indicating good model calibration.",
            "hl_poor": "Since p < 0.05, the null hypothesis is rejected, suggesting poor model calibration.",
            "class_perf_section": "#### Classification Performance\n",
            "class_report_title": "**Detailed Classification Report**: `{}`\n\n",
            "class_interp": "The model's discriminative ability is assessed through classification metrics. The Area Under the ROC Curve (AUC) is {:.3f}, indicating {} discrimination ability. The overall classification accuracy is {:.2%}.",
            "disc_excellent": "excellent",
            "disc_good": "good",
            "disc_fair": "fair",
            "disc_poor": "poor",
            "confusion_matrix": "**Confusion Matrix**: `{}`\n",
            "roc_curve": "**ROC Curve**: `{}`\n\n",
            "diagnostics_section": "### Model Diagnostics\n\n",
            "multicol_section": "#### Multicollinearity Assessment\n",
            "vif_table": "**Variance Inflation Factors**: `{}`\n\n",
            "multicol_interp": "The maximum Variance Inflation Factor (VIF) is {:.2f}. {}",
            "vif_ok": "All VIF values are below 10, indicating no multicollinearity concerns.",
            "vif_issue": "VIF values above 10 suggest potential multicollinearity issues requiring further investigation.",
            "calibration_section": "#### Model Calibration\n",
            "calibration_plot": "**Calibration Plot**: `{}`\n\n",
            "calibration_desc": "The calibration plot assesses whether predicted probabilities align with observed outcomes. A well-calibrated model shows points close to the diagonal reference line.\n",
            "reanalyze_issue": "Non-significant variables or factors detected",
            "reanalyze_comment": "Re-run logistic regression analysis after removing non-significant variables",
            "reanalyze_reflection_comment": "Re-run logistic regression with significant variables only",
            "sig_check_issue": "p-value = {:.3f} >= 0.05",
            "remove_factor_comment": "Remove factor `{}` due to lack of statistical significance",
            "remove_variable_comment": "Remove variable `{}` due to lack of statistical significance"
        },
        "vi": {
            "title": "# Báo Cáo Phân Tích Hồi Quy Logistic\n\n",
            "section_title": "## Phân Tích Hồi Quy Logistic\n\n",
            "analysis_of": "## Phân Tích: `{}`\n\n",
            "error_dep_count": "**Lỗi**: Yêu cầu chính xác một biến phụ thuộc, tìm thấy {}.\n",
            "error_binary": "**Lỗi**: Biến phụ thuộc `{}` phải là nhị phân (0/1), tìm thấy các giá trị: {}.\n",
            "error_no_indep": "**Lỗi**: Không tìm thấy biến độc lập hợp lệ trong dữ liệu.\n",
            "error_fit": "**Lỗi**: Không thể khớp mô hình hồi quy logistic: {}.\n",
            "intro": "Phân tích hồi quy logistic được thực hiện để đánh giá mối quan hệ giữa các biến độc lập và kết quả nhị phân `{}`.\n\n",
            "coeff_section": "### Hệ Số và Tỷ Số Odds\n",
            "coeff_table": "**Bảng Hệ Số**: `{}`\n\n",
            "interpretation": "**Diễn Giải**:\n",
            "sig_effect": "- **`{}` ({})**: Có tác động thống kê có ý nghĩa (p={:.3f}). Khi tăng một đơn vị `{}`, tỷ lệ odds của `{}` bằng 1 {} {:.1f}% (Odds Ratio = {:.3f}).",
            "no_sig_effect": "- **`{}` ({})**: Không có tác động thống kê có ý nghĩa (p={:.3f}).",
            "increase": "tăng",
            "decrease": "giảm",
            "equation_title": "**Phương Trình Hồi Quy Logistic**:\n",
            "model_fit_section": "### Độ Phù Hợp và Hiệu Suất Mô Hình\n\n",
            "overall_fit_section": "#### Độ Phù Hợp Tổng Thể Của Mô Hình\n",
            "model_summary": "**Tóm Tắt Mô Hình**: `{}`\n\n",
            "model_fit_interp": "Ý nghĩa tổng thể của mô hình được đánh giá bằng kiểm định Likelihood Ratio (LLR). Với p-value = {:.3f}, mô hình {} ở mức tổng thể. Pseudo R² của McFadden là {:.3f}, cho thấy mô hình giải thích {:.1f}% phương sai, điều này cho thấy độ phù hợp mô hình {}.",
            "stat_sig": "có ý nghĩa thống kê",
            "not_stat_sig": "không có ý nghĩa thống kê",
            "fit_good": "tốt",
            "fit_moderate": "trung bình",
            "fit_poor": "kém",
            "goodness_fit_section": "#### Kiểm Định Độ Phù Hợp\n",
            "hl_test_title": "**Kết Quả Kiểm Định Hosmer-Lemeshow**:\n",
            "hl_interp": "Kiểm định Hosmer-Lemeshow cho p-value = {:.3f}. {}",
            "hl_good": "Vì p > 0.05, giả thuyết không bị bác bỏ, cho thấy mô hình hiệu chuẩn tốt.",
            "hl_poor": "Vì p < 0.05, giả thuyết bị bác bỏ, cho thấy mô hình hiệu chuẩn kém.",
            "class_perf_section": "#### Hiệu Suất Phân Loại\n",
            "class_report_title": "**Báo Cáo Phân Loại Chi Tiết**: `{}`\n\n",
            "class_interp": "Khả năng phân biệt của mô hình được đánh giá thông qua các chỉ số phân loại. Diện tích dưới đường cong ROC (AUC) là {:.3f}, cho thấy khả năng phân biệt {}. Độ chính xác phân loại tổng thể là {:.2%}.",
            "disc_excellent": "xuất sắc",
            "disc_good": "tốt",
            "disc_fair": "khá",
            "disc_poor": "kém",
            "confusion_matrix": "**Ma Trận Nhầm Lẫn**: `{}`\n",
            "roc_curve": "**Đường Cong ROC**: `{}`\n\n",
            "diagnostics_section": "### Chẩn Đoán Mô Hình\n\n",
            "multicol_section": "#### Đánh Giá Đa Cộng Tuyến\n",
            "vif_table": "**Variance Inflation Factors**: `{}`\n\n",
            "multicol_interp": "Variance Inflation Factor (VIF) tối đa là {:.2f}. {}",
            "vif_ok": "Tất cả các giá trị VIF đều dưới 10, cho thấy không có vấn đề đa cộng tuyến.",
            "vif_issue": "Giá trị VIF trên 10 cho thấy có thể có vấn đề đa cộng tuyến cần điều tra thêm.",
            "calibration_section": "#### Hiệu Chuẩn Mô Hình\n",
            "calibration_plot": "**Biểu Đồ Hiệu Chuẩn**: `{}`\n\n",
            "calibration_desc": "Biểu đồ hiệu chuẩn đánh giá xem xác suất dự đoán có phù hợp với kết quả quan sát hay không. Một mô hình được hiệu chuẩn tốt sẽ có các điểm gần đường tham chiếu đường chéo.\n",
            "reanalyze_issue": "Phát hiện các biến hoặc nhân tố không có ý nghĩa",
            "reanalyze_comment": "Chạy lại phân tích hồi quy logistic sau khi loại bỏ các biến không có ý nghĩa",
            "reanalyze_reflection_comment": "Chạy lại hồi quy logistic chỉ với các biến có ý nghĩa",
            "sig_check_issue": "p-value = {:.3f} >= 0.05",
            "remove_factor_comment": "Loại bỏ nhân tố `{}` do thiếu ý nghĩa thống kê",
            "remove_variable_comment": "Loại bỏ biến `{}` do thiếu ý nghĩa thống kê"
        }
    }

    # Get translations for selected language
    t = get_t_dict(translations.get(language, translations["en"]), language=language)

    # Format title with iteration count if count > 1
    t["title"] = format_title_with_count(t["title"], count, language)

    # Generate timestamped output directory
    now = datetime.now()
    timestamp = f"{now.microsecond // 10000:02d}"
    output_dir = os.path.join(os.path.dirname(base_output_dir) or ".", f"{timestamp}_{os.path.basename(base_output_dir)}")

    # Relative path for file_contents
    rel_output_dir = os.path.relpath(output_dir, start=os.path.dirname(base_output_dir) or ".")
    file_contents = {}
    logs = []

    # Validate dependent variable (must be binary)
    dependent_vars = [var for var in variables if var.role == VariableRole.DEPENDENT and var.variable_type == VariableType.OBSERVED]
    if len(dependent_vars) != 1:
        report = f"""{t["title"]}{t["section_title"]}{t["error_dep_count"].format(len(dependent_vars))}"""
        return ToolOutput(results={}, logs=[report], file_contents=file_contents, action=None)
    
    dependent_var = dependent_vars[0].code
    dependent_name = variable_names.get(dependent_var, dependent_var)
    dependent_labels = parse_variable_values(dependent_vars[0].values)
    
    if not set(data[dependent_var].unique()).issubset({0, 1}):
        report = f"""{t["title"]}{t["section_title"]}{t["error_binary"].format(dependent_var, data[dependent_var].unique())}"""
        return ToolOutput(results={}, logs=[report], file_contents=file_contents, action=None)

    # Group independent variables by parent_code for latent variables
    latent_groups = {}
    independent_observed_vars = [
        var for var in variables 
        if var.role == VariableRole.INDEPENDENT and var.variable_type == VariableType.OBSERVED and var.code in data.columns
    ]
    
    for var in independent_observed_vars:
        parent_code = var.parent_code
        if parent_code:
            if parent_code not in latent_groups: 
                latent_groups[parent_code] = []
            latent_groups[parent_code].append(var.code)
        else:
            latent_groups[var.code] = [var.code]

    # Compute means for latent variables
    regression_vars = {}
    for group_key, var_codes in latent_groups.items():
        if len(var_codes) > 1:
            data[group_key] = data[var_codes].mean(axis=1)
            regression_vars[group_key] = variable_names.get(group_key, group_key)
        else:
            regression_vars[var_codes[0]] = variable_names.get(var_codes[0], var_codes[0])

    independent_vars = list(regression_vars.keys())
    if not independent_vars:
        report = f"""{t["title"]}{t["section_title"]}{t["error_no_indep"]}"""
        return ToolOutput(results={}, logs=[report], file_contents=file_contents, action=None)

    # Check sample size (10–20 observations per independent variable)
    n_obs = len(data)
    min_sample = 10 * len(independent_vars)
    if n_obs < min_sample:
        sample_warning = f"Sample size ({n_obs}) is below the recommended minimum of {min_sample} observations for {len(independent_vars)} independent variables."

    # Perform logistic regression
    X = sm.add_constant(data[independent_vars])
    try:
        model = sm.Logit(data[dependent_var], X).fit(disp=0)
    except Exception as e:
        report = f"""{t["title"]}{t["section_title"]}{t["error_fit"].format(str(e))}"""
        return ToolOutput(results={}, logs=[report], file_contents=file_contents, action=None)

    # --- METRICS AND DIAGNOSTICS COMPUTATION ---
    
    # Coefficients and Odds Ratios
    coeff_table = pd.DataFrame({
        "Variable": model.params.index,
        "Coefficient": model.params.values,
        "Std. Error": model.bse,
        "z": model.tvalues,
        "p-value": model.pvalues,
        "Odds Ratio": np.exp(model.params.values)
    })
    coeff_table_filename = os.path.join(rel_output_dir, "coefficients_table.csv")
    file_contents[coeff_table_filename] = coeff_table.to_csv(index=False)

    # VIF for multicollinearity
    vif_data = pd.DataFrame()
    vif_data["Variable"] = independent_vars
    vif_data["VIF"] = [variance_inflation_factor(X[independent_vars].values, i) for i in range(len(independent_vars))]
    vif_filename = os.path.join(rel_output_dir, "vif_table.csv")
    file_contents[vif_filename] = vif_data.to_csv(index=False)

    # Model fit metrics
    pseudo_r2 = compute_pseudo_r2(model, data, dependent_var)
    
    # Classification metrics
    predicted_probs = model.predict(X)
    predicted_labels = (predicted_probs >= 0.5).astype(int)
    cm, sensitivity, specificity, accuracy = compute_confusion_matrix(data, dependent_var, predicted_probs)
    fpr, tpr, roc_auc = compute_roc_auc(data, dependent_var, predicted_probs)
    
    # Hosmer-Lemeshow Test
    hl_test_results = hosmer_lemeshow_test(data[dependent_var], predicted_probs)
    
    # Detailed Classification Report as a CSV
    class_report_dict = classification_report(
        data[dependent_var],
        predicted_labels,
        target_names=[f'Class [{dependent_labels.get("0", "0")}]', f'Class [{dependent_labels.get("1", "1")}]'],
        output_dict=True
    )

    # Convert the dictionary to a DataFrame
    report_df = pd.DataFrame(class_report_dict).T

    # The 'accuracy' row is a single value, which pandas broadcasts. We need to fix it.
    if 'accuracy' in report_df.index:
        accuracy_val = report_df.loc['accuracy', 'f1-score'] # The value is in all columns
        total_support = report_df.loc['macro avg', 'support']
        # Recreate the accuracy row correctly
        report_df.loc['accuracy', ['precision', 'recall']] = np.nan # Blank out other cells
        report_df.loc['accuracy', 'f1-score'] = accuracy_val
        report_df.loc['accuracy', 'support'] = total_support

    # Ensure support column is integer
    report_df['support'] = report_df['support'].astype(int)
    
    # Set the index name for clarity in the CSV
    report_df.index.name = ' '

    # Convert to CSV string, np.nan will be converted to an empty field
    class_report_csv_content = report_df.to_csv()
    
    # Update filename and content
    class_report_filename = os.path.join(rel_output_dir, "classification_report.csv")
    file_contents[class_report_filename] = class_report_csv_content
    
    # --- VISUALIZATIONS ---

    # ROC Curve
    plt.figure(figsize=(4, 3))
    plt.plot(fpr, tpr, color='darkorange', lw=2, label=f"ROC curve (AUC = {roc_auc:.3f})")
    plt.plot([0, 1], [0, 1], color='navy', lw=2, linestyle='--', label='Random Classifier')
    plt.xlabel("False Positive Rate", fontsize=6)
    plt.ylabel("True Positive Rate", fontsize=6)
    plt.title("Receiver Operating Characteristic (ROC) Curve", fontsize=7, fontweight='bold')
    plt.legend(loc="lower right")
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    buffer = BytesIO()
    plt.savefig(buffer, format="png", dpi=300, bbox_inches='tight')
    roc_plot_filename = os.path.join(rel_output_dir, "roc_curve.png")
    file_contents[roc_plot_filename] = base64.b64encode(buffer.getvalue()).decode("utf-8")
    plt.close()

    # Confusion Matrix Heatmap
    plt.figure(figsize=(4, 3))
    sns.heatmap(cm, annot=True, fmt="d", cmap="Blues", cbar=True, annot_kws={"size": 14})
    plt.xlabel("Predicted Label", fontsize=6)
    plt.ylabel("True Label", fontsize=6)
    plt.title("Confusion Matrix", fontsize=7, fontweight='bold')
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    buffer = BytesIO()
    plt.savefig(buffer, format="png", dpi=300, bbox_inches='tight')
    cm_plot_filename = os.path.join(rel_output_dir, "confusion_matrix.png")
    file_contents[cm_plot_filename] = base64.b64encode(buffer.getvalue()).decode("utf-8")
    plt.close()
    
    # Calibration Plot
    plt.figure(figsize=(4, 4))
    ax = plt.gca()
    CalibrationDisplay.from_predictions(data[dependent_var], predicted_probs, n_bins=10, ax=ax, strategy='quantile')
    plt.title("Calibration Plot (Reliability Curve)", fontsize=7, fontweight='bold')
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    buffer = BytesIO()
    plt.savefig(buffer, format="png", dpi=300, bbox_inches='tight')
    calibration_plot_filename = os.path.join(rel_output_dir, "calibration_plot.png")
    file_contents[calibration_plot_filename] = base64.b64encode(buffer.getvalue()).decode("utf-8")
    plt.close()

    # --- INTERPRETATION AND ACTIONS ---
    
    actions = []
    significant_vars = []
    coefficients_interpretation = []
    
    for _, row in coeff_table.iterrows():
        var, p_value, odds_ratio = row["Variable"], row["p-value"], row["Odds Ratio"]
        if var == "const": 
            continue
        var_name = regression_vars.get(var, var)
        
        if p_value < 0.05:
            significant_vars.append(var)
            direction = t["increase"] if odds_ratio > 1 else t["decrease"]
            magnitude = (odds_ratio - 1) * 100 if odds_ratio > 1 else (1 - odds_ratio) * 100
            coefficients_interpretation.append(
                t["sig_effect"].format(var, var_name, p_value, var, dependent_name, direction, magnitude, odds_ratio)
            )
        else:
            coefficients_interpretation.append(
                t["no_sig_effect"].format(var, var_name, p_value)
            )
            action_type = ActionType.DISCARD_FACTOR if var in latent_groups and len(latent_groups[var]) > 1 else ActionType.REMOVE_VARIABLE
            
            comment_key = "remove_factor_comment" if action_type == ActionType.DISCARD_FACTOR else "remove_variable_comment"
            
            actions.append(Action(
                action_type=action_type,
                method="run_logistic_regression_analysis",
                issue=t["sig_check_issue"].format(p_value),
                comment=t[comment_key].format(var),
                status="pending",
                action_params={"factor" if action_type == ActionType.DISCARD_FACTOR else "variable": var}
            ))

    # --- REPORT GENERATION ---

    # Model Summary
    model_summary = {
        "Pseudo R² (McFadden)": pseudo_r2, 
        "AIC": model.aic, 
        "BIC": model.bic,
        "Log-Likelihood": model.llf, 
        "LLR p-value": model.llr_pvalue,
        "Accuracy": accuracy, 
        "AUC": roc_auc,
        "HL_statistic": hl_test_results["statistic"], 
        "HL_p_value": hl_test_results["p_value"]
    }
    model_summary_df = pd.DataFrame([model_summary])
    model_summary_filename = os.path.join(rel_output_dir, "model_summary.csv")
    file_contents[model_summary_filename] = model_summary_df.to_csv(index=False)

    # Logistic Regression Equation
    intercept = model.params.get("const", 0)
    equation_terms = [f"{intercept:.3f}"] + [f"{model.params.get(var, 0):+.3f} × {var}" for var in independent_vars]
    log_odds_equation = f"log(odds) = {' '.join(equation_terms)}"

    # Build Report Content
    coeff_text = '\n'.join(coefficients_interpretation)
    
    stat_sig = t["stat_sig"] if model.llr_pvalue < 0.05 else t["not_stat_sig"]
    if pseudo_r2 >= 0.2:
        fit_quality = t["fit_good"]
    elif pseudo_r2 >= 0.1:
        fit_quality = t["fit_moderate"]
    else:
        fit_quality = t["fit_poor"]
    model_fit_interpretation = t["model_fit_interp"].format(
        model.llr_pvalue, stat_sig, pseudo_r2, pseudo_r2*100, fit_quality
    )
    
    hl_p = hl_test_results['p_value']
    hl_concl = t["hl_good"] if hl_p >= 0.05 else t["hl_poor"]
    hl_interp = t["hl_interp"].format(hl_p, hl_concl)

    if roc_auc >= 0.9:
        disc_quality = t["disc_excellent"]
    elif roc_auc >= 0.8:
        disc_quality = t["disc_good"]
    elif roc_auc >= 0.7:
        disc_quality = t["disc_fair"]
    else:
        disc_quality = t["disc_poor"]
    classification_interp = t["class_interp"].format(roc_auc, disc_quality, accuracy)
    
    max_vif = vif_data["VIF"].max()
    vif_concl = t["vif_ok"] if max_vif < 10 else t["vif_issue"]
    multicollinearity_interpretation = t["multicol_interp"].format(max_vif, vif_concl)

    equation_report = f"{t['equation_title']}{log_odds_equation}"
    
    additional_report = f"""
{t["model_fit_section"]}{t["overall_fit_section"]}{t["model_summary"].format(model_summary_filename)}{t["interpretation"]}{model_fit_interpretation}

{t["goodness_fit_section"]}{t["hl_test_title"]}{hl_interp}

{t["class_perf_section"]}{t["class_report_title"].format(class_report_filename)}{t["interpretation"]}{classification_interp}

{t["confusion_matrix"].format(cm_plot_filename)}{t["roc_curve"].format(roc_plot_filename)}
{t["diagnostics_section"]}{t["multicol_section"]}{t["vif_table"].format(vif_filename)}{t["interpretation"]}{multicollinearity_interpretation}

{t["calibration_section"]}{t["calibration_plot"].format(calibration_plot_filename)}{t["calibration_desc"]}"""

    # Add REANALYZE action if needed
    if any(action.action_type in [ActionType.DISCARD_FACTOR, ActionType.REMOVE_VARIABLE] for action in actions):
        actions.append(Action(
            action_type=ActionType.REANALYZE,
            method="run_logistic_regression_analysis",
            issue=t["reanalyze_issue"],
            comment=t["reanalyze_comment"],
            status="pending",
            action_params=None,
            reflection_params={
                "tool": "run_logistic_regression_analysis",
                "parameters": {
                    "factor_key": dependent_var,
                    "independent_vars": significant_vars,
                    "save_files": save_files,
                    "output_dir": base_output_dir,
                    "language": language,
                    "count": count + 1
                },
                "comment": t["reanalyze_reflection_comment"]
            },
            reset_actions=True
        ))
        equation_report = ""
        additional_report = ""

    # Main Report
    report = f"""{t["title"]}{t["analysis_of"].format(dependent_name)}{t["intro"].format(dependent_name)}{t["coeff_section"]}{t["coeff_table"].format(coeff_table_filename)}{t["interpretation"]}{coeff_text}

{equation_report}
{additional_report}
"""

    logs.append(report)

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

    # Prepare results dictionary
    results = {
        "dependent_variable": dependent_var,
        "independent_variables": independent_vars,
        "significant_variables": significant_vars,
        "coefficients_table": coeff_table.to_dict(),
        "model_summary": model_summary,
        "roc_auc": roc_auc,
        "confusion_matrix": cm.tolist()
    }

    return ToolOutput(
        results=serialize_dict(results),
        logs=logs,
        file_contents=file_contents,
        action=actions if actions else None
    )
