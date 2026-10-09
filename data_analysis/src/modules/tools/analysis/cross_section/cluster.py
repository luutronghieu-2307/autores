import os
import base64
import logging
from io import BytesIO
from datetime import datetime

import numpy as np
import pandas as pd
import seaborn as sns
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

from sklearn.decomposition import PCA
from sklearn.cluster import KMeans, DBSCAN
from sklearn.mixture import GaussianMixture
from sklearn.metrics import silhouette_score, davies_bouldin_score
from sklearn.preprocessing import StandardScaler

from scipy.cluster.hierarchy import dendrogram, linkage, fcluster

from data_analysis.src.schemas.analyzer_states import (
    Variable, 
    ToolOutput, 
    VariableRole, 
    VariableType, 
    ScaleType
    )
from data_analysis.src.modules.utils import serialize_dict

from data_analysis.src.modules.tools.analysis.cross_section.pipeline_utils import get_t_dict, format_title_with_count

logger = logging.getLogger(__name__)



######################################################
################## HELPER FUNCTIONS ##################
######################################################

def compute_gap_statistic(X: pd.DataFrame, k_range: list[int], n_refs: int = 10) -> list[float]:
    """Compute gap statistic for selecting optimal k."""
    gaps = []
    X_np = X.to_numpy()
    for k in k_range:
        model = KMeans(n_clusters=k, random_state=42, n_init=10)
        model.fit(X)
        log_wk = np.log(model.inertia_)
        
        # Generate reference datasets
        ref_log_wks = []
        for _ in range(n_refs):
            X_ref = np.random.uniform(X_np.min(axis=0), X_np.max(axis=0), X_np.shape)
            ref_model = KMeans(n_clusters=k, random_state=42, n_init=10)
            ref_model.fit(X_ref)
            ref_log_wks.append(np.log(ref_model.inertia_))
        
        gap = np.mean(ref_log_wks) - log_wk
        gaps.append(gap)
    return gaps

def compute_cluster_characteristics(data: pd.DataFrame, cluster_labels: np.ndarray, variables: list[str]) -> pd.DataFrame:
    """Compute means and frequencies for each cluster."""
    df = data[variables].copy()
    df['Cluster'] = cluster_labels
    characteristics = df.groupby('Cluster').agg(['mean', 'count']).round(3)
    return characteristics

def generate_scatter_plot(data: pd.DataFrame, cluster_labels: np.ndarray, t: dict = None) -> str:
    """Generate a 2D scatter plot using PCA with improved layout and readability."""
    t_dict = t or {
        "pca_comp1": "PCA Component 1",
        "pca_comp2": "PCA Component 2",
        "scatter_title": "Cluster Scatter Plot (PCA)"
    }
    pca = PCA(n_components=2)
    X_pca = pca.fit_transform(data)
    
    plt.figure(figsize=(5, 4))
    palette = sns.color_palette('deep', n_colors=len(np.unique(cluster_labels)))
    
    sns.scatterplot(x=X_pca[:, 0], y=X_pca[:, 1], hue=cluster_labels, palette=palette, s=50, alpha=0.8)
    
    plt.xlabel(t_dict.get("pca_comp1", "PCA Component 1"), fontsize=6)
    plt.ylabel(t_dict.get("pca_comp2", "PCA Component 2"), fontsize=6)
    plt.title(t_dict.get("scatter_title", "Cluster Scatter Plot (PCA)"), fontsize=7, pad=7)
    plt.grid(True, linestyle='--', alpha=0.6)
    plt.tight_layout()
    
    buffer = BytesIO()
    plt.savefig(buffer, format="png", dpi=300)
    buffer.seek(0)
    content = base64.b64encode(buffer.getvalue()).decode("utf-8")
    plt.close()
    return content

def generate_elbow_plot(metric_values: list[float], k_range: list[int], metric_name: str, t: dict = None) -> str:
    """Generate a generic elbow plot for clustering metrics with full x-axis ticks and improved layout."""
    t_dict = t or {
        "k_label": "Number of Clusters (k)",
        "elbow_title": "Elbow Plot for Optimal k ({})"
    }
    plt.figure(figsize=(5, 3))
    
    plt.plot(k_range, metric_values, marker='o', linestyle='-', markersize=8)
    plt.xticks(k_range)
    
    plt.xlabel(t_dict.get("k_label", "Number of Clusters (k)"), fontsize=12)
    plt.ylabel(metric_name, fontsize=12)
    elbow_title = t_dict.get("elbow_title", "Elbow Plot for Optimal k ({})").format(metric_name)
    plt.title(elbow_title, fontsize=7, pad=7)
    plt.grid(True, linestyle='--', alpha=0.6)
    plt.tight_layout()
    
    buffer = BytesIO()
    plt.savefig(buffer, format="png", dpi=300)
    buffer.seek(0)
    content = base64.b64encode(buffer.getvalue()).decode("utf-8")
    plt.close()
    return content

def generate_dendrogram_plot(data: pd.DataFrame, t: dict = None) -> str:
    """Generate dendrogram for hierarchical clustering with a larger, more readable layout."""
    t_dict = t or {
        "dendro_xlabel": "Data Points (or Cluster Index)",
        "dendro_ylabel": "Distance (Ward Linkage)",
        "dendro_title": "Hierarchical Clustering Dendrogram"
    }
    Z = linkage(data, method='ward')
    
    plt.figure(figsize=(7, 4))
    dendrogram(Z)
    
    plt.xlabel(t_dict.get("dendro_xlabel", "Data Points (or Cluster Index)"), fontsize=6)
    plt.ylabel(t_dict.get("dendro_ylabel", "Distance (Ward Linkage)"), fontsize=6)
    plt.title(t_dict.get("dendro_title", "Hierarchical Clustering Dendrogram"), fontsize=7, pad=10)
    plt.tight_layout()
    
    buffer = BytesIO()
    plt.savefig(buffer, format="png", dpi=300)
    buffer.seek(0)
    content = base64.b64encode(buffer.getvalue()).decode("utf-8")
    plt.close()
    return content

######################################################
##################### CLUSTERING #####################
######################################################

def run_clustering_analysis(
    data: pd.DataFrame,
    variables: list[Variable],
    params: dict
) -> ToolOutput:
    """
    Perform clustering analysis using specified algorithm, evaluate clusters, and generate a report.
    
    Parameters:
        data: Input DataFrame containing the data
        variables: list of Variable objects describing the data columnsdpi=300)
        params: dictionary containing analysis parameters
            - algorithm (str): clustering algorithm - 'kmeans', 'gmm', 'hierarchical', 'dbscan' (default: 'kmeans')
            - k_range (list[int]): range of k values to test (default: [2-12])
            - output_dir (str): base output directory name
            - save_files (bool): whether to save generated files to disk
            - variable_names (Dict): mapping of variable codes to display names
            - eps (float): epsilon parameter for DBSCAN (default: 'auto')
            - min_samples (int): minimum samples for DBSCAN (default: 5)
    
    Returns:
        ToolOutput: Contains results, logs, file contents, and suggested actions
    """
    # Extract parameters at the start
    algorithm = params.get("algorithm", "kmeans").lower()
    k_range = params.get("k_range", [2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12])
    base_output_dir = params.get("output_dir", "clus")
    save_files = params.get("save_files", False)
    variable_names_map = params.get("variable_names", {v.code: v.name for v in variables})
    eps_param = params.get("eps", "auto")
    min_samples = params.get("min_samples", 5)

    # Translation dictionary
    translations = {
        "en": {
            "preprocessing_header": "**Variable Preprocessing:**",
            "using_continuous": "- Using variable '{var_name}' ({var_code}) as continuous feature",
            "onehot_nominal": "- One-hot encoded nominal variable '{var_name}' ({var_code}) into: {dummy_names}",
            "unsupported_scale": "- Warning: Variable '{var_name}' ({var_code}) has unsupported scale '{scale}' and will be skipped",
            "error_no_variables": "**Error**: No variables suitable for clustering after preprocessing.",
            "warning_low_variance": "**Warning**: Low variance detected in variables: {vars}. Consider removing them.",
            "data_standardized": "Data has been standardized before applying the {algorithm} algorithm.",
            "running_kmeans": "**Running K-means clustering** with k_range={k_range}, random_state=42",
            "optimal_k_kmeans": "Optimal k={optimal_k} selected based on silhouette, Davies-Bouldin, and gap statistic.",
            "running_hierarchical": "**Running Hierarchical clustering** with method='ward'",
            "optimal_k_hierarchical": "Optimal k={optimal_k} suggested based on largest distance jump in dendrogram.",
            "running_dbscan": "**Running DBSCAN clustering** with initial min_samples={min_samples}",
            "searching_eps": "Searching for optimal 'eps' in range {min_eps:.2f} to {max_eps:.2f}",
            "found_dbscan_params": "Found optimal DBSCAN parameters: eps={eps:.3f}, min_samples={min_samples} with Silhouette Score={score:.3f}",
            "warning_dbscan_failed": "**Warning**: DBSCAN could not find a solution with at least 2 clusters. Data may not be suitable for DBSCAN with current parameter search range.",
            "running_gmm": "**Running Gaussian Mixture Model clustering** with k_range={k_range}, random_state=42",
            "optimal_k_gmm": "Optimal k={optimal_k} selected based on BIC and silhouette score.",
            "error_invalid_algorithm": "**Error**: Invalid algorithm '{algorithm}'. Supported algorithms: kmeans, hierarchical, dbscan, gmm.",
            "error_clustering_failed": "**Error**: Clustering '{algorithm}' failed to produce a valid multi-cluster solution.",
            "warning_small_clusters": "**Warning**: Small clusters detected with size < 5% of data: {clusters}. Consider merging or re-evaluating.",
            "cluster_noise": "Cluster -1 (Noise): Contains {count} points that do not belong to any cluster.",
            "cluster_desc_nominal": "'{var_name}': {value:.1f}%",
            "cluster_desc_continuous": "'{var_name}': mean = {value:.3f}",
            "cluster_member_count": "Cluster {cluster_id} ({count} members): {desc}",
            "report_title": "# Clustering Analysis Report",
            "section_algorithm": "\n## Algorithm and Variables",
            "algorithm_description": "Clustering was performed using the **{algorithm}** algorithm on variables: {variables}",
            "section_parameters": "\n### Parameters",
            "param_algorithm": "- Algorithm: {algorithm}",
            "param_k_range": "- k_range: {k_range}",
            "param_dbscan": "- eps: {eps:.3f}, min_samples: {min_samples}",
            "param_hierarchical": "- Linkage method: ward, optimal_k: {optimal_k}",
            "section_characteristics": "\n### Cluster Characteristics",
            "characteristics_table": "**Cluster characteristics table:** `{filename}`",
            "section_interpretation": "\n**Interpretation:**",
            "section_quality": "\n### Cluster Quality Metrics",
            "metric_silhouette": "- Silhouette Score = {score:.3f} ({quality} separation)",
            "metric_db": "- Davies-Bouldin Index = {score:.3f} (lower is better)",
            "metric_wss": "- WSS = {value}",
            "metric_bic": "- BIC = {value}",
            "metric_noise": "- Noise points = {count} ({percent:.1f}% of data)",
            "section_visualizations": "\n### Visualizations",
            "viz_scatter": "- **Scatter Plot (PCA):** `{filename}`",
            "viz_elbow_wss": "- **Elbow Plot (WSS):** `{filename}`",
            "viz_elbow_bic": "- **Elbow Plot (BIC):** `{filename}`",
            "viz_dendrogram": "- **Dendrogram:** `{filename}`",
            "viz_elbow_distance": "- **Elbow Plot (Linkage Distance):** `{filename}`",
            "section_conclusion": "\n### Conclusion",
            "conclusion_optimal_k": "**Optimal Number of Clusters:** {optimal_k}",
            "quality_good": "good",
            "quality_moderate": "moderate",
            "quality_poor": "poor",
            "pca_comp1": "PCA Component 1",
            "pca_comp2": "PCA Component 2",
            "scatter_title": "Cluster Scatter Plot (PCA)",
            "k_label": "Number of Clusters (k)",
            "elbow_title": "Elbow Plot for Optimal k ({})",
            "dendro_xlabel": "Data Points (or Cluster Index)",
            "dendro_ylabel": "Distance (Ward Linkage)",
            "dendro_title": "Hierarchical Clustering Dendrogram"
        },
        "vi": {
            "preprocessing_header": "**Tiền Xử Lý Biến:**",
            "using_continuous": "- Sử dụng biến '{var_name}' ({var_code}) làm đặc trưng liên tục",
            "onehot_nominal": "- Mã hóa one-hot biến danh nghĩa '{var_name}' ({var_code}) thành: {dummy_names}",
            "unsupported_scale": "- Cảnh báo: Biến '{var_name}' ({var_code}) có thang đo không được hỗ trợ '{scale}' và sẽ bị bỏ qua",
            "error_no_variables": "**Lỗi**: Không có biến nào phù hợp để phân cụm sau tiền xử lý.",
            "warning_low_variance": "**Cảnh Báo**: Phát hiện phương sai thấp ở các biến: {vars}. Xem xét loại bỏ chúng.",
            "data_standardized": "Dữ liệu đã được chuẩn hóa trước khi áp dụng thuật toán {algorithm}.",
            "running_kmeans": "**Đang Chạy Phân Cụm K-means** với k_range={k_range}, random_state=42",
            "optimal_k_kmeans": "K tối ưu={optimal_k} được chọn dựa trên silhouette, Davies-Bouldin và thống kê gap.",
            "running_hierarchical": "**Đang Chạy Phân Cụm Phân Cấp** với method='ward'",
            "optimal_k_hierarchical": "K tối ưu={optimal_k} được đề xuất dựa trên bước nhảy khoảng cách lớn nhất trong dendrogram.",
            "running_dbscan": "**Đang Chạy Phân Cụm DBSCAN** với min_samples ban đầu={min_samples}",
            "searching_eps": "Đang tìm kiếm 'eps' tối ưu trong khoảng {min_eps:.2f} đến {max_eps:.2f}",
            "found_dbscan_params": "Tìm thấy tham số DBSCAN tối ưu: eps={eps:.3f}, min_samples={min_samples} với Silhouette Score={score:.3f}",
            "warning_dbscan_failed": "**Cảnh Báo**: DBSCAN không thể tìm được giải pháp với ít nhất 2 cụm. Dữ liệu có thể không phù hợp với DBSCAN với phạm vi tham số hiện tại.",
            "running_gmm": "**Đang Chạy Phân Cụm Gaussian Mixture Model** với k_range={k_range}, random_state=42",
            "optimal_k_gmm": "K tối ưu={optimal_k} được chọn dựa trên BIC và điểm silhouette.",
            "error_invalid_algorithm": "**Lỗi**: Thuật toán không hợp lệ '{algorithm}'. Các thuật toán được hỗ trợ: kmeans, hierarchical, dbscan, gmm.",
            "error_clustering_failed": "**Lỗi**: Phân cụm '{algorithm}' không tạo được giải pháp đa cụm hợp lệ.",
            "warning_small_clusters": "**Cảnh Báo**: Phát hiện cụm nhỏ với kích thước < 5% dữ liệu: {clusters}. Xem xét hợp nhất hoặc đánh giá lại.",
            "cluster_noise": "Cụm -1 (Nhiễu): Chứa {count} điểm không thuộc bất kỳ cụm nào.",
            "cluster_desc_nominal": "'{var_name}': {value:.1f}%",
            "cluster_desc_continuous": "'{var_name}': trung bình = {value:.3f}",
            "cluster_member_count": "Cụm {cluster_id} ({count} thành viên): {desc}",
            "report_title": "# Báo Cáo Phân Tích Phân Cụm",
            "section_algorithm": "\n## Thuật Toán Và Biến",
            "algorithm_description": "Phân cụm được thực hiện bằng thuật toán **{algorithm}** trên các biến: {variables}",
            "section_parameters": "\n### Tham Số",
            "param_algorithm": "- Thuật toán: {algorithm}",
            "param_k_range": "- k_range: {k_range}",
            "param_dbscan": "- eps: {eps:.3f}, min_samples: {min_samples}",
            "param_hierarchical": "- Phương pháp liên kết: ward, optimal_k: {optimal_k}",
            "section_characteristics": "\n### Đặc Điểm Cụm",
            "characteristics_table": "**Bảng đặc điểm cụm:** `{filename}`",
            "section_interpretation": "\n**Giải Thích:**",
            "section_quality": "\n### Chỉ Số Chất Lượng Cụm",
            "metric_silhouette": "- Điểm Silhouette = {score:.3f} (phân tách {quality})",
            "metric_db": "- Chỉ số Davies-Bouldin = {score:.3f} (thấp hơn là tốt hơn)",
            "metric_wss": "- WSS = {value}",
            "metric_bic": "- BIC = {value}",
            "metric_noise": "- Điểm nhiễu = {count} ({percent:.1f}% dữ liệu)",
            "section_visualizations": "\n### Trực Quan Hóa",
            "viz_scatter": "- **Biểu Đồ Phân Tán (PCA):** `{filename}`",
            "viz_elbow_wss": "- **Biểu Đồ Elbow (WSS):** `{filename}`",
            "viz_elbow_bic": "- **Biểu Đồ Elbow (BIC):** `{filename}`",
            "viz_dendrogram": "- **Dendrogram:** `{filename}`",
            "viz_elbow_distance": "- **Biểu Đồ Elbow (Khoảng Cách Liên Kết):** `{filename}`",
            "section_conclusion": "\n### Kết Luận",
            "conclusion_optimal_k": "**Số Cụm Tối Ưu:** {optimal_k}",
            "quality_good": "tốt",
            "quality_moderate": "trung bình",
            "quality_poor": "kém",
            "pca_comp1": "Thành phần PCA 1",
            "pca_comp2": "Thành phần PCA 2",
            "scatter_title": "Biểu đồ phân tán cụm (PCA)",
            "k_label": "Số lượng cụm (k)",
            "elbow_title": "Biểu đồ Elbow cho k tối ưu ({})",
            "dendro_xlabel": "Điểm dữ liệu (hoặc chỉ số cụm)",
            "dendro_ylabel": "Khoảng cách (Ward Linkage)",
            "dendro_title": "Dendrogram phân cụm phân cấp"
        }
    }
    language = params.get("language", "en")
    count = params.get("count", 1)
    t = get_t_dict(translations.get(language, translations["en"]), language=language)

    # Format title with iteration count if count > 1
    t["report_title"] = format_title_with_count(t["report_title"], count, language)

    # Initialize output structure
    now = datetime.now()
    timestamp = f"{now.microsecond // 10000:02d}"
    output_dir = os.path.join(os.path.dirname(base_output_dir) or ".", f"{timestamp}_{os.path.basename(base_output_dir)}")
    rel_output_dir = os.path.relpath(output_dir, start=os.path.dirname(base_output_dir) or ".")
    file_contents = {}
    logs = []
    actions = []

    # Validate variables
    clustering_vars_meta = [
        var for var in variables
        if var.role == VariableRole.INDEPENDENT and var.variable_type == VariableType.OBSERVED and var.code in data.columns
    ]
    if not clustering_vars_meta:
        logs.append(t["error_no_variables"])
        return ToolOutput(results={}, logs=logs, file_contents=file_contents, action=None)

    # Preprocess variables based on their scale type
    X_processed = pd.DataFrame()
    processed_var_codes = []

    logs.append(t["preprocessing_header"])
    for var in clustering_vars_meta:
        if var.scale in [ScaleType.INTERVAL, ScaleType.RATIO, ScaleType.ORDINAL]:
            X_processed[var.code] = data[var.code]
            processed_var_codes.append(var.code)
            logs.append(t["using_continuous"].format(var_name=var.name, var_code=var.code))
        elif var.scale == ScaleType.NOMINAL:
            # One-hot encode nominal variables
            dummies = pd.get_dummies(data[var.code], prefix=var.code, drop_first=True)
            X_processed = pd.concat([X_processed, dummies], axis=1)
            dummy_names = dummies.columns.tolist()
            processed_var_codes.extend(dummy_names)
            logs.append(t["onehot_nominal"].format(
                var_name=var.name, var_code=var.code, dummy_names=', '.join(dummy_names)
            ))
            # Update the variable names map for the new dummy variables
            for d_name in dummy_names:
                variable_names_map[d_name] = f"{var.name}_{d_name.split('_')[-1]}"
        else:
            logs.append(t["unsupported_scale"].format(
                var_name=var.name, var_code=var.code, scale=var.scale
            ))

    if X_processed.empty:
        logs.append(t["error_no_variables"])
        return ToolOutput(results={}, logs=logs, file_contents=file_contents, action=None)
    
    var_codes = processed_var_codes

    # Check variable variance
    variances = X_processed.var()
    low_variance_vars = variances[variances < 0.01].index.tolist()
    if low_variance_vars:
        logs.append(t["warning_low_variance"].format(vars=low_variance_vars))

    # Apply scaling for distance-based algorithms
    X = X_processed.copy()
    if algorithm in ["kmeans", "gmm", "hierarchical", "dbscan"]:
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)
        X = pd.DataFrame(X_scaled, columns=var_codes)
        logs.append(t["data_standardized"].format(algorithm=algorithm.upper()))

    # Perform clustering based on algorithm
    cluster_labels = None
    optimal_k = None
    metrics = {}
    
    if algorithm == "kmeans":
        logs.append(t["running_kmeans"].format(k_range=k_range))
        wss = []
        silhouette_scores = []
        db_scores = []
        gap_stats = compute_gap_statistic(X, k_range)

        for k in k_range:
            model = KMeans(n_clusters=k, random_state=42, n_init=10)
            labels = model.fit_predict(X)
            wss.append(model.inertia_)
            if len(set(labels)) > 1:
                silhouette_scores.append(silhouette_score(X, labels))
                db_scores.append(davies_bouldin_score(X, labels))
            else:
                silhouette_scores.append(-1)
                db_scores.append(float('inf'))

        silhouette_weights = np.array(silhouette_scores) / (np.max(silhouette_scores) if np.max(silhouette_scores) > 0 else 1)
        db_weights = 1 - (np.array(db_scores) / np.max(db_scores)) if len(db_scores) > 0 and np.max(db_scores) != float('inf') else np.zeros(len(k_range))
        gap_weights = np.array(gap_stats) / np.max(gap_stats) if gap_stats else np.zeros(len(k_range))
        combined_scores = silhouette_weights + db_weights + gap_weights
        optimal_k = k_range[np.argmax(combined_scores)]

        logs.append(t["optimal_k_kmeans"].format(optimal_k=optimal_k))
        
        model = KMeans(n_clusters=optimal_k, random_state=42, n_init=10)
        cluster_labels = model.fit_predict(X)
        metrics = {
            "Silhouette Score": silhouette_score(X, cluster_labels),
            "WSS": model.inertia_,
            "Davies-Bouldin": davies_bouldin_score(X, cluster_labels),
            "Gap Statistic": gap_stats[k_range.index(optimal_k)]
        }
        
        elbow_plot_filename = os.path.join(rel_output_dir, "elbow_plot_wss.png")
        file_contents[elbow_plot_filename] = generate_elbow_plot(wss, k_range, "WSS", t=t)

    elif algorithm == "hierarchical":
        logs.append(t["running_hierarchical"])
        Z = linkage(X, method='ward')
        dendrogram_plot_filename = os.path.join(rel_output_dir, "dendrogram.png")
        file_contents[dendrogram_plot_filename] = generate_dendrogram_plot(X, t=t)

        distances = Z[:, 2][::-1]
        jumps = np.diff(distances)
        optimal_k = np.argmax(jumps) + 2
        logs.append(t["optimal_k_hierarchical"].format(optimal_k=optimal_k))
        
        cluster_labels = fcluster(Z, t=optimal_k, criterion='maxclust')
        if len(set(cluster_labels)) > 1:
            metrics = {
                "Silhouette Score": silhouette_score(X, cluster_labels),
                "Davies-Bouldin": davies_bouldin_score(X, cluster_labels)
            }
        
        elbow_plot_filename = os.path.join(rel_output_dir, "elbow_plot_distances.png")
        file_contents[elbow_plot_filename] = generate_elbow_plot(
            distances[:len(k_range)], k_range, "Linkage Distance", t=t
        )

    elif algorithm == "dbscan":
        logs.append(t["running_dbscan"].format(min_samples=min_samples))

        best_silhouette = -1
        best_params = (None, None)
        best_labels = None

        # Define a search range for eps
        eps_range = np.linspace(0.1, 2.0, 20)

        logs.append(t["searching_eps"].format(min_eps=eps_range.min(), max_eps=eps_range.max()))
        for eps in eps_range:
            model = DBSCAN(eps=eps, min_samples=min_samples)
            labels = model.fit_predict(X)

            # We need at least 2 clusters (excluding noise label -1) to calculate silhouette score
            unique_labels = set(labels)
            num_clusters = len(unique_labels) - (1 if -1 in unique_labels else 0)

            if num_clusters >= 2:
                labels_no_noise = labels[labels != -1]
                X_no_noise = X[labels != -1]
                score = silhouette_score(X_no_noise, labels_no_noise)
                if score > best_silhouette:
                    best_silhouette = score
                    best_params = (eps, min_samples)
                    best_labels = labels

        if best_labels is not None:
            eps, min_samples = best_params
            cluster_labels = best_labels
            logs.append(t["found_dbscan_params"].format(
                eps=eps, min_samples=min_samples, score=best_silhouette
            ))

            labels_no_noise = cluster_labels[cluster_labels != -1]
            X_no_noise = X[cluster_labels != -1]
            metrics = {
                "Silhouette Score": silhouette_score(X_no_noise, labels_no_noise),
                "Davies-Bouldin": davies_bouldin_score(X_no_noise, labels_no_noise),
                "Num Clusters": len(set(labels_no_noise)),
                "Noise Points": np.sum(cluster_labels == -1)
            }
        else:
            logs.append(t["warning_dbscan_failed"])
            cluster_labels = np.zeros(len(X), dtype=int)

    elif algorithm == "gmm":
        logs.append(t["running_gmm"].format(k_range=k_range))
        silhouette_scores = []
        bics = []
        for k in k_range:
            model = GaussianMixture(n_components=k, random_state=42)
            labels = model.fit_predict(X)
            bics.append(model.bic(X))
            if len(set(labels)) > 1:
                silhouette_scores.append(silhouette_score(X, labels))
            else:
                silhouette_scores.append(-1)

        bic_weights = 1 - (np.array(bics) - np.min(bics)) / (np.max(bics) - np.min(bics))
        silhouette_weights = np.array(silhouette_scores) / (np.max(silhouette_scores) if np.max(silhouette_scores) > 0 else 1)
        combined_scores = bic_weights + silhouette_weights
        optimal_k = k_range[np.argmax(combined_scores)]
        logs.append(t["optimal_k_gmm"].format(optimal_k=optimal_k))
        
        model = GaussianMixture(n_components=optimal_k, random_state=42)
        cluster_labels = model.fit_predict(X)
        metrics = {
            "Silhouette Score": silhouette_score(X, cluster_labels),
            "Davies-Bouldin": davies_bouldin_score(X, cluster_labels),
            "BIC": model.bic(X)
        }
        
        elbow_plot_filename = os.path.join(rel_output_dir, "elbow_plot_bic.png")
        file_contents[elbow_plot_filename] = generate_elbow_plot(bics, k_range, "BIC", t=t)

    else:
        logs.append(t["error_invalid_algorithm"].format(algorithm=algorithm))
        return ToolOutput(results={}, logs=logs, file_contents=file_contents, action=actions)

    if cluster_labels is None or len(set(cluster_labels)) < 2:
        logs.append(t["error_clustering_failed"].format(algorithm=algorithm))
        return ToolOutput(results={}, logs=logs, file_contents=file_contents, action=actions)

    # Compute cluster characteristics
    characteristics = compute_cluster_characteristics(X_processed, cluster_labels, var_codes)
    characteristics_filename = os.path.join(rel_output_dir, "cluster_characteristics.csv")
    file_contents[characteristics_filename] = characteristics.to_csv()

    # Generate scatter plot
    scatter_plot_filename = os.path.join(rel_output_dir, "scatter_plot.png")
    file_contents[scatter_plot_filename] = generate_scatter_plot(X, cluster_labels, t=t)

    # Evaluate cluster quality
    sil_score = metrics.get('Silhouette Score', -1)
    quality = t["quality_good"] if sil_score >= 0.5 else t["quality_moderate"] if sil_score >= 0.25 else t["quality_poor"]
    silhouette_interpretation = t["metric_silhouette"].format(score=sil_score, quality=quality)
    db_interpretation = t["metric_db"].format(score=metrics.get('Davies-Bouldin', float('inf')))
    wss_interpretation = t["metric_wss"].format(value=metrics.get('WSS', 'N/A')) if algorithm == "kmeans" else ""
    bic_interpretation = t["metric_bic"].format(value=metrics.get('BIC', 'N/A')) if algorithm == "gmm" else ""
    dbscan_interpretation = t["metric_noise"].format(
        count=metrics.get('Noise Points', 'N/A'),
        percent=metrics.get('Noise Points', 0) / len(data) * 100
    ) if algorithm == "dbscan" else ""

    # Check for insignificant clusters
    cluster_sizes = pd.Series(cluster_labels).value_counts()
    small_clusters = cluster_sizes[cluster_sizes < len(data) * 0.05].index.tolist()
    if -1 in small_clusters: small_clusters.remove(-1)
    if small_clusters:
        logs.append(t["warning_small_clusters"].format(clusters=small_clusters))

    # Generate cluster interpretations
    characteristics_interpretation = []
    for cluster in sorted(characteristics.index):
        if cluster == -1:
            characteristics_interpretation.append(t["cluster_noise"].format(count=cluster_sizes.get(-1, 0)))
            continue
        cluster_desc = []
        for var in var_codes:
            mean_val = characteristics.loc[cluster, (var, 'mean')]
            if any(var.startswith(v.code) for v in clustering_vars_meta if v.scale == ScaleType.NOMINAL):
                cluster_desc.append(t["cluster_desc_nominal"].format(
                    var_name=variable_names_map.get(var, var), value=mean_val*100
                ))
            else:
                cluster_desc.append(t["cluster_desc_continuous"].format(
                    var_name=variable_names_map.get(var, var), value=mean_val
                ))
        characteristics_interpretation.append(t["cluster_member_count"].format(
            cluster_id=cluster, count=cluster_sizes[cluster], desc='; '.join(cluster_desc)
        ))

    # Generate comprehensive report
    report_sections = []

    # Header
    report_sections.append(t["report_title"])
    report_sections.append(t["section_algorithm"])
    report_sections.append(t["algorithm_description"].format(
        algorithm=algorithm.upper(),
        variables=', '.join([variable_names_map.get(v, v) for v in var_codes])
    ))

    # Parameters
    report_sections.append(t["section_parameters"])
    report_sections.append(t["param_algorithm"].format(algorithm=algorithm.upper()))
    if algorithm in ['kmeans', 'gmm']:
        report_sections.append(t["param_k_range"].format(k_range=k_range))
    if algorithm == 'dbscan' and 'eps' in locals():
        report_sections.append(t["param_dbscan"].format(eps=eps, min_samples=min_samples))
    if algorithm == 'hierarchical':
        report_sections.append(t["param_hierarchical"].format(optimal_k=optimal_k))

    # Cluster characteristics
    report_sections.append(t["section_characteristics"])
    report_sections.append(t["characteristics_table"].format(filename=characteristics_filename))
    report_sections.append(t["section_interpretation"])
    for line in characteristics_interpretation:
        report_sections.append(f"- {line}")

    # Quality metrics
    report_sections.append(t["section_quality"])
    report_sections.append(silhouette_interpretation)
    report_sections.append(db_interpretation)
    if wss_interpretation:
        report_sections.append(wss_interpretation)
    if bic_interpretation:
        report_sections.append(bic_interpretation)
    if dbscan_interpretation:
        report_sections.append(dbscan_interpretation)

    # Visualizations
    report_sections.append(t["section_visualizations"])
    report_sections.append(t["viz_scatter"].format(filename=scatter_plot_filename))
    if algorithm == "kmeans":
        report_sections.append(t["viz_elbow_wss"].format(filename=elbow_plot_filename))
    elif algorithm == "gmm":
        report_sections.append(t["viz_elbow_bic"].format(filename=elbow_plot_filename))
    elif algorithm == "hierarchical":
        report_sections.append(t["viz_dendrogram"].format(filename=dendrogram_plot_filename))
        report_sections.append(t["viz_elbow_distance"].format(filename=elbow_plot_filename))

    # Conclusion
    report_sections.append(t["section_conclusion"])
    report_sections.append(t["conclusion_optimal_k"].format(
        optimal_k=optimal_k if optimal_k else metrics.get('Num Clusters', 'Determined by algorithm')
    ))
    
    # Combine all sections
    final_report = "\n".join(report_sections)
    logs.append(final_report)

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

    # Prepare results
    results = {
        "algorithm": algorithm,
        "variables": var_codes,
        "cluster_labels": cluster_labels.tolist(),
        "optimal_k": optimal_k if optimal_k else metrics.get('Num Clusters'),
        "metrics": metrics,
        "cluster_characteristics": characteristics.to_dict()
    }

    return ToolOutput(
        results=serialize_dict(results),
        logs=logs,
        file_contents=file_contents,
        action=actions if actions else None
    )
