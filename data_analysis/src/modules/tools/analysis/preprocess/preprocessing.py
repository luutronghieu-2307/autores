import pandas as pd
import numpy as np
import os
import base64
from scipy import stats
from datetime import datetime
import matplotlib.pyplot as plt
from data_analysis.src.modules.utils import serialize_dict


from data_analysis.src.schemas.analyzer_states import (
    Action,
    ActionType,
    ToolOutput,
    Variable,
    VariableType
)

def run_data_preprocessing(
    data: pd.DataFrame,
    variables: list[Variable],
    params: dict
) -> ToolOutput:
    """
    Comprehensive data preprocessing tool that handles outliers, missing values, 
    and other data quality issues with automatic detection and suggestion of actions.
    
    This tool performs various preprocessing steps including:
    - Outlier detection using Z-score and IQR methods
    - Missing value analysis and imputation strategies
    - Data type validation and conversion
    - Duplicate detection and removal
    - Data distribution analysis
    - Automatic action suggestions based on data characteristics
    
    Parameters:
        data: Input DataFrame containing the data to preprocess
        variables: list of Variable objects describing the data columns
        params: dictionary containing preprocessing parameters:
            - target_variables (list[str]): variables to preprocess (default: all numeric variables)
            - outlier_methods (list[str]): outlier detection methods ['z_score', 'iqr'] (default: ['z_score', 'iqr'])
            - z_score_threshold (float): Z-score threshold for outlier detection (default: 3.0)
            - iqr_multiplier (float): IQR multiplier for outlier detection (default: 1.5)
            - missing_value_threshold (float): % threshold for missing values to trigger action (default: 0.05)
            - outlier_threshold (float): % threshold for outliers to trigger action (default: 0.05)
            - auto_apply_preprocessing (bool): whether to automatically apply preprocessing (default: True)
            - missing_value_strategy (str): strategy for handling missing values ['remove', 'interpolate', 'mean', 'median', 'mode'] (default: 'auto')
            - outlier_strategy (str): strategy for handling outliers ['remove', 'cap', 'transform', 'keep'] (default: 'auto')
            - duplicate_check (bool): whether to check for duplicate rows (default: True)
            - data_type_validation (bool): whether to validate and suggest data type conversions (default: True)
            - distribution_analysis (bool): whether to analyze data distributions (default: True)
            - output_dir (str): base output directory name (default: 'data_preprocessing')
            - save_files (bool): whether to save generated files to disk (default: False)
    
    Returns:
        ToolOutput: Contains preprocessing results, quality metrics, diagnostic plots, 
                   and suggested transformation actions
    """
    
    # Parameter extraction and initialization
    target_variable_codes = params.get('target_variables', [
        var.code for var in variables
        if var.variable_type == VariableType.OBSERVED and var.code in data.columns
    ])

    outlier_methods = params.get('outlier_methods', ['z_score', 'iqr'])
    z_score_threshold = params.get('z_score_threshold', 3.0)
    iqr_multiplier = params.get('iqr_multiplier', 1.5)
    missing_threshold = params.get('missing_value_threshold', 0.05)
    outlier_threshold = params.get('outlier_threshold', 0.05)
    auto_apply = params.get('auto_apply_preprocessing', True)
    missing_strategy = params.get('missing_value_strategy', 'auto')
    outlier_strategy = params.get('outlier_strategy', 'auto')
    duplicate_check = params.get('duplicate_check', True)
    data_type_validation = params.get('data_type_validation', True)
    distribution_analysis = params.get('distribution_analysis', True)
    base_output_dir = params.get("output_dir", "data_preprocessing")
    save_files = params.get("save_files", False)

    # Translation dictionary
    translations = {
        "en": {
            "title": "# Data Preprocessing Analysis\n\n",
            "status_using_numeric_cols": "No target variables specified, using all numeric columns: {cols}",
            "error_no_variables": "No suitable variables found for preprocessing",
            "status_starting": "Starting comprehensive data preprocessing for {count} variables",
            "status_dataset_info": "Dataset contains {rows} rows and {cols} columns",
            "warning_duplicates_found": "Found {count} duplicate rows ({percentage:.2f}%)",
            "status_no_duplicates": "No duplicate rows found",
            "error_var_not_found": "Variable '{var_code}' not found in data",
            "status_processing_var": "Processing variable: {var_code}",
            "status_var_stats": "  {var_code}: {valid} valid values, {missing} missing ({percentage:.2f}%)",
            "status_missing_below_threshold": "  {var_code}: Missing values below threshold, no action needed",
            "warning_insufficient_data": "  {var_code}: Insufficient data for outlier detection",
            "status_outliers_detected": "  {var_code}: {count} outliers detected ({percentage:.2f}%)",
            "status_summary_saved": "Preprocessing summary report saved: {path}",
            "error_summary_failed": "Error generating summary report: {error}",
            "status_completed": "Data preprocessing completed. {count} actions suggested.",
            "error_plot_failed": "Error creating plots for {var_code}: {error}",
            "error_save_image_failed": "Error saving image {filename}: {error}",
            "status_files_saved": "Files saved to {dir}",
            "error_save_files_failed": "Error saving files: {error}"
        },
        "vi": {
            "title": "# Phân Tích Tiền Xử Lý Dữ Liệu\n\n",
            "status_using_numeric_cols": "Không chỉ định biến mục tiêu, sử dụng tất cả cột số: {cols}",
            "error_no_variables": "Không tìm thấy biến phù hợp để tiền xử lý",
            "status_starting": "Bắt đầu tiền xử lý dữ liệu toàn diện cho {count} biến",
            "status_dataset_info": "Tập dữ liệu chứa {rows} hàng và {cols} cột",
            "warning_duplicates_found": "Tìm thấy {count} hàng trùng lặp ({percentage:.2f}%)",
            "status_no_duplicates": "Không tìm thấy hàng trùng lặp",
            "error_var_not_found": "Không tìm thấy biến '{var_code}' trong dữ liệu",
            "status_processing_var": "Đang xử lý biến: {var_code}",
            "status_var_stats": "  {var_code}: {valid} giá trị hợp lệ, {missing} thiếu ({percentage:.2f}%)",
            "status_missing_below_threshold": "  {var_code}: Giá trị thiếu dưới ngưỡng, không cần hành động",
            "warning_insufficient_data": "  {var_code}: Không đủ dữ liệu để phát hiện ngoại lai",
            "status_outliers_detected": "  {var_code}: Phát hiện {count} ngoại lai ({percentage:.2f}%)",
            "status_summary_saved": "Đã lưu báo cáo tóm tắt tiền xử lý: {path}",
            "error_summary_failed": "Lỗi tạo báo cáo tóm tắt: {error}",
            "status_completed": "Tiền xử lý dữ liệu hoàn tất. Đã đề xuất {count} hành động.",
            "error_plot_failed": "Lỗi tạo biểu đồ cho {var_code}: {error}",
            "error_save_image_failed": "Lỗi lưu hình ảnh {filename}: {error}",
            "status_files_saved": "Đã lưu tệp vào {dir}",
            "error_save_files_failed": "Lỗi lưu tệp: {error}"
        }
    }
    language = params.get("language", "en")
    t = translations.get(language, translations["en"])
    
    # Initialize output containers
    logs = []
    file_contents = {}
    actions = []
    preprocessing_summary = []
    
    # Generate timestamped output directory
    now = datetime.now()
    timestamp = f"{now.microsecond // 10000:02d}"
    output_dir_id = f"{timestamp}_{base_output_dir}"
    output_dir = os.path.join(os.path.dirname(base_output_dir) or ".", f"{timestamp}_{os.path.basename(base_output_dir)}")
    
    # Input validation
    if not target_variable_codes:
        # If no target variables specified, use all numeric columns
        numeric_columns = data.select_dtypes(include=[np.number]).columns.tolist()
        target_variable_codes = [col for col in numeric_columns if col in [var.code for var in variables]]
        logs.append(t["status_using_numeric_cols"].format(cols=target_variable_codes))

    if not target_variable_codes:
        logs.append(t["error_no_variables"])
        return ToolOutput(results={}, logs=logs, file_contents=file_contents, action=None)

    logs.append(t["title"])
    logs.append(t["status_starting"].format(count=len(target_variable_codes)))

    # Global data quality checks
    total_rows = len(data)
    logs.append(t["status_dataset_info"].format(rows=total_rows, cols=len(data.columns)))

    # Check for duplicate rows
    if duplicate_check:
        duplicate_rows = data.duplicated().sum()
        if duplicate_rows > 0:
            duplicate_percentage = (duplicate_rows / total_rows) * 100
            logs.append(t["warning_duplicates_found"].format(count=duplicate_rows, percentage=duplicate_percentage))
            
            if duplicate_percentage > 1.0:  # More than 1% duplicates
                action = Action(
                    action_type=ActionType.HANDLE_MISSING_VALUES,  # Using this as generic data cleaning
                    method="run_data_preprocessing",
                    issue=f"Dataset contains {duplicate_rows} duplicate rows ({duplicate_percentage:.2f}%)",
                    comment=f"Remove {duplicate_rows} duplicate rows to improve data quality",
                    status="pending",
                    action_params={
                        'operation': 'remove_duplicates',
                        'duplicate_count': duplicate_rows
                    }
                )
                actions.append(action)
        else:
            logs.append(t["status_no_duplicates"])

    # Process each target variable
    for var_code in target_variable_codes:
        if var_code not in data.columns:
            logs.append(t["error_var_not_found"].format(var_code=var_code))
            continue

        logs.append(t["status_processing_var"].format(var_code=var_code))
        var_summary = {'Variable': var_code}

        # Get variable metadata
        var_meta = next((v for v in variables if v.code == var_code), None)
        current_series = data[var_code].copy()

        # Basic statistics
        total_values = len(current_series)
        missing_values = current_series.isnull().sum()
        valid_values = total_values - missing_values
        missing_percentage = (missing_values / total_values) * 100 if total_values > 0 else 0

        var_summary.update({
            'Total Values': total_values,
            'Missing Values': missing_values,
            'Missing %': round(missing_percentage, 2),
            'Valid Values': valid_values
        })

        logs.append(t["status_var_stats"].format(
            var_code=var_code, valid=valid_values, missing=missing_values, percentage=missing_percentage
        ))
        
        # Handle missing values
        if missing_values > 0:
            if missing_percentage > missing_threshold * 100:
                # Significant missing values detected
                if missing_percentage > 50:
                    # Too many missing values - suggest removal
                    action = Action(
                        action_type=ActionType.REMOVE_VARIABLE,
                        method="run_data_preprocessing",
                        issue=f"Variable {var_code} has {missing_percentage:.2f}% missing values (>{missing_threshold*100}%)",
                        comment=f"Remove variable {var_code} due to excessive missing data",
                        status="pending",
                        action_params={'variable': var_code}
                    )
                    actions.append(action)
                    var_summary['Recommended Action'] = 'Remove Variable'
                else:
                    # Moderate missing values - suggest imputation
                    if missing_strategy == 'auto':
                        # Determine best strategy based on data type and distribution
                        if var_meta and var_meta.scale in ['nominal', 'ordinal']:
                            suggested_strategy = 'mode'
                        elif current_series.dtype in ['object', 'category']:
                            suggested_strategy = 'mode'
                        else:
                            # For numeric data, check distribution
                            if _is_normally_distributed(current_series.dropna()):
                                suggested_strategy = 'mean'
                            else:
                                suggested_strategy = 'median'
                    else:
                        suggested_strategy = missing_strategy
                    
                    action = Action(
                        action_type=ActionType.HANDLE_MISSING_VALUES,
                        method="run_data_preprocessing",
                        issue=f"Variable {var_code} has {missing_percentage:.2f}% missing values",
                        comment=f"Impute missing values in {var_code} using {suggested_strategy} method",
                        status="pending",
                        action_params={
                            'variable': var_code,
                            'method': suggested_strategy,
                            'missing_count': missing_values
                        }
                    )
                    actions.append(action)
                    var_summary['Recommended Action'] = f'Impute ({suggested_strategy})'
            else:
                logs.append(t["status_missing_below_threshold"].format(var_code=var_code))

        # Skip outlier analysis if too many missing values or non-numeric
        if missing_percentage > 50 or not pd.api.types.is_numeric_dtype(current_series):
            preprocessing_summary.append(var_summary)
            continue

        # Outlier detection for numeric variables
        clean_series = current_series.dropna()
        if len(clean_series) < 10:
            logs.append(t["warning_insufficient_data"].format(var_code=var_code))
            preprocessing_summary.append(var_summary)
            continue
            
        outliers_detected = {}
        outlier_indices = set()
        
        # Z-score method
        if 'z_score' in outlier_methods:
            z_scores = np.abs(stats.zscore(clean_series))
            z_outliers = clean_series[z_scores > z_score_threshold]
            outliers_detected['z_score'] = {
                'count': len(z_outliers),
                'percentage': (len(z_outliers) / len(clean_series)) * 100,
                'indices': z_outliers.index.tolist()
            }
            outlier_indices.update(z_outliers.index)
            
        # IQR method
        if 'iqr' in outlier_methods:
            Q1 = clean_series.quantile(0.25)
            Q3 = clean_series.quantile(0.75)
            IQR = Q3 - Q1
            lower_bound = Q1 - iqr_multiplier * IQR
            upper_bound = Q3 + iqr_multiplier * IQR
            
            iqr_outliers = clean_series[(clean_series < lower_bound) | (clean_series > upper_bound)]
            outliers_detected['iqr'] = {
                'count': len(iqr_outliers),
                'percentage': (len(iqr_outliers) / len(clean_series)) * 100,
                'indices': iqr_outliers.index.tolist(),
                'bounds': {'lower': lower_bound, 'upper': upper_bound}
            }
            outlier_indices.update(iqr_outliers.index)
        
        # Combine outlier results
        total_outliers = len(outlier_indices)
        outlier_percentage = (total_outliers / len(clean_series)) * 100 if len(clean_series) > 0 else 0
        
        var_summary.update({
            'Outliers (Z-score)': outliers_detected.get('z_score', {}).get('count', 0),
            'Outliers (IQR)': outliers_detected.get('iqr', {}).get('count', 0),
            'Total Unique Outliers': total_outliers,
            'Outlier %': round(outlier_percentage, 2)
        })

        logs.append(t["status_outliers_detected"].format(count=total_outliers, percentage=outlier_percentage, var_code=var_code))
        
        # Handle outliers
        if total_outliers > 0 and outlier_percentage > outlier_threshold * 100:
            if outlier_strategy == 'auto':
                if outlier_percentage > 20:
                    # Too many outliers - suggest transformation
                    suggested_strategy = 'transform'
                elif outlier_percentage > 10:
                    # Moderate outliers - suggest capping
                    suggested_strategy = 'cap_floor'
                else:
                    # Few outliers - suggest removal
                    suggested_strategy = 'remove'
            else:
                suggested_strategy = outlier_strategy
            
            action = Action(
                action_type=ActionType.HANDLE_OUTLIERS,
                method="run_data_preprocessing",
                issue=f"Variable {var_code} has {total_outliers} outliers ({outlier_percentage:.2f}%)",
                comment=f"Handle outliers in {var_code} using {suggested_strategy} method",
                status="pending",
                action_params={
                    'variable': var_code,
                    'method': suggested_strategy,
                    'outlier_count': total_outliers,
                    'outlier_indices': list(outlier_indices),
                    'detection_methods': outlier_methods
                }
            )
            actions.append(action)
            var_summary['Outlier Action'] = suggested_strategy
        
        # Data type validation
        if data_type_validation and var_meta:
            current_dtype = str(current_series.dtype)
            expected_scale = var_meta.scale
            
            # Check if data type matches expected scale
            type_mismatch = False
            if expected_scale in ['nominal', 'ordinal'] and current_dtype not in ['object', 'category']:
                if current_series.nunique() < 10:  # Likely categorical
                    type_mismatch = True
                    suggested_type = 'category'
            elif expected_scale in ['interval', 'ratio'] and not pd.api.types.is_numeric_dtype(current_series):
                type_mismatch = True
                suggested_type = 'numeric'
                
            if type_mismatch:
                action = Action(
                    action_type=ActionType.TRANSFORM_VARIABLES,
                    method="run_data_preprocessing",
                    issue=f"Variable {var_code} has data type '{current_dtype}' but scale is '{expected_scale}'",
                    comment=f"Convert {var_code} to {suggested_type} type for consistency",
                    status="pending",
                    action_params={
                        'variable': var_code,
                        'transform_type': 'data_type_conversion',
                        'transform_params': {
                            'target_type': suggested_type,
                            'current_type': current_dtype
                        }
                    }
                )
                actions.append(action)
                var_summary['Type Conversion'] = f"{current_dtype} -> {suggested_type}"
        
        # Distribution analysis
        if distribution_analysis and pd.api.types.is_numeric_dtype(current_series):
            skewness = stats.skew(clean_series)
            kurtosis = stats.kurtosis(clean_series)
            
            var_summary.update({
                'Skewness': round(skewness, 3),
                'Kurtosis': round(kurtosis, 3),
                'Distribution': _classify_distribution(skewness, kurtosis)
            })
            
            # Suggest transformation for highly skewed data
            if abs(skewness) > 2:
                transform_type = 'log' if skewness > 0 else 'square_root'
                action = Action(
                    action_type=ActionType.TRANSFORM_VARIABLES,
                    method="run_data_preprocessing",
                    issue=f"Variable {var_code} is highly skewed (skewness={skewness:.3f})",
                    comment=f"Apply {transform_type} transformation to reduce skewness",
                    status="pending",
                    action_params={
                        'variable': var_code,
                        'transform_type': transform_type,
                        'transform_params': {'original_skewness': skewness}
                    }
                )
                actions.append(action)
                var_summary['Skewness Action'] = transform_type
        
        # Create diagnostic plots
        if save_files or len(file_contents) < 20:  # Limit number of plots
            _create_preprocessing_plots(current_series, var_code, outlier_indices,
                                      output_dir_id, file_contents, logs, t)
        
        preprocessing_summary.append(var_summary)
    
    # Create reprocessing action for variables that need transformation
    transformed_variables = [
        action.action_params.get('variable') for action in actions 
        if action.action_type in [ActionType.TRANSFORM_VARIABLES, ActionType.HANDLE_OUTLIERS, ActionType.HANDLE_MISSING_VALUES]
        and action.action_params.get('variable')
    ]
    
    if transformed_variables and auto_apply:
        reprocess_action = Action(
            action_type=ActionType.REANALYZE,
            method="run_data_preprocessing",
            issue="Data preprocessing verification needed",
            comment=f"Re-run preprocessing analysis after transformations",
            status="pending",
            reflection_params={
                'tool': 'run_data_preprocessing',
                'parameters': {
                    'target_variables': list(set(transformed_variables)),
                    'outlier_methods': outlier_methods,
                    'z_score_threshold': z_score_threshold,
                    'iqr_multiplier': iqr_multiplier,
                    'auto_apply_preprocessing': False,
                    'save_files': save_files,
                    'output_dir': base_output_dir,
                    'language': language
                },
                'comment': f"Verify preprocessing results for {len(set(transformed_variables))} variables"
            },
            reset_actions=True
        )
        actions.append(reprocess_action)
    
    # Generate comprehensive summary report
    if preprocessing_summary:
        summary_df = pd.DataFrame(preprocessing_summary)
        
        # Ensure all expected columns exist
        expected_columns = [
            'Variable', 'Total Values', 'Missing Values', 'Missing %', 'Valid Values',
            'Outliers (Z-score)', 'Outliers (IQR)', 'Total Unique Outliers', 'Outlier %',
            'Skewness', 'Kurtosis', 'Distribution', 'Recommended Action', 'Outlier Action',
            'Skewness Action', 'Type Conversion'
        ]
        
        for col in expected_columns:
            if col not in summary_df.columns:
                summary_df[col] = None
        
        # Reorder columns
        summary_df = summary_df.reindex(columns=[col for col in expected_columns if col in summary_df.columns])
        
        try:
            summary_csv = summary_df.to_csv(index=False)
            summary_path = f"{output_dir_id}/preprocessing_summary_report.csv"
            file_contents[summary_path] = summary_csv
            logs.append(t["status_summary_saved"].format(path=summary_path))
        except Exception as e:
            logs.append(t["error_summary_failed"].format(error=str(e)))

    # Save files if requested
    if save_files:
        _save_preprocessing_files(output_dir, file_contents, logs, t)

    # Prepare final results
    results = {
        'total_variables_processed': len(target_variable_codes),
        'total_actions_suggested': len(actions),
        'summary_statistics': {
            'total_rows': total_rows,
            'duplicate_rows': duplicate_rows if duplicate_check else 0,
            'variables_with_missing': len([s for s in preprocessing_summary if s.get('Missing Values', 0) > 0]),
            'variables_with_outliers': len([s for s in preprocessing_summary if s.get('Total Unique Outliers', 0) > 0])
        }
    }

    logs.append(t["status_completed"].format(count=len(actions)))
    
    return ToolOutput(
        results=serialize_dict(results),
        logs=logs,
        file_contents=file_contents,
        action=actions if actions else None
    )
    

# Helper functions
def _is_normally_distributed(series, alpha=0.05):
    """Check if a series is normally distributed using Shapiro-Wilk test."""
    try:
        if len(series) < 3:
            return False
        stat, p_value = stats.shapiro(series.sample(min(5000, len(series))))
        return p_value > alpha
    except:
        return False


def _classify_distribution(skewness, kurtosis):
    """Classify distribution based on skewness and kurtosis."""
    if abs(skewness) < 0.5 and abs(kurtosis) < 0.5:
        return "Normal"
    elif skewness > 1:
        return "Right-skewed"
    elif skewness < -1:
        return "Left-skewed"
    elif kurtosis > 1:
        return "Heavy-tailed"
    elif kurtosis < -1:
        return "Light-tailed"
    else:
        return "Moderate"


def _create_preprocessing_plots(series, var_code, outlier_indices, output_dir_id, file_contents, logs, t):
    """Create diagnostic plots for preprocessing analysis."""
    try:

        # Create subplots
        fig, axes = plt.subplots(2, 2, figsize=(7, 6))
        fig.suptitle(f'Preprocessing Analysis: {var_code}', fontsize=16)

        clean_series = series.dropna()

        # Time series plot
        axes[0, 0].plot(clean_series.index, clean_series.values, 'b-', alpha=0.7)
        if outlier_indices:
            outlier_values = clean_series.loc[outlier_indices]
            axes[0, 0].scatter(outlier_values.index, outlier_values.values,
                             color='red', s=30, alpha=0.7, label='Outliers')
        axes[0, 0].set_title('Time Series with Outliers')
        axes[0, 0].set_ylabel('Values')
        axes[0, 0].legend()

        # Histogram
        axes[0, 1].hist(clean_series, bins=30, alpha=0.7, color='skyblue', edgecolor='black')
        axes[0, 1].set_title('Distribution')
        axes[0, 1].set_xlabel('Values')
        axes[0, 1].set_ylabel('Frequency')

        # Box plot
        box_plot = axes[1, 0].boxplot(clean_series, patch_artist=True)
        box_plot['boxes'][0].set_facecolor('lightblue')
        axes[1, 0].set_title('Box Plot')
        axes[1, 0].set_ylabel('Values')

        # Q-Q plot
        stats.probplot(clean_series, dist="norm", plot=axes[1, 1])
        axes[1, 1].set_title('Q-Q Plot (Normal)')

        plt.tight_layout()

        # Save plot
        plot_path = f"{output_dir_id}/preprocessing_{var_code}_diagnostics.png"
        plt.savefig(plot_path, dpi=300, bbox_inches='tight')

        # Convert to base64 for storage
        import io
        import base64
        buffer = io.BytesIO()
        plt.savefig(buffer, format='png', dpi=300, bbox_inches='tight')
        buffer.seek(0)
        image_base64 = base64.b64encode(buffer.read()).decode()
        file_contents[plot_path] = image_base64

        plt.close()

    except Exception as e:
        logs.append(t["error_plot_failed"].format(var_code=var_code, error=str(e)))


def _save_preprocessing_files(output_dir, file_contents, logs, t):
    """Save preprocessing files to disk."""
    try:

        os.makedirs(output_dir, exist_ok=True)

        for filename, content in file_contents.items():
            save_path = os.path.join(output_dir, os.path.basename(filename))

            if filename.endswith(".png"):
                try:
                    decoded_content = base64.b64decode(content)
                    with open(save_path, "wb") as f:
                        f.write(decoded_content)
                except Exception as e:
                    logs.append(t["error_save_image_failed"].format(filename=filename, error=str(e)))
            else:
                with open(save_path, "w", encoding="utf-8") as f:
                    f.write(str(content))

        logs.append(t["status_files_saved"].format(dir=output_dir))

    except Exception as e:
        logs.append(t["error_save_files_failed"].format(error=str(e)))
