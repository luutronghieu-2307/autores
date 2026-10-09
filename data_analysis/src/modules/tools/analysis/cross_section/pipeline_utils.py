import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns
import base64
import io
import json
import os
from scipy.stats import spearmanr


from data_analysis.src.modules.tools.analysis.cross_section.utils import (
    pearson_correlation_analysis,
    multivariate_regression_analysis,
    evaluate_coefficient_of_determination,
    student_t_test,
    fisher_f_test,
    durbin_watson_test,
    homoscedasticity_test,
    variance_inflation_factor_test,
    evaluate_regression_fit,
    cronbach_alpha_analysis,
    exploratory_factor_analysis,
    kmo_test,
    pca_varimax_analysis,
    bartlett_sphericity_test,
    communality_analysis,
    eigenvalue_eigenvector_analysis,
    determine_number_of_factors,
    multivariate_regression_analysis_no_intercept,
    evaluate_regression_fit_no_intercept,
)
import statsmodels.api as sm
import seaborn as sns
import scipy.stats as stats

from data_analysis.src.modules.tools.analysis.cross_section.criteria import get_diagnostic_criteria

import warnings
warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=UserWarning)

from typing import Dict, Optional

DEFAULT_TRANSLATIONS = {
    "en": {
        "met_requirements": "Met requirements",
        "not_met_requirements": "Not met requirements",
        "factor": "Factor",
        "observed_variable": "Observed Variable",
        "loading_factor": "Loading Factor",
        "cronbach_alpha": "Cronbach's Alpha",
        "evaluation": "Evaluation",
        "low_item_total_corr": "Low item-total correlation for {}",
        "kmo_per_item_label": "Kaiser-Meyer-Olkin Measure of Sampling Adequacy",
        "kmo_bartlett_title": "KMO and Bartlett's Test",
        "kmo_result": "Kaiser-Meyer-Olkin (KMO) = {:.3f} ({}): Data is {} for factor analysis.",
        "kmo_suitable": "suitable",
        "kmo_partially_suitable": "partially suitable but use with caution",
        "kmo_unsuitable": "unsuitable",
        "low_kmo_vars": "Variables with low KMO (< 0.5): {}. Consider removal.",
        "bartlett_result": "Bartlett’s Test of Sphericity: Chi-Square = {:.3f}, p-value = {:.3f} ({}): Variables are {} for factor analysis.",
        "bartlett_suitable": "correlated significantly, suitable",
        "bartlett_unsuitable": "not correlated significantly, unsuitable",
        "warning": "Warning: {}",
        "total_variance_explained_title": "Total Variance Explained = {:.3f}% ({}): Factor model {} data.",
        "variance_status_very_good": "Very good",
        "variance_status_good": "Good",
        "variance_status_acceptable": "Acceptable",
        "variance_status_insufficient": "Insufficient",
        "variance_expl_good": "explains data well",
        "variance_expl_acceptable": "explains data acceptably but can be improved",
        "variance_expl_insufficient": "does not explain data sufficiently, adjustment needed",
        "num_factors_selected": "Number of factors selected: {}.",
        "rotated_component_matrix_title": "Rotated Component Matrix shows the factor structure as follows:",
        "factor_has_loadings": "- {}: {} variables have significant loadings (> 0.4).",
        "low_loading_vars": "Variables with low loadings (< 0.4) on all factors: {}. Consider removal.",
        "cross_loading_vars": "Variables with loadings on multiple factors (> 0.4): {}. Consider reviewing factor structure.",
        "independent_variable": "Independent Variable",
        "unstandardized_b": "Unstandardized B",
        "standard_error": "Std. Error",
        "standardized_beta": "Standardized Beta",
        "t_stat": "t",
        "sig": "Sig.",
        "tolerance": "Tolerance",
        "vif": "VIF",
        "constant": "(Constant)",
        "regression_significant": "Significant",
        "regression_not_significant": "Not Significant",
        "r_square": "R Square",
        "adj_r_square": "Adjusted R Square",
        "std_error_estimate": "Std. Error of the Estimate",
        "r_square_change": "R Square Change",
        "f_change": "F Change",
        "sig_f_change": "Sig. F Change",
        "correlation_between": "Correlation between {} and {}: r = {:.3f}, Sig (2-tailed) = {:.3f}, {}",
        "model_summary_predictors": "Predictors: {}",
        "no_intercept_note": "This is a regression through the origin (no-intercept model)",
        "r_square_measure_note": "R Square measures the proportion of variability in the dependent variable about the origin explained by regression",
        "r_square_compare_note": "The R Square value cannot be compared to R Square for models including an intercept",
        "bartlett_chi": "Bartlett's Test of Sphericity - Approx. Chi-Square",
        "bartlett_df": "Bartlett's Test of Sphericity - df",
        "bartlett_sig": "Bartlett's Test of Sphericity - Sig.",
        "dependent_variable_note": "Dependent Variable: {}",
        "no_intercept_model_note": "This is a Linear Regression through the Origin model",
        "anova_title": "ANOVA",
        "no_intercept_total_ss_note": "The total sum of squares is not corrected for the constant because the constant is zero for regression through the origin",
        "anova_with_intercept_title": "ANOVA(a)",
        "with_intercept_model_note": "Linear Regression with Intercept",
        "with_intercept_predictors_note": "Predictors: (Constant), {}",
        "spearman_rho_significant": "Significant Spearman’s rho ({:.3f}, p={:.3f}) between squared residuals and {}, suggesting potential heteroscedasticity.",
        "spearman_rho_none": "No significant Spearman’s rho correlations found, suggesting no evidence of heteroscedasticity.",
        "model": "Model",
        "source": "Source",
        "regression": "Regression",
        "residual": "Residual",
        "total": "Total",
        "sum_of_squares": "Sum of Squares",
        "df": "df",
        "mean_square": "Mean Square",
        "f_stat": "F",
        "item": "Item",
        "scale_mean_if_deleted": "Scale Mean if Item Deleted",
        "scale_variance_if_deleted": "Scale Variance if Item Deleted",
        "corrected_item_total_corr": "Corrected Item-Total Correlation",
        "alpha_if_deleted": "Cronbach's Alpha if Item Deleted",
        "scale_reliable": "The scale is reliable (Alpha ≥ 0.7).",
        "scale_unreliable": "The scale reliability is below the recommended threshold (Alpha < 0.7).",
        "alpha_not_computed": "Cronbach’s Alpha could not be computed.",
        "item_contributes": "Item contributes adequately to the scale (Correlation ≥ 0.3).",
        "item_low_corr": "Item has low correlation with the scale (Correlation < 0.3). Consider removal.",
        "removing_item_improves": "Removing {} increases Cronbach’s Alpha to {:.3f}, suggesting potential removal.",
        "removing_item_not_improves": "Removing {} does not improve Cronbach’s Alpha (remains or decreases to {:.3f}).",
        'variable_label': 'Variable',
        'category_label': 'Category',
        'frequency_label': 'Frequency',
        'percentage_label': 'Percentage (%)',
        'correlation_coefficient': 'Correlation Coefficient',
        'sig_2_tailed': 'Sig. (2-tailed)',
        'metric_label': 'Metric',
        'num_items': 'N of Items',
        "homoscedastic": "Homoscedastic",
        "heteroscedastic": "Heteroscedastic",
        "normal": "Normal",
        "non_normal": "Non-Normal",
        "no_autocorr_detected": "No significant autocorrelation detected.",
        "potential_autocorr_detected": "Potential autocorrelation detected.",
        "residuals_ok": "Residuals are homoscedastic and normally distributed.",
        "residuals_violate": "Residuals may violate homoscedasticity or normality assumptions.",
        "multicollinearity_detected": "Multicollinearity detected in variables: {} (VIF > 5).",
        "no_multicollinearity_detected": "No significant multicollinearity detected (all VIF < 5).",
    },
    "vi": {
        "met_requirements": "Đạt yêu cầu",
        "not_met_requirements": "Không đạt yêu cầu",
        "factor": "Nhân tố",
        "observed_variable": "Biến quan sát",
        "loading_factor": "Hệ số tải",
        "cronbach_alpha": "Hệ số Cronbach's Alpha",
        "evaluation": "Đánh giá",
        "low_item_total_corr": "Tương quan biến-tổng thấp cho {}",
        "kmo_per_item_label": "Hệ số Kaiser-Meyer-Olkin (KMO)",
        "kmo_bartlett_title": "Kiểm định KMO và Bartlett",
        "kmo_result": "Độ phù hợp mẫu Kaiser-Meyer-Olkin (KMO) = {:.3f} ({}): Dữ liệu {} để thực hiện phân tích nhân tố.",
        "kmo_suitable": "phù hợp",
        "kmo_partially_suitable": "có thể phù hợp nhưng cần thận trọng",
        "kmo_unsuitable": "không phù hợp",
        "low_kmo_vars": "Các biến có KMO thấp (< 0.5): {}. Cân nhắc loại bỏ.",
        "bartlett_result": "Kiểm định Bartlett’s Sphericity: Chi-Square = {:.3f}, p-value = {:.3f} ({}): Các biến {} để thực hiện phân tích nhân tố.",
        "bartlett_suitable": "có tương quan đáng kể, phù hợp",
        "bartlett_unsuitable": "không có tương quan đáng kể, không phù hợp",
        "warning": "Cảnh báo: {}",
        "total_variance_explained_title": "Tổng phương sai giải thích được = {:.3f}% ({}): Mô hình nhân tố {} dữ liệu.",
        "variance_status_very_good": "Rất tốt",
        "variance_status_good": "Tốt",
        "variance_status_acceptable": "Chấp nhận được",
        "variance_status_insufficient": "Không đủ",
        "variance_expl_good": "giải thích tốt dữ liệu",
        "variance_expl_acceptable": "giải thích chấp nhận được nhưng có thể cải thiện",
        "variance_expl_insufficient": "giải thích không đủ dữ liệu, cần điều chỉnh",
        "num_factors_selected": "Số nhân tố được chọn: {}.",
        "rotated_component_matrix_title": "Ma trận nhân tố xoay (Rotated Component Matrix) cho thấy cấu trúc nhân tố như sau:",
        "factor_has_loadings": "- {}: {} biến có tải trọng đáng kể (> 0.4).",
        "low_loading_vars": "Các biến có tải trong thấp (< 0.4) trên tất cả nhân tố: {}. Cân nhắc loại bỏ.",
        "cross_loading_vars": "Các biến có tải trọng trên nhiều nhân tố (> 0.4): {}. Cân nhắc xem xét cấu trúc nhân tố.",
        "independent_variable": "Biến độc lập",
        "unstandardized_b": "Hệ số chưa chuẩn hóa (B)",
        "standard_error": "Sai số chuẩn",
        "standardized_beta": "Hệ số chuẩn hóa (Beta)",
        "t_stat": "t",
        "sig": "Sig.",
        "tolerance": "Hệ số Tolerance",
        "vif": "VIF",
        "constant": "(Constant)",
        "regression_significant": "Có ý nghĩa",
        "regression_not_significant": "Không có ý nghĩa",
        "r_square": "R Square",
        "adj_r_square": "R Square hiệu chỉnh",
        "std_error_estimate": "Sai số chuẩn của ước lượng",
        "r_square_change": "R Square thay đổi",
        "f_change": "F thay đổi",
        "sig_f_change": "Sig. F thay đổi",
        "correlation_between": "Tương quan giữa {} và {}: r = {:.3f}, Sig (2-tailed) = {:.3f}, {}",
        "model_summary_predictors": "Biến độc lập: {}",
        "no_intercept_note": "Đây là hồi quy qua gốc tọa độ (mô hình không có hệ số chặn)",
        "r_square_measure_note": "R Square đo lường tỷ lệ biến thiên của biến phụ thuộc quanh gốc tọa độ được giải thích bởi hồi quy",
        "r_square_compare_note": "Giá trị R Square không thể so sánh với R Square của các mô hình có hệ số chặn",
        "dependent_variable_note": "Biến phụ thuộc: {}",
        "no_intercept_model_note": "Đây là mô hình Hồi quy tuyến tính qua gốc tọa độ",
        "anova_title": "ANOVA",
        "no_intercept_total_ss_note": "Tổng bình phương không được hiệu chỉnh cho hằng số vì hằng số bằng không đối với hồi quy qua gốc tọa độ",
        "anova_with_intercept_title": "ANOVA(a)",
        "with_intercept_model_note": "Hồ quy tuyến tính có hệ số chặn",
        "with_intercept_predictors_note": "Biến độc lập: (Constant), {}",
        "spearman_rho_significant": "Hệ số Spearman’s rho có ý nghĩa ({:.3f}, p={:.3f}) giữa bình phương phần dư và {}, cho thấy khả năng có phương sai thay đổi.",
        "spearman_rho_none": "Không tìm thấy tương quan Spearman’s rho có ý nghĩa, cho thấy không có bằng chứng về phương sai thay đổi.",
        "model": "Mô hình",
        "source": "Nguồn",
        "regression": "Hồi quy",
        "residual": "Phần dư",
        "total": "Tổng",
        "sum_of_squares": "Tổng bình phương",
        "df": "df",
        "mean_square": "Trung bình bình phương",
        "f_stat": "F",
        "item": "Biến",
        "scale_mean_if_deleted": "Trung bình thang đo nếu loại biến",
        "scale_variance_if_deleted": "Phương sai thang đo nếu loại biến",
        "corrected_item_total_corr": "Tương quan biến-tổng hiệu chỉnh",
        "alpha_if_deleted": "Hệ số Cronbach's Alpha nếu loại biến",
        "scale_reliable": "Thang đo đạt độ tin cậy (Alpha ≥ 0.7).",
        "scale_unreliable": "Độ tin cậy thang đo dưới mức khuyến nghị (Alpha < 0.7).",
        "alpha_not_computed": "Không thể tính toán hệ số Cronbach’s Alpha.",
        "item_contributes": "Biến đóng góp tốt cho thang đo (Tương quan ≥ 0.3).",
        "item_low_corr": "Biến có tương quan thấp với thang đo (Tương quan < 0.3). Cân nhắc loại bỏ.",
        "removing_item_improves": "Loại bỏ {} làm tăng Cronbach’s Alpha lên {:.3f}, gợi ý nên loại bỏ.",
        "removing_item_not_improves": "Loại bỏ {} không cải thiện Cronbach’s Alpha (giữ nguyên hoặc giảm xuống {:.3f}).",
        'variable_label': 'Biến',
        'category_label': 'Danh mục',
        'frequency_label': 'Tần số',
        'percentage_label': 'Tỷ lệ (%)',
        'correlation_coefficient': 'Hệ số tương quan',
        'sig_2_tailed': 'Sig. (2-tailed)',
        'metric_label': 'Chỉ số',
        'num_items': 'Số lượng biến',
        "homoscedastic": "Đẳng phương sai",
        "heteroscedastic": "Phương sai thay đổi",
        "normal": "Phân phối chuẩn",
        "non_normal": "Phân phối không chuẩn",
        "no_autocorr_detected": "Không phát hiện tự tương quan đáng kể.",
        "potential_autocorr_detected": "Có khả năng xảy ra tự tương quan.",
        "residuals_ok": "Phần dư có đẳng phương sai và phân phối chuẩn.",
        "residuals_violate": "Phần dư có thể vi phạm giả định đẳng phương sai hoặc phân phối chuẩn.",
        "bartlett_chi": "Kiểm định Bartlett - Chi-Square xấp xỉ",
        "bartlett_df": "Kiểm định Bartlett - Bậc tự do (df)",
        "bartlett_sig": "Kiểm định Bartlett - Sig.",
        "multicollinearity_detected": "Phát hiện đa cộng tuyến ở các biến: {} (VIF > 5).",
        "no_multicollinearity_detected": "Không phát hiện đa cộng tuyến đáng kể (tất cả VIF < 5).",
    }
}

def get_t_dict(t: Optional[Dict] = None, language: str = "en") -> Dict:
    defaults = DEFAULT_TRANSLATIONS.get(language, DEFAULT_TRANSLATIONS["en"])
    if t:
        # Merge provided t with defaults to ensure all keys exist
        merged = defaults.copy()
        merged.update(t)
        return merged
    return defaults


def get_iteration_suffix(count: int, language: str = "en") -> str:
    """
    Generate iteration suffix for analysis titles based on count and language.

    Parameters:
        count: The iteration count (1, 2, 3, ...)
        language: Language code - "en" for English, "vi" for Vietnamese

    Returns:
        - For count = 1: Empty string (no suffix needed)
        - For count >= 2 in English: " (2nd)", " (3rd)", " (4th)", etc.
        - For count >= 2 in Vietnamese: " (lần 2)", " (lần 3)", etc.
    """
    if count <= 1:
        return ""

    if language == "vi":
        return f" (lần {count})"
    else:
        # English ordinal suffix
        if count == 2:
            ordinal = "2nd"
        elif count == 3:
            ordinal = "3rd"
        else:
            ordinal = f"{count}th"
        return f" ({ordinal})"


def format_title_with_count(title: str, count: int, language: str = "en") -> str:
    """
    Append iteration suffix to a title based on count.

    Parameters:
        title: The base title string (e.g., "# Multiple Regression Analysis Report\n\n")
        count: The iteration count (1, 2, 3, ...)
        language: Language code - "en" for English, "vi" for Vietnamese

    Returns:
        Title with iteration suffix appended before the trailing newlines.
        For count = 1, returns the original title unchanged.

    Example:
        format_title_with_count("# Report\n\n", 2, "en") -> "# Report (2nd)\n\n"
        format_title_with_count("# Báo Cáo\n\n", 3, "vi") -> "# Báo Cáo (lần 3)\n\n"
    """
    if count <= 1:
        return title

    suffix = get_iteration_suffix(count, language)

    # Find trailing newlines and insert suffix before them
    stripped = title.rstrip('\n')
    trailing_newlines = title[len(stripped):]

    return stripped + suffix + trailing_newlines


# Function to make data JSON serializable
def json_serializable(obj):
    if isinstance(obj, pd.Series):
        return obj.to_dict()
    elif isinstance(obj, pd.DataFrame):
        return obj.to_dict(orient='records')
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, (float, np.float32, np.float64)) and (np.isnan(obj) or np.isinf(obj)):
        return None
    elif hasattr(obj, 'tolist'):
        return obj.tolist()
    elif hasattr(obj, '__dict__'):
        return {key: json_serializable(value) for key, value in obj.__dict__.items()}
    else:
        return str(obj)

def prepare_for_json(data):
    if isinstance(data, dict):
        return {k: prepare_for_json(v) for k, v in data.items()}
    elif isinstance(data, list) or isinstance(data, tuple):
        return [prepare_for_json(item) for item in data]
    elif isinstance(data, (pd.Series, pd.DataFrame, np.ndarray)):
        return json_serializable(data)
    else:
        try:
            json.dumps(data)
            return data
        except (TypeError, OverflowError):
            return str(data)



#########################################################
##### 3.3.10 Định nghĩa bảng biểu kết quả đầu ra ########
#########################################################

#---------------------------------------------#
# Phần 1
#---------------------------------------------#

#---------------------------------------------#
# Phần 2
#---------------------------------------------#

def analyze_factor_group(
    data: pd.DataFrame,
    factor_name: str,
    variables: list[str],
    save_results: bool = False,
    output_dir: str = None,
    t: dict = None
) -> tuple[list[dict], dict]:
    """
    Analyze a factor group: compute Cronbach's alpha and EFA, return table rows and diagnostics.
    
    Parameters:
    - data: DataFrame with survey data.
    - factor_name: Name of the factor.
    - variables: list of variable names in the factor group.
    - save_results: If True, save results to output_dir (default False).
    - output_dir: Directory to save results if save_results is True.
    
    Returns:
    - rows: list of dictionaries for table rows.
    - diagnostics: dictionary of diagnostic results.
    """
    factor_data = data[variables]
    
    # Cronbach's Alpha
    alpha, ci, item_total_corr, alpha_diagnostics = cronbach_alpha_analysis(factor_data, t=t)
    
    # EFA with n_factors=1
    loadings, communalities, efa_diagnostics = exploratory_factor_analysis(
        factor_data, n_factors=1, rotation='varimax', method='minres', visualize=False, t=t
    )
    
    # Get diagnostic criteria for Cronbach’s Alpha
    low_corr_items = [k for k, v in item_total_corr.items() if abs(v) < 0.3]
    alpha_diag = get_diagnostic_criteria(
        analysis_type="cronbach_alpha",
        metric_value=alpha,
        additional_data={"item_total_corr": low_corr_items}
    )
    
    # Check criteria
    alpha_ok = alpha >= 0.7
    item_corr_ok = len(low_corr_items) == 0
    
    # Prepare rows and diagnostics
    rows = []
    diagnostics = {
        'Cronbach_Alpha': {
            'Alpha': alpha,
            'CI_95': ci,
            'Item_Total_Correlations': item_total_corr,  # Fixed: Removed .to_dict()
            'Diagnostics': alpha_diag
        },
        'EFA': {
            'Loadings': loadings.to_dict(),
            'Communalities': communalities.to_dict(),
            'Diagnostics': efa_diagnostics,
            'Factor_Loadings_Diagnostics': {}
        }
    }
    
    for var in variables:
        loading = loadings.loc[var, 'Factor1']
        
        # Get diagnostic criteria for factor loading
        loading_diag = get_diagnostic_criteria(
            analysis_type="factor_loading",
            metric_value=abs(loading)
        )
        
        # Check loading
        loading_ok = abs(loading) >= 0.4
        
        # Store loading diagnostics
        diagnostics['EFA']['Factor_Loadings_Diagnostics'][var] = loading_diag
        
        # Compile evaluation comments
        evaluation_comments = []
        all_ok = alpha_ok and item_corr_ok and loading_ok
        
        if all_ok:
            evaluation = t["met_requirements"]
            evaluation_comments.append(f"Alpha={alpha:.3f} ({alpha_diag['status']})")
            evaluation_comments.append(f"Loading={loading:.3f} ({loading_diag['status']})")
        else:
            evaluation = t["not_met_requirements"]
            if not alpha_ok:
                evaluation_comments.append(f"Alpha={alpha:.3f} ({alpha_diag['status']})")
                evaluation_comments.extend(alpha_diag['warnings'])
            if not item_corr_ok and var in low_corr_items:
                evaluation_comments.append(t['low_item_total_corr'].format(var))
            if not loading_ok:
                evaluation_comments.append(f"Loading={loading:.3f} ({loading_diag['status']})")
                evaluation_comments.extend(loading_diag['warnings'])
        
        # Create row
        row = {
            t['factor']: factor_name,
            t['observed_variable']: var,
            t['loading_factor']: f"{loading:.3f}",
            t['cronbach_alpha']: f"{alpha:.3f}",
            t['evaluation']: f"{evaluation}: {'; '.join(evaluation_comments)}"
        }
        rows.append(row)
    
    # Optional saving
    if save_results and output_dir:
        os.makedirs(output_dir, exist_ok=True)
        pd.DataFrame(rows).to_csv(
            os.path.join(output_dir, f'factor_{factor_name}_results.csv'), index=False
        )
        with open(os.path.join(output_dir, f'factor_{factor_name}_diagnostics.json'), 'w') as f:
            json.dump(prepare_for_json(diagnostics), f, indent=2)
    
    return rows, diagnostics

def generate_demographic_statistics(
    demographics: pd.DataFrame,
    save_results: bool = False,
    output_dir: str = None,
    t: dict = None
) -> pd.DataFrame:
    """
    Generate demographic statistics table.
    
    Parameters:
    - demographics: DataFrame with demographic data.
    - save_results: If True, save results to output_dir (default False).
    - output_dir: Directory to save results if save_results is True.
    
    Returns:
    - demo_table: DataFrame with demographic statistics.
    """
    t = get_t_dict(t)
    demo_stats = []
    for col in demographics.columns:
        freq = demographics[col].value_counts()
        perc = demographics[col].value_counts(normalize=True) * 100
        for category in freq.index:
            demo_stats.append({
                t['variable_label']: col,
                t['category_label']: category,
                t['frequency_label']: freq[category],
                t['percentage_label']: f"{perc[category]:.1f}"
            })
    demo_table = pd.DataFrame(demo_stats)
    
    if save_results and output_dir:
        os.makedirs(output_dir, exist_ok=True)
        demo_table.to_csv(os.path.join(output_dir, 'demographic_statistics.csv'), index=False)
    
    return demo_table

def create_appendix(
    data: pd.DataFrame,
    all_vars: list[str],
    save_results: bool = False,
    output_dir: str = None,
    t: dict = None
) -> dict:
    """
    Generate appendix with additional analyses.
    
    Parameters:
    - data: DataFrame with survey data.
    - all_vars: list of all variable names.
    - save_results: If True, save results to output_dir (default False).
    - output_dir: Directory to save results if save_results is True.
    
    Returns:
    - appendix: dictionary with appendix results.
    """
    t = get_t_dict(t)
    full_data = data[all_vars]
    appendix = {
        'KMO': kmo_test(full_data, t=t),
        'Bartlett': bartlett_sphericity_test(full_data, t=t),
        'Communalities': communality_analysis(full_data, t=t),
        'Eigenvalues': eigenvalue_eigenvector_analysis(full_data, t=t),
        'Number_of_Factors': determine_number_of_factors(full_data, plot_scree=False, t=t)
    }
    
    if save_results and output_dir:
        os.makedirs(output_dir, exist_ok=True)
        with open(os.path.join(output_dir, 'factor_analysis_appendix.json'), 'w') as f:
            json.dump(prepare_for_json(appendix), f, indent=2)
    
    return appendix

def save_outputs_1(
    table: pd.DataFrame,
    demo_table: pd.DataFrame,
    appendix: dict,
    diagnostics_summary: dict,
    data: pd.DataFrame,
    demographics: pd.DataFrame,
    output_dir: str
) -> None:
    """
    Save all analysis outputs to the specified directory.
    
    Parameters:
    - table: Factor analysis results table.
    - demo_table: Demographic statistics table.
    - appendix: Appendix dictionary.
    - diagnostics_summary: Diagnostics summary dictionary.
    - data: Raw survey data.
    - demographics: Raw demographics data.
    - output_dir: Directory to save all files.
    """
    os.makedirs(output_dir, exist_ok=True)
    
    table.to_csv(os.path.join(output_dir, 'factor_analysis_results.csv'), index=False)
    demo_table.to_csv(os.path.join(output_dir, 'demographic_statistics.csv'), index=False)
    with open(os.path.join(output_dir, 'factor_analysis_appendix.json'), 'w') as f:
        json.dump(prepare_for_json(appendix), f, indent=2)
    with open(os.path.join(output_dir, 'diagnostics_summary.json'), 'w') as f:
        json.dump(prepare_for_json(diagnostics_summary), f, indent=2)
    data.to_csv(os.path.join(output_dir, 'raw_data.csv'), index=False)
    demographics.to_csv(os.path.join(output_dir, 'demographics_data.csv'), index=False)


#---------------------------------------------#
# Phần 3: Kết quả hồi quy
#---------------------------------------------#

#---------------------------------------------#
# Bước 1: Pearson Correlation Analysis
#---------------------------------------------#

def compute_pearson_correlations(
    data: pd.DataFrame,
    variables: list[str],
    save_results: bool = False,
    output_dir: str = None,
    t: dict = None
) -> tuple[pd.DataFrame, pd.DataFrame, list[str]]:
    """
    Compute Pearson correlation matrix, full significance table, and comments.
    
    Parameters:
    - data: DataFrame with variables for correlation analysis.
    - variables: list of variable names.
    - save_results: If True, save results to output_dir.
    - output_dir: Directory to save results if save_results is True.
    
    Returns:
    - corr_table: DataFrame with correlation coefficients, Sig (2-tailed), N for all variables.
    - corr_matrix: DataFrame with full correlation matrix.
    - comments: list of significance comments for each variable pair.
    """
    t_dict = get_t_dict(t)
    # Note: Assuming pearson_correlation_analysis is defined elsewhere
    # Compute correlation matrix
    corr_matrix = pearson_correlation_analysis(
        data[variables], visualize=False, output_dir=output_dir, filename='pearson_correlation_heatmap.png', t=t_dict
    )
    
    # Compute correlations, p-values, and sample sizes
    n_samples = len(data)
    corr_data = {var: {'Correlation Coefficient': {}, 'Sig. (2-tailed)': {}, 'N': {}} for var in variables}
    
    for var1 in variables:
        for var2 in variables:
            corr, pval = stats.pearsonr(data[var1], data[var2])
            corr_data[var1]['Correlation Coefficient'][var2] = corr
            corr_data[var1]['Sig. (2-tailed)'][var2] = pval
            corr_data[var1]['N'][var2] = n_samples
    
    # Prepare correlation table in the desired format
    corr_table_data = []
    for var in variables:
        # Correlation Coefficient row
        row = {'Variable': var, 'Metric': 'Correlation Coefficient'}
        for var2 in variables:
            row[var2] = f"{corr_data[var]['Correlation Coefficient'][var2]:.3f}"
        corr_table_data.append(row)
        
        # Sig. (2-tailed) row
        row = {'Variable': var, 'Metric': 'Sig. (2-tailed)'}
        for var2 in variables:
            if var == var2:
                row[var2] = '.'
            else:
                row[var2] = f"{corr_data[var]['Sig. (2-tailed)'][var2]:.3f}"
        corr_table_data.append(row)
        
        # N row
        row = {'Variable': var, 'Metric': 'N'}
        for var2 in variables:
            row[var2] = int(corr_data[var]['N'][var2])
        corr_table_data.append(row)
    
    corr_table = pd.DataFrame(corr_table_data)
    
    # Generate comments for non-self correlations
    comments = []
    for var1 in variables:
        for var2 in variables:
            if var1 < var2:  # Avoid duplicates and self-correlations
                corr_value = corr_data[var1]['Correlation Coefficient'][var2]
                p_value = corr_data[var1]['Sig. (2-tailed)'][var2]
                significance = t_dict["regression_significant"] if p_value < 0.05 else t_dict["regression_not_significant"]
                comments.append(
                    t_dict['correlation_between'].format(var1, var2, corr_value, p_value, significance)
                )
    
    if save_results and output_dir:
        os.makedirs(output_dir, exist_ok=True)
        # Save correlation table
        corr_table.to_csv(os.path.join(output_dir, 'correlation_matrix.csv'), index=False)
        # Save comments to text file
        with open(os.path.join(output_dir, 'correlation_comments.txt'), 'w') as f:
            f.write("Pearson Correlation Significance Comments\n")
            f.write("=" * 50 + "\n")
            for comment in comments:
                f.write(f"{comment}\n")
        print(f"Correlation table and comments saved to '{output_dir}'")
    
    return corr_table, corr_matrix, comments

def evaluate_model_fit(
    data: pd.DataFrame,
    dependent_var: str,
    independent_vars: list[str],
    save_results: bool = False,
    output_dir: str = None,
    t: dict = None
) -> dict:
    """
    Evaluate regression model fit and produce a summary table matching the provided example.

    Parameters:
    - data: DataFrame with regression data.
    - dependent_var: Name of the dependent variable.
    - independent_vars: list of independent variable names.
    - save_results: If True, save results to output_dir (default False).
    - output_dir: Directory to save results if save_results is True.

    Returns:
    - model_summary: dictionary with model fit metrics formatted with appropriate rounding.
    """
    t_dict = get_t_dict(t)
    # Compute R² and related metrics
    r2_results = evaluate_coefficient_of_determination(data, dependent_var, independent_vars)
    fit_results = evaluate_regression_fit(data, dependent_var, independent_vars)

    # Fit the regression model to get additional statistics
    X = data[independent_vars]
    y = data[dependent_var]
    X_sm = sm.add_constant(X)  # Add intercept term
    model = sm.OLS(y, X_sm).fit()

    # Extract required metrics
    r = np.sqrt(r2_results['R_squared'])  # R = sqrt(R²)
    r_square = r2_results['R_squared']
    adjusted_r_square = r2_results['R_squared_adjusted']
    std_error = fit_results['Se']
    r_square_change = r_square  # For a single model, R² Change = R²
    f_change = model.fvalue
    df1 = len(independent_vars)  # Number of predictors
    df2 = model.df_resid  # Residual degrees of freedom (n - k - 1)
    sig_f_change = model.f_pvalue

    # Create model summary dictionary with rounded values
    # IMPORTANT: We include both translated keys for display and hardcoded English keys 
    # for internal code logic (backward compatibility)
    model_summary = {
        t_dict['model']: 1,
        'model': 1,
        'R': f"{r:.3f}{'ᵃ' if r >= 0.3 else ''}",
        t_dict['r_square']: f"{r_square:.3f}",
        'R Square': f"{r_square:.3f}",
        t_dict['adj_r_square']: f"{adjusted_r_square:.3f}",
        'Adjusted R Square': f"{adjusted_r_square:.3f}",
        t_dict['std_error_estimate']: f"{std_error:.5f}",
        'Std. Error of the Estimate': f"{std_error:.5f}",
        t_dict['r_square_change']: f"{r_square_change:.3f}",
        'R Square Change': f"{r_square_change:.3f}",
        t_dict['f_change']: f"{f_change:.3f}",
        'F Change': f"{f_change:.3f}",
        'df1': int(df1),
        'df2': int(df2),
        t_dict['sig_f_change']: f"{sig_f_change:.3f}",
        'Sig. F Change': f"{sig_f_change:.3f}"
    }

    # Save results if requested
    if save_results and output_dir:
        os.makedirs(output_dir, exist_ok=True)
        # Save numerical results as CSV
        summary_df = pd.DataFrame([model_summary])
        summary_df.to_csv(os.path.join(output_dir, 'model_summary.csv'), index=False)
        # # Save notes in a separate text file
        # notes = [
        #     "Notes",
        #     f"Predictors (Constants): {', '.join(independent_vars)}",
        #     f"Dependent Variable: {dependent_var}"
        # ]
        # with open(os.path.join(output_dir, 'model_summary_notes.txt'), 'w') as f:
        #     f.write('\n'.join(notes))

    return model_summary

def compute_coefficients_table(
    data: pd.DataFrame,
    dependent_var: str,
    independent_vars: list[str],
    save_results: bool = False,
    output_dir: str = None,
    t: dict = None
) -> pd.DataFrame:
    """
    Compute regression coefficients table with t-tests and VIF, formatted like SPSS.
    
    Parameters:
    - data: DataFrame with regression data.
    - dependent_var: Name of the dependent variable.
    - independent_vars: list of independent variable names.
    - save_results: If True, save results to output_dir (default False).
    - output_dir: Directory to save results if save_results is True.
    
    Returns:
    - coeff_table: DataFrame with coefficients, t-tests, and VIF metrics.
    """
    intercept, coefficients, _ = multivariate_regression_analysis(data, dependent_var, independent_vars)
    t_test_results = student_t_test(data, dependent_var, independent_vars)
    vif_results = variance_inflation_factor_test(data, independent_vars)
    
    t_dict = get_t_dict(t)
    coeff_table_data = []
    
    # Add intercept (Constant) as the first row
    intercept_value = intercept.iloc[0]
    # Get standard error and p-value from multivariate_regression_analysis
    X_sm = sm.add_constant(data[independent_vars])
    model = sm.OLS(data[dependent_var], X_sm).fit()
    intercept_std_err = model.bse['const']
    intercept_p_value = model.pvalues['const']
    intercept_t_stat = model.tvalues['const']
    
    coeff_table_data.append({
        t_dict['independent_variable']: t_dict['constant'],
        t_dict['unstandardized_b']: f"{intercept_value:.3f}",
        t_dict['standard_error']: f"{intercept_std_err:.3f}",
        t_dict['standardized_beta']: "-",
        t_dict['t_stat']: f"{intercept_t_stat:.3f}",
        t_dict['sig']: f"{intercept_p_value:.3f}",
        t_dict['tolerance']: "-",
        t_dict['vif']: "-"
    })
    
    # Add independent variables
    for var in independent_vars:
        coeff = coefficients.loc[var, 'Coefficient']
        std_err = coefficients.loc[var, 'Standard Error']
        beta = coeff * (data[var].std() / data[dependent_var].std())
        t_stat = t_test_results['results'].loc[var, 't_statistic']
        p_value = t_test_results['results'].loc[var, 'p_value']
        
        vif_row = vif_results['results'][vif_results['results']['Variable'] == var]
        vif = vif_row['VIF'].values[0] if not vif_row.empty else float('nan')
        tolerance = 1 / vif if not np.isnan(vif) else float('nan')
        
        coeff_table_data.append({
            t_dict['independent_variable']: var,
            t_dict['unstandardized_b']: f"{coeff:.3f}",
            t_dict['standard_error']: f"{std_err:.3f}",
            t_dict['standardized_beta']: f"{beta:.3f}",
            t_dict['t_stat']: f"{t_stat:.3f}",
            t_dict['sig']: f"{p_value:.3f}",
            t_dict['tolerance']: f"{tolerance:.3f}",
            t_dict['vif']: f"{vif:.3f}"
        })
    
    coeff_table = pd.DataFrame(coeff_table_data)
    
    if save_results and output_dir:
        os.makedirs(output_dir, exist_ok=True)
        coeff_table.to_csv(os.path.join(output_dir, 'coefficients_table.csv'), index=False)
    
    return coeff_table

def perform_anova_f_test(
    data: pd.DataFrame,
    dependent_var: str,
    independent_vars: list[str],
    save_results: bool = False,
    output_dir: str = None,
    t: dict = None
) -> dict:
    """
    Perform ANOVA F-test for regression model.
    
    Parameters:
    - data: DataFrame with regression data.
    - dependent_var: Name of the dependent variable.
    - independent_vars: list of independent variable names.
    - save_results: If True, save results to output_dir (default False).
    - output_dir: Directory to save results if save_results is True.
    
    Returns:
    - anova_summary: dictionary with F-statistic, p-value, and decision.
    """
    t_dict = get_t_dict(t)
    f_test_results = fisher_f_test(data, dependent_var, independent_vars)
    
    anova_summary = {
        'F-Statistic': f"{f_test_results['F_statistic']:.3f}",
        'p-value': f"{f_test_results['p_value']:.3f}",
        'Decision': f_test_results['diagnostics']['suitability']
    }
    
    if save_results and output_dir:
        os.makedirs(output_dir, exist_ok=True)
        pd.DataFrame([anova_summary]).to_csv(os.path.join(output_dir, 'anova_summary.csv'), index=False)
    
    return anova_summary

def test_statistical_assumptions(
    data: pd.DataFrame,
    dependent_var: str,
    independent_vars: list[str],
    save_results: bool = False,
    output_dir: str = None,
    t: dict = None
) -> tuple[dict, list[str]]:
    """
    Test regression assumptions: autocorrelation, homoscedasticity, normality, multicollinearity.
    
    Parameters:
    - data: DataFrame with regression data.
    - dependent_var: Name of the dependent variable.
    - independent_vars: list of independent variable names.
    - save_results: If True, save results and residual plot to output_dir (default False).
    - output_dir: Directory to save results if save_results is True.
    
    Returns:
    - assumption_results: dictionary with test results.
    - assumption_comments: list of evaluation comments.
    """
    t_dict = get_t_dict(t)
    # Durbin-Watson Test
    dw_results = durbin_watson_test(data, dependent_var, independent_vars)
    dw_stat = dw_results['DW_statistic']
    dw_status = dw_results['diagnostics']['status']
    
    # Homoscedasticity and Normality Tests
    homo_results = homoscedasticity_test(data, dependent_var, independent_vars)
    jb_p_value = homo_results['results']['Jarque-Bera']['p_value']
    bp_p_value = homo_results['results']['Breusch-Pagan']['p_value']
    homo_status = t_dict["homoscedastic"] if bp_p_value > 0.05 else t_dict["heteroscedastic"]
    normality_status = t_dict["normal"] if jb_p_value > 0.05 else t_dict["non_normal"]
    
    # VIF for multicollinearity
    vif_results = variance_inflation_factor_test(data, independent_vars)
    vif_issues = [row['Variable'] for _, row in vif_results['results'].iterrows() if row['VIF'] > 5]
    
    # Residual Plot
    model = sm.OLS(data[dependent_var], sm.add_constant(data[independent_vars])).fit()
    residuals = model.resid
    fitted = model.fittedvalues
    
    if save_results and output_dir:
        os.makedirs(output_dir, exist_ok=True)
        plt.figure(figsize=(4, 3))
        sns.scatterplot(x=fitted, y=residuals)
        plt.axhline(0, color='red', linestyle='--')
        plt.xlabel('Fitted Values')
        plt.ylabel('Residuals')
        plt.title('Residual Plot for Homoscedasticity Check')
        plt.savefig(os.path.join(output_dir, 'residual_plot.png'))
        plt.close()
    
    # Compile results
    assumption_results = {
        'Durbin-Watson': {'Statistic': dw_stat, 'Status': dw_status},
        'Homoscedasticity': {'Breusch-Pagan p-value': bp_p_value, 'Status': homo_status},
        'Normality': {'Jarque-Bera p-value': jb_p_value, 'Status': normality_status},
        'Multicollinearity': {'Issues': vif_issues}
    }
    
    # Compile comments
    assumption_comments = [
        f"Durbin-Watson: {dw_stat:.3f} ({dw_status})",
        t_dict["no_autocorr_detected"] if 1.5 <= dw_stat <= 2.5 else t_dict["potential_autocorr_detected"],
        f"Breusch-Pagan p-value: {bp_p_value:.3f} ({homo_status})",
        f"Jarque-Bera p-value: {jb_p_value:.3f} ({normality_status})",
        t_dict["residuals_ok"] if bp_p_value > 0.05 and jb_p_value > 0.05
        else t_dict["residuals_violate"],
        t_dict["multicollinearity_detected"].format(', '.join(vif_issues)) if vif_issues
        else t_dict["no_multicollinearity_detected"]
    ]
    
    if save_results and output_dir:
        with open(os.path.join(output_dir, 'assumption_tests.json'), 'w') as f:
            json.dump(assumption_results, f, indent=2)
    
    return assumption_results, assumption_comments

def save_outputs_2(
    corr_table: pd.DataFrame,
    model_summary: dict,
    coeff_table: pd.DataFrame,
    anova_summary: dict,
    assumption_results: dict,
    output_dir: str
) -> None:
    """
    Save all regression analysis outputs to the specified directory.
    
    Parameters:
    - corr_table: Correlation matrix table.
    - model_summary: Model fit summary.
    - coeff_table: Coefficients table.
    - anova_summary: ANOVA F-test summary.
    - assumption_results: Assumption test results.
    - output_dir: Directory to save all files.
    """
    os.makedirs(output_dir, exist_ok=True)
    
    corr_table.to_csv(os.path.join(output_dir, 'correlation_matrix.csv'), index=False)
    pd.DataFrame([model_summary]).to_csv(os.path.join(output_dir, 'model_summary.csv'), index=False)
    coeff_table.to_csv(os.path.join(output_dir, 'coefficients_table.csv'), index=False)
    pd.DataFrame([anova_summary]).to_csv(os.path.join(output_dir, 'anova_summary.csv'), index=False)
    with open(os.path.join(output_dir, 'assumption_tests.json'), 'w') as f:
        json.dump(assumption_results, f, indent=2)
    print(f"All regression results saved to '{output_dir}'")




#---------------------------------------------#
# Phần 2.1: Reliability Analysis for Dependent Variable (GK)
#---------------------------------------------#

def compute_item_total_statistics(data: pd.DataFrame) -> dict:
    """
    Computes Item-Total Statistics for a given DataFrame.

    Parameters:
    - data: DataFrame with numerical columns (items).

    Returns:
    - item_stats: dict with Scale Mean if Item Deleted, Scale Variance if Item Deleted,
                  Corrected Item-Total Correlation, and Cronbach's Alpha if Item Deleted.
    """
    item_stats = {}
    variables = data.columns
    n_items = len(variables)

    # Overall Cronbach's Alpha
    try:
        _, _, item_total_corr, _ = cronbach_alpha_analysis(data)
    except Exception:
        return {}

    for var in variables:
        # Compute sum of all items excluding the current one
        other_items = [v for v in variables if v != var]
        scale_sum = data[other_items].sum(axis=1)

        # Scale Mean if Item Deleted
        scale_mean = scale_sum.mean()

        # Scale Variance if Item Deleted
        scale_variance = scale_sum.var(ddof=1)

        # Cronbach's Alpha if Item Deleted
        reduced_data = data[other_items]
        try:
            alpha_if_deleted, _, _, _ = cronbach_alpha_analysis(reduced_data)
        except Exception:
            alpha_if_deleted = None

        # Store results
        item_stats[var] = {
            'Scale Mean if Item Deleted': scale_mean,
            'Scale Variance if Item Deleted': scale_variance,
            'Corrected Item-Total Correlation': item_total_corr.get(var, None),
            'Cronbach Alpha if Item Deleted': alpha_if_deleted
        }

    return item_stats

def generate_reliability_analysis(
    data: pd.DataFrame,
    variables: list[str],
    factor_name: str,
    save_results: bool = False,
    output_dir: str = None,
    t: dict = None
) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    """
    Perform reliability analysis for a factor, generating reliability and item-total statistics tables,
    and diagnostic comments.

    Parameters:
    - data: DataFrame with survey data.
    - variables: list of variable names for the factor.
    - factor_name: Name of the factor (for naming outputs).
    - save_results: If True, save results to output_dir (default False).
    - output_dir: Directory to save results if save_results is True.

    Returns:
    - reliability_table: DataFrame with reliability statistics (Cronbach’s Alpha, N of Items).
    - item_total_table: DataFrame with item-total statistics.
    - diagnostics: dictionary with diagnostic results and comments.
    """
    t_dict = get_t_dict(t)
    
    factor_data = data[variables]

    # Cronbach's Alpha Analysis
    try:
        alpha, ci, item_total_corr, alpha_diagnostics = cronbach_alpha_analysis(factor_data)
    except Exception:
        alpha, ci, item_total_corr, alpha_diagnostics = None, None, {}, {}

    reliability_stats = {
        t_dict['cronbach_alpha']: f"{alpha:.3f}" if alpha is not None else "N/A",
        t_dict.get('num_items', 'N of Items'): len(variables)
    }
    reliability_table = pd.DataFrame([reliability_stats])

    # Item-Total Statistics Table
    item_stats = compute_item_total_statistics(factor_data)
    item_total_table_data = []
    for var in variables:
        stats = item_stats.get(var, {})
        item_total_table_data.append({
            t_dict['item']: var,
            t_dict['scale_mean_if_deleted']: f"{stats.get('Scale Mean if Item Deleted', float('nan')):.3f}",
            t_dict['scale_variance_if_deleted']: f"{stats.get('Scale Variance if Item Deleted', float('nan')):.3f}",
            t_dict['corrected_item_total_corr']: f"{stats.get('Corrected Item-Total Correlation', float('nan')):.3f}",
            t_dict['alpha_if_deleted']: f"{stats.get('Cronbach Alpha if Item Deleted', float('nan')):.3f}"
        })
    item_total_table = pd.DataFrame(item_total_table_data)

    # Generate Diagnostic Comments
    reliability_comments = []
    if alpha is not None:
        alpha_diag = get_diagnostic_criteria(
            analysis_type="cronbach_alpha",
            metric_value=alpha,
            additional_data={"item_total_corr": [k for k, v in item_total_corr.items() if abs(v) < 0.3]}
        )
        reliability_comments.append(f"Cronbach’s Alpha = {alpha:.3f} ({alpha_diag['status']})")
        reliability_comments.append(
            t_dict['scale_reliable'] if alpha >= 0.7
            else t_dict['scale_unreliable']
        )
        if alpha < 0.7:
            reliability_comments.extend(alpha_diag.get('warnings', []))
    else:
        reliability_comments.append(t_dict['alpha_not_computed'])

    # Item-Specific Comments
    item_comments = {}
    for var in variables:
        stats = item_stats.get(var, {})
        corr = stats.get('Corrected Item-Total Correlation', None)
        alpha_if_deleted = stats.get('Cronbach Alpha if Item Deleted', None)

        corr_value = f"{corr:.3f}" if corr is not None else "N/A"
        item_comment = [f"Item {var}: Corrected Item-Total Correlation = {corr_value}"]
        if corr is not None:
            corr_diag = get_diagnostic_criteria(
                analysis_type="item_total_correlation",
                metric_value=corr
            )
            item_comment.append(f"Status: {corr_diag['status']}")
            item_comment.append(
                "Item contributes adequately to the scale (Correlation ≥ 0.3)." if corr >= 0.3
                else "Item has low correlation with the scale (Correlation < 0.3). Consider removal."
            )
            if corr < 0.3:
                item_comment.extend(corr_diag.get('warnings', []))
        
        if alpha is not None and alpha_if_deleted is not None:
            item_comment.append(
                f"Removing {var} increases Cronbach’s Alpha to {alpha_if_deleted:.3f}, suggesting potential removal."
                if alpha_if_deleted > alpha
                else f"Removing {var} does not improve Cronbach’s Alpha (remains or decreases to {alpha_if_deleted:.3f})."
            )

        item_comments[var] = item_comment

    # Compile Diagnostics
    diagnostics = {
        'Overall_Scale': {
            'Cronbach_Alpha': alpha if alpha is not None else 'N/A',
            'CI_95': ci if ci is not None else 'N/A',
            'Diagnostics': alpha_diag if alpha is not None else {},
            'Comments': reliability_comments
        },
        'Item_Total_Statistics': {
            var: {
                'Stats': item_stats.get(var, {}),
                'Diagnostics': get_diagnostic_criteria(
                    analysis_type="item_total_correlation",
                    metric_value=item_stats.get(var, {}).get('Corrected Item-Total Correlation', float('nan'))
                ) if item_stats.get(var, {}).get('Corrected Item-Total Correlation') is not None else {},
                'Comments': comments
            } for var, comments in item_comments.items()
        }
    }

    # Optional Saving
    if save_results and output_dir:
        os.makedirs(output_dir, exist_ok=True)
        reliability_table.to_csv(os.path.join(output_dir, f'reliability_statistics_{factor_name}.csv'), index=False)
        item_total_table.to_csv(os.path.join(output_dir, f'item_total_statistics_{factor_name}.csv'), index=False)
        with open(os.path.join(output_dir, f'reliability_diagnostics_{factor_name}.json'), 'w') as f:
            json.dump(prepare_for_json(diagnostics), f, indent=2)

    return reliability_table, item_total_table, diagnostics




########### 2: Phân tích nhân tố ############

def select_factor_analysis_data(data: pd.DataFrame, factor_groups: dict[str, list[str]]) -> pd.DataFrame:
    """
    Select variables for factor analysis, excluding 'GK'.
    
    Parameters:
    - data: DataFrame containing all variables.
    - factor_groups: dictionary mapping factor prefixes to variable lists.
    
    Returns:
    - fa_data: DataFrame with selected variables.
    """
    fa_variables = [var for factor in ['DK', 'YN', 'PT', 'DN', 'LI', 'CB'] for var in factor_groups[factor]]
    return data[fa_variables]

def perform_kmo_and_bartlett_tests(
    data: pd.DataFrame,
    save_results: bool = False,
    output_dir: str = None,
    results_filename: str = 'kmo_bartlett_results.csv',
    comments_filename: str = 'kmo_bartlett_comments.txt',
    t: dict = None
) -> tuple[dict, list[str]]:
    """
    Perform KMO and Bartlett's Sphericity tests and generate comments.
    
    Parameters:
    - data: DataFrame with variables for factor analysis.
    - save_results: If True, save results to output_dir (default False).
    - output_dir: Directory to save results if save_results is True.
    - results_filename: Filename for the KMO and Bartlett's test results CSV (default 'kmo_bartlett_results.csv').
    - comments_filename: Filename for the KMO and Bartlett's comments text file (default 'kmo_bartlett_comments.txt').
    
    Returns:
    - kmo_bartlett_table: dictionary for KMO and Bartlett's test results.
    - comments: list of comments for KMO and Bartlett's tests.
    """
    t_dict = get_t_dict(t)
    kmo_total, kmo_diagnostics = kmo_test(data, t=t_dict)
    chi_square, p_value, bartlett_diagnostics = bartlett_sphericity_test(data, t=t_dict)
    
    # KMO Comments
    kmo_status = kmo_diagnostics['kmo_status']
    comments = [
        t_dict['kmo_result'].format(kmo_total, kmo_status, 
                                    t_dict['kmo_suitable'] if kmo_total >= 0.7 else t_dict['kmo_partially_suitable'] if kmo_total >= 0.5 else t_dict['kmo_unsuitable'])
    ]
    low_kmo_vars = [var for var, kmo in kmo_diagnostics['kmo_per_item'].items() if kmo < 0.5]
    if low_kmo_vars:
        comments.append(t_dict['low_kmo_vars'].format(', '.join(low_kmo_vars)))
    if kmo_diagnostics['warnings']:
        comments.extend([t_dict['warning'].format(w) for w in kmo_diagnostics['warnings']])
    
    # Bartlett's Test Comments
    bartlett_comments = [
        t_dict['bartlett_result'].format(chi_square, p_value, bartlett_diagnostics['p_value_status'],
                                          t_dict['bartlett_suitable'] if p_value < 0.05 else t_dict['bartlett_unsuitable'])
    ]
    if bartlett_diagnostics['warnings']:
        bartlett_comments.extend([t_dict['warning'].format(w) for w in bartlett_diagnostics['warnings']])
    comments.extend(bartlett_comments)
    
    # KMO and Bartlett's Table
    kmo_bartlett_table = {
        t_dict.get('kmo_measure', t_dict.get('kmo_per_item_label', 'KMO')): f"{kmo_total:.3f}",
        t_dict.get('bartlett_chi', "Bartlett's Test of Sphericity - Approx. Chi-Square"): f"{chi_square:.3f}",
        t_dict.get('bartlett_df', "Bartlett's Test of Sphericity - df"): int((data.shape[1] * (data.shape[1] - 1)) / 2),
        t_dict.get('bartlett_sig', "Bartlett's Test of Sphericity - Sig."): f"{p_value:.3f}"
    }
    
    # Optional Saving
    if save_results and output_dir:
        os.makedirs(output_dir, exist_ok=True)
        # Save table results
        kmo_bartlett_df = pd.DataFrame([kmo_bartlett_table])
        kmo_bartlett_df.to_csv(os.path.join(output_dir, results_filename), index=False)
        # Save comments
        with open(os.path.join(output_dir, comments_filename), 'w', encoding='utf-8') as f:
            for comment in comments:
                f.write(comment + '\n')
    
    return kmo_bartlett_table, comments

def determine_factors(
    data: pd.DataFrame,
    save_results: bool = False,
    output_dir: str = None,
    eigenvalues_filename: str = 'eigenvalues.csv',
    comments_filename: str = 'variance_comments.txt',
    t: dict = None
) -> tuple[int, pd.DataFrame, list[str], str]:
    """
    Determine the number of factors and generate variance explained comments, returning scree plot as base64.

    Parameters:
    - data: DataFrame with variables for factor analysis.
    - save_results: If True, save results to output_dir (default False).
    - output_dir: Directory to save results if save_results is True.
    - eigenvalues_filename: Filename for the eigenvalues CSV (default 'eigenvalues.csv').
    - comments_filename: Filename for the variance comments text file (default 'variance_comments.txt').

    Returns:
    - n_factors: Number of factors determined.
    - eigenvalues_df: DataFrame with eigenvalues.
    - comments: list of comments for variance explained.
    - scree_plot_base64: Base64-encoded string of the scree plot image.
    """
    t_dict = get_t_dict(t)
    n_factors, eigenvalues_df, factor_diagnostics = determine_number_of_factors(
        data,
        plot_scree=False,  # We'll handle the plot ourselves
        save_path=None,
        t=t_dict
    )

    total_variance = factor_diagnostics['total_variance_explained']
    variance_status = factor_diagnostics['variance_status']
    
    # Map variance status to translation
    status_map = {
        "Very good": t_dict["variance_status_very_good"],
        "Good": t_dict["variance_status_good"],
        "Acceptable": t_dict["variance_status_acceptable"],
        "Insufficient": t_dict["variance_status_insufficient"],
        "Rất tốt": t_dict["variance_status_very_good"],
        "Tốt": t_dict["variance_status_good"],
        "Chấp nhận được": t_dict["variance_status_acceptable"],
        "Không đủ": t_dict["variance_status_insufficient"]
    }
    translated_status = status_map.get(variance_status, variance_status)

    expl_msg = t_dict['variance_expl_good'] if total_variance >= 0.6 else t_dict['variance_expl_acceptable'] if total_variance >= 0.5 else t_dict['variance_expl_insufficient']

    comments = [
        t_dict['total_variance_explained_title'].format(total_variance*100, translated_status, expl_msg),
        t_dict['num_factors_selected'].format(n_factors)
    ]
    if factor_diagnostics['warnings']:
        comments.extend([t_dict['warning'].format(w) for w in factor_diagnostics['warnings']])

    # Generate scree plot and convert to base64
    plt.figure(figsize=(5, 3))  # Increased width for better label spacing
    plt.plot(range(1, len(eigenvalues_df['Eigenvalue']) + 1), eigenvalues_df['Eigenvalue'], marker='o')
    plt.title("Scree Plot")
    plt.xlabel("Component Number")
    plt.ylabel("Eigenvalue")
    plt.xticks(range(1, len(eigenvalues_df['Eigenvalue']) + 1))  # Set x-axis ticks to 1, 2, 3, ...
    plt.subplots_adjust(bottom=0.15)  # Adjust bottom margin for label spacing
    buf = io.BytesIO()
    plt.savefig(buf, format="png", dpi=300)
    buf.seek(0)
    scree_plot_base64 = base64.b64encode(buf.getvalue()).decode("utf-8")
    buf.close()
    plt.close()

    # Optional Saving
    if save_results and output_dir:
        os.makedirs(output_dir, exist_ok=True)
        # Save eigenvalues table
        eigenvalues_df.to_csv(os.path.join(output_dir, eigenvalues_filename), index=True)
        # Save comments
        with open(os.path.join(output_dir, comments_filename), 'w', encoding='utf-8') as f:
            for comment in comments:
                f.write(comment + '\n')
        # Save scree plot
        with open(os.path.join(output_dir, 'scree_plot.png'), 'wb') as f:
            f.write(base64.b64decode(scree_plot_base64))

    return n_factors, eigenvalues_df, comments, scree_plot_base64

def perform_pca_varimax(
    data: pd.DataFrame,
    n_factors: int,
    save_results: bool = False,
    output_dir: str = None,
    rotated_matrix_filename: str = 'rotated_component_matrix.csv',
    comments_filename: str = 'pca_varimax_comments.txt',
    t: dict = None
) -> tuple[pd.DataFrame, list[str], dict]:
    """
    Perform PCA with Varimax rotation and generate comments.
    
    Parameters:
    - data: DataFrame with variables for factor analysis.
    - n_factors: Number of factors to extract.
    - save_results: If True, save results to output_dir (default False).
    - output_dir: Directory to save results if save_results is True.
    - rotated_matrix_filename: Filename for the rotated component matrix CSV (default 'rotated_component_matrix.csv').
    - comments_filename: Filename for the PCA Varimax comments text file (default 'pca_varimax_comments.txt').
    
    Returns:
    - loadings: DataFrame with rotated loadings.
    - comments: list of comments for rotated component matrix.
    - pca_diagnostics: dictionary with PCA diagnostics.
    """
    t_dict = get_t_dict(t)
    loadings, pca_diagnostics = pca_varimax_analysis(data, n_factors, t=t_dict)
    
    comments = [
        t_dict['rotated_component_matrix_title']
    ]
    high_loadings = pca_diagnostics['high_loadings']
    for factor, count in high_loadings.items():
        comments.append(t_dict['factor_has_loadings'].format(factor, count))
    low_loading_vars = [var for var in data.columns if (abs(loadings.loc[var]) < 0.4).all()]
    if low_loading_vars:
        comments.append(t_dict['low_loading_vars'].format(', '.join(low_loading_vars)))
    cross_loading_vars = [var for var in data.columns if (abs(loadings.loc[var]) > 0.4).sum() > 1]
    if cross_loading_vars:
        comments.append(t_dict['cross_loading_vars'].format(', '.join(cross_loading_vars)))
    
    # Optional Saving
    if save_results and output_dir:
        os.makedirs(output_dir, exist_ok=True)
        # Save rotated component matrix
        rotated_matrix = loadings.round(3)
        rotated_matrix.index.name = 'Variable'
        rotated_matrix.to_csv(os.path.join(output_dir, rotated_matrix_filename), index=True)
        # Save comments
        with open(os.path.join(output_dir, comments_filename), 'w', encoding='utf-8') as f:
            for comment in comments:
                f.write(comment + '\n')
    
    return loadings, comments, pca_diagnostics

def generate_variance_table(
    eigenvalues_df: pd.DataFrame,
    n_factors: int = None,
    pca_diagnostics: dict = None,
    full_table: bool = False
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Generate variance explained tables for EFA.

    Parameters:
    - eigenvalues_df: DataFrame with eigenvalues and cumulative variance.
    - n_factors: Number of factors to extract.
    - pca_diagnostics: dictionary with PCA diagnostics.
    - full_table: If True, include all components; otherwise, include only extracted factors.

    Returns:
    - variance_table: DataFrame with variance explained for extracted factors.
    - full_variance_table: DataFrame with variance for all components.
    """
    max_factors = len(eigenvalues_df)
    variance_table_data = []
    full_variance_table_data = []

    # Total variance from eigenvalues
    total_variance = eigenvalues_df['Eigenvalue'].sum()

    def compute_row(i, is_full=False, extracted=False):
        initial_eigenvalue = float(eigenvalues_df['Eigenvalue'].iloc[i])  # Ensure float
        initial_variance = (initial_eigenvalue / total_variance) * 100
        initial_cumulative = float(eigenvalues_df['Cumulative Variance'].iloc[i]) * 100  # Ensure float

        row = {
            'Component': f"Component {i+1}",
            'Initial Eigenvalues - Total': initial_eigenvalue,
            'Initial Eigenvalues - % of Variance': initial_variance,
            'Initial Eigenvalues - Cumulative %': initial_cumulative,
            'Extraction Sums of Squared Loadings - Total': initial_eigenvalue if extracted else np.nan,
            'Extraction Sums of Squared Loadings - % of Variance': initial_variance if extracted else np.nan,
            'Extraction Sums of Squared Loadings - Cumulative %': initial_cumulative if extracted else np.nan
        }

        if pca_diagnostics and not is_full and extracted:
            proportion = pca_diagnostics['variance_per_factor'][i]
            rotation_total = proportion * total_variance  # Sum of squared rotated loadings
            rotation_variance = proportion * 100          # % of variance
            rotation_cumulative = sum(pca_diagnostics['variance_per_factor'][:i+1]) * 100
            row.update({
                'Rotation Sums of Squared Loadings - Total': rotation_total,
                'Rotation Sums of Squared Loadings - % of Variance': rotation_variance,
                'Rotation Sums of Squared Loadings - Cumulative %': rotation_cumulative
            })
        else:
            row.update({
                'Rotation Sums of Squared Loadings - Total': np.nan,
                'Rotation Sums of Squared Loadings - % of Variance': np.nan,
                'Rotation Sums of Squared Loadings - Cumulative %': np.nan
            })

        return row

    # Generate rows for extracted factors
    if n_factors is not None:
        if pca_diagnostics is None:
            raise ValueError("pca_diagnostics must be provided when n_factors is specified.")
        for i in range(min(n_factors, max_factors)):
            variance_table_data.append(compute_row(i, extracted=True))

    # Generate rows for full table
    if full_table or n_factors is None:
        for i in range(max_factors):
            extracted = i < n_factors if n_factors is not None else False
            full_variance_table_data.append(compute_row(i, is_full=True, extracted=extracted))

    # Create DataFrames
    variance_table = pd.DataFrame(variance_table_data) if variance_table_data else pd.DataFrame()
    full_variance_table = pd.DataFrame(full_variance_table_data) if full_variance_table_data else pd.DataFrame()

    # Ensure numeric columns are float
    numeric_columns = [
        'Initial Eigenvalues - Total',
        'Initial Eigenvalues - % of Variance',
        'Initial Eigenvalues - Cumulative %',
        'Extraction Sums of Squared Loadings - Total',
        'Extraction Sums of Squared Loadings - % of Variance',
        'Extraction Sums of Squared Loadings - Cumulative %',
        'Rotation Sums of Squared Loadings - Total',
        'Rotation Sums of Squared Loadings - % of Variance',
        'Rotation Sums of Squared Loadings - Cumulative %'
    ]
    for col in numeric_columns:
        if col in variance_table.columns:
            variance_table[col] = pd.to_numeric(variance_table[col], errors='coerce')
        if col in full_variance_table.columns:
            full_variance_table[col] = pd.to_numeric(full_variance_table[col], errors='coerce')

    # # Debugging: Inspect the variance_table
    # print("Debugging variance_table:")
    # print(variance_table)
    # print("Column dtypes:")
    # print(variance_table.dtypes)

    return variance_table, full_variance_table


def validate_inputs(data: pd.DataFrame, dependent_var: str, independent_vars: list[str]) -> None:
    """Validate that variables exist in DataFrame and data has no missing values."""
    if dependent_var not in data.columns or not all(var in data.columns for var in independent_vars):
        raise ValueError("Specified variables not found in DataFrame.")
    if data[dependent_var].isnull().any() or data[independent_vars].isnull().any().any():
        raise ValueError("Data contains missing values.")

# Helper functions for generating notes
def get_model_summary_notes(dependent_var: str, independent_vars: list[str], t: dict = None) -> list[str]:
    """Generate notes for model summary (no-intercept)."""
    t_dict = get_t_dict(t)
    return [
        t_dict['model_summary_predictors'].format(', '.join(independent_vars)),
        t_dict['no_intercept_note'],
        t_dict['r_square_measure_note'],
        t_dict['r_square_compare_note'],
        t_dict['dependent_variable_note'].format(dependent_var),
        t_dict['no_intercept_model_note']
    ]

def get_anova_no_intercept_notes(dependent_var: str, independent_vars: list[str], t: dict = None) -> list[str]:
    """Generate notes for ANOVA table (no-intercept)."""
    t_dict = get_t_dict(t)
    return [
        t_dict['anova_title'],
        t_dict['dependent_variable_note'].format(dependent_var),
        t_dict['no_intercept_model_note'],
        t_dict['model_summary_predictors'].format(', '.join(independent_vars)),
        t_dict['no_intercept_total_ss_note']
    ]

def get_anova_with_intercept_notes(dependent_var: str, independent_vars: list[str], t: dict = None) -> list[str]:
    """Generate base notes for ANOVA table (with-intercept)."""
    t_dict = get_t_dict(t)
    return [
        t_dict['anova_with_intercept_title'],
        t_dict['dependent_variable_note'].format(dependent_var),
        t_dict['with_intercept_model_note'],
        t_dict['with_intercept_predictors_note'].format(', '.join(independent_vars))
    ]

def compute_r_no_intercept(data: pd.DataFrame, dependent_var: str, independent_vars: list[str]) -> float:
    """
    Compute the correlation coefficient R for a no-intercept regression model.
    
    Parameters:
    - data: DataFrame with dependent and independent variables.
    - dependent_var: Name of the dependent variable.
    - independent_vars: list of independent variable names.
    
    Returns:
    - R coefficient (float) or np.nan if invalid.
    """
    validate_inputs(data, dependent_var, independent_vars)
    y = data[dependent_var]
    X = data[independent_vars]
    model = sm.OLS(y, X).fit()
    y_pred = model.fittedvalues
    ssr = np.sum(y_pred ** 2)
    sst = np.sum(y ** 2)
    return np.sqrt(ssr / sst) if sst > 0 else np.nan

def generate_model_summary_no_intercept(
    data: pd.DataFrame,
    dependent_var: str,
    independent_vars: list[str],
    output_dir: str = None,
    save_results: bool = False,
    t: dict = None
) -> tuple[pd.DataFrame, list[str]]:
    """
    Generate the Model Summary table for a no-intercept regression model.
    
    Parameters:
    - data: DataFrame with dependent and independent variables.
    - dependent_var: Name of the dependent variable.
    - independent_vars: list of independent variable names.
    - output_dir: Directory to save results if save_results is True.
    - save_results: If True, save table and notes to files (default False).
    
    Returns:
    - model_summary_df: DataFrame with model summary metrics.
    - notes: list of notes for the model summary.
    """
    validate_inputs(data, dependent_var, independent_vars)
    
    # Compute regression metrics
    _, _, diagnostics = multivariate_regression_analysis_no_intercept(data, dependent_var, independent_vars)
    fit_results = evaluate_regression_fit_no_intercept(data, dependent_var, independent_vars)
    dw_results = durbin_watson_test(data, dependent_var, independent_vars)
    r = compute_r_no_intercept(data, dependent_var, independent_vars)
    
    t_dict = get_t_dict(t)
    # Model summary data
    model_summary = {
        t_dict['model']: '1',
        'R': f"{r:.3f}",
        t_dict['r_square']: f"{diagnostics['R-squared']:.3f}",
        t_dict['adj_r_square']: f"{diagnostics['Adjusted R-squared']:.3f}",
        t_dict['std_error_estimate']: f"{fit_results['SSE'] / (fit_results['diagnostics']['sample_size'] - len(independent_vars)):.8f}",
        'Durbin-Watson': f"{dw_results['DW_statistic']:.3f}"
    }
    
    # Create DataFrame
    model_summary_df = pd.DataFrame([model_summary])
    
    # Generate notes
    notes = get_model_summary_notes(dependent_var, independent_vars, t=t_dict)
    
    # Save results if requested
    if save_results and output_dir:
        os.makedirs(output_dir, exist_ok=True)
        model_summary_df.to_csv(os.path.join(output_dir, 'model_summary_no_intercept.csv'), index=False)
        with open(os.path.join(output_dir, 'model_summary_no_intercept_notes.txt'), 'w') as f:
            f.write("\n".join(notes))
    
    return model_summary_df, notes

# Nonparametric Correlations
def generate_spearman_rho_table(
    data: pd.DataFrame,
    dependent_var: str,
    independent_vars: list[str],
    output_dir: str = None,
    save_results: bool = False,
    t: dict = None
) -> tuple[pd.DataFrame, list[str]]:
    """
    Generate Spearman's rho correlation table between squared residuals and independent variables.
    
    Parameters:
    - data: DataFrame with dependent and independent variables.
    - dependent_var: Name of the dependent variable.
    - independent_vars: list of independent variable names.
    - output_dir: Directory to save results if save_results is True.
    - save_results: If True, save table and comments to files (default False).
    
    Returns:
    - spearman_df: DataFrame with Spearman's rho correlations in SPSS-like format without 'Spearman's rho' level.
    - comments: list of comments on significant correlations.
    """
    validate_inputs(data, dependent_var, independent_vars)
    
    # Fit with-intercept model to get residuals
    y = data[dependent_var]
    X = data[independent_vars]
    X_sm = sm.add_constant(X)
    model = sm.OLS(y, X_sm).fit()
    squared_residuals = model.resid ** 2
    
    # Variables for correlation (ABSRES + independent_vars)
    vars = ['ABSRES'] + independent_vars
    n_vars = len(vars)
    n = len(y)
    
    # Initialize matrices
    corr_matrix = np.zeros((n_vars, n_vars))
    pval_matrix = np.zeros((n_vars, n_vars))
    n_matrix = np.full((n_vars, n_vars), n)
    
    # Compute Spearman's rho
    for i, var1 in enumerate(vars):
        for j, var2 in enumerate(vars):
            if i == j:
                corr_matrix[i, j] = 1.0
                pval_matrix[i, j] = np.nan
            else:
                x1 = squared_residuals if var1 == 'ABSRES' else data[var1]
                x2 = squared_residuals if var2 == 'ABSRES' else data[var2]
                rho, pval = spearmanr(x1, x2)
                corr_matrix[i, j] = rho
                pval_matrix[i, j] = pval
    
    t_dict = get_t_dict(t)
    # Create a MultiIndex for rows (Variable, Metric)
    index = pd.MultiIndex.from_tuples(
        [
            (var, metric)
            for var in vars
            for metric in [t_dict['correlation_coefficient'], t_dict['sig_2_tailed'], 'N']
        ],
        names=[t_dict['variable_label'], t_dict['metric_label']]
    )
    
    # Create DataFrame with variables as columns
    spearman_data = {}
    for col_var in vars:
        col_data = []
        for row_var in vars:
            i, j = vars.index(row_var), vars.index(col_var)
            # Correlation Coefficient
            corr = corr_matrix[i, j]
            col_data.append(f"{corr:.3f}" if not np.isnan(corr) else "1.000")
            # Sig. (2-tailed)
            pval = pval_matrix[i, j]
            col_data.append(f"{pval:.3f}" if not np.isnan(pval) else ".")
            # N
            n_val = n_matrix[i, j]
            col_data.append(int(n_val))
        spearman_data[col_var] = col_data
    
    spearman_df = pd.DataFrame(spearman_data, index=index)
    
    # Generate comments
    comments = [
        t_dict['spearman_rho_significant'].format(corr_matrix[0, vars.index(var)], pval_matrix[0, vars.index(var)], var)
        for var in independent_vars
        if pval_matrix[0, vars.index(var)] < 0.05
    ] or [t_dict['spearman_rho_none']]
    
    # Save results if requested
    if save_results and output_dir:
        os.makedirs(output_dir, exist_ok=True)
        spearman_df.to_csv(os.path.join(output_dir, 'spearman_rho_correlations.csv'))
        with open(os.path.join(output_dir, 'spearman_rho_comments.txt'), 'w') as f:
            f.write("\n".join(comments))
    
    return spearman_df, comments

def generate_anova_table_no_intercept(
    data: pd.DataFrame,
    dependent_var: str,
    independent_vars: list[str],
    output_dir: str = None,
    save_results: bool = False
) -> tuple[pd.DataFrame, list[str]]:
    """
    Generate the ANOVA table for a no-intercept regression model (ANOVA(a,b)).
    
    Parameters:
    - data: DataFrame with dependent and independent variables.
    - dependent_var: Name of the dependent variable.
    - independent_vars: list of independent variable names.
    - output_dir: Directory to save results if save_results is True.
    - save_results: If True, save table and notes to files (default False).
    
    Returns:
    - anova_df: DataFrame with ANOVA table.
    - notes: list of notes for the ANOVA table.
    """
    validate_inputs(data, dependent_var, independent_vars)
    
    # Compute regression fit
    fit_results = evaluate_regression_fit_no_intercept(data, dependent_var, independent_vars)
    n = fit_results['diagnostics']['sample_size']
    k = len(independent_vars)
    
    # Fit model to get F-statistic and p-value
    y = data[dependent_var]
    X = data[independent_vars]
    model = sm.OLS(y, X).fit()
    
    # ANOVA data
    anova_data = [
        {
            'Model': '1',
            'Source': 'Regression',
            'Sum of Squares': f"{fit_results['SSR']:.3f}",
            'df': k,
            'Mean Square': f"{fit_results['SSR'] / k:.3f}",
            'F': f"{model.fvalue:.3f}",
            'Sig.': f"{model.f_pvalue:.3f}"
        },
        {
            'Model': '1',
            'Source': 'Residual',
            'Sum of Squares': f"{fit_results['SSE']:.3f}",
            'df': n - k,
            'Mean Square': f"{fit_results['SSE'] / (n - k):.3f}",
            'F': '',
            'Sig.': ''
        },
        {
            'Model': '1',
            'Source': 'Total',
            'Sum of Squares': f"{fit_results['SST']:.3f}",
            'df': n,
            'Mean Square': '',
            'F': '',
            'Sig.': ''
        }
    ]
    
    # Create DataFrame
    anova_df = pd.DataFrame(anova_data)
    
    # Generate notes
    notes = get_anova_no_intercept_notes(dependent_var, independent_vars)
    
    # Save results if requested
    if save_results and output_dir:
        os.makedirs(output_dir, exist_ok=True)
        anova_df.to_csv(os.path.join(output_dir, 'anova_no_intercept.csv'), index=False)
        with open(os.path.join(output_dir, 'anova_no_intercept_notes.txt'), 'w') as f:
            f.write("\n".join(notes))
    
    return anova_df, notes

def generate_anova_table_with_intercept(
    data: pd.DataFrame,
    dependent_var: str,
    independent_vars: list[str],
    output_dir: str = None,
    save_results: bool = False
) -> tuple[pd.DataFrame, list[str]]:
    """
    Generate the ANOVA table for a regression model with intercept (ANOVA(a)).
    
    Parameters:
    - data: DataFrame with dependent and independent variables.
    - dependent_var: Name of the dependent variable.
    - independent_vars: list of independent variable names.
    - output_dir: Directory to save results if save_results is True.
    - save_results: If True, save table and notes to files (default False).
    
    Returns:
    - anova_df: DataFrame with ANOVA table.
    - notes: list of base notes for the ANOVA table (Spearman's rho comments to be appended outside).
    """
    validate_inputs(data, dependent_var, independent_vars)
    
    # Extract data
    y = data[dependent_var]
    X = data[independent_vars]
    n = len(y)
    k = len(independent_vars)
    
    # Fit model with intercept
    X_sm = sm.add_constant(X)
    model = sm.OLS(y, X_sm).fit()
    
    # Compute Sum of Squares
    y_pred = model.fittedvalues
    y_mean = np.mean(y)
    sst = np.sum((y - y_mean) ** 2)
    ssr = np.sum((y_pred - y_mean) ** 2)
    sse = np.sum((y - y_pred) ** 2)
    
    # ANOVA data
    anova_data = [
        {
            'Model': '1',
            'Source': 'Regression',
            'Sum of Squares': f"{ssr:.3f}",
            'df': k,
            'Mean Square': f"{ssr / k:.3f}",
            'F': f"{model.fvalue:.3f}",
            'Sig.': f"{model.f_pvalue:.3f}"
        },
        {
            'Model': '1',
            'Source': 'Residual',
            'Sum of Squares': f"{sse:.3f}",
            'df': n - k - 1,
            'Mean Square': f"{sse / (n - k - 1):.3f}",
            'F': '',
            'Sig.': ''
        },
        {
            'Model': '1',
            'Source': 'Total',
            'Sum of Squares': f"{sst:.3f}",
            'df': n - 1,
            'Mean Square': '',
            'F': '',
            'Sig.': ''
        }
    ]
    
    # Create DataFrame
    anova_df = pd.DataFrame(anova_data)
    
    # Generate base notes
    notes = get_anova_with_intercept_notes(dependent_var, independent_vars)
    
    # Save results if requested
    if save_results and output_dir:
        os.makedirs(output_dir, exist_ok=True)
        anova_df.to_csv(os.path.join(output_dir, 'anova_with_intercept.csv'), index=False)
        with open(os.path.join(output_dir, 'anova_with_intercept_notes.txt'), 'w') as f:
            f.write("\n".join(notes))
    
    return anova_df, notes


#########################################################
###################### Usage ############################
#########################################################

if __name__ == "__main__":
    # Get the current directory where this Python file is located
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Join with the output folder
    output_dir = os.path.join(current_dir, "table_results")
    
    # Create output directory
    os.makedirs(output_dir, exist_ok=True)
    print(f"Output directory: {output_dir}")

    #---------------------------------------------#
    # Sample data preparation
    #---------------------------------------------#

    # Pre-defined factors and variables
    factor_names = {
        "DK": "Điều kiện làm việc (DK)",
        "YN": "Ý nghĩa công việc (YN)",
        "PT": "Sự phát triển nghề nghiệp (PT)",
        "DN": "Đồng nghiệp (DN)",
        "LI": "Lợi ích công việc đem lại (LI)",
        "CB": "Sự cân bằng giữa công việc và gia đình (CB)",
        "GK": "Sự cam kết với tổ chức (GK)"
    }

    factor_groups = {
        "DK": ["DK1", "DK2", "DK3", "DK4", "DK5"],
        "YN": ["YN1", "YN2", "YN3", "YN4", "YN5"],
        "PT": ["PT1", "PT2", "PT3", "PT4", "PT5"],
        "DN": ["DN1", "DN2", "DN3", "DN4", "DN5"],
        "LI": ["LI1", "LI2", "LI3", "LI4", "LI5"],
        "CB": ["CB1", "CB2", "CB3", "CB4", "CB5"],
        "GK": ["GK1", "GK2", "GK3", "GK4", "GK5"]
    }

    # Generate correlated fake data
    np.random.seed(42)
    n_samples = 100
    all_vars = [var for vars in factor_groups.values() for var in vars]
    data = pd.DataFrame()

    for factor, vars in factor_groups.items():
        n_vars = len(vars)
        cov_matrix = np.full((n_vars, n_vars), 0.5) + np.eye(n_vars) * 0.5
        mean = np.full(n_vars, 3.5)
        factor_data = np.random.multivariate_normal(mean, cov_matrix, n_samples)
        factor_data = np.clip(factor_data, 1, 5).round().astype(int)
        factor_data = pd.DataFrame(factor_data, columns=vars)
        data = pd.concat([data, factor_data], axis=1)

    print("Data Preview:")
    print(data.head())

    # Simulate demographic data
    demographics = pd.DataFrame({
        'Gender': np.random.choice(['Male', 'Female'], size=n_samples, p=[0.6, 0.4]),
        'Age_Group': np.random.choice(['18-25', '26-35', '36-45', '46+'], size=n_samples, p=[0.2, 0.4, 0.3, 0.1])
    })


    #########################################################
    ##### 3.3.10 Định nghĩa bảng biểu kết quả đầu ra ########
    #########################################################

    #---------------------------------------------#
    # Phần 1
    #---------------------------------------------#

    #---------------------------------------------#
    # Phần 2
    #---------------------------------------------#


    # Analyze factor groups
    table_data = []
    diagnostics_summary = {}
    for factor_code, variables in factor_groups.items():
        factor_name = factor_names[factor_code]
        rows, diagnostics = analyze_factor_group(
            data, factor_name, variables, save_results=False  # Default: no individual saving
        )
        table_data.extend(rows)
        diagnostics_summary[factor_name] = diagnostics

    # Generate demographic statistics
    demo_table = generate_demographic_statistics(demographics, save_results=False)

    # Create appendix
    appendix = create_appendix(data, all_vars, save_results=False)

    # Create table
    table = pd.DataFrame(table_data)

    # Print results
    print(f"Output directory: {output_dir}")
    print("\nTable for Article:")
    print(table.to_string(index=False))
    print(f"\nTotal Sample Size: {n_samples}")
    print("\nDemographic Statistics:")
    print(demo_table.to_string(index=False))

    # Save all outputs (optional)
    save_outputs_1(table, demo_table, appendix, diagnostics_summary, data, demographics, output_dir)
    print(f"All results saved to '{output_dir}'")

    #---------------------------------------------#
    # Phần 3: Kết quả hồi quy
    #---------------------------------------------#



    #------------------------------------------#

    # Compute factor scores (means) for dependent and independent variables
    data['GK_mean'] = data[['GK1', 'GK2', 'GK3', 'GK4', 'GK5']].mean(axis=1)
    data['DK_mean'] = data[['DK1', 'DK2', 'DK3', 'DK4', 'DK5']].mean(axis=1)
    data['YN_mean'] = data[['YN1', 'YN2', 'YN3', 'YN4', 'YN5']].mean(axis=1)
    data['PT_mean'] = data[['PT1', 'PT2', 'PT3', 'PT4', 'PT5']].mean(axis=1)
    data['DN_mean'] = data[['DN1', 'DN2', 'DN3', 'DN4', 'DN5']].mean(axis=1)
    data['LI_mean'] = data[['LI1', 'LI2', 'LI3', 'LI4', 'LI5']].mean(axis=1)
    data['CB_mean'] = data[['CB1', 'CB2', 'CB3', 'CB4', 'CB5']].mean(axis=1)

    # Define independent and dependent variables
    indep_vars = ['DK_mean', 'YN_mean', 'PT_mean', 'DN_mean', 'LI_mean', 'CB_mean']
    dep_var = 'GK_mean'

    # Subset data for regression
    reg_data = data[[dep_var] + indep_vars]

    print("Regression Data Preview:")
    print(reg_data.head())
        
    # Perform analyses
    corr_table, corr_matrix, corr_comments = compute_pearson_correlations(
        reg_data, [dep_var] + indep_vars, save_results=True, output_dir=output_dir
    )
    model_summary = evaluate_model_fit(reg_data, dep_var, indep_vars, save_results=False)
    coeff_table = compute_coefficients_table(reg_data, dep_var, indep_vars, save_results=False)
    anova_summary = perform_anova_f_test(reg_data, dep_var, indep_vars, save_results=False)
    assumption_results, assumption_comments = test_statistical_assumptions(
        reg_data, dep_var, indep_vars, save_results=False
    )

    # Print results
    print("Regression Data Preview:")
    print(reg_data.head())
    print("\nCorrelation Matrix (Upper Triangle):")
    print(corr_table.to_string(index=False))
    print("\nCorrelation Comments:")
    for comment in corr_comments:
        print(f"- {comment}")
    print("\nModel Summary:")
    print(pd.DataFrame([model_summary]).to_string(index=False))
    print("\nCoefficients Table:")
    print(coeff_table.to_string(index=False))
    print("\nANOVA Summary:")
    print(pd.DataFrame([anova_summary]).to_string(index=False))
    print("\nAssumption Test Evaluation:")
    for comment in assumption_comments:
        print(f"- {comment}")

    # Save all outputs
    save_outputs_2(corr_table, model_summary, coeff_table, anova_summary, assumption_results, output_dir)
    #------------------------------------------#



    #---------------------------------------------#
    # Phần 2.1: Reliability Analysis for Dependent Variable (GK)
    #---------------------------------------------#


    # Reliability Analysis for GK
    gk_variables = factor_groups['GK']
    factor_name = factor_names['GK']  # "Sự cam kết với tổ chức"

    reliability_table, item_total_table, diagnostics = generate_reliability_analysis(
        data, gk_variables, factor_name, save_results=True, output_dir=output_dir
    )

    # Print Results
    print(f"\nReliability Statistics for {factor_name}:")
    print(reliability_table.to_string(index=False))
    print(f"\nItem-Total Statistics for {factor_name}:")
    print(item_total_table.to_string(index=False))
    print(f"\nReliability Analysis Comments for {factor_name}:")
    print("Overall Scale:")
    for comment in diagnostics['Overall_Scale']['Comments']:
        print(f"- {comment}")
    print("\nItem-Specific Comments:")
    for var, comments in diagnostics['Item_Total_Statistics'].items():
        print(f"{var}:")
        for comment in comments['Comments']:
            print(f"  - {comment}")

    # Confirm Saving
    print(f"Reliability statistics saved to '{os.path.join(output_dir, f'reliability_statistics_{factor_name}.csv')}'")
    print(f"Item-Total Statistics saved to '{os.path.join(output_dir, f'item_total_statistics_{factor_name}.csv')}'")
    print(f"Reliability diagnostics saved to '{os.path.join(output_dir, f'reliability_diagnostics_{factor_name}.json')}'")


    ########### 2: Phân tích nhân tố ############

    fa_variables = [var for factor in ['DK', 'YN', 'PT', 'DN', 'LI', 'CB'] for var in factor_groups[factor]]
    fa_data = data[fa_variables]
    factor_comments = []

    # KMO and Bartlett's Tests
    kmo_bartlett_table, kmo_bartlett_comments = perform_kmo_and_bartlett_tests(fa_data, save_results=False, output_dir=None)
    factor_comments.extend(kmo_bartlett_comments)
    kmo_bartlett_df = pd.DataFrame([kmo_bartlett_table])
    print("\nKMO and Bartlett's Test Results:")
    print(kmo_bartlett_df.to_string(index=False))
    kmo_bartlett_df.to_csv(os.path.join(output_dir, 'kmo_bartlett_results.csv'), index=False)
    print(f"KMO and Bartlett's test results saved to '{output_dir}/kmo_bartlett_results.csv'")

    # Determine Number of Factors
    n_factors, eigenvalues_df, variance_comments = determine_factors(fa_data, save_results=True, output_dir=output_dir)
    factor_comments.extend(variance_comments)
    print(f"Scree plot saved to '{os.path.join(output_dir, 'scree_plot.png')}'")

    # PCA with Varimax Rotation
    loadings, loading_comments, pca_diagnostics = perform_pca_varimax(fa_data, n_factors)
    factor_comments.extend(loading_comments)
    rotated_matrix = loadings.round(3)
    rotated_matrix.index.name = 'Variable'
    print("\nRotated Component Matrix:")
    print(rotated_matrix.to_string())
    rotated_matrix.to_csv(os.path.join(output_dir, 'rotated_component_matrix.csv'))
    print(f"Rotated Component Matrix saved to '{output_dir}/rotated_component_matrix.csv'")

    # Total Variance Explained
    variance_table, full_variance_table = generate_variance_table(eigenvalues_df, n_factors, pca_diagnostics, full_table=True)
    print("\nTotal Variance Explained (Selected Factors):")
    print(variance_table.to_string(index=False))
    variance_table.to_csv(os.path.join(output_dir, 'total_variance_explained.csv'), index=False)
    print(f"Total Variance Explained (Selected Factors) saved to '{output_dir}/total_variance_explained.csv'")

    print("\nTotal Variance Explained (All Factors):")
    print(full_variance_table.to_string(index=False))
    full_variance_table.to_csv(os.path.join(output_dir, 'total_variance_explained_full.csv'), index=False)
    print(f"Total Variance Explained (All Factors) saved to '{output_dir}/total_variance_explained_full.csv'")

    # Print Comments
    print("\nNhận xét phân tích nhân tố:")
    for comment in factor_comments:
        print(f"- {comment}")




    # Generate Model Summary (No-Intercept)
    model_summary_df, model_summary_notes = generate_model_summary_no_intercept(
        reg_data, dep_var, indep_vars, output_dir, save_results=True
    )
    print("\nModel Summary (No-Intercept):")
    print(model_summary_df.to_string(index=False))
    print(f"Model Summary table saved to '{os.path.join(output_dir, 'model_summary_no_intercept.csv')}'")
    print(f"Model Summary notes saved to '{os.path.join(output_dir, 'model_summary_no_intercept_notes.txt')}'")

    # Generate ANOVA Table (No-Intercept, ANOVA(a,b))
    anova_df_no_intercept, anova_no_intercept_notes = generate_anova_table_no_intercept(
        reg_data, dep_var, indep_vars, output_dir, save_results=True
    )
    print("\nANOVA Table (No-Intercept, ANOVA(a,b)):")
    print(anova_df_no_intercept.to_string(index=False))
    print(f"ANOVA table (no-intercept) saved to '{os.path.join(output_dir, 'anova_no_intercept.csv')}'")
    print(f"ANOVA notes (no-intercept) saved to '{os.path.join(output_dir, 'anova_no_intercept_notes.txt')}'")

    # Generate Spearman's Rho Table
    spearman_df, rho_comments = generate_spearman_rho_table(
        reg_data, dep_var, indep_vars, output_dir, save_results=True
    )
    print("\nSpearman's Rho Correlation Table:")
    print(spearman_df.to_string(index=False))
    print(f"Spearman's rho correlation table saved to '{os.path.join(output_dir, 'spearman_rho_correlations.csv')}'")
    print(f"Spearman's rho comments saved to '{os.path.join(output_dir, 'spearman_rho_comments.txt')}'")

    # Generate ANOVA Table (With-Intercept, ANOVA(a))
    anova_df_with_intercept, anova_with_intercept_notes = generate_anova_table_with_intercept(
        reg_data, dep_var, indep_vars, output_dir, save_results=False  # Notes will be saved below
    )
    # Append rho comments to ANOVA notes
    anova_with_intercept_notes.extend(rho_comments)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
        anova_df_with_intercept.to_csv(os.path.join(output_dir, 'anova_with_intercept.csv'), index=False)
        with open(os.path.join(output_dir, 'anova_with_intercept_notes.txt'), 'w') as f:
            f.write("\n".join(anova_with_intercept_notes))

    print("\nANOVA Table (With-Intercept, ANOVA(a)):")
    print(anova_df_with_intercept.to_string(index=False))
    print(f"ANOVA table (with-intercept) saved to '{os.path.join(output_dir, 'anova_with_intercept.csv')}'")
    print(f"ANOVA notes (with-intercept) saved to '{os.path.join(output_dir, 'anova_with_intercept_notes.txt')}'")