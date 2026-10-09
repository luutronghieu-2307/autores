import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
import statsmodels.api as sm
from statsmodels.tsa.vector_ar.vecm import JohansenTestResult
from statsmodels.tsa.vector_ar.var_model import VARResults
from statsmodels.tsa.vector_ar.irf import IRAnalysis
from typing import Optional, Any

DEFAULT_TRANSLATIONS = {
    "en": {
        "time": "Time",
        "value": "Value",
        "acf_title": "Autocorrelation Function (ACF)",
        "pacf_title": "Partial Autocorrelation Function (PACF)",
        "residuals_analysis": "Residuals Analysis",
        "residuals_over_time": "Residuals Over Time",
        "residual_value": "Residual Value",
        "histogram_residuals": "Histogram of Residuals",
        "density": "Density",
        "qq_plot_residuals": "Q-Q Plot of Residuals",
        "forecast_vs_actuals": "Forecast vs Actuals",
        "historical_actuals": "Historical Actuals",
        "forecast": "Forecast",
        "confidence_interval": "Confidence interval",
        "johansen_trace_title": "Johansen Cointegration Test: Trace Statistic",
        "johansen_eigen_title": "Johansen Cointegration Test: Max Eigenvalue Statistic",
        "cointegrating_relations": "Number of Cointegrating Relations (r)",
        "statistic_value": "Statistic Value",
        "crit_value_90": "90% Crit Value",
        "crit_value_95": "95% Crit Value",
        "crit_value_99": "99% Crit Value",
        "cointegration_test_for": "Cointegration Test for: {}",
        "var_stability_title": "VAR Model Stability: Roots of Characteristic Polynomial",
        "unit_circle": "Unit Circle",
        "irf_title": "Impulse Response Functions (IRF)",
        "fevd_title": "Forecast Error Variance Decomposition (FEVD)"
    },
    "vi": {
        "time": "Thời gian",
        "value": "Giá trị",
        "acf_title": "Hàm tự tương quan (ACF)",
        "pacf_title": "Hàm tự tương quan riêng (PACF)",
        "residuals_analysis": "Phân tích phần dư",
        "residuals_over_time": "Phần dư theo thời gian",
        "residual_value": "Giá trị phần dư",
        "histogram_residuals": "Biểu đồ tần suất phần dư",
        "density": "Mật độ",
        "qq_plot_residuals": "Biểu đồ Q-Q của phần dư",
        "forecast_vs_actuals": "Dự báo so với thực tế",
        "historical_actuals": "Giá trị thực tế lịch sử",
        "forecast": "Dự báo",
        "confidence_interval": "Khoảng tin cậy",
        "johansen_trace_title": "Kiểm định Johansen: Thống kê Trace",
        "johansen_eigen_title": "Kiểm định Johansen: Thống kê Giá trị riêng tối đa",
        "cointegrating_relations": "Số lượng quan hệ đồng liên kết (r)",
        "statistic_value": "Giá trị thống kê",
        "crit_value_90": "Giá trị tới hạn 90%",
        "crit_value_95": "Giá trị tới hạn 95%",
        "crit_value_99": "Giá trị tới hạn 99%",
        "cointegration_test_for": "Kiểm định đồng liên kết cho: {}",
        "var_stability_title": "Độ ổn định mô hình VAR: Các nghiệm của đa thức đặc trưng",
        "unit_circle": "Vòng tròn đơn vị",
        "irf_title": "Hàm phản ứng xung (IRF)",
        "fevd_title": "Phân rã phương sai sai số dự báo (FEVD)"
    }
}

def get_t_dict(t: Optional[dict] = None) -> dict:
    """Helper to get the translation dictionary."""
    if t is None:
        return DEFAULT_TRANSLATIONS["en"]
    return t


def plot_time_series(
    series_dict: dict[str, pd.Series],
    title: str,
    xlabel: Optional[str] = None,
    ylabel: Optional[str] = None,
    show_legend: bool = True,
    t: Optional[dict] = None
) -> Figure:
    """
    Plots one or more time series on the same axes.
    """
    t = get_t_dict(t)
    fig, ax = plt.subplots(figsize=(6, 3))
    for label, series_data in series_dict.items():
        if isinstance(series_data, pd.Series):
            ax.plot(series_data.index, series_data.values, label=label)
        else:
            raise TypeError(f"Data for '{label}' is not a pandas Series.")
    ax.set_title(title)
    ax.set_xlabel(xlabel if xlabel is not None else t["time"])
    ax.set_ylabel(ylabel if ylabel is not None else t["value"])
    if show_legend and len(series_dict) > 1:
        ax.legend()
    ax.grid(True)
    plt.tight_layout()
    return fig

def plot_time_series_before_after(
    original_series: pd.Series,
    transformed_series: pd.Series,
    title_original: str,
    title_transformed: str,
    suptitle: str,
    t: Optional[dict] = None
) -> Figure:
    """
    Side-by-side or top-bottom plots for comparison.
    """
    t = get_t_dict(t)
    fig, axes = plt.subplots(2, 1, figsize=(6, 4))
    
    axes[0].plot(original_series.index, original_series.values, label=title_original)
    axes[0].set_title(title_original)
    axes[0].set_xlabel(t["time"])
    axes[0].set_ylabel(t["value"])
    axes[0].grid(True)
    axes[0].legend()

    axes[1].plot(transformed_series.index, transformed_series.values, label=title_transformed, color='orange')
    axes[1].set_title(title_transformed)
    axes[1].set_xlabel(t["time"])
    axes[1].set_ylabel(t["value"])
    axes[1].grid(True)
    axes[1].legend()
    
    fig.suptitle(suptitle, fontsize=16)
    plt.tight_layout(rect=[0, 0, 1, 0.96])
    return fig

def plot_acf_pacf(
    series: pd.Series,
    lags: Optional[int] = None,
    title_suffix: str = "",
    t: Optional[dict] = None
) -> Figure:
    """
    Plots ACF and PACF using statsmodels.
    """
    t = get_t_dict(t)
    if not isinstance(series, pd.Series):
        raise TypeError("Input 'series' must be a pandas Series.")
    
    fig, axes = plt.subplots(2, 1, figsize=(6, 4))
    
    sm.graphics.tsa.plot_acf(series.dropna(), lags=lags, ax=axes[0], zero=False)
    axes[0].set_title(f'{t["acf_title"]}{title_suffix}')
    
    sm.graphics.tsa.plot_pacf(series.dropna(), lags=lags, ax=axes[1], zero=False, method='ywm')
    axes[1].set_title(f'{t["pacf_title"]}{title_suffix}')
    
    plt.tight_layout()
    return fig

def plot_residuals_overview(
    residuals: pd.Series,
    title: Optional[str] = None,
    t: Optional[dict] = None
) -> Figure:
    """
    Creates a multi-panel plot: residuals over time, histogram, Q-Q plot.
    """
    t = get_t_dict(t)
    if not isinstance(residuals, pd.Series):
        raise TypeError("Input 'residuals' must be a pandas Series.")
        
    fig = plt.figure(figsize=(6, 5))
    gs = fig.add_gridspec(2, 2)

    ax1 = fig.add_subplot(gs[0, :])
    ax1.plot(residuals.index, residuals.values)
    ax1.axhline(0, color='r', linestyle='--')
    ax1.set_title(t["residuals_over_time"])
    ax1.set_xlabel(t["time"])
    ax1.set_ylabel(t["residual_value"])
    ax1.grid(True)

    ax2 = fig.add_subplot(gs[1, 0])
    ax2.hist(residuals.dropna(), bins=30, density=True, alpha=0.7, color='blue')
    try:
        residuals.dropna().plot(kind='kde', ax=ax2, color='red', secondary_y=False)
    except Exception:
        pass
    ax2.set_title(t["histogram_residuals"])
    ax2.set_xlabel(t["residual_value"])
    ax2.set_ylabel(t["density"])
    ax2.grid(True)

    ax3 = fig.add_subplot(gs[1, 1])
    sm.qqplot(residuals.dropna(), line='s', ax=ax3)
    ax3.set_title(t["qq_plot_residuals"])
    ax3.grid(True)
    
    fig.suptitle(title if title is not None else t["residuals_analysis"], fontsize=8)
    plt.tight_layout(rect=[0, 0, 1, 0.95])
    return fig

def plot_forecast_vs_actual(
    actual_history: pd.Series,
    forecast_values: pd.Series,
    confidence_intervals: Optional[pd.DataFrame] = None,
    title: Optional[str] = None,
    t: Optional[dict] = None
) -> Figure:
    """
    Plots historical data, forecasts, and optional confidence intervals.
    """
    t = get_t_dict(t)
    fig, ax = plt.subplots(figsize=(6, 3))
    
    if isinstance(actual_history, pd.Series):
        ax.plot(actual_history.index, actual_history.values, label=t["historical_actuals"])
    else:
        raise TypeError("actual_history must be a pandas Series.")

    if isinstance(forecast_values, pd.Series):
        ax.plot(forecast_values.index, forecast_values.values, label=t["forecast"], linestyle='--')
    else:
        raise TypeError("forecast_values must be a pandas Series.")
        
    if confidence_intervals is not None:
        if not isinstance(confidence_intervals, pd.DataFrame):
            raise TypeError("confidence_intervals must be a pandas DataFrame.")
        if 'lower_ci' in confidence_intervals.columns and 'upper_ci' in confidence_intervals.columns:
            ax.fill_between(confidence_intervals.index,
                            confidence_intervals['lower_ci'],
                            confidence_intervals['upper_ci'],
                            color='gray', alpha=0.3, label=t["confidence_interval"])
        else:
            print("Warning: Confidence interval DataFrame must contain 'lower_ci' and 'upper_ci' columns.")
            
    ax.set_title(title if title is not None else t["forecast_vs_actuals"])
    ax.set_xlabel(t["time"])
    ax.set_ylabel(t["value"])
    ax.legend()
    ax.grid(True)
    plt.tight_layout()
    return fig

def plot_johansen_test_results(
    johansen_result: JohansenTestResult,
    series_names: list[str],
    t: Optional[dict] = None
) -> Figure:
    """
    Visualizes Johansen cointegration test trace statistics and eigenvalues
    against critical values.
    """
    t = get_t_dict(t)
    fig, axes = plt.subplots(2, 1, figsize=(6, 5))
    num_series = len(series_names)

    ranks = np.arange(num_series + 1)
    
    ax1 = axes[0]
    ax1.plot(ranks[:num_series], johansen_result.lr1, marker='o', label=t["johansen_trace_title"])
    crit_vals_trace = johansen_result.cvt
    ax1.plot(ranks[:num_series], crit_vals_trace[:, 0], marker='x', linestyle='--', label=t["crit_value_90"])
    ax1.plot(ranks[:num_series], crit_vals_trace[:, 1], marker='x', linestyle='--', label=t["crit_value_95"])
    ax1.plot(ranks[:num_series], crit_vals_trace[:, 2], marker='x', linestyle='--', label=t["crit_value_99"])
    ax1.set_title(t["johansen_trace_title"])
    ax1.set_xlabel(t["cointegrating_relations"])
    ax1.set_ylabel(t["statistic_value"])
    ax1.legend()
    ax1.grid(True)
    ax1.set_xticks(ranks[:num_series])

    ax2 = axes[1]
    ax2.plot(ranks[:num_series], johansen_result.lr2, marker='o', label=t["johansen_eigen_title"])
    crit_vals_max_eig = johansen_result.cvm
    ax2.plot(ranks[:num_series], crit_vals_max_eig[:, 0], marker='x', linestyle='--', label=t["crit_value_90"])
    ax2.plot(ranks[:num_series], crit_vals_max_eig[:, 1], marker='x', linestyle='--', label=t["crit_value_95"])
    ax2.plot(ranks[:num_series], crit_vals_max_eig[:, 2], marker='x', linestyle='--', label=t["crit_value_99"])
    ax2.set_title(t["johansen_eigen_title"])
    ax2.set_xlabel(t["cointegrating_relations"])
    ax2.set_ylabel(t["statistic_value"])
    ax2.legend()
    ax2.grid(True)
    ax2.set_xticks(ranks[:num_series])

    fig.suptitle(t["cointegration_test_for"].format(', '.join(series_names)), fontsize=14)
    plt.tight_layout(rect=[0, 0, 1, 0.96])
    return fig

def plot_var_stability(
    fitted_var_model: VARResults,
    t: Optional[dict] = None
) -> Figure:
    """
    Plots the roots of the characteristic polynomial for a fitted VAR model.
    Roots inside the unit circle indicate stability.
    """
    t = get_t_dict(t)
    fig = fitted_var_model.plot_roots(figsize=(4,4))
    fig.suptitle(t["var_stability_title"], fontsize=14)
    ax = fig.get_axes()[0]
    circle = plt.Circle((0, 0), 1, fill=False, color='red', linestyle='--', linewidth=1.5, label=t["unit_circle"])
    ax.add_artist(circle)
    if not any(label.get_text() == t["unit_circle"] for label in ax.get_legend().get_texts()):
         handles, labels = ax.get_legend_handles_labels()
         handles.append(circle)
         labels.append(t["unit_circle"])
         ax.legend(handles, labels)
    plt.tight_layout(rect=[0, 0, 1, 0.95])
    return fig

def plot_impulse_response_functions(
    irf_results: IRAnalysis,
    impulse: Optional[str] = None,
    response: Optional[list[str]] = None,
    plot_stderr: bool = True,
    t: Optional[dict] = None
) -> Figure:
    """
    Plots Impulse Response Functions from statsmodels VAR results.
    `irf_results` is typically `fitted_var_model.irf()`
    """
    t = get_t_dict(t)
    fig = irf_results.plot(impulse=impulse, response=response, stderr=plot_stderr, orth=False)
    fig.suptitle(t["irf_title"], fontsize=14)
    plt.tight_layout(rect=[0, 0, 1, 0.96])
    return fig

def plot_forecast_error_variance_decomposition(
    fitted_var_model: VARResults,
    periods: Optional[int] = None,
    t: Optional[dict] = None
) -> Figure:
    """
    Plots Forecast Error Variance Decomposition (FEVD) results.
    Takes a fitted VAR model and computes FEVD internally.
    """
    t = get_t_dict(t)
    fevd_results = fitted_var_model.fevd(periods=periods)
    fig = fevd_results.plot()
    fig.suptitle(t["fevd_title"], fontsize=14)
    plt.tight_layout(rect=[0, 0, 1, 0.96])
    return fig