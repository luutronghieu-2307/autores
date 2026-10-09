import os
import io
import base64
from collections import defaultdict
from typing import Union, Optional, Dict, List, Tuple

import numpy as np
import pandas as pd

import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.patches import Ellipse, FancyBboxPatch

import seaborn as sns
import networkx as nx

from scipy import stats
from scipy.stats import f, t

import statsmodels.api as sm
from statsmodels.stats.diagnostic import het_breuschpagan
from statsmodels.stats.stattools import durbin_watson
from statsmodels.stats.outliers_influence import variance_inflation_factor

from factor_analyzer import FactorAnalyzer, calculate_kmo, calculate_bartlett_sphericity

import pingouin as pg

from typing import Union

DEFAULT_TRANSLATIONS = {
    "en": {
        "alpha_unreliable": "Unreliable (remove scale)",
        "alpha_acceptable": "Acceptable",
        "alpha_good": "Good (recommended)",
        "alpha_very_good": "Very good",
        "alpha_too_high": "Too high (possible variable redundancy)",
        "optimal_range_alpha": "0.7–0.8",
        "note_alpha": "≥ 0.7 preferred (per 3.2.8)",
        "remove_scale_alpha": "Remove scale: Alpha < 0.6",
        "check_redundancy_alpha": "Check for variable redundancy: Alpha > 0.9",
        "low_corr_items_warn": "Consider removing items with low correlation (< 0.3): {}",
        "pearson_title": "Pearson Correlation Matrix",
        "scree_plot_title": "Scree Plot",
        "factor_label": "Factor",
        "eigenvalue_label": "Eigenvalue",
        "loadings_heatmap_title": "Factor Loadings Heatmap",
        "kmo_unsuitable": "Unsuitable (remove EFA)",
        "kmo_acceptable": "Acceptable",
        "kmo_fairly_good": "Fairly good",
        "kmo_good": "Good",
        "kmo_very_good": "Very good",
        "kmo_excellent": "Excellent",
        "optimal_range_kmo": "0.7–0.9",
        "remove_efa_kmo": "Remove EFA: KMO < 0.5",
        "bartlett_reject_h0": "Reject H0 (variables are correlated)",
        "bartlett_fail_h0": "Fail to reject H0 (variables uncorrelated)",
        "sig_p_less_05": "Significant (p < 0.05)",
        "not_sig_p_ge_05": "Not significant (p >= 0.05)",
        "suitable_efa": "Suitable for EFA",
        "unsuitable_efa": "Unsuitable for EFA (no correlation between variables)",
        "optimal_bartlett": "p < 0.05 (smaller is better, p ≤ 0.01 is better)",
        "remove_efa_bartlett": "Remove EFA: p-value > 0.05",
        "keep_factor": "Keep Factor {}: Eigenvalue > 1",
        "remove_factor": "Remove Factor {}: Eigenvalue <= 1",
        "optimal_eigenvalue": "≥ 1",
        "exclude_factor_warn": "Exclude factor {}: Eigenvalue < 1",
        "remove_efa_no_factors": "Remove EFA: No factors with eigenvalue > 1",
        "remove_variable": "Remove variable",
        "acceptable": "Acceptable",
        "good": "Good",
        "very_good": "Very good",
        "optimal_loadings": "> 0.5 (acceptable), > 0.7 (best)",
        "notes_loadings": "Loadings evaluated as absolute values",
        "acceptable_review": "Acceptable but review",
        "optimal_communality": "Communality > 0.5",
        "remove_variable_communality": "Remove variable {}: Communality < 0.3",
        "insufficient": "Insufficient",
        "optimal_variance": "≥ 50% (minimum), ≥ 60% (best)",
        "eigenvalue_gt_1": "Eigenvalue > 1 ({:.3f})",
        "eigenvalue_le_1": "Eigenvalue ≤ 1 ({:.3f})",
        "warn_variance_low": "Warning: Total variance < 50%",
        "warn_no_factors": "Warning: No factors with eigenvalue > 1",
        "warn_factors_exceed_variance": "Warning: Selected factors exceed variance threshold",
        "ideal_sample": "Ideal",
        "small_sample": "Small",
        "large_sample": "Large",
        "too_few_sample": "Too few",
        "selection_rationale": "Selected {} factors: Maximum with eigenvalues > 1 ({}), constrained by max_factors ({}). Cumulative variance: {:.1f}%",
        "reject_h0": "Reject H₀",
        "fail_reject_h0": "Fail to reject H₀",
        "significant_difference": "Significant difference",
        "no_significant_difference": "No significant difference",
        "unequal_variances": "Unequal variances",
        "equal_variances": "Equal variances",
        "variances_unequal": "Variances are unequal",
        "variances_equal": "Variances are equal",
    },
    "vi": {
        "alpha_unreliable": "Không tin cậy (loại bỏ thang đo)",
        "alpha_acceptable": "Chấp nhận được",
        "alpha_good": "Tốt (khuyến nghị)",
        "alpha_very_good": "Rất tốt",
        "alpha_too_high": "Quá cao (có thể dư thừa biến)",
        "optimal_range_alpha": "0.7–0.8",
        "note_alpha": "Ưu tiên ≥ 0.7 (theo 3.2.8)",
        "remove_scale_alpha": "Loại bỏ thang đo: Alpha < 0.6",
        "check_redundancy_alpha": "Kiểm tra dư thừa biến: Alpha > 0.9",
        "low_corr_items_warn": "Cân nhắc loại bỏ các biến có tương quan thấp (< 0.3): {}",
        "pearson_title": "Ma trận tương quan Pearson",
        "scree_plot_title": "Biểu đồ Scree",
        "factor_label": "Nhân tố",
        "eigenvalue_label": "Giá trị riêng (Eigenvalue)",
        "loadings_heatmap_title": "Bản đồ nhiệt hệ số tải nhân tố",
        "kmo_unsuitable": "Không phù hợp (loại bỏ EFA)",
        "kmo_acceptable": "Chấp nhận được",
        "kmo_fairly_good": "Khá tốt",
        "kmo_good": "Tốt",
        "kmo_very_good": "Rất tốt",
        "kmo_excellent": "Xuất sắc",
        "optimal_range_kmo": "0.7–0.9",
        "remove_efa_kmo": "Loại bỏ EFA: KMO < 0.5",
        "bartlett_reject_h0": "Bác bỏ H0 (các biến có tương quan)",
        "bartlett_fail_h0": "Chưa đủ bằng chứng bác bỏ H0 (các biến không tương quan)",
        "sig_p_less_05": "Có ý nghĩa (p < 0.05)",
        "not_sig_p_ge_05": "Không có ý nghĩa (p >= 0.05)",
        "suitable_efa": "Phù hợp để phân tích EFA",
        "unsuitable_efa": "Không phù hợp để phân tích EFA (không có tương quan giữa các biến)",
        "optimal_bartlett": "p < 0.05 (càng nhỏ càng tốt, p ≤ 0.01 là tốt nhất)",
        "remove_efa_bartlett": "Loại bỏ EFA: p-value > 0.05",
        "keep_factor": "Giữ lại Nhân tố {}: Eigenvalue > 1",
        "remove_factor": "Loại bỏ Nhân tố {}: Eigenvalue <= 1",
        "optimal_eigenvalue": "≥ 1",
        "exclude_factor_warn": "Loại trừ nhân tố {}: Eigenvalue < 1",
        "remove_efa_no_factors": "Loại bỏ EFA: Không có nhân tố nào có eigenvalue > 1",
        "remove_variable": "Loại bỏ biến",
        "acceptable": "Chấp nhận được",
        "good": "Tốt",
        "very_good": "Rất tốt",
        "optimal_loadings": "> 0.5 (chấp nhận được), > 0.7 (tốt nhất)",
        "notes_loadings": "Hệ số tải được đánh giá theo giá trị tuyệt đối",
        "acceptable_review": "Chấp nhận được nhưng cần xem xét",
        "optimal_communality": "Phần chung > 0.5",
        "remove_variable_communality": "Loại bỏ biến {}: Phần chung < 0.3",
        "insufficient": "Không đủ",
        "optimal_variance": "≥ 50% (tối thiểu), ≥ 60% (tốt nhất)",
        "eigenvalue_gt_1": "Eigenvalue > 1 ({:.3f})",
        "eigenvalue_le_1": "Eigenvalue ≤ 1 ({:.3f})",
        "warn_variance_low": "Cảnh báo: Tổng phương sai < 50%",
        "warn_no_factors": "Cảnh báo: Không có nhân tố nào có eigenvalue > 1",
        "warn_factors_exceed_variance": "Cảnh báo: Số nhân tố được chọn vượt quá ngưỡng phương sai",
        "ideal_sample": "Lý tưởng",
        "small_sample": "Nhỏ",
        "large_sample": "Lớn",
        "too_few_sample": "Quá ít",
        "selection_rationale": "Đã chọn {} nhân tố: Tối đa với eigenvalues > 1 ({}), bị giới hạn bởi max_factors ({}). Tổng phương sai tích lũy: {:.1f}%",
        "reject_h0": "Bác bỏ H₀",
        "fail_reject_h0": "Chưa đủ bằng chứng bác bỏ H₀",
        "significant_difference": "Có sự khác biệt ý nghĩa",
        "no_significant_difference": "Không có sự khác biệt ý nghĩa",
        "unequal_variances": "Phương sai không đồng nhất",
        "equal_variances": "Phương sai đồng nhất",
        "variances_unequal": "Phương sai không đồng nhất",
        "variances_equal": "Phương sai đồng nhất",
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




##########################################################
## 3.2.1 Độ tin cậy thang đo với hệ số Cronbach’s Alpha ##
##########################################################


def cronbach_alpha_analysis(data: pd.DataFrame, t: dict = None) -> tuple[float, tuple, dict, dict]:
    """
    Calculate Cronbach’s Alpha and item-total correlations per section 3.2.1.
    
    Parameters:
    - data: pd.DataFrame, columns are items (numerical, no missing values).
    - t: dict, translation dictionary.
    
    Returns:
    - alpha: float, Cronbach’s Alpha.
    - ci: tuple, 95% confidence interval for Alpha.
    - item_total_corr: dict, item-total correlations (item vs. sum of others).
    - diagnostics: dict, status, optimal range, warnings, and low correlation items.
    
    Requirements (per section 3.2.9):
    - Alpha: < 0.6 (Unreliable, remove), 0.6–0.7 (Acceptable), 0.7–0.8 (Good),
      0.8–0.9 (Very good), > 0.9 (Too high, possible redundancy).
    - Optimal: 0.7–0.8.
    - Item-total correlation: ≥ 0.3 (absolute value).
    - Note (per 3.2.8): ≥ 0.7 preferred.
    """
    t = get_t_dict(t)
    # Compute Cronbach’s Alpha
    alpha, ci = pg.cronbach_alpha(data)
    
    # Item-total correlations
    item_total_corr = {}
    for col in data.columns:
        total = data.drop(columns=col).sum(axis=1)
        corr = data[col].corr(total)
        item_total_corr[col] = corr
    
    # Diagnostics per 3.2.9
    diagnostics = {
        'alpha_status': (
            t['alpha_unreliable'] if alpha < 0.6 else
            t['alpha_acceptable'] if 0.6 <= alpha < 0.7 else
            t['alpha_good'] if 0.7 <= alpha < 0.8 else
            t['alpha_very_good'] if 0.8 <= alpha < 0.9 else
            t['alpha_too_high']
        ),
        'optimal_range': t['optimal_range_alpha'],
        'note': t['note_alpha'],
        'low_corr_items': [col for col, corr in item_total_corr.items() if abs(corr) < 0.3],
        'warnings': []
    }
    
    # Add warnings
    if alpha < 0.6:
        diagnostics['warnings'].append(t['remove_scale_alpha'])
    if alpha > 0.9:
        diagnostics['warnings'].append(t['check_redundancy_alpha'])
    if diagnostics['low_corr_items']:
        diagnostics['warnings'].append(
            t['low_corr_items_warn'].format(', '.join(diagnostics['low_corr_items']))
        )
    
    return alpha, ci, item_total_corr, diagnostics


#########################################################
########### 3.2.2 Hệ số tương quan Pearson ##############
#########################################################


def pearson_correlation_analysis(
    data: pd.DataFrame,
    visualize: bool = False,
    output_dir: str = None,
    filename: str = 'correlation_heatmap.png',
    t: dict = None
) -> pd.DataFrame:
    """
    Calculate Pearson correlation coefficients and optionally visualize as a heatmap.
    
    Parameters:
    - data: pd.DataFrame, columns are variables (numerical, no missing values).
    - visualize: bool, if True, display a correlation heatmap.
    - output_dir: str, directory to save the visualization if not None.
    - filename: str, name of the file to save the plot.
    - t: dict, translation dictionary.
    
    Returns:
    - corr_matrix: pd.DataFrame, pairwise Pearson correlations.
    """
    t = get_t_dict(t)
    # Compute Pearson correlation matrix
    corr_matrix = data.corr(method='pearson')
    
    if visualize or output_dir:
        plt.figure(figsize=(4, 3))
        sns.heatmap(corr_matrix, annot=True, cmap='coolwarm', vmin=-1, vmax=1)
        plt.title(t['pearson_title'])
        
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
            filepath = os.path.join(output_dir, filename)
            plt.savefig(filepath, dpi=300, bbox_inches='tight')
            print(f"Correlation heatmap saved to '{filepath}'")
        
        if visualize:
            plt.show()
        else:
            plt.close()
    
    return corr_matrix


#########################################################
######## 3.2.3 Phân tích nhân tố khám phá EFA ###########
#########################################################

def exploratory_factor_analysis(data: pd.DataFrame, n_factors: int = None, rotation: str = 'varimax', 
                               method: str = 'minres', visualize: bool = False, t: dict = None) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    """
    Perform Exploratory Factor Analysis (EFA) per section 3.2.3.
    
    Parameters:
    - data: pd.DataFrame, columns are observed variables (numerical, no missing values).
    - n_factors: int, number of factors to extract (if None, determined by eigenvalues > 1).
    - rotation: str, rotation method ('varimax', 'promax', or None).
    - method: str, factor extraction method ('minres', 'ml', 'principal').
    - visualize: bool, if True, display scree plot and factor loading heatmap.
    - t: dict, translation dictionary.
    
    Returns:
    - loadings: pd.DataFrame, factor loadings (variables x factors).
    - communalities: pd.DataFrame, communality estimates for each variable.
    - diagnostics: dict, variance explained, eigenvalues, and factor selection info.
    
    Requirements:
    - Variables should be standardized (mean=0, std=1) for better interpretation.
    - Kaiser criterion (eigenvalues > 1) for factor selection if n_factors is None.
    - Loadings > 0.4 are considered significant for interpretation.
    """
    t = get_t_dict(t)
    # Standardize data
    data_std = (data - data.mean()) / data.std()
    
    # Initialize factor analyzer
    fa = FactorAnalyzer(rotation=rotation, method=method, n_factors=999)  # Extract all possible factors initially
    fa.fit(data_std)
    
    # Determine number of factors (if not specified) using Kaiser criterion
    eigenvalues = fa.get_eigenvalues()[0]  # Common variance eigenvalues
    if n_factors is None:
        n_factors = sum(eigenvalues > 1)
    
    # Refit with specified number of factors
    fa = FactorAnalyzer(rotation=rotation, method=method, n_factors=n_factors)
    fa.fit(data_std)
    
    # Get factor loadings
    loadings = pd.DataFrame(fa.loadings_, index=data.columns, 
                           columns=[f'Factor{i+1}' for i in range(n_factors)])
    
    # Get communalities
    communalities = pd.DataFrame(fa.get_communalities(), index=data.columns, columns=['Communality'])
    
    # Variance explained
    variance = fa.get_factor_variance()
    variance_explained = {
        'Total Variance Explained': variance[1][-1],  # Cumulative proportion
        'Variance Per Factor': variance[1]  # Proportion per factor
    }
    
    # Diagnostics
    diagnostics = {
        'n_factors': n_factors,
        'eigenvalues': eigenvalues.tolist(),
        'variance_explained': variance_explained,
        'low_loading_vars': loadings[abs(loadings) < 0.4].dropna(how='all').index.tolist()
    }
    
    # Visualizations
    if visualize:
        # Scree plot
        plt.figure(figsize=(4, 3))
        plt.plot(range(1, len(eigenvalues) + 1), eigenvalues, 'o-')
        plt.axhline(y=1, color='r', linestyle='--')
        plt.title(t['scree_plot_title'])
        plt.xlabel(t['factor_label'])
        plt.ylabel(t['eigenvalue_label'])
        plt.grid(True)
        plt.show()
        
        # Heatmap of loadings
        plt.figure(figsize=(5, 3))
        sns.heatmap(loadings, annot=True, cmap='coolwarm', vmin=-1, vmax=1)
        plt.title(t['loadings_heatmap_title'])
        plt.show()
    
    return loadings, communalities, diagnostics



#---------------------------------------------#
# 3.2.3.1 Hệ số Kaiser-Meyer-Olkin (KMO)
#---------------------------------------------#

def kmo_test(data: pd.DataFrame, t: dict = None) -> tuple[float, dict]:
    """
    Calculate Kaiser-Meyer-Olkin (KMO) coefficient per section 3.2.3.1.
    
    Parameters:
    - data: pd.DataFrame, columns are variables (numerical, no missing values).
    - t: dict, translation dictionary.
    
    Returns:
    - kmo_total: float, overall KMO coefficient.
    - diagnostics: dict, KMO per variable, status, optimal range, and warnings.
    
    Requirements (per section 3.2.9):
    - KMO: < 0.5 (Unsuitable, remove EFA), 0.5–0.6 (Acceptable), 0.6–0.7 (Fairly good),
      0.7–0.8 (Good), 0.8–0.9 (Very good), > 0.9 (Excellent).
    - Optimal: 0.7–0.9.
    """
    t = get_t_dict(t)
    # Calculate KMO
    kmo_per_item, kmo_total = calculate_kmo(data)
    
    # Diagnostics per 3.2.9
    diagnostics = {
        'kmo_per_item': pd.Series(kmo_per_item, index=data.columns).to_dict(),
        'kmo_status': (
            t['kmo_unsuitable'] if kmo_total < 0.5 else
            t['kmo_acceptable'] if 0.5 <= kmo_total < 0.6 else
            t['kmo_fairly_good'] if 0.6 <= kmo_total < 0.7 else
            t['kmo_good'] if 0.7 <= kmo_total < 0.8 else
            t['kmo_very_good'] if 0.8 <= kmo_total < 0.9 else
            t['kmo_excellent']
        ),
        'optimal_range': t['optimal_range_kmo'],
        'warnings': [t['remove_efa_kmo']] if kmo_total < 0.5 else []
    }
    
    return kmo_total, diagnostics

#---------------------------------------------#
# 3.2.3.2 Kiểm định Bartlett
#---------------------------------------------#

def bartlett_sphericity_test(data: pd.DataFrame, t: dict = None) -> tuple[float, float, dict]:
    """
    Perform Bartlett’s test of sphericity per section 3.2.3.2.
    
    Tests H0: Correlation matrix is an identity matrix (variables are uncorrelated).
    Rejects H0 if p-value < 0.05, indicating significant correlations at γ = 95%.
    
    Parameters:
    - data: pd.DataFrame, columns are variables (numerical, no missing values).
    - t: dict, translation dictionary.
    
    Returns:
    - chi_square: float, Chi-Square statistic.
    - p_value: float, p-value of the test.
    - diagnostics: dict, test decision, suitability, and warnings.
    
    Requirements:
    - p-value < 0.05 to reject H0 (variables are correlated).
    - Uses Chi-Square test via factor_analyzer implementation.
    """
    t = get_t_dict(t)
    # Calculate Bartlett's test using factor_analyzer
    chi_square, p_value = calculate_bartlett_sphericity(data)
    
    # Get number of variables for interpretation
    p = data.shape[1]  # Number of variables
    
    # Updated diagnostics per section 3.2.9
    diagnostics = {
        'decision': t['bartlett_reject_h0'] if p_value < 0.05 
                   else t['bartlett_fail_h0'],
        'p_value_status': t['sig_p_less_05'] if p_value < 0.05 
                         else t['not_sig_p_ge_05'],
        'suitability': t['suitable_efa'] if p_value < 0.05 
                       else t['unsuitable_efa'],
        'optimal': t['optimal_bartlett'],
        'warnings': [t['remove_efa_bartlett'] if p_value > 0.05 else '']
    }
    
    return chi_square, p_value, diagnostics

#---------------------------------------------#
# 3.2.3.3 Eigenvalue và Eigenvector
#---------------------------------------------#

def eigenvalue_eigenvector_analysis(data: pd.DataFrame, t: dict = None) -> tuple[np.ndarray, np.ndarray, float, dict]:
    """
    Compute eigenvalues and eigenvectors of the correlation matrix per section 3.2.3.3.
    
    Eigenvalues satisfy det(A - bI) = 0, where A is the correlation matrix and I is the identity.
    Eigenvectors satisfy (A - bI)C = 0 for eigenvalue b.
    
    Parameters:
    - data: pd.DataFrame, columns are variables (numerical, no missing values).
    - t: dict, translation dictionary.
    
    Returns:
    - eigenvalues: np.ndarray, sorted eigenvalues (descending order).
    - eigenvectors: np.ndarray, corresponding eigenvectors (columns).
    - dominant_eigenvalue: float, eigenvalue with largest absolute value.
    - diagnostics: dict, eigenvalue status and matrix properties.
    """
    t = get_t_dict(t)
    # Compute correlation matrix
    corr_matrix = data.corr(method='pearson').to_numpy()
    
    # Compute eigenvalues and eigenvectors
    eigenvalues, eigenvectors = np.linalg.eigh(corr_matrix)  # eigh for symmetric matrices
    # Sort eigenvalues and eigenvectors in descending order
    idx = np.argsort(eigenvalues)[::-1]
    eigenvalues = eigenvalues[idx]
    eigenvectors = eigenvectors[:, idx]
    
    # Identify dominant eigenvalue
    dominant_eigenvalue = eigenvalues[0]  # Largest eigenvalue (sorted descending)
    
    # Updated diagnostics per section 3.2.9
    diagnostics = {
        'num_factors': np.sum(eigenvalues > 1),
        'eigenvalue_status': {
            t['keep_factor'].format(i+1) if eig > 1 else t['remove_factor'].format(i+1)
            for i, eig in enumerate(eigenvalues)
        },
        'optimal_eigenvalue': t['optimal_eigenvalue'],
        'factors_to_remove': [i+1 for i, eig in enumerate(eigenvalues) if eig < 1],
        'warnings': (
            [t['exclude_factor_warn'].format(i+1) for i, eig in enumerate(eigenvalues) if eig < 1] +
            [t['remove_efa_no_factors']] if np.sum(eigenvalues > 1) == 0 else []
        ),
        'matrix_symmetric': np.allclose(corr_matrix, corr_matrix.T),
        'eigenvalues_positive': np.all(eigenvalues > 0)
    }
    
    return eigenvalues, eigenvectors, dominant_eigenvalue, diagnostics

#---------------------------------------------#
# 3.2.3.4 Hệ số tải nhân tố
#---------------------------------------------#
def factor_loading_coefficient(data: pd.DataFrame, n_factors: int = None, t: dict = None) -> tuple[pd.DataFrame, dict]:
    """
    Calculate factor loading coefficients per section 3.2.3.4.
    
    Formula: λᵢₛ = cᵢₛ * sqrt(bₛ), where cᵢₛ is the eigenvector and bₛ is the eigenvalue.
    
    Parameters:
    - data: pd.DataFrame, columns are variables (numerical, no missing values).
    - n_factors: int, number of factors to retain (default: eigenvalues > 1).
    - t: dict, translation dictionary.
    
    Returns:
    - loadings: pd.DataFrame, factor loadings (variables x factors).
    - diagnostics: dict, loading thresholds and factor interpretability.
    
    Requirements:
    - Uses eigenvalues and eigenvectors from correlation matrix.
    """
    t = get_t_dict(t)
    # Compute eigenvalues and eigenvectors
    eigenvalues, eigenvectors, _, _ = eigenvalue_eigenvector_analysis(data, t=t)
    
    # Determine number of factors (default: eigenvalues > 1)
    if n_factors is None:
        n_factors = np.sum(eigenvalues > 1)
    
    # Calculate factor loadings: λᵢₛ = cᵢₛ * sqrt(bₛ)
    loadings = eigenvectors[:, :n_factors] * np.sqrt(eigenvalues[:n_factors])
    
    # Convert to DataFrame
    loadings = pd.DataFrame(
        loadings,
        index=data.columns,
        columns=[f'Factor{i+1}' for i in range(n_factors)]
    )
    
    # Diagnostics
    diagnostics = {
        'n_factors': n_factors,
        'loading_status': {
            var: (
                t['remove_variable'] if max(abs(loadings.loc[var])) < 0.3 else
                t['acceptable'] if 0.3 <= max(abs(loadings.loc[var])) <= 0.5 else
                t['good'] if 0.5 < max(abs(loadings.loc[var])) <= 0.7 else
                t['very_good']
            ) for var in loadings.index
        },
        'optimal_loadings': t['optimal_loadings'],
        'variables_to_remove': [
            var for var in loadings.index if max(abs(loadings.loc[var])) < 0.3
        ],
        'cross_loadings': [
            (var, loadings.loc[var].abs().nlargest(2).to_dict())
            for var in loadings.index
            if (loadings.loc[var].abs() > 0.5).sum() > 1
        ],
        'notes': t['notes_loadings']
    }
    
    return loadings, diagnostics

#---------------------------------------------#
# 3.2.3.5 Phần chung
#---------------------------------------------#

def communality_analysis(data: pd.DataFrame, n_factors: int = None, t: dict = None) -> tuple[pd.Series, dict]:
    """
    Calculate communalities per Section 3.2.3.5, aligned with PCA for Section 3.2.3.7.
    
    Formula: h²ᵢ = Σ λ²ᵢₛ (sum of squared factor loadings across factors).
    
    Parameters:
    - data: pd.DataFrame, columns are variables (numerical, no missing values).
    - n_factors: int, number of factors to retain (default: eigenvalues > 1).
    - t: dict, translation dictionary.
    
    Returns:
    - communalities: pd.Series, communality for each variable.
    - diagnostics: dict, communality status, thresholds, and warnings.
    
    Requirements:
    - Communalities ∈ [0, 1].
    - Uses PCA loadings for consistency with Section 3.2.3.7.
    """
    t = get_t_dict(t)
    # Determine number of factors if not specified
    if n_factors is None:
        fa_temp = FactorAnalyzer(rotation=None, method='principal')
        fa_temp.fit(data)
        n_factors = sum(fa_temp.get_eigenvalues()[0] > 1)
    
    # Compute factor loadings (unrotated PCA)
    fa = FactorAnalyzer(n_factors=n_factors, rotation=None, method='principal')
    fa.fit(data)
    loadings = pd.DataFrame(fa.loadings_, index=data.columns)
    
    # Calculate communalities: sum of squared loadings
    communalities = (loadings ** 2).sum(axis=1)
    
    # Convert to Series
    communalities = pd.Series(communalities, index=loadings.index, name='Communality')
    
    # Updated diagnostics per section 3.2.9
    diagnostics = {
        'mean_communality': communalities.mean(),
        'communality_status': {
            var: t['good'] if comm > 0.5 else 
                 t['acceptable_review'] if 0.3 <= comm <= 0.5 else 
                 t['remove_variable'] 
            for var, comm in communalities.items()
        },
        'optimal': t['optimal_communality'],
        'variables_to_remove': [var for var, comm in communalities.items() if comm < 0.3],
        'warnings': [t['remove_variable_communality'].format(var) 
                     for var, comm in communalities.items() if comm < 0.3]
    }
    
    return communalities, diagnostics

#---------------------------------------------#
# 3.2.3.6 Số nhân tố
#---------------------------------------------#

def determine_number_of_factors(data: pd.DataFrame, plot_scree: bool = True, save_path: str = None, t: dict = None) -> tuple[int, pd.DataFrame, dict]:
    """
    Determine the number of factors per Section 3.2.3.6 using Kaiser criterion, scree plot, and variance explained.
    Selects the maximum number of factors with eigenvalues > 1, subject to max_factors constraint.
    
    Parameters:
    - data: pd.DataFrame, columns are variables (numerical, no missing values).
    - plot_scree: bool, if True, generate the scree plot.
    - save_path: str, optional path to save the scree plot. If None and plot_scree is True, saves to 'scree_plot.png'.
    - t: dict, translation dictionary.
    
    Returns:
    - n_factors: int, suggested number of factors.
    - eigenvalues_df: pd.DataFrame, eigenvalues and cumulative variance.
    - diagnostics: dict, metrics, variance status, and warnings.
    """
    t = get_t_dict(t)
    k = data.shape[1]  # Number of variables
    max_factors = (k - 1) // 2  # Condition: m ≤ (k-1)/2

    # Perform PCA without rotation to get eigenvalues
    fa = FactorAnalyzer(n_factors=k, rotation=None, method='principal')
    fa.fit(data)
    
    # Extract eigenvalues
    eigenvalues = fa.get_eigenvalues()[0]
    eigenvalues_df = pd.DataFrame({
        'Eigenvalue': eigenvalues,
        'Cumulative Variance': (eigenvalues / eigenvalues.sum()).cumsum()
    }, index=[f'Factor {i+1}' for i in range(k)])
    
    # Kaiser criterion: factors with eigenvalues > 1
    n_factors_eigen = sum(eigenvalues > 1.0)
    
    # Variance criterion: number of factors to reach ≥ 50% variance (for diagnostics)
    cumulative_variance = eigenvalues_df['Cumulative Variance']
    n_factors_variance = next(i for i, v in enumerate(cumulative_variance) if v >= 0.5) + 1
    
    # Final number of factors: maximum of eigen, constrained by max_factors
    n_factors = min(n_factors_eigen, max_factors)
    
    # Scree plot
    if plot_scree:
        plt.figure(figsize=(4, 3))
        plt.plot(range(1, k+1), eigenvalues, 'o-', label='Eigenvalues')
        plt.axhline(y=1.0, color='r', linestyle='--', label='Eigenvalue = 1')
        plt.title(t['scree_plot_title'])
        plt.xlabel(t['factor_label'] + ' Number')
        plt.ylabel(t['eigenvalue_label'])
        plt.legend()
        plt.grid(True)
        
        # Set default save path to current directory if not specified
        if save_path is None:
            save_path = os.path.join(os.getcwd(), 'scree_plot.png')
        
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        plt.close()
    
    # Updated diagnostics per section 3.2.9
    total_variance = cumulative_variance.iloc[n_factors - 1]
    diagnostics = {
        'max_factors_allowed': max_factors,
        'n_factors_eigen': n_factors_eigen,
        'n_factors_variance': n_factors_variance,
        'n_factors_selected': n_factors,
        'total_variance_explained': total_variance,
        'variance_status': (
            t['very_good'] if total_variance >= 0.7 else 
            t['good'] if total_variance >= 0.6 else 
            t['acceptable'] if total_variance >= 0.5 else 
            t['insufficient']
        ),
        'optimal_variance': t['optimal_variance'],
        'eigenvalue_status': {
            f'Factor {i+1}': t['eigenvalue_gt_1'].format(eig) if eig > 1 else t['eigenvalue_le_1'].format(eig)
            for i, eig in enumerate(eigenvalues)
        },
        'optimal_eigenvalue': t['optimal_eigenvalue'],
        'warnings': (
            [t['warn_variance_low']] if total_variance < 0.5 else []
        ) + (
            [t['warn_no_factors']] if n_factors_eigen == 0 else []
        ) + (
            [t['warn_factors_exceed_variance']] if n_factors > n_factors_variance else []
        ),
        'sample_size': k,
        'sample_size_status': (
            t['ideal_sample'] if 20 <= k <= 50 else 
            t['small_sample'] if 10 <= k < 20 else 
            t['large_sample'] if k > 50 else 
            t['too_few_sample']
        ),
        'selection_rationale': t['selection_rationale'].format(n_factors, n_factors_eigen, max_factors, total_variance*100)
    }
    
    return n_factors, eigenvalues_df, diagnostics

#-----------------------------------------------------#
# 3.2.3.7 Phương pháp phân tích nhân tố và phép xoay
#-----------------------------------------------------#

def pca_varimax_analysis(data: pd.DataFrame, n_factors: int, t: dict = None) -> tuple[pd.DataFrame, dict]:
    """
    Perform Principal Components Analysis (PCA) with Varimax rotation for EFA per Section 3.2.3.7.
    
    Parameters:
    - data: pd.DataFrame, columns are variables (numerical, no missing values).
    - n_factors: int, number of factors to extract.
    
    Returns:
    - loadings: pd.DataFrame, rotated factor loadings.
    - diagnostics: dict, total variance explained and other metrics.
    """
    # Verify input data
    if not data.select_dtypes(include=np.number).columns.equals(data.columns):
        raise ValueError("All columns in data must be numeric.")
    if data.isna().any().any():
        raise ValueError("Data contains missing values.")
    
    # Perform PCA with Varimax rotation, with stricter convergence
    fa = FactorAnalyzer(
        n_factors=n_factors,
        rotation='varimax',
        method='principal',
        rotation_kwargs={'normalize': True, 'max_iter': 5000, 'tol': 1e-8}
    )
    fa.fit(data)
    
    # Get rotated factor loadings
    loadings_array = fa.loadings_
    
    # Compute rotated sums of squared loadings
    rotated_sums = np.sum(loadings_array ** 2, axis=0)
    
    # Sort components by rotated sums (descending order)
    sorted_indices = np.argsort(-rotated_sums)
    rotated_sums = rotated_sums[sorted_indices]
    loadings_array = loadings_array[:, sorted_indices]
    
    # Convert loadings to DataFrame with sorted components
    loadings = pd.DataFrame(
        loadings_array,
        index=data.columns,
        columns=[f'Factor {i+1}' for i in range(n_factors)]
    )
    
    # Compute variance per factor
    num_variables = data.shape[1]
    variance_per_factor = rotated_sums / num_variables

    # Compute total variance explained
    eigenvalues = fa.get_eigenvalues()[0][:n_factors]
    total_variance_explained = eigenvalues.sum() / fa.get_eigenvalues()[0].sum()
    
    # Diagnostics
    diagnostics = {
        'total_variance_explained': total_variance_explained,
        'variance_per_factor': variance_per_factor,
        'high_loadings': (loadings.abs() > 0.4).sum().to_dict()
    }
    
    return loadings, diagnostics


#########################################################
########## 3.2.4 Phân tích phương sai ANOVA #############
#########################################################

#-----------------------------------------------------#
# 3.2.4.1 Kiểm định trung bình 2 tổng thể
#-----------------------------------------------------#


def two_sample_ttest(sample1: pd.Series, sample2: pd.Series, alpha: float = 0.05, 
                    equal_var: bool = True, t: dict = None) -> tuple[float, float, str, dict]:
    """
    Test the equality of two population means per Section 3.2.4.1.
    
    Parameters:
    - sample1: pd.Series or array-like, first sample (numerical, no missing values).
    - sample2: pd.Series or array-like, second sample (numerical, no missing values).
    - alpha: float, significance level (default: 0.05).
    - equal_var: bool, assume equal variances (True) or unequal (False).
    - t: dict, translation dictionary.
    
    Returns:
    - t_stat: float, t-statistic.
    - p_value: float, p-value for the test.
    - decision: str, decision to reject or fail to reject H₀.
    - diagnostics: dict, additional metrics (e.g., CI, critical values, variance assumption).
    
    Formulas:
    - Equal variances: t = [(X̄₁ - X̄₂) - (μ₁ - μ₂)] / √[S²ₚ(1/n₁ + 1/n₂)]
    - Unequal variances: t = [(X̄₁ - X̄₂) - (μ₁ - μ₂)] / √[(S₁²/n₁) + (S₂²/n₂)]
    - Reject H₀ if |t| > t_{n-1, α/2}.
    """
    t_dict = get_t_dict(t)
    # Convert inputs to numpy arrays
    sample1 = np.asarray(sample1)
    sample2 = np.asarray(sample2)
    
    # Sample sizes
    n1, n2 = len(sample1), len(sample2)
    
    # Perform t-test using pingouin
    result = pg.ttest(sample1, sample2, paired=False, alternative='two-sided', 
                     correction='auto' if not equal_var else False)
    
    # Extract t-statistic and p-value
    t_stat = result['T'].iloc[0]
    p_value = result['p-val'].iloc[0]
    
    # Degrees of freedom (approximate for unequal variances)
    df = result['dof'].iloc[0]
    
    # Critical value for two-tailed test
    critical_val = t.ppf(1 - alpha / 2, df)
    
    # Decision rule
    decision = t_dict['reject_h0'] if abs(t_stat) > critical_val or p_value < alpha else t_dict['fail_reject_h0']
    
    # Confidence interval from pingouin
    ci = result['CI95%'].iloc[0]
    
    # Diagnostics
    diagnostics = {
        'sample_sizes': {'n1': n1, 'n2': n2},
        'sample_means': {'mean1': np.mean(sample1), 'mean2': np.mean(sample2)},
        'sample_variances': {'var1': np.var(sample1, ddof=1), 'var2': np.var(sample2, ddof=1)},
        'degrees_of_freedom': df,
        'critical_value': critical_val,
        'confidence_interval': ci,
        'variance_assumption': t_dict['equal_variances'] if equal_var else t_dict['unequal_variances'],
        'conclusion': t_dict['significant_difference'] if decision == t_dict['reject_h0'] else t_dict['no_significant_difference']
    }
    
    return t_stat, p_value, decision, diagnostics

#---------------------------------------------------------#
# 3.2.4.2 Kiểm định trung bình nhiều hơn 2 tổng thể (ANOVA)
#---------------------------------------------------------#

def one_way_anova_analysis(data: pd.DataFrame, dv: str, between: str, alpha: float = 0.05, t_dict: dict = None) -> tuple[dict, dict]:
    """
    Perform one-way ANOVA to test differences in means across 3+ groups per Section 3.2.4.2.
    
    Parameters:
    - data: pd.DataFrame, contains dependent variable and group labels (no missing values).
    - dv: str, column name of the dependent variable (numerical).
    - between: str, column name of the grouping variable (categorical).
    - alpha: float, significance level (default: 0.05).
    - t_dict: dict, translation dictionary.
    
    Returns:
    - levene_results: dict, Levene’s test results (F-stat, p-value, decision, critical value).
    - anova_results: dict, ANOVA results (F-stat, p-value, decision, critical value, eta-squared).
    
    Process:
    - Step 1: Levene’s test for homogeneity of variances.
      - Decision: If F > F_{k-1, n-k, α}, variances are unequal.
    - Step 2: One-way ANOVA.
      - Decision: If F > F_{df1, df2, α}, at least two group means differ.
    """
    t_dict = get_t_dict(t_dict)
    # Validate input
    if dv not in data.columns or between not in data.columns:
        raise ValueError("Specified columns not found in DataFrame.")
    
    # Extract groups
    groups = [group[dv].values for _, group in data.groupby(between)]
    group_labels = data[between].unique()
    k = len(group_labels)  # Number of groups
    n = len(data)  # Total sample size
    
    # Step 1: Levene’s test for homogeneity of variances
    levene_result = pg.homoscedasticity(data, dv=dv, group=between, method='levene')
    levene_f = levene_result['W'].iloc[0]  # Corrected to 'W'
    levene_p = levene_result['pval'].iloc[0]
    
    # Degrees of freedom for Levene’s test
    df_levene1 = k - 1
    df_levene2 = n - k
    
    # Critical value for Levene’s test
    levene_critical = f.ppf(1 - alpha, df_levene1, df_levene2)
    
    # Decision for Levene’s test
    levene_decision = t_dict['unequal_variances'] if levene_f > levene_critical or levene_p < alpha else t_dict['equal_variances']
    
    # Levene’s test results
    levene_results = {
        'F_statistic': levene_f,
        'p_value': levene_p,
        'decision': levene_decision,
        'critical_value': levene_critical,
        'degrees_of_freedom': {'df1': df_levene1, 'df2': df_levene2},
        'conclusion': t_dict['variances_unequal'] if levene_decision == t_dict['unequal_variances'] else t_dict['variances_equal']
    }
    
    # Step 2: One-way ANOVA
    anova_result = pg.anova(data=data, dv=dv, between=between, detailed=True)
    anova_f = anova_result.loc[0, 'F']
    anova_p = anova_result.loc[0, 'p-unc']
    
    # Degrees of freedom for ANOVA
    df_anova1 = k - 1
    df_anova2 = n - k
    
    # Critical value for ANOVA
    anova_critical = f.ppf(1 - alpha, df_anova1, df_anova2)
    
    # Decision for ANOVA
    anova_decision = t_dict['reject_h0'] if anova_f > anova_critical or anova_p < alpha else t_dict['fail_reject_h0']
    
    # Calculate eta-squared (effect size)
    ss_between = anova_result.loc[0, 'SS']
    ss_total = anova_result['SS'].sum()
    eta_squared = ss_between / ss_total
    
    # ANOVA results
    anova_results = {
        'F_statistic': anova_f,
        'p_value': anova_p,
        'decision': anova_decision,
        'critical_value': anova_critical,
        'degrees_of_freedom': {'df1': df_anova1, 'df2': df_anova2},
        'eta_squared': eta_squared,
        'conclusion': t_dict['significant_difference'] if anova_decision == t_dict['reject_h0'] else t_dict['no_significant_difference']
    }
    
    return levene_results, anova_results



#########################################################
####### 3.2.5 Phân tích/Hồi quy đa biến tuyến tính ######
#########################################################


#---------------------------------------------------------#
# 3.2.5.1 Hệ số hồi quy
#---------------------------------------------------------#


def multivariate_regression_analysis(
    data: pd.DataFrame,
    dependent_var: str,
    independent_vars: list[str],
    manual_calc: bool = False
) -> tuple[pd.Series, pd.DataFrame, dict]:
    """
    Perform multivariate linear regression analysis per Section 3.2.5 using OLS.
    
    Parameters:
    - data: pd.DataFrame, columns include dependent and independent variables (numerical, no missing values).
    - dependent_var: str, name of the dependent variable column (Y).
    - independent_vars: list[str], names of independent variable columns (X1, X2, ...).
    - manual_calc: bool, if True and len(independent_vars) == 2, compute coefficients manually.
    
    Returns:
    - intercept: pd.Series, intercept (b0) of the regression model.
    - coefficients: pd.DataFrame, regression coefficients with p-values and standard errors.
    - diagnostics: dict, R-squared, adjusted R-squared, coefficient significance per Section 3.2.9.
    
    Formulas (manual_calc=True, k=2):
    - b₁ = [∑yᵢx₁ᵢ∑x²₂ᵢ - ∑yᵢx₂ᵢ∑x₁ᵢx₂ᵢ] / [∑x²₁ᵢ∑x²₂ᵢ - (∑x₁ᵢx₂ᵢ)²]
    - b₂ = [∑yᵢx₂ᵢ∑x²₁ᵢ - ∑yᵢx₁ᵢ∑x₁ᵢx₂ᵢ] / [∑x²₁ᵢ∑x²₂ᵢ - (∑x₁ᵢx₂ᵢ)²]
    - b₀ = Ȳ - β̂₁x̄₁ - β̂₂x̄₂
    """
    # Validate inputs
    if dependent_var not in data.columns or not all(var in data.columns for var in independent_vars):
        raise ValueError("Specified variables not found in DataFrame.")
    if data[dependent_var].isnull().any() or data[independent_vars].isnull().any().any():
        raise ValueError("Data contains missing values.")
    
    # Extract data
    y = data[dependent_var]
    X = data[independent_vars]
    n = len(y)
    
    if manual_calc and len(independent_vars) == 2:
        # Manual calculation for k=2
        x1, x2 = X[independent_vars[0]], X[independent_vars[1]]
        y_mean = y.mean()
        x1_mean = x1.mean()
        x2_mean = x2.mean()
        
        # Transformed sums
        sum_y2 = np.sum(y**2) - n * y_mean**2
        sum_x1_2 = np.sum(x1**2) - n * x1_mean**2
        sum_x2_2 = np.sum(x2**2) - n * x2_mean**2
        sum_y_x1 = np.sum(y * x1) - n * y_mean * x1_mean
        sum_y_x2 = np.sum(y * x2) - n * y_mean * x2_mean
        sum_x1_x2 = np.sum(x1 * x2) - n * x1_mean * x2_mean
        
        # Compute coefficients
        denominator = sum_x1_2 * sum_x2_2 - sum_x1_x2**2
        if abs(denominator) < 1e-10:
            raise ValueError("Denominator is zero or near-zero; variables may be collinear.")
        
        b1 = (sum_y_x1 * sum_x2_2 - sum_y_x2 * sum_x1_x2) / denominator
        b2 = (sum_y_x2 * sum_x1_2 - sum_y_x1 * sum_x1_x2) / denominator
        b0 = y_mean - b1 * x1_mean - b2 * x2_mean
        
        coefficients = pd.DataFrame({
            'Coefficient': [b1, b2],
            'Standard Error': [np.nan, np.nan],
            'P-value': [np.nan, np.nan]
        }, index=independent_vars)
        
        # Compute R² and adjusted R²
        y_pred = b0 + b1 * x1 + b2 * x2
        ss_total = np.sum((y - y_mean)**2)
        ss_residual = np.sum((y - y_pred)**2)
        r_squared = 1 - ss_residual / ss_total if ss_total > 0 else np.nan
        adj_r_squared = 1 - (1 - r_squared) * (n - 1) / (n - 3) if n > 3 else np.nan
        
        # Diagnostics for manual path
        diagnostics = {
            'R-squared': r_squared,
            'R-squared_status': (
                'Insufficient' if r_squared < 0.3 else
                'Acceptable (weak model)' if 0.3 <= r_squared < 0.5 else
                'Fairly good' if 0.5 <= r_squared <= 0.7 else
                'Good' if 0.7 < r_squared <= 0.9 else
                'Possible overfitting'
            ),
            'Adjusted R-squared': adj_r_squared,
            'Adjusted R-squared_status': (
                'Acceptable' if adj_r_squared >= 0.5 else
                'Insufficient'
            ),
            'optimal_R-squared': '0.5–0.7 (avoids overfitting)',
            'notes': 'Adjusted R² ≥ 0.5 preferred for explanatory power (Section 3.2.8)',
            'coefficient_significance': 'Not computed (manual calculation)',
            'optimal_significance': 'Not applicable (manual calculation)',
            'variables_to_remove': [],
            'warnings': [
                w for w in [
                    'Poor model fit: R² < 0.3' if r_squared < 0.3 else None,
                    'Possible overfitting: R² > 0.9' if r_squared > 0.9 else None,
                    'Insufficient explanatory power: Adjusted R² < 0.5' if adj_r_squared < 0.5 else None,
                    'Manual calculation: Significance testing requires statsmodels for p-values',
                    'Run F-test, Durbin-Watson, and VIF tests for complete model evaluation (Section 3.2.9)'
                ] if w is not None
            ],
            'sample_size': n
        }
        
        intercept = pd.Series([b0], index=['Intercept'])
    
    else:
        # Statsmodels implementation
        X_sm = sm.add_constant(X)
        model = sm.OLS(y, X_sm).fit()
        
        intercept = pd.Series(model.params['const'], index=['Intercept'])
        coefficients = pd.DataFrame({
            'Coefficient': model.params[independent_vars],
            'Standard Error': model.bse[independent_vars],
            'P-value': model.pvalues[independent_vars]
        }, index=independent_vars)
        
        # Use evaluate_coefficient_of_determination
        r2_results = evaluate_coefficient_of_determination(data, dependent_var, independent_vars)
        
        diagnostics = {
            'R-squared': r2_results['R_squared'],
            'R-squared_status': r2_results['diagnostics']['R-squared_status'],
            'Adjusted R-squared': r2_results['R_squared_adjusted'],
            'Adjusted R-squared_status': r2_results['diagnostics']['Adjusted R-squared_status'],
            'optimal_R-squared': r2_results['diagnostics']['optimal_R-squared'],
            'notes': 'Adjusted R² ≥ 0.5 preferred for explanatory power (Section 3.2.8)',
            'coefficient_significance': {
                var: 'Highly significant' if p <= 0.01 else 'Significant' if p < 0.05 else 'Insignificant'
                for var, p in model.pvalues[independent_vars].items()
            },
            'optimal_significance': 'p < 0.05 (p ≤ 0.01 preferred for stronger significance, Section 3.2.8)',
            'variables_to_remove': [
                var for var, p in model.pvalues[independent_vars].items() if p > 0.05
            ],
            'warnings': r2_results['diagnostics']['warnings'] + [
                'Run F-test, Durbin-Watson, and VIF tests for complete model evaluation (Section 3.2.9)'
            ],
            'sample_size': n
        }
    
    return intercept, coefficients, diagnostics


#---------------------------------------------------------#
# 3.2.5.2 Đánh giá mức độ phù hợp
#---------------------------------------------------------#

############# 3.2.5.2.1 Đánh giá qua sai số #############

def evaluate_regression_fit(
    data: pd.DataFrame,
    dependent_var: str,
    independent_vars: list[str]
) -> dict[str, float]:
    """
    Evaluate the fit of a multivariate regression model using Sum of Squares.

    Parameters:
    - data: pd.DataFrame, columns include dependent and independent variables (numerical, no missing values).
    - dependent_var: str, name of the dependent variable column (Y).
    - independent_vars: list[str], names of independent variable columns (X1, X2, ...).

    Returns:
    - results: dict, containing SST, SSR, SSE, Se², Se, and diagnostics.
    """
    # Validate inputs
    if dependent_var not in data.columns or not all(var in data.columns for var in independent_vars):
        raise ValueError("Specified variables not found in DataFrame.")
    if data[dependent_var].isnull().any() or data[independent_vars].isnull().any().any():
        raise ValueError("Data contains missing values.")
    
    # Extract data
    y = data[dependent_var]
    X = data[independent_vars]
    n = len(y)
    
    # Fit the regression model
    X_sm = sm.add_constant(X)
    model = sm.OLS(y, X_sm).fit()
    
    # Get observed, predicted, and mean values
    y_pred = model.fittedvalues
    y_mean = y.mean()
    
    # Compute Sum of Squares
    sst = np.sum((y - y_mean) ** 2)
    ssr = np.sum((y_pred - y_mean) ** 2)
    sse = np.sum((y - y_pred) ** 2)
    
    # Compute variance and standard error of the estimate
    k = len(independent_vars)
    se_squared = sse / (n - k - 1) if n > k + 1 else np.nan
    se = np.sqrt(se_squared) if not np.isnan(se_squared) else np.nan
    
    # Verify SST = SSR + SSE
    sum_squares_verified = np.abs(sst - (ssr + sse)) < 1e-10
    
    # Diagnostics
    diagnostics = {
        'sum_squares_verified': sum_squares_verified,
        'sample_size': n,
        'degrees_of_freedom': n - k - 1 if n > k + 1 else 0
    }
    
    results = {
        'SST': sst,
        'SSR': ssr,
        'SSE': sse,
        'Se_squared': se_squared,
        'Se': se,
        'diagnostics': diagnostics
    }
    
    return results


############# 3.2.5.2.2 Đánh giá qua hệ số xác định #############


def evaluate_coefficient_of_determination(
    data: pd.DataFrame,
    dependent_var: str,
    independent_vars: list[str]
) -> dict[str, float]:
    """
    Evaluate the fit of a multivariate regression model using R² and Adjusted R².

    Parameters:
    - data: pd.DataFrame, columns include dependent and independent variables (numerical, no missing values).
    - dependent_var: str, name of the dependent variable column (Y).
    - independent_vars: list[str], names of independent variable columns (X1, X2, ...).

    Returns:
    - results: dict, containing R², Adjusted R², and diagnostics.
    """
    # Validate inputs
    if dependent_var not in data.columns or not all(var in data.columns for var in independent_vars):
        raise ValueError("Specified variables not found in DataFrame.")
    if data[dependent_var].isnull().any() or data[independent_vars].isnull().any().any():
        raise ValueError("Data contains missing values.")
    
    # Extract data
    y = data[dependent_var]
    X = data[independent_vars]
    n = len(y)
    k = len(independent_vars)
    
    # Fit the regression model
    X_sm = sm.add_constant(X)
    model = sm.OLS(y, X_sm).fit()
    
    # Get R² and Adjusted R²
    r_squared = model.rsquared
    r_squared_adj = model.rsquared_adj
    
    # Compute manual R² for k=2
    manual_r_squared = np.nan
    if k == 2:
        beta_1 = model.params[independent_vars[0]]
        beta_2 = model.params[independent_vars[1]]
        y_mean = y.mean()
        x1 = X[independent_vars[0]]
        x2 = X[independent_vars[1]]
        x1_mean = x1.mean()
        x2_mean = x2.mean()
        sum_y_x1 = np.sum(y * x1) - n * y_mean * x1_mean
        sum_y_x2 = np.sum(y * x2) - n * y_mean * x2_mean
        sum_y_squared = np.sum(y ** 2) - n * y_mean ** 2
        numerator = beta_1 * sum_y_x1 + beta_2 * sum_y_x2
        denominator = sum_y_squared
        manual_r_squared = numerator / denominator if abs(denominator) > 1e-10 else np.nan
    
    # Verify Adjusted R²
    r_squared_adj_calc = 1 - (1 - r_squared) * (n - 1) / (n - k - 1) if n > k + 1 else np.nan
    
    # Diagnostics
    diagnostics = {
        'sample_size': n,
        'num_predictors': k,
        'manual_r_squared': manual_r_squared if k == 2 else 'Not computed (k ≠ 2)',
        'r_squared_adj_verified': np.abs(r_squared_adj - r_squared_adj_calc) < 1e-10 if not np.isnan(r_squared_adj_calc) else False,
        'degrees_of_freedom': n - k - 1 if n > k + 1 else 0,
        'R-squared_status': (
            'Insufficient' if r_squared < 0.3 else
            'Acceptable (weak model)' if 0.3 <= r_squared < 0.5 else
            'Fairly good' if 0.5 <= r_squared <= 0.7 else
            'Good' if 0.7 < r_squared <= 0.9 else
            'Possible overfitting'
        ),
        'Adjusted R-squared_status': (
            'Acceptable' if r_squared_adj >= 0.5 else
            'Insufficient'
        ),
        'optimal_R-squared': '0.5–0.7 (avoids overfitting)',
        'notes': 'Adjusted R² ≥ 0.5 preferred for explanatory power',
        'warnings': [
            w for w in [
                'Poor model fit: R² < 0.3' if r_squared < 0.3 else None,
                'Possible overfitting: R² > 0.9' if r_squared > 0.9 else None,
                'Insufficient explanatory power: Adjusted R² < 0.5' if r_squared_adj < 0.5 else None
            ] if w is not None
        ]
    }
    
    results = {
        'R_squared': r_squared,
        'R_squared_adjusted': r_squared_adj,
        'diagnostics': diagnostics
    }
    
    return results


#---------------------------------------------------------#
# 3.2.5.3 Kiểm định mô hình
#---------------------------------------------------------#

def student_t_test(
    data: pd.DataFrame,
    dependent_var: str,
    independent_vars: list[str]
) -> dict[str, Union[pd.DataFrame, dict]]:
    """
    Perform Student's t-Test for regression coefficients per Section 3.2.5.3.
    
    Tests statistical significance of each coefficient (βi) using t = (βi - 0) / Sbi (Formula 23).
    
    Parameters:
    - data: pd.DataFrame, columns include dependent and independent variables (numerical, no missing values).
    - dependent_var: str, name of the dependent variable column (Y).
    - independent_vars: list[str], names of independent variable columns (X1, X2, ...).
    
    Returns:
    - results: dict, containing t-statistics, p-values, and significance diagnostics.
    """
    # Validate inputs
    if dependent_var not in data.columns or not all(var in data.columns for var in independent_vars):
        raise ValueError("Specified variables not found in DataFrame.")
    if data[dependent_var].isnull().any() or data[independent_vars].isnull().any().any():
        raise ValueError("Data contains missing values.")
    
    # Extract data
    y = data[dependent_var]
    X = data[independent_vars]
    n = len(y)
    
    # Fit the regression model
    X_sm = sm.add_constant(X)  # Add intercept term
    model = sm.OLS(y, X_sm).fit()
    
    # Extract t-statistics and p-values
    t_stats = model.tvalues
    p_values = model.pvalues
    
    # Create results DataFrame (remove 'significant' column)
    results_df = pd.DataFrame({
        't_statistic': t_stats,
        'p_value': p_values
    })
    
    # Updated diagnostics (aligned with section 3.2.9 and 3.2.8 note)
    diagnostics = {
        'sample_size': n,
        'significance_level': 0.05,
        'significance_status': {
            var: 'Significant' if p < 0.05 else 'Not Significant'
            for var, p in p_values.items()
        },
        'optimal': 'p < 0.05',
        'variables_to_remove': [var for var, p in p_values.items() if p > 0.05 and var != 'const'],
        'warnings': ['Consider removing variables with p > 0.05: {}'.format(
            ', '.join([var for var, p in p_values.items() if p > 0.05 and var != 'const'])
        )] if any(p > 0.05 for var, p in p_values.items() if var != 'const') else [],
        'note': 'Significance at α = 0.05; p ≤ 0.01 indicates stronger significance.'
    }
    
    return {'results': results_df, 'diagnostics': diagnostics}


def fisher_f_test(
    data: pd.DataFrame,
    dependent_var: str,
    independent_vars: list[str]
) -> dict[str, Union[float, dict]]:
    """
    Perform Fisher's F-Test for overall model significance per Section 3.2.5.3.
    
    Uses F = MSR/S²e = SSR/k ÷ SSE/(n-k-1) = R²(n-k-1)/(1-R²)k (Formula 24).
    
    Parameters:
    - data: pd.DataFrame, columns include dependent and independent variables (numerical, no missing values).
    - dependent_var: str, name of the dependent variable column (Y).
    - independent_vars: list[str], names of independent variable columns (X1, X2, ...).
    
    Returns:
    - results: dict, containing F-statistic, p-value, and significance diagnostics.
    """
    # Validate inputs
    if dependent_var not in data.columns or not all(var in data.columns for var in independent_vars):
        raise ValueError("Specified variables not found in DataFrame.")
    if data[dependent_var].isnull().any() or data[independent_vars].isnull().any().any():
        raise ValueError("Data contains missing values.")
    
    # Extract data
    y = data[dependent_var]
    X = data[independent_vars]
    n = len(y)
    k = len(independent_vars)
    
    # Fit the regression model
    X_sm = sm.add_constant(X)  # Add intercept term
    model = sm.OLS(y, X_sm).fit()
    
    # Extract F-statistic and p-value
    f_stat = model.fvalue
    f_pvalue = model.f_pvalue
    
    # Updated diagnostics (aligned with section 3.2.9 and 3.2.8 note)
    diagnostics = {
        'sample_size': n,
        'num_predictors': k,
        'degrees_of_freedom': (k, n - k - 1),
        'suitability': 'Model suitable' if f_pvalue < 0.05 else 'Model unsuitable',
        'significance_level': 0.05,
        'optimal': 'p < 0.05',
        'warnings': ['Adjust model: p > 0.05 indicates model is not suitable'] if f_pvalue > 0.05 else [],
        'note': 'Significance at α = 0.05; p ≤ 0.01 indicates stronger model significance.'
    }
    
    return {
        'F_statistic': f_stat,
        'p_value': f_pvalue,
        'diagnostics': diagnostics
    }


def durbin_watson_test(
    data: pd.DataFrame,
    dependent_var: str,
    independent_vars: list[str]
) -> dict[str, Union[float, dict]]:
    """
    Perform Durbin-Watson Test for autocorrelation in residuals per Section 3.2.5.3.
    
    Uses DW = Σ(εi - εi-1)² / Σεi² (Formula 25).
    
    Parameters:
    - data: pd.DataFrame, columns include dependent and independent variables (numerical, no missing values).
    - dependent_var: str, name of the dependent variable column (Y).
    - independent_vars: list[str], names of independent variable columns (X1, X2, ...).
    
    Returns:
    - results: dict, containing DW statistic and diagnostics.
    """
    # Validate inputs
    if dependent_var not in data.columns or not all(var in data.columns for var in independent_vars):
        raise ValueError("Specified variables not found in DataFrame.")
    if data[dependent_var].isnull().any() or data[independent_vars].isnull().any().any():
        raise ValueError("Data contains missing values.")
    
    # Extract data
    y = data[dependent_var]
    X = data[independent_vars]
    n = len(y)
    k = len(independent_vars)
    
    # Fit the regression model
    X_sm = sm.add_constant(X)  # Add intercept term
    model = sm.OLS(y, X_sm).fit()
    
    # Compute Durbin-Watson statistic
    dw_stat = durbin_watson(model.resid)
    
    # Updated diagnostics
    diagnostics = {
        'sample_size': n,
        'num_predictors': k,
        'status': 'No autocorrelation' if 1 <= dw_stat <= 3 else 'Autocorrelation detected',
        'optimal': '1 – 3',
        'warnings': ['Review model: Autocorrelation detected'] if dw_stat < 1 or dw_stat > 3 else [],
        'note': 'Ideal value ~2 (no autocorrelation typically around 2).'
    }
    
    return {'DW_statistic': dw_stat, 'diagnostics': diagnostics}


def homoscedasticity_test(
    data: pd.DataFrame,
    dependent_var: str,
    independent_vars: list[str]
) -> dict[str, Union[dict, dict]]:
    """
    Perform Homoscedasticity Test using Jarque-Bera and Breusch-Pagan tests per Section 3.2.5.3.
    
    Parameters:
    - data: pd.DataFrame, columns include dependent and independent variables (numerical, no missing values).
    - dependent_var: str, name of the dependent variable column (Y).
    - independent_vars: list[str], names of independent variable columns (X1, X2, ...).
    
    Returns:
    - results: dict, containing Jarque-Bera and Breusch-Pagan test results and diagnostics.
    """
    # Validate inputs
    if dependent_var not in data.columns or not all(var in data.columns for var in independent_vars):
        raise ValueError("Specified variables not found in DataFrame.")
    if data[dependent_var].isnull().any() or data[independent_vars].isnull().any().any():
        raise ValueError("Data contains missing values.")
    
    # Extract data
    y = data[dependent_var]
    X = data[independent_vars]
    n = len(y)
    
    # Fit the regression model
    X_sm = sm.add_constant(X)  # Add intercept term
    model = sm.OLS(y, X_sm).fit()
    
    # Jarque-Bera test for normality of residuals
    from scipy import stats
    jb_stat, jb_pvalue = stats.jarque_bera(model.resid)
    
    # Breusch-Pagan test for homoscedasticity
    bp_test = het_breuschpagan(model.resid, X_sm)
    bp_stat, bp_pvalue = bp_test[0], bp_test[1]
    
    # Results
    results = {
        'Jarque-Bera': {
            'statistic': jb_stat,
            'p_value': jb_pvalue,
            'significant': 'Non-normal residuals' if jb_pvalue < 0.05 else 'Normal residuals'
        },
        'Breusch-Pagan': {
            'statistic': bp_stat,
            'p_value': bp_pvalue,
            'significant': 'Heteroscedasticity' if bp_pvalue < 0.05 else 'Homoscedasticity'
        }
    }
    
    # Diagnostics
    diagnostics = {
        'sample_size': n,
        'num_predictors': len(independent_vars),
        'significance_level': 0.05,
        'note': 'Jarque-Bera tests normality; Breusch-Pagan tests constant variance.'
    }
    
    return {'results': results, 'diagnostics': diagnostics}

def variance_inflation_factor_test(
    data: pd.DataFrame,
    independent_vars: list[str]
) -> dict[str, Union[pd.DataFrame, dict]]:
    """
    Compute Variance Inflation Factor (VIF) to detect multicollinearity per Section 3.2.5.3.
    
    Uses VIFj = 1/(1-R²j) (Formula 26).
    
    Parameters:
    - data: pd.DataFrame, columns include independent variables (numerical, no missing values).
    - independent_vars: list[str], names of independent variables columns (X1, X2, ...).
    
    Returns:
    - results: dict, containing VIF values and diagnostics.
    """
    # Validate inputs
    if not all(var in data.columns for var in independent_vars):
        raise ValueError("Specified variables not found in DataFrame.")
    if data[independent_vars].isnull().any().any():
        raise ValueError("Data contains missing values.")
    
    # Extract data and center it (subtract the mean from each variable)
    X = data[independent_vars].copy()
    X_centered = X - X.mean()  # Center the data to match SPSS behavior
    n = len(X)
    
    # Compute VIF for each variable using the centered data
    vif_data = []
    for i, var in enumerate(independent_vars):
        # Compute VIF
        vif = variance_inflation_factor(X_centered.values, i)
        
        # Compute the auxiliary regression to get R² and its statistical significance
        target_var = X_centered[var]
        other_vars = [v for v in independent_vars if v != var]
        X_other = sm.add_constant(X_centered[other_vars])  # Add intercept for the regression
        model = sm.OLS(target_var, X_other).fit()
        r_squared = model.rsquared
        p_value = model.f_pvalue  # p-value of the overall F-test for the regression
        
        # Interpretation based on VIF and significance
        if vif < 2:
            interpretation = 'No multicollinearity'
        elif 2 <= vif <= 10:
            interpretation = 'Acceptable but review'
        else:  # vif > 10
            interpretation = (
                'Severe multicollinearity (remove variable)' if p_value < 0.05
                else 'High VIF but auxiliary regression not significant'
            )
        
        vif_data.append({
            'Variable': var,
            'VIF': vif,
            'R²': r_squared,
            'Auxiliary Regression p-value': p_value,
            'Interpretation': interpretation
        })
    
    # Create results DataFrame
    results_df = pd.DataFrame(vif_data)
    
    # Updated diagnostics
    variables_to_remove = [
        row['Variable'] for row in vif_data
        if row['VIF'] > 10 and row['Auxiliary Regression p-value'] < 0.05
    ]
    diagnostics = {
        'sample_size': n,
        'num_predictors': len(independent_vars),
        'optimal': '< 2',
        'variables_to_remove': variables_to_remove,
        'warnings': [f"Remove variables with VIF > 10 and significant auxiliary regression: {variables_to_remove}"] if variables_to_remove else [],
        'note': 'VIF < 2 indicates no multicollinearity; VIF > 10 with significant auxiliary regression indicates severe multicollinearity.'
    }
    
    return {'results': results_df, 'diagnostics': diagnostics}

#########################################################
################# 3.2.6 Thống kê miêu tả ################
#########################################################

def descriptive_statistics(
    data: Union[pd.DataFrame, pd.Series],
    column: str = None
) -> dict[str, float]:
    """
    Compute descriptive statistics per Section 3.2.6, including measures of central tendency
    (Mean, Median, Mode) and dispersion (Variance, Standard Deviation, Range).
    
    Parameters:
    - data: pd.DataFrame or pd.Series, numerical data with no missing values.
    - column: str, name of the column in DataFrame to analyze (ignored if data is Series).
    
    Returns:
    - results: dict, containing Mean, Median, Mode, Variance, Standard Deviation, Range,
               and diagnostics.
    
    Formulas:
    - Mean: X̄ = ΣXi / n
    - Median: Middle value (odd n) or average of two middle values (even n)
    - Mode: Most frequent value
    - Variance: s² = Σ(Xi - X̄)² / (n-1)
    - Standard Deviation: s = √[Σ(Xi - X̄)² / (n-1)]
    - Range: Range = Xmax - Xmin
    """
    # Handle input type
    if isinstance(data, pd.DataFrame):
        if column is None or column not in data.columns:
            raise ValueError("Column name must be specified and exist in DataFrame.")
        series = data[column]
    elif isinstance(data, pd.Series):
        series = data
    else:
        raise ValueError("Input must be a pandas DataFrame or Series.")
    
    # Validate data
    if series.isnull().any():
        raise ValueError("Data contains missing values.")
    if not np.issubdtype(series.dtype, np.number):
        raise ValueError("Data must be numerical.")
    
    # Convert to numpy array for computations
    x = series.to_numpy()
    n = len(x)
    
    if n == 0:
        raise ValueError("Data is empty.")
    
    # Compute measures of central tendency
    mean = np.mean(x)  # X̄ = ΣXi / n
    
    # Median
    sorted_x = np.sort(x)
    if n % 2 == 0:
        median = (sorted_x[n//2 - 1] + sorted_x[n//2]) / 2
    else:
        median = sorted_x[n//2]
    
    # Mode (handle multiple modes, return the first)
    mode_counts = pd.Series(x).mode()
    mode = mode_counts[0] if not mode_counts.empty else np.nan
    
    # Compute measures of dispersion
    variance = np.var(x, ddof=1)  # s² = Σ(Xi - X̄)² / (n-1)
    std_dev = np.std(x, ddof=1)  # s = √[Σ(Xi - X̄)² / (n-1)]
    range_val = np.max(x) - np.min(x)  # Range = Xmax - Xmin
    
    # Verify computations manually for variance and standard deviation
    manual_variance = np.sum((x - mean) ** 2) / (n - 1) if n > 1 else np.nan
    manual_std_dev = np.sqrt(manual_variance) if not np.isnan(manual_variance) else np.nan
    
    # Diagnostics
    diagnostics = {
        'sample_size': n,
        'variance_verified': np.abs(variance - manual_variance) < 1e-10 if not np.isnan(manual_variance) else False,
        'std_dev_verified': np.abs(std_dev - manual_std_dev) < 1e-10 if not np.isnan(manual_std_dev) else False,
        'degrees_of_freedom': n - 1 if n > 1 else 0
    }
    
    # Results dictionary
    results = {
        'Mean': mean,
        'Median': median,
        'Mode': mode,
        'Variance': variance,
        'Standard Deviation': std_dev,
        'Range': range_val,
        'diagnostics': diagnostics
    }
    
    return results

#########################################################
################# 3.2.7 Thống kê suy luận ###############
#########################################################



#---------------------------------------------------------#
# 3.2.7.2.1 Kiểm định giả thuyết thống kê / Statistical Hypothesis Testing (Z-Test)
#---------------------------------------------------------#

def z_test(
    data: Union[pd.Series, pd.DataFrame],
    column: str = None,
    population_mean: float = 0.0,
    population_std: float = None,
    alpha: float = 0.05,
    alternative: str = 'two-sided'
) -> dict[str, Union[float, str, dict]]:
    """
    Perform a single-sample Z-test per Section 3.2.7.2.1 to test a population mean.
    
    Parameters:
    - data: pd.Series or pd.DataFrame, numerical data for the sample.
    - column: str, column name if data is DataFrame (default: None, expects Series).
    - population_mean: float, hypothesized population mean (μ, default: 0.0).
    - population_std: float, known population standard deviation (σ, default: None, uses sample std).
    - alpha: float, significance level (default: 0.05).
    - alternative: str, 'two-sided', 'greater', or 'less' (default: 'two-sided').
    
    Returns:
    - results: dict, containing Z-statistic, p-value, decision, and diagnostics.
    
    Formula:
    - Z = (X̄ - μ) / (σ / √n), where X̄ is sample mean, μ is population mean,
      σ is population standard deviation, n is sample size.
    """
    # Input validation
    if isinstance(data, pd.DataFrame):
        if column is None or column not in data.columns:
            raise ValueError("Column name must be specified and exist in DataFrame.")
        sample = data[column]
    elif isinstance(data, pd.Series):
        sample = data
    else:
        raise ValueError("Data must be a pandas Series or DataFrame.")
    
    if sample.isnull().any():
        raise ValueError("Data contains missing values.")
    if not np.issubdtype(sample.dtype, np.number):
        raise ValueError("Data must be numerical.")
    
    # Extract sample statistics
    sample_mean = sample.mean()
    n = len(sample)
    
    # Use population standard deviation or sample standard deviation
    if population_std is None:
        sigma = sample.std(ddof=1)  # Sample std with Bessel's correction
    else:
        sigma = population_std
    
    if sigma <= 0:
        raise ValueError("Standard deviation must be positive.")
    if n < 1:
        raise ValueError("Sample size must be at least 1.")
    
    # Compute Z-statistic
    z_stat = (sample_mean - population_mean) / (sigma / np.sqrt(n))
    
    # Compute p-value based on alternative hypothesis
    if alternative == 'two-sided':
        p_value = 2 * (1 - stats.norm.cdf(abs(z_stat)))
    elif alternative == 'greater':
        p_value = 1 - stats.norm.cdf(z_stat)
    elif alternative == 'less':
        p_value = stats.norm.cdf(z_stat)
    else:
        raise ValueError("Alternative must be 'two-sided', 'greater', or 'less'.")
    
    # Decision based on p-value and alpha
    decision = 'Reject H0' if p_value < alpha else 'Fail to reject H0'
    
    # Critical value for two-sided test (for diagnostics)
    critical_value = stats.norm.ppf(1 - alpha / 2) if alternative == 'two-sided' else stats.norm.ppf(1 - alpha)
    
    # Diagnostics
    diagnostics = {
        'sample_size': n,
        'sample_mean': sample_mean,
        'population_mean': population_mean,
        'standard_deviation': sigma,
        'critical_value': critical_value if alternative == 'two-sided' else critical_value,
        'alternative_hypothesis': alternative,
        'confidence_level': 1 - alpha
    }
    
    # Results dictionary
    results = {
        'Z_statistic': z_stat,
        'p_value': p_value,
        'decision': decision,
        'diagnostics': diagnostics
    }
    
    return results

#---------------------------------------------------------#
# 3.2.7.2.2 Khoảng tin cậy (Confidence interval)
#---------------------------------------------------------#

def confidence_interval(
    data: Union[pd.Series, pd.DataFrame],
    column: str = None,
    population_std: float = None,
   _wrapper: bool = False,
    confidence_level: float = 0.95
) -> dict[str, Union[float, dict]]:
    """
    Compute a confidence interval for the population mean per Section 3.2.7.2.2.
    
    Parameters:
    - data: pd.Series or pd.DataFrame, numerical data for the sample.
    - column: str, column name if data is DataFrame (default: None, expects Series).
    - population_std: float, known population standard deviation (σ, default: None, uses sample std).
    - confidence_level: float, confidence level (default: 0.95).
    
    Returns:
    - results: dict, containing lower and upper bounds of the confidence interval and diagnostics.
    
    Formula:
    - CI = X̄ ± Z_{α/2} × (σ / √n), where X̄ is sample mean, σ is standard deviation,
      Z_{α/2} is critical value for confidence level.
    """
    # Input validation
    if isinstance(data, pd.DataFrame):
        if column is None or column not in data.columns:
            raise ValueError("Column name must be specified and exist in DataFrame.")
        sample = data[column]
    elif isinstance(data, pd.Series):
        sample = data
    else:
        raise ValueError("Data must be a pandas Series or DataFrame.")
    
    if sample.isnull().any():
        raise ValueError("Data contains missing values.")
    if not np.issubdtype(sample.dtype, np.number):
        raise ValueError("Data must be numerical.")
    if not 0 < confidence_level < 1:
        raise ValueError("Confidence level must be between 0 and 1.")
    
    # Extract sample statistics
    sample_mean = sample.mean()
    n = len(sample)
    
    # Use population standard deviation or sample standard deviation
    if population_std is None:
        sigma = sample.std(ddof=1)  # Sample std with Bessel's correction
    else:
        sigma = population_std
    
    if sigma <= 0:
        raise ValueError("Standard deviation must be positive.")
    if n < 1:
        raise ValueError("Sample size must be at least 1.")
    
    # Compute critical value
    alpha = 1 - confidence_level
    z_critical = stats.norm.ppf(1 - alpha / 2)
    
    # Compute confidence interval
    margin_of_error = z_critical * (sigma / np.sqrt(n))
    ci_lower = sample_mean - margin_of_error
    ci_upper = sample_mean + margin_of_error
    
    # Diagnostics
    diagnostics = {
        'sample_size': n,
        'sample_mean': sample_mean,
        'standard_deviation': sigma,
        'confidence_level': confidence_level,
        'critical_value': z_critical,
        'margin_of_error': margin_of_error
    }
    
    # Results dictionary
    results = {
        'ci_lower': ci_lower,
        'ci_upper': ci_upper,
        'diagnostics': diagnostics
    }
    
    return results


#---------------------------------------------------------#
# 3.2.7.2.3 Phân tích hồi quy tuyến tính
#---------------------------------------------------------#
# Already implemeted in 3.2.5.1 Hệ số hồi quy




#---------------------------------------------------------#
# Others
#---------------------------------------------------------#
def evaluate_coefficient_of_determination_no_intercept(
    data: pd.DataFrame,
    dependent_var: str,
    independent_vars: list[str]
) -> dict[str, float]:
    """
    Evaluate R² and Adjusted R² for a no-intercept regression model.
    Adapted from evaluate_coefficient_of_determination for regression through the origin.
    
    Parameters:
    - data: pd.DataFrame, columns include dependent and independent variables.
    - dependent_var: str, name of the dependent variable column (Y).
    - independent_vars: list[str], names of independent variable columns (X1, X2, ...).
    
    Returns:
    - results: dict, containing R², Adjusted R², and diagnostics.
    """
    # Validate inputs
    if dependent_var not in data.columns or not all(var in data.columns for var in independent_vars):
        raise ValueError("Specified variables not found in DataFrame.")
    if data[dependent_var].isnull().any() or data[independent_vars].isnull().any().any():
        raise ValueError("Data contains missing values.")
    
    y = data[dependent_var]
    X = data[independent_vars]
    n = len(y)
    k = len(independent_vars)
    
    # Fit no-intercept model
    model = sm.OLS(y, X).fit()
    
    # R² for no-intercept model: SSR / SST, where SST is not centered
    y_pred = model.fittedvalues
    ssr = np.sum(y_pred ** 2)  # Sum of squares regression
    sst = np.sum(y ** 2)  # Total sum of squares (not centered)
    r_squared = ssr / sst if sst > 0 else np.nan
    
    # Adjusted R²: 1 - [(1 - R²)(n) / (n - k)]
    adj_r_squared = 1 - (1 - r_squared) * n / (n - k) if n > k else np.nan
    
    # Diagnostics
    diagnostics = {
        'sample_size': n,
        'num_predictors': k,
        'degrees_of_freedom': n - k,
        'R-squared_status': (
            'Insufficient' if r_squared < 0.3 else
            'Acceptable (weak model)' if 0.3 <= r_squared < 0.5 else
            'Fairly good' if 0.5 <= r_squared <= 0.7 else
            'Good' if 0.7 < r_squared <= 0.9 else
            'Possible overfitting'
        ),
        'Adjusted R-squared_status': (
            'Acceptable' if adj_r_squared >= 0.5 else
            'Insufficient'
        ),
        'optimal_R-squared': '0.5–0.7 (avoids overfitting)',
        'notes': 'Adjusted R² ≥ 0.5 preferred for explanatory power. R² for no-intercept model measures variance about origin.',
        'warnings': [
            w for w in [
                'Poor model fit: R² < 0.3' if r_squared < 0.3 else None,
                'Possible overfitting: R² > 0.9' if r_squared > 0.9 else None,
                'Insufficient explanatory power: Adjusted R² < 0.5' if adj_r_squared < 0.5 else None
            ] if w is not None
        ]
    }
    
    return {
        'R_squared': r_squared,
        'R_squared_adjusted': adj_r_squared,
        'diagnostics': diagnostics
    }

def multivariate_regression_analysis_no_intercept(
    data: pd.DataFrame,
    dependent_var: str,
    independent_vars: list[str]
) -> tuple[None, pd.DataFrame, dict]:
    """
    Perform multivariate linear regression without intercept.
    Adapted from multivariate_regression_analysis for regression through the origin.
    
    Parameters:
    - data: pd.DataFrame, columns include dependent and independent variables.
    - dependent_var: str, name of the dependent variable column (Y).
    - independent_vars: list[str], names of independent variable columns (X1, X2, ...).
    
    Returns:
    - intercept: None (no intercept in model).
    - coefficients: pd.DataFrame, regression coefficients with standard errors and p-values.
    - diagnostics: dict, R-squared, adjusted R-squared, coefficient significance.
    """
    # Validate inputs
    if dependent_var not in data.columns or not all(var in data.columns for var in independent_vars):
        raise ValueError("Specified variables not found in DataFrame.")
    if data[dependent_var].isnull().any() or data[independent_vars].isnull().any().any():
        raise ValueError("Data contains missing values.")
    
    y = data[dependent_var]
    X = data[independent_vars]
    n = len(y)
    
    # Fit no-intercept model
    model = sm.OLS(y, X).fit()
    
    # Coefficients
    coefficients = pd.DataFrame({
        'Coefficient': model.params,
        'Standard Error': model.bse,
        'P-value': model.pvalues
    }, index=independent_vars)
    
    # R² and diagnostics
    r2_results = evaluate_coefficient_of_determination_no_intercept(data, dependent_var, independent_vars)
    
    diagnostics = {
        'R-squared': r2_results['R_squared'],
        'R-squared_status': r2_results['diagnostics']['R-squared_status'],
        'Adjusted R-squared': r2_results['R_squared_adjusted'],
        'Adjusted R-squared_status': r2_results['diagnostics']['Adjusted R-squared_status'],
        'optimal_R-squared': r2_results['diagnostics']['optimal_R-squared'],
        'notes': 'Adjusted R² ≥ 0.5 preferred. R² measures variance about origin.',
        'coefficient_significance': {
            var: 'Highly significant' if p <= 0.01 else 'Significant' if p < 0.05 else 'Insignificant'
            for var, p in model.pvalues.items()
        },
        'optimal_significance': 'p < 0.05 (p ≤ 0.01 preferred)',
        'variables_to_remove': [var for var, p in model.pvalues.items() if p > 0.05],
        'warnings': r2_results['diagnostics']['warnings'] + [
            'Run F-test, Durbin-Watson, and VIF tests for complete evaluation.'
        ],
        'sample_size': n
    }
    
    return None, coefficients, diagnostics

def evaluate_regression_fit_no_intercept(
    data: pd.DataFrame,
    dependent_var: str,
    independent_vars: list[str]
) -> dict[str, float]:
    """
    Evaluate regression fit using Sum of Squares for no-intercept model.
    Adapted from evaluate_regression_fit for regression through the origin.
    
    Parameters:
    - data: pd.DataFrame, columns include dependent and independent variables.
    - dependent_var: str, name of the dependent variable column (Y).
    - independent_vars: list[str], names of independent variable columns (X1, X2, ...).
    
    Returns:
    - results: dict, containing SST, SSR, SSE, Se², Se, and diagnostics.
    """
    # Validate inputs
    if dependent_var not in data.columns or not all(var in data.columns for var in independent_vars):
        raise ValueError("Specified variables not found in DataFrame.")
    if data[dependent_var].isnull().any() or data[independent_vars].isnull().any().any():
        raise ValueError("Data contains missing values.")
    
    y = data[dependent_var]
    X = data[independent_vars]
    n = len(y)
    k = len(independent_vars)
    
    # Fit no-intercept model
    model = sm.OLS(y, X).fit()
    
    # Compute Sum of Squares
    y_pred = model.fittedvalues
    sst = np.sum(y ** 2)  # Total SS (not centered)
    ssr = np.sum(y_pred ** 2)  # Regression SS
    sse = np.sum((y - y_pred) ** 2)  # Residual SS
    
    # Variance and standard error
    se_squared = sse / (n - k) if n > k else np.nan
    se = np.sqrt(se_squared) if not np.isnan(se_squared) else np.nan
    
    # Verify SST = SSR + SSE
    sum_squares_verified = np.abs(sst - (ssr + sse)) < 1e-10
    
    # Diagnostics
    diagnostics = {
        'sum_squares_verified': sum_squares_verified,
        'sample_size': n,
        'degrees_of_freedom': n - k
    }
    
    return {
        'SST': sst,
        'SSR': ssr,
        'SSE': sse,
        'Se_squared': se_squared,
        'Se': se,
        'diagnostics': diagnostics
    }

def _calculate_text_dimensions(text: str, fontsize: int = 10, fontweight: str = 'normal') -> tuple[float, float]:
    """
    Calculate approximate text dimensions in matplotlib units.
    """
    # Much more realistic character dimensions for matplotlib
    char_width = fontsize * 0.008  # Reduced dramatically
    char_height = fontsize * 0.012  # Reduced dramatically
    
    # Adjust for font weight
    if fontweight == 'bold':
        char_width *= 1.1
    
    text_width = len(text) * char_width
    text_height = char_height
    
    return text_width, text_height


def _create_cfa_layout(latent_nodes: list, latent_indicators: dict, orphan_observed: list = None) -> dict:
    """
    Create systematic layout for CFA diagrams with improved spacing to prevent overlap.
    """
    pos = {}
    num_factors = len(latent_nodes)
    orphan_observed = orphan_observed or []
    
    if num_factors == 0 and not orphan_observed:
        return pos
    
    # Determine grid layout for latent factors
    # Handle case with only orphan observed variables
    if num_factors == 0 and orphan_observed:
        return _layout_orphan_variables(orphan_observed)
    
    # Calculate maximum indicator spread for each factor to determine spacing
    max_indicator_spread = 0
    for latent in latent_nodes:
        indicators = latent_indicators.get(latent, [])
        if indicators:
            spread = _calculate_indicator_spread(len(indicators))
            max_indicator_spread = max(max_indicator_spread, spread)
    
    # Determine optimal grid layout for latent factors
    if num_factors <= 4:
        cols = min(2, num_factors)
        rows = (num_factors + cols - 1) // cols
    elif num_factors <= 9:
        cols = 3
        rows = (num_factors + cols - 1) // cols
    else:
        # For many factors, use a more square layout
        cols = int(np.ceil(np.sqrt(num_factors * 1.2)))
        rows = (num_factors + cols - 1) // cols
    
    # Adaptive spacing based on indicator spread
    factor_spacing_x = 3.0 + max_indicator_spread * 0.8  # Horizontal spacing
    factor_spacing_y = 2.5 + max_indicator_spread * 0.6  # Vertical spacing to prevent overlap
    
    # Position latent factors in a centered grid
    total_width = (cols - 1) * factor_spacing_x
    total_height = (rows - 1) * factor_spacing_y

    
    start_x = -total_width / 2
    start_y = total_height / 2

    
    for i, latent in enumerate(latent_nodes):
        row = i // cols
        col = i % cols
        
        x = start_x + col * factor_spacing_x
        y = start_y - row * factor_spacing_y

        
        pos[latent] = (x, y)
        
        # Position indicators around this latent factor
        indicators = latent_indicators.get(latent, [])
        if indicators:
            _position_indicators_around_factor(pos, latent, indicators, (x, y))
    # Handle orphan observed variables at the bottom with sufficient spacing
    if orphan_observed:
        min_y = min(pos[node][1] for node in pos if node in latent_nodes) if latent_nodes else 0
        # Add extra space to prevent overlap with indicators
        orphan_y = min_y - factor_spacing_y
        _add_orphan_variables_to_layout(pos, orphan_observed, orphan_y)

    return pos


def _create_sem_layout(latent_nodes: list, latent_indicators: dict, structural_paths: list, orphan_observed: list = None) -> dict:
    """
    Create systematic layout for SEM diagrams with improved spacing to prevent overlap.
    """
    pos = {}
    orphan_observed = orphan_observed or []
    if not latent_nodes and not orphan_observed:
        return pos
    # Handle case with only orphan observed variables
    if not latent_nodes and orphan_observed:
        return _layout_orphan_variables(orphan_observed)

    # Build dependency graph for topological ordering
    dep_graph = {node: [] for node in latent_nodes}
    in_degree = {node: 0 for node in latent_nodes}
    
    for from_node, to_node in structural_paths:
        if from_node in dep_graph and to_node in dep_graph:
            dep_graph[from_node].append(to_node)
            in_degree[to_node] += 1
    
    # Topological sort to determine levels
    levels = []
    remaining = set(latent_nodes)
    
    while remaining:
        # Find nodes with no incoming edges (exogenous at this level)
        current_level = [node for node in remaining if in_degree[node] == 0]
        
        if not current_level:
            # Handle cycles - pick nodes with minimum in-degree
            min_degree = min(in_degree[node] for node in remaining)
            current_level = [node for node in remaining if in_degree[node] == min_degree]
        
        # Sort nodes in each level for consistency
        current_level.sort()
        levels.append(current_level)
        
        for node in current_level:
            remaining.remove(node)
            for target in dep_graph[node]:
                if target in remaining:
                    in_degree[target] -= 1
    
    # Calculate maximum indicator spread across all factors
    max_indicator_spread = 0
    for latent in latent_nodes:
        indicators = latent_indicators.get(latent, [])
        if indicators:
            spread = _calculate_indicator_spread(len(indicators))
            max_indicator_spread = max(max_indicator_spread, spread)
    
    # Adaptive spacing based on model complexity and indicator spread
    max_level_size = max(len(level) for level in levels)
    
    level_spacing_x = 3.5 + max_indicator_spread * 0.5  # Horizontal spacing between levels
    factor_spacing_y = 2.2 + max_indicator_spread * 0.4  # Vertical spacing within levels

    # Position factors by levels (left to right: exogenous to endogenous)
    total_width = (len(levels) - 1) * level_spacing_x
    start_x = -total_width / 2
    
    for level_idx, level_nodes in enumerate(levels):
        x = start_x + level_idx * level_spacing_x
        
        total_height = (len(level_nodes) - 1) * factor_spacing_y
        start_y = total_height / 2

        for i, node in enumerate(level_nodes):
            y = start_y - i * factor_spacing_y
            pos[node] = (x, y)
            
            # Position indicators around this factor
            indicators = latent_indicators.get(node, [])
            if indicators:
                _position_indicators_around_factor(pos, node, indicators, (x, y))

    # Handle orphan observed variables
    if orphan_observed:
        min_y = min(pos[node][1] for node in pos if node in latent_nodes) if latent_nodes else 0
        # Add sufficient space to prevent overlap
        orphan_y = min_y - factor_spacing_y * 1.5
        _add_orphan_variables_to_layout(pos, orphan_observed, orphan_y)

    return pos

def _calculate_indicator_spread(num_indicators: int) -> float:
    """
    Calculate the vertical spread of indicators based on their number.
    """
    if num_indicators <= 1:
        return 0.0
    elif num_indicators == 2:
        return 1.2  # Two indicators spread vertically
    elif num_indicators == 3:
        return 1.6  # Three indicators spread
    else:
        # For many indicators, calculate based on semicircle arrangement
        base_radius = 1.2 + num_indicators * 0.1
        # Maximum spread is approximately 2 * radius
        return base_radius * 2.0


def _position_indicators_around_factor(pos: dict, factor: str, indicators: list, factor_pos: tuple):
    """
    Position indicator variables around their latent factor with better spacing to prevent overlap.
    """
    if not indicators:
        return
    
    factor_x, factor_y = factor_pos
    num_indicators = len(indicators)
    # Adaptive radius based on number of indicators
    base_radius = 1.2 + num_indicators * 0.1
    radius = max(base_radius, 1.0)
    
    if num_indicators == 1:
        pos[indicators[0]] = (factor_x + radius, factor_y)
    elif num_indicators == 2:
        # Vertical arrangement for two indicators
        vertical_spacing = 0.8
        pos[indicators[0]] = (factor_x + radius * 0.9, factor_y + vertical_spacing)
        pos[indicators[1]] = (factor_x + radius * 0.9, factor_y - vertical_spacing)
    elif num_indicators == 3:
        pos[indicators[0]] = (factor_x + radius, factor_y)
        pos[indicators[1]] = (factor_x + radius * 0.8, factor_y + 1.0)
        pos[indicators[2]] = (factor_x + radius * 0.8, factor_y - 1.0)
    else:
        # For many indicators, use a more spread out semicircle arrangement
        if num_indicators <= 6:
            # Semicircle arrangement with wider spread
            start_angle = -np.pi/1.8  # Wider angle spread
            end_angle = np.pi/1.8
        else:
            # Even wider spread for many indicators
            start_angle = -np.pi/1.4
            end_angle = np.pi/1.4

        angles = np.linspace(start_angle, end_angle, num_indicators)
        # Increase radius for larger numbers of indicators
        extended_radius = radius + (num_indicators - 4) * 0.1
        
        for i, indicator in enumerate(indicators):
            angle = angles[i]
            x = factor_x + extended_radius * np.cos(angle)
            y = factor_y + extended_radius * np.sin(angle)
            pos[indicator] = (x, y)

def _layout_orphan_variables(orphan_observed: list) -> dict:
    """Layout for observed variables without latent parents."""
    pos = {}
    if not orphan_observed:
        return pos
    
    # Arrange in a grid with better spacing
    num_vars = len(orphan_observed)
    cols = int(np.ceil(np.sqrt(num_vars)))
    rows = (num_vars + cols - 1) // cols
    
    spacing_x = 2.0  # Increased spacing
    spacing_y = 1.5  # Increased spacing
    
    total_width = (cols - 1) * spacing_x
    total_height = (rows - 1) * spacing_y
    
    start_x = -total_width / 2
    start_y = total_height / 2
    
    for i, var in enumerate(orphan_observed):
        row = i // cols
        col = i % cols
        
        x = start_x + col * spacing_x
        y = start_y - row * spacing_y
        
        pos[var] = (x, y)
    
    return pos


def _add_orphan_variables_to_layout(pos: dict, orphan_observed: list, base_y: float):
    """Add orphan observed variables to existing layout with better spacing."""
    if not orphan_observed:
        return
    
    # Arrange orphans in a horizontal row with increased spacing
    num_orphans = len(orphan_observed)
    spacing_x = 2.0  # Increased from 1.5
    
    total_width = (num_orphans - 1) * spacing_x
    start_x = -total_width / 2
    
    for i, var in enumerate(orphan_observed):
        x = start_x + i * spacing_x
        pos[var] = (x, base_y)


def _calculate_figure_size(pos: dict, min_width: int = 8, min_height: int = 6) -> tuple[float, float]:
    """Calculate optimal figure size based on node positions with better margins."""
    if not pos:
        return min_width, min_height
    
    # Get bounds of all positions
    x_coords = [x for x, y in pos.values()]
    y_coords = [y for x, y in pos.values()]
    
    x_min, x_max = min(x_coords), max(x_coords)
    y_min, y_max = min(y_coords), max(y_coords)
    
    # Add larger padding around the diagram to accommodate node sizes
    padding_x = 2.0  # Increased from 1.5
    padding_y = 1.5  # Increased from 1.0
    
    content_width = x_max - x_min + 2 * padding_x
    content_height = y_max - y_min + 2 * padding_y
    
    # Scale to reasonable figure size (matplotlib units)
    scale_factor = 2.8  # Slightly increased
    fig_width = max(min_width, content_width * scale_factor)
    fig_height = max(min_height, content_height * scale_factor)
    
    # Limit maximum size to prevent huge figures
    fig_width = min(fig_width, 24)  # Increased limit
    fig_height = min(fig_height, 20)  # Increased limit
    
    return fig_width, fig_height