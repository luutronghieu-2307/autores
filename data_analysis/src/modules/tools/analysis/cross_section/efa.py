import base64
import io
import logging
import os
import copy
import shutil
import networkx as nx
import matplotlib.patches as patches
from matplotlib.patches import Ellipse, Rectangle, FancyBboxPatch
from io import BytesIO
from collections import defaultdict, deque
import traceback
from collections import defaultdict
from datetime import datetime
from typing import Any, Optional, List, Tuple
import warnings

os.environ["RPY2_CFFI_MODE"] = "ABI"
warnings.filterwarnings("ignore", message=".*Environment variable \"PATH\" redefined by R.*")

# Third-party imports
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pingouin as pg
from graphviz import Digraph
import tempfile

import plspm.config as plspm_config
from plspm.plspm import Plspm
from plspm.scheme import Scheme
from plspm.mode import Mode
from rpy2.robjects import pandas2ri
import rpy2.robjects as ro
from rpy2.robjects.packages import importr
from scipy import stats
from scipy.stats import kurtosis, skew

from semopy import calc_stats, semplot
from semopy import Model as SemopyModel
from statsmodels.regression.linear_model import OLS
from statsmodels.tools.tools import add_constant
from statsmodels.tools.sm_exceptions import MissingDataError

# Local application imports
from data_analysis.src.modules.tools.analysis.cross_section.pipeline_utils import get_t_dict, format_title_with_count
from data_analysis.src.schemas.analyzer_states import (
    Action,
    ActionType,
    ScaleType,
    ToolOutput,
    Variable,
    VariableRole,
    VariableType
)

# Logger
logger = logging.getLogger(__name__)

# Import Actual Utility Functions
from data_analysis.src.modules.tools.analysis.cross_section.criteria import get_diagnostic_criteria
from data_analysis.src.modules.tools.analysis.cross_section.pipeline_utils import (
    generate_reliability_analysis, perform_kmo_and_bartlett_tests,
    determine_factors, perform_pca_varimax, generate_variance_table
)

from data_analysis.src.modules.utils import (
    serialize_dict, parse_variable_values
)

from data_analysis.src.modules.tools.analysis.cross_section.utils import (
    _create_cfa_layout, _create_sem_layout,
    _calculate_figure_size, _calculate_text_dimensions
)


#####################################################
#####################################################
#####################################################

def single_factor_scale_reliability_testing(
    data: pd.DataFrame,
    variables: list[Variable],
    params: dict
) -> ToolOutput:
    """
    Perform reliability analysis for a single independent factor and suggest variables to remove based on CITC.
    Includes reflection parameters to re-run the tool after actions are applied.

    Parameters:
        data: Input DataFrame containing observed variables
        variables: list of Variable objects for this factor (parent latent + observed children)
        params: dictionary containing analysis parameters
            - factor_key (str): identifier for the factor being analyzed
            - output_dir (str): base output directory name
            - save_files (bool): whether to save generated files to disk
            - variable_names (dict): mapping of variable codes to display names
            - language (str): language for output messages - "en" or "vi" (default: "en")

    Returns:
        ToolOutput: Contains analysis results, logs, file contents, and list of suggested data-affecting actions
    """
    # Extract parameters
    factor_key = params["factor_key"]
    base_output_dir = params.get("output_dir", "rel_single")
    save_files = params.get("save_files", False)
    variable_names = params.get("variable_names", {v.code: v.name for v in variables})
    language = params.get("language", "en")

    # Translation dictionary
    translations = {
        "en": {
            "analysis_for_factor": "### Analysis for Factor: {}\n\n",
            "no_observed_vars": "No observed variables found for this factor.",
            "reliability_results": "**Reliability Analysis Results:**",
            "reliability_table": "- Reliability table: `{}`",
            "item_total_stats": "- Item-total statistics: `{}`",
            "cronbach_alpha_fmt": "**Cronbach's Alpha**: {}",
            "diagnostic_assessment": "**Diagnostic Assessment:**",
            "overall_scale": "- Overall Scale: {}",
            "issue_alpha_high": "**Issue Identified**: Cronbach's Alpha ≥ 0.95 ({}). Variables may measure identical content, suggesting redundancy.",
            "issue_alpha_low": "**Issue Identified**: Cronbach's Alpha < 0.6 ({}). Scale reliability is insufficient.",
            "factor_cannot_analyze": "**Factor Status**: Factor `{}` cannot be analyzed (insufficient items or unavailable alpha).",
            "low_citc_vars": "**Variables with Low CITC**: {} (CITC < 0.3)",
            "analysis_complete": "**Analysis Complete**: Factor `{}` meets reliability criteria with variables: {}",
            "not_available": "Not Available",
            "action_no_observed_vars_issue": "No observed variables",
            "action_no_observed_vars_comment": "Factor cannot be analyzed due to lack of observed variables",
            "action_alpha_high_issue": "Cronbach's Alpha ≥ 0.95",
            "action_alpha_high_comment": "Review variables for redundancy; consider retaining only one variable",
            "action_alpha_low_issue": "Cronbach's Alpha < 0.6",
            "action_alpha_low_comment": "Recheck variable list, collect more data, review scale content, or check research model",
            "action_alpha_na_issue": "Alpha N/A or insufficient items",
            "action_alpha_na_comment": "Factor unsuitable for analysis",
            "action_low_citc_issue": "Corrected Item-Total Correlation (CITC) < 0.3",
            "action_low_citc_comment": "Remove variable to improve reliability"
        },
        "vi": {
            "analysis_for_factor": "### Phân Tích Nhân Tố: {}\n\n",
            "no_observed_vars": "Không tìm thấy biến quan sát nào cho nhân tố này.",
            "reliability_results": "**Kết Quả Phân Tích Độ Tin Cậy:**",
            "reliability_table": "- Bảng độ tin cậy: `{}`",
            "item_total_stats": "- Thống kê tương quan mục-tổng: `{}`",
            "cronbach_alpha_fmt": "**Cronbach's Alpha**: {}",
            "diagnostic_assessment": "**Đánh Giá Chẩn Đoán:**",
            "overall_scale": "- Thang đo tổng thể: {}",
            "issue_alpha_high": "**Vấn Đề Đã Xác Định**: Cronbach's Alpha ≥ 0.95 ({}). Các biến có thể đo lường nội dung giống hệt nhau, cho thấy sự dư thừa.",
            "issue_alpha_low": "**Vấn Đề Đã Xác Định**: Cronbach's Alpha < 0.6 ({}). Độ tin cậy của thang đo không đủ.",
            "factor_cannot_analyze": "**Trạng Thái Nhân Tố**: Nhân tố `{}` không thể phân tích được (không đủ mục hoặc alpha không khả dụng).",
            "low_citc_vars": "**Các Biến Có CITC Thấp**: {} (CITC < 0.3)",
            "analysis_complete": "**Phân Tích Hoàn Tất**: Nhân tố `{}` đáp ứng tiêu chí độ tin cậy với các biến: {}",
            "not_available": "Không Khả Dụng",
            "action_no_observed_vars_issue": "Không có biến quan sát",
            "action_no_observed_vars_comment": "Nhân tố không thể được phân tích do thiếu biến quan sát",
            "action_alpha_high_issue": "Cronbach's Alpha ≥ 0.95",
            "action_alpha_high_comment": "Rà soát các biến về tính dư thừa; xem xét giữ lại chỉ một biến",
            "action_alpha_low_issue": "Cronbach's Alpha < 0.6",
            "action_alpha_low_comment": "Kiểm tra lại danh sách biến, thu thập thêm dữ liệu, xem xét nội dung thang đo, hoặc kiểm tra mô hình nghiên cứu",
            "action_alpha_na_issue": "Alpha N/A hoặc mục không đủ",
            "action_alpha_na_comment": "Nhân tố không phù hợp để phân tích",
            "action_low_citc_issue": "Tương quan Mục-Tổng đã chỉnh (CITC) < 0.3",
            "action_low_citc_comment": "Loại bỏ biến để cải thiện độ tin cậy"
        }
    }

    # Get translations for selected language
    t = get_t_dict(translations.get(language, translations["en"]), language=language)

    # Generate timestamped output directory
    now = datetime.now()
    timestamp = f"{now.microsecond // 10000:02d}"
    output_dir = os.path.join(os.path.dirname(base_output_dir) or ".", f"{timestamp}_{os.path.basename(base_output_dir)}")

    # Setup file paths
    rel_output_dir = os.path.relpath(output_dir, start=os.path.dirname(base_output_dir) or ".")
    rel_table_filename = os.path.join(rel_output_dir, f"reliability_{factor_key}.csv")
    item_table_filename = os.path.join(rel_output_dir, f"item_total_{factor_key}.csv")

    file_contents = {}
    markdown_log = [t["analysis_for_factor"].format(variable_names.get(factor_key, factor_key))]

    def log_message(message: str):
        markdown_log.append(message + "\n")

    # Get observed variables for this factor
    variables_list = [v.code for v in variables if v.variable_type == VariableType.OBSERVED and v.parent_code == factor_key]
    
    if not variables_list:
        log_message(t["no_observed_vars"])
        actions = [
            Action(
                action_type=ActionType.DISCARD_FACTOR,
                method="single_factor_scale_reliability_testing",
                issue=t["action_no_observed_vars_issue"],
                comment=t["action_no_observed_vars_comment"],
                status="pending",
                action_params={"factor": factor_key},
                reflection_params={
                    "tool": "single_factor_scale_reliability_testing",
                    "parameters": {"factor_key": factor_key, "language": language},
                    "comment": f"Verify factor `{factor_key}` after discard attempt"
                }
            )
        ]
        return ToolOutput(
            results=serialize_dict({"factor_key": factor_key, "variables": []}),
            logs=markdown_log,
            file_contents=file_contents,
            action=actions
        )

    # Perform reliability analysis
    reliability_table, item_total_table, diagnostics = generate_reliability_analysis(
        data=data,
        variables=variables_list,
        factor_name=factor_key,
        save_results=False,
        output_dir=output_dir,
        t=t
    )

    # Convert and format tables
    reliability_table = pd.DataFrame({
        "Cronbach's Alpha": [float(reliability_table[t['cronbach_alpha']][0]) if reliability_table[t['cronbach_alpha']][0] != "N/A" else None],
        "Number of Items": [reliability_table[t.get('num_items', 'N of Items')][0]]
    })
    
    item_total_table = pd.DataFrame({
        "Variable": item_total_table[t['item']],
        "Scale Mean if Item Deleted": item_total_table[t['scale_mean_if_deleted']].astype(float).round(3),
        "Scale Variance if Item Deleted": item_total_table[t['scale_variance_if_deleted']].astype(float).round(3),
        "Corrected Item-Total Correlation": item_total_table[t['corrected_item_total_corr']].astype(float).round(3),
        "Cronbach's Alpha if Item Deleted": item_total_table[t['alpha_if_deleted']].astype(float).round(3)
    })

    # Store tables in file_contents
    file_contents[rel_table_filename] = reliability_table.to_csv(index=False)
    file_contents[item_table_filename] = item_total_table.to_csv(index=False)

    # Log table information
    log_message(t["reliability_results"])
    log_message(t["reliability_table"].format(rel_table_filename))
    log_message(t["item_total_stats"].format(item_table_filename))

    # Extract diagnostics
    alpha = diagnostics["Overall_Scale"]["Cronbach_Alpha"]
    diagnostic_comments = {
        "Overall": diagnostics["Overall_Scale"]["Comments"],
        "Items": {var: diagnostics["Item_Total_Statistics"][var]["Comments"] for var in variables_list}
    }

    # Get diagnostic criteria
    alpha_diag = get_diagnostic_criteria(
        analysis_type="cronbach_alpha",
        metric_value=alpha if alpha != "N/A" else None,
        additional_data={"item_total_corr": [row["Variable"] for _, row in item_total_table.iterrows() if row["Corrected Item-Total Correlation"] < 0.3]}
    )
    
    low_citc_vars = [
        item for warning in alpha_diag.get("warnings", [])
        for item in warning.split(": ")[-1].split(", ")
        if "Consider removing items" in warning
    ]

    # Report results
    log_message(t["cronbach_alpha_fmt"].format(alpha if alpha != 'N/A' else t["not_available"]))
    log_message(t["diagnostic_assessment"])
    log_message(t["overall_scale"].format('; '.join(diagnostic_comments['Overall'])))
    
    for var, comments in diagnostic_comments["Items"].items():
        log_message(f"- {var}: {'; '.join(comments)}")

    # Determine required actions
    actions = []
    
    if alpha != "N/A":
        if alpha >= 0.95:
            log_message(f"\n{t['issue_alpha_high'].format(f'{alpha:.3f}')}")
            actions.append(
                Action(
                    action_type=ActionType.RECHECK_DATA,
                    method="single_factor_scale_reliability_testing",
                    issue=t["action_alpha_high_issue"],
                    comment=t["action_alpha_high_comment"],
                    status="pending",
                    action_params={"factor": factor_key, "issue_type": "alpha_high"}
                )
            )
        elif alpha < 0.6:
            log_message(f"\n{t['issue_alpha_low'].format(f'{alpha:.3f}')}")
            actions.append(
                Action(
                    action_type=ActionType.RECHECK_DATA,
                    method="single_factor_scale_reliability_testing",
                    issue=t["action_alpha_low_issue"],
                    comment=t["action_alpha_low_comment"],
                    status="pending",
                    action_params={"factor": factor_key, "issue_type": "alpha_low"}
                )
            )

    if alpha == "N/A" or len(variables_list) < 2:
        log_message(f"\n{t['factor_cannot_analyze'].format(factor_key)}")
        actions.append(
            Action(
                action_type=ActionType.DISCARD_FACTOR,
                method="single_factor_scale_reliability_testing",
                issue=t["action_alpha_na_issue"],
                comment=t["action_alpha_na_comment"],
                status="pending",
                action_params={"factor": factor_key},
                 reflection_params={
                    "tool": "single_factor_scale_reliability_testing",
                    "parameters": {"factor_key": factor_key, "language": language},
                    "comment": f"Re-evaluate factor `{factor_key}` after discard"
                }
            )
        )
    
    if low_citc_vars:
        log_message(f"\n{t['low_citc_vars'].format(', '.join(low_citc_vars))}")
        for var in low_citc_vars:
            citc_value = item_total_table[item_total_table['Variable'] == var]['Corrected Item-Total Correlation'].iloc[0]
            actions.append(
                Action(
                    action_type=ActionType.REMOVE_VARIABLE,
                    method="single_factor_scale_reliability_testing",
                    issue=t["action_low_citc_issue"],
                    comment=t["action_low_citc_comment"],
                    status="pending",
                    action_params={"variable": var},
                     reflection_params={
                        "tool": "single_factor_scale_reliability_testing",
                        "parameters": {"factor_key": factor_key, "language": language},
                        "comment": f"Re-run reliability analysis for `{factor_key}` after removing `{var}`"
                    }
                )
            )
    
    if not actions:
        log_message(f"\n{t['analysis_complete'].format(factor_key, ', '.join(variables_list))}")
    
    return ToolOutput(
        results={"factor_key": factor_key, "variables": variables_list, "diagnostics": diagnostic_comments},
        logs=markdown_log,
        file_contents=file_contents,
        action=actions if actions else None
    )


def run_reliability_analysis(
    data: pd.DataFrame,
    variables: list[Variable],
    params: dict
) -> ToolOutput:
    """
    Orchestrate reliability analysis for ALL latent factors regardless of role.
    Collects actions and reflections from sub-tools and uses timestamped directories to avoid overwriting.

    Parameters:
        data: Input DataFrame containing observed variables
        variables: list of all Variable objects
        params: dictionary containing analysis parameters
            - output_dir (str): base output directory name (default: "reliability_analysis")
            - save_files (bool): whether to save generated files to disk (default: False)
            - language (str): language for output messages - "en" or "vi" (default: "en")

    Returns:
        ToolOutput: Contains combined results, logs, file_contents, and list of data-affecting actions
    """
    # Extract parameters
    base_output_dir = params.get("output_dir", "rel_mul")
    save_files = params.get("save_files", False)

    # Translation dictionary
    translations = {
        "en": {
            "title": "# Reliability Analysis Report\n\n",
            "overview": "## Overview\n\n",
            "overview_desc": "This report presents the reliability analysis results for all latent factors using Cronbach's Alpha assessment.\n\n",
            "no_latent_vars": "**Note**: No latent variables found in the dataset. Reliability analysis is only applicable to latent constructs with multiple observed indicators.\n",
            "no_indicators": "**Note**: No latent variables with observed indicators found. Reliability analysis requires latent factors with multiple observed variables.\n",
            "desc_stats": "## Descriptive Statistics\n\n",
            "desc_stats_summary": "Summary statistics for all observed variables across all latent factors: `{}`\n\n",
            "total_vars": "**Total variables**: {}\n\n",
            "factor_results": "## Factor Analysis Results\n\n",
            "analyzing_factors": "Analyzing {} latent factor(s):\n",
            "standalone_vars": "## Standalone Observed Variables\n\n",
            "standalone_desc": "The following observed variables are not part of any latent factor:\n",
            "summary": "## Summary\n\n",
            "total_analyzed": "- **Total latent factors analyzed**: {}\n",
            "factors_retained": "- **Factors retained after analysis**: {}\n",
            "items_after": "- **Total items after reliability check**: {}\n",
            "actions_required": "- **Actions required**: {}\n"
        },
        "vi": {
            "title": "# Báo Cáo Phân Tích Độ Tin Cậy\n\n",
            "overview": "## Tổng Quan\n\n",
            "overview_desc": "Báo cáo này trình bày kết quả phân tích độ tin cậy cho tất cả các nhân tố tiềm ẩn bằng phương pháp đánh giá Cronbach's Alpha.\n\n",
            "no_latent_vars": "**Lưu ý**: Không tìm thấy biến tiềm ẩn nào trong tập dữ liệu. Phân tích độ tin cậy chỉ áp dụng cho các cấu trúc tiềm ẩn có nhiều chỉ báo quan sát.\n",
            "no_indicators": "**Lưu ý**: Không tìm thấy biến tiềm ẩn nào có chỉ báo quan sát. Phân tích độ tin cậy yêu cầu các nhân tố tiềm ẩn phải có nhiều biến quan sát.\n",
            "desc_stats": "## Thống Kê Mô Tả\n\n",
            "desc_stats_summary": "Thống kê tóm tắt cho tất cả các biến quan sát trên tất cả các nhân tố tiềm ẩn: `{}`\n\n",
            "total_vars": "**Tổng số biến**: {}\n\n",
            "factor_results": "## Kết Quả Phân Tích Nhân Tố\n\n",
            "analyzing_factors": "Đang phân tích {} nhân tố tiềm ẩn:\n",
            "standalone_vars": "## Các Biến Quan Sát Độc Lập\n\n",
            "standalone_desc": "Các biến quan sát sau không thuộc nhân tố tiềm ẩn nào:\n",
            "summary": "## Tóm Tắt\n\n",
            "total_analyzed": "- **Tổng số nhân tố tiềm ẩn đã phân tích**: {}\n",
            "factors_retained": "- **Các nhân tố được giữ lại sau phân tích**: {}\n",
            "items_after": "- **Tổng số mục sau kiểm tra độ tin cậy**: {}\n",
            "actions_required": "- **Các hành động cần thực hiện**: {}\n"
        }
    }
    
    language = params.get("language", "en")
    # Get translations for selected language
    t = get_t_dict(translations.get(language, translations["en"]), language=language)
    
    # Generate timestamped output directory
    now = datetime.now()
    timestamp = f"{now.microsecond // 10000:02d}"
    output_dir = os.path.join(os.path.dirname(base_output_dir) or ".", f"{timestamp}_{os.path.basename(base_output_dir)}")
    
    # Setup file paths
    variable_names = {var.code: var.name for var in variables}
    rel_output_dir = os.path.relpath(output_dir, start=os.path.dirname(base_output_dir) or ".")
    
    file_contents = {}
    markdown_log = [
        t["title"],
        t["overview"],
        t["overview_desc"]
    ]

    # Identify ALL latent variables (regardless of role)
    all_latents = [var for var in variables if var.variable_type == VariableType.LATENT]
    
    if not all_latents:
        markdown_log.append(t["no_latent_vars"])
        return ToolOutput(
            results={"factor_groups_refined": {}, "items_after_reliability": []},
            logs=markdown_log,
            file_contents=file_contents,
            action=None
        )

    # Build factor groups for all latent variables
    factor_groups = {}
    for latent in all_latents:
        observed_vars = [var.code for var in variables if var.parent_code == latent.code and var.variable_type == VariableType.OBSERVED]
        if observed_vars:
            factor_groups[latent.code] = observed_vars

    if not factor_groups:
        markdown_log.append(t["no_indicators"])
        return ToolOutput(
            results={"factor_groups_refined": {}, "items_after_reliability": []},
            logs=markdown_log,
            file_contents=file_contents,
            action=None
        )
    # Compute descriptive statistics for all observed variables across all latent factors
    all_observed_vars = []
    for latent in all_latents:
        observed_vars = [var.code for var in variables if var.parent_code == latent.code and var.variable_type == VariableType.OBSERVED]
        all_observed_vars.extend(observed_vars)
    
    if all_observed_vars:
        descriptive_stats = []
        for var_code in all_observed_vars:
            if var_code in data.columns:
                var_data = data[var_code].dropna()
                descriptive_stats.append({
                    "Variable": var_code,
                    "Mean": var_data.mean(),
                    "Std": var_data.std(),
                    "N": len(var_data)
                })
        
        if descriptive_stats:
            descriptive_table = pd.DataFrame(descriptive_stats)
            descriptive_table["Mean"] = descriptive_table["Mean"].round(3)
            descriptive_table["Std"] = descriptive_table["Std"].round(3)
            
            # Save descriptive statistics table
            descriptive_filename = os.path.join(rel_output_dir, "descriptive_statistics_all_variables.csv")
            file_contents[descriptive_filename] = descriptive_table.to_csv(index=False)
            
            markdown_log.append(t["desc_stats"])
            markdown_log.append(t["desc_stats_summary"].format(descriptive_filename))
            markdown_log.append(t["total_vars"].format(len(descriptive_stats)))
            
    # Process each latent factor
    all_actions = []
    factor_groups_refined = {}
    items_after_reliability = []

    markdown_log.append(t["factor_results"])
    markdown_log.append(t["analyzing_factors"].format(len(all_latents)))
    for latent in all_latents:
        role_label = latent.role.value if latent.role else "unspecified"
        markdown_log.append(f"- **{latent.name}** ({latent.code}): {role_label}\n")
    markdown_log.append("\n")

    for latent in all_latents:
        factor_key = latent.code
        factor_vars = [var for var in variables if var.code == factor_key or var.parent_code == factor_key]
        
        # Prepare sub-tool parameters
        sub_params = {
            "factor_key": factor_key,
            "output_dir": output_dir,
            "save_files": False,  # Handle saving at the end
            "variable_names": variable_names,
            "language": language
        }
        
        # Run single factor analysis
        factor_output = single_factor_scale_reliability_testing(data, factor_vars, sub_params)

        # Integrate results
        markdown_log.extend(factor_output.logs)
        file_contents.update(factor_output.file_contents)

        # Process factor results
        kept_vars = factor_output.results["variables"]
        if factor_output.action:
            all_actions.extend(factor_output.action)
            
        # Check if factor should be kept (not discarded)
        if not any(a.action_type == ActionType.DISCARD_FACTOR for a in factor_output.action or []):
            if kept_vars:  # Only add if there are variables
                factor_groups_refined[factor_key] = kept_vars
                items_after_reliability.extend(kept_vars)

    # Include any standalone observed variables (not part of latent factors)
    standalone_observed = [
        var.code for var in variables 
        if var.variable_type == VariableType.OBSERVED 
        and var.parent_code is None
    ]
    
    if standalone_observed:
        markdown_log.append(t["standalone_vars"])
        markdown_log.append(t["standalone_desc"])
        for obs_code in standalone_observed:
            obs_var = next((v for v in variables if v.code == obs_code), None)
            if obs_var:
                markdown_log.append(f"- **{obs_var.name}** ({obs_code}): {obs_var.role.value if obs_var.role else 'unspecified'}\n")
                items_after_reliability.append(obs_code)
        markdown_log.append("\n")

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
            elif filename.endswith((".csv", ".txt", ".md")):
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
    results = {
        "factor_groups_refined": factor_groups_refined,
        "items_after_reliability": items_after_reliability
    }

    # Summary
    markdown_log.append(t["summary"])
    markdown_log.append(t["total_analyzed"].format(len(all_latents)))
    markdown_log.append(t["factors_retained"].format(len(factor_groups_refined)))
    markdown_log.append(t["items_after"].format(len(items_after_reliability)))
    if all_actions:
        markdown_log.append(t["actions_required"].format(len(all_actions)))

    return ToolOutput(
        results=results,
        logs=markdown_log,
        file_contents=file_contents,
        action=all_actions if all_actions else None
    )

#####################################################
#####################################################
#####################################################

# Exploratory Factor Analysis (EFA)
def perform_kmo_bartlett_tool(
    data: pd.DataFrame,
    variables: list[Variable],
    params: dict
) -> ToolOutput:
    """
    Perform KMO and Bartlett's tests to assess EFA suitability and suggest actions if criteria are not met.

    Parameters:
        data: DataFrame with observed variables
        variables: list of Variable objects
        params: dictionary containing analysis parameters
            - output_dir (str): base output directory name (default: "efa_analysis")
            - save_files (bool): whether to save generated files to disk (default: False)
            - variable_names (dict): mapping of variable codes to display names
            - language (str): language for output messages - "en" or "vi" (default: "en")

    Returns:
        ToolOutput: Contains KMO and Bartlett's test results, logs, file contents, and suggested actions
    """
    # Extract parameters
    base_output_dir = params.get("output_dir", "efa")
    save_files = params.get("save_files", False)
    variable_names = params.get("variable_names", {var.code: var.name for var in variables})
    language = params.get("language", "en")

    # Define translations dictionary
    translations = {
        "en": {
            "title": "### KMO and Bartlett's Test Analysis\n",
            "results_title": "**KMO and Bartlett's Test Results**\n\n",
            "results_table_label": "\n\nResults table: `{}`\n",
            "analysis_comments": "\n**Analysis Comments**:\n",
            "warning_kmo": "\n**Warning**: KMO = {:.3f} < 0.5. Data is not suitable for EFA.\n",
            "warning_bartlett": "\n**Warning**: Bartlett's Sig. = {:.3f} > 0.05. Variables are not significantly correlated.\n",
            "result_suitable": "\n**Result**: Data is suitable for EFA analysis.\n",
            "action_issue_kmo": "KMO = {kmo:.3f} < 0.5",
            "action_issue_bartlett": "Bartlett's Sig. = {p:.3f} > 0.05",
            "action_comment": "Check variable list, collect more data, review scale content, or examine research model",
            "kmo_measure": "Kaiser-Meyer-Olkin (KMO) Measure of Sampling Adequacy",
            "bartlett_chi": "Bartlett's Test of Sphericity - Approx. Chi-Square",
            "bartlett_df": "Bartlett's Test of Sphericity - df",
            "bartlett_sig": "Bartlett's Test of Sphericity - Sig."
        },
        "vi": {
            "title": "### Phân Tích Kiểm Định KMO và Bartlett\n",
            "results_title": "**Kết Quả Kiểm Định KMO và Bartlett**\n\n",
            "results_table_label": "\n\nBảng kết quả: `{}`\n",
            "analysis_comments": "\n**Nhận Xét Phân Tích**:\n",
            "warning_kmo": "\n**Cảnh báo**: KMO = {:.3f} < 0.5. Dữ liệu không phù hợp cho EFA.\n",
            "warning_bartlett": "\n**Cảnh báo**: Bartlett's Sig. = {:.3f} > 0.05. Các biến không có tương quan có ý nghĩa.\n",
            "result_suitable": "\n**Kết quả**: Dữ liệu phù hợp cho phân tích EFA.\n",
            "action_issue_kmo": "KMO = {kmo:.3f} < 0.5",
            "action_issue_bartlett": "Giá trị p Bartlett = {p:.3f} > 0.05",
            "action_comment": "Kiểm tra danh sách biến, thu thập thêm dữ liệu, xem xét nội dung thang đo, hoặc kiểm tra mô hình nghiên cứu",
            "kmo_measure": "Hệ số Kaiser-Meyer-Olkin (KMO)",
            "bartlett_chi": "Kiểm định Bartlett - Chi-Square xấp xỉ",
            "bartlett_df": "Kiểm định Bartlett - Bậc tự do (df)",
            "bartlett_sig": "Kiểm định Bartlett - Ý nghĩa (Sig.)"
        }
    }

    # Get translations for selected language
    t = get_t_dict(translations.get(language, translations["en"]), language=language)
    
    # Generate timestamped output directory
    now = datetime.now()
    timestamp = f"{now.microsecond // 10000:02d}"
    output_dir = os.path.join(os.path.dirname(base_output_dir) or ".", f"{timestamp}_{os.path.basename(base_output_dir)}")
    rel_output_dir = os.path.relpath(output_dir, start=os.path.dirname(base_output_dir) or ".")
    
    logs = [t["title"]]
    file_contents = {}
    actions = []

    # Perform KMO and Bartlett's tests
    kmo_bartlett_table, kmo_comments = perform_kmo_and_bartlett_tests(
        data=data, save_results=False, output_dir=output_dir, t=t
    )

    # Extract test results
    kmo_value = float(kmo_bartlett_table[t.get("kmo_measure", t.get("kmo_per_item_label", "Kaiser-Meyer-Olkin Measure of Sampling Adequacy"))])
    bartlett_p = float(kmo_bartlett_table[t.get("bartlett_sig", "Bartlett's Test of Sphericity - Sig.")])
    bartlett_chi = float(kmo_bartlett_table[t.get("bartlett_chi", "Bartlett's Test of Sphericity - Approx. Chi-Square")])
    bartlett_df = int(kmo_bartlett_table[t.get("bartlett_df", "Bartlett's Test of Sphericity - df")])

    # Prepare results dataframe
    kmo_bartlett_df = pd.DataFrame([{
        'Kaiser-Meyer-Olkin Measure of Sampling Adequacy': kmo_value,
        "Bartlett's Test of Sphericity - Approx. Chi-Square": bartlett_chi,
        "Bartlett's Test of Sphericity - df": bartlett_df,
        "Bartlett's Test of Sphericity - Sig.": bartlett_p
    }])

    # Store file content
    kmo_filename = os.path.join(rel_output_dir, "kmo_bartlett_results.csv")
    file_contents[kmo_filename] = kmo_bartlett_df.to_csv(index=False)

    # Generate logs
    # Build Markdown summary table using DataFrame
    summary_df = pd.DataFrame({
        "Measure": [
            t["kmo_measure"],
            t["bartlett_chi"],
            t["bartlett_df"],
            t["bartlett_sig"]
        ],
        "Value": [
            f"{kmo_value:.3f}",
            f"{bartlett_chi:.3f}",
            f"{bartlett_df}",
            f"{bartlett_p:.3f}"
        ]
    })

    logs.append(t["results_title"])
    logs.append(summary_df.to_markdown(index=False))
    logs.append(t["results_table_label"].format(kmo_filename))
    logs.append(t["analysis_comments"])

    for comment in kmo_comments:
        logs.append(f"- {comment}\n")

    # Determine actions based on criteria
    if kmo_value < 0.5:
        logs.append(t["warning_kmo"].format(kmo_value))
        actions.append(
            Action(
                action_type=ActionType.RECHECK_DATA,
                method="perform_kmo_bartlett_tool",
                issue=t["action_issue_kmo"].format(kmo=kmo_value),
                comment=t["action_comment"],
                status="pending"
            )
        )

    if bartlett_p > 0.05:
        logs.append(t["warning_bartlett"].format(bartlett_p))
        actions.append(
            Action(
                action_type=ActionType.RECHECK_DATA,
                method="perform_kmo_bartlett_tool",
                issue=t["action_issue_bartlett"].format(p=bartlett_p),
                comment=t["action_comment"],
                status="pending"
            )
        )

    if not actions:
        logs.append(t["result_suitable"])

    # Save files if requested
    if save_files:
        os.makedirs(output_dir, exist_ok=True)
        for filename, content in file_contents.items():
            save_path = os.path.join(output_dir, os.path.basename(filename))
            if filename.endswith(".csv"):
                with open(save_path, "w", encoding="utf-8") as f:
                    f.write(str(content))

    results = {"kmo_value": kmo_value, "bartlett_p": bartlett_p}
    return ToolOutput(
        results=results,
        logs=logs,
        file_contents=file_contents,
        action=actions if actions else None
    )


def determine_number_of_factors_tool(
    data: pd.DataFrame,
    variables: list[Variable],
    params: dict
) -> ToolOutput:
    """
    Determine the number of factors for EFA based on eigenvalues and generate scree plot.

    Parameters:
        data: DataFrame with observed variables
        variables: list of Variable objects
        params: dictionary containing analysis parameters
            - output_dir (str): base output directory name (default: "efa_analysis")
            - save_files (bool): whether to save generated files to disk (default: False)
            - language (str): language for output messages - "en" or "vi" (default: "en")

    Returns:
        ToolOutput: Contains number of factors, eigenvalues, scree plot, and analysis logs
    """
    # Extract parameters
    base_output_dir = params.get("output_dir", "efa_analysis")
    save_files = params.get("save_files", False)
    language = params.get("language", "en")

    # Define translations dictionary
    translations = {
        "en": {
            "title": "### Factor Number Determination\n",
            "n_factors_msg": "Number of factors extracted: {} (eigenvalue > 1).\n",
            "scree_plot": "Scree plot: `{}`\n",
            "eigenvalues_table": "Eigenvalues table: `{}`\n",
            "analysis_comments": "\n**Analysis Comments**:\n"
        },
        "vi": {
            "title": "### Xác Định Số Lượng Nhân Tố\n",
            "n_factors_msg": "Số lượng nhân tố trích xuất: {} (eigenvalue > 1).\n",
            "scree_plot": "Biểu đồ scree: `{}`\n",
            "eigenvalues_table": "Bảng eigenvalues: `{}`\n",
            "analysis_comments": "\n**Nhận Xét Phân Tích**:\n"
        }
    }

    # Get translations for selected language
    t = get_t_dict(translations.get(language, translations["en"]), language=language)
    
    # Generate timestamped output directory
    now = datetime.now()
    timestamp = f"{now.microsecond // 10000:02d}"
    output_dir = os.path.join(os.path.dirname(base_output_dir) or ".", f"{timestamp}_{os.path.basename(base_output_dir)}")
    rel_output_dir = os.path.relpath(output_dir, start=os.path.dirname(base_output_dir) or ".")
    
    logs = [t["title"]]
    file_contents = {}

    # Define filenames
    scree_plot_filename = "scree_plot.png"
    eigenvalues_filename = "eigenvalues.csv"
    comments_filename = "variance_comments.txt"

    # Determine factors using eigenvalues
    n_factors, eigenvalues_df, comments, scree_plot_base64 = determine_factors(
        data=data,
        save_results=False,
        output_dir=None,
        eigenvalues_filename=eigenvalues_filename,
        comments_filename=comments_filename,
        t=t
    )

    # Store file contents
    eigenvalues_path = os.path.join(rel_output_dir, eigenvalues_filename)
    file_contents[eigenvalues_path] = eigenvalues_df.to_csv(index=True)

    scree_filename = os.path.join(rel_output_dir, scree_plot_filename)
    file_contents[scree_filename] = scree_plot_base64

    # Generate logs
    logs.append(t["n_factors_msg"].format(n_factors))
    logs.append(t["scree_plot"].format(scree_filename))
    logs.append(t["eigenvalues_table"].format(eigenvalues_path))
    logs.append(t["analysis_comments"])

    for comment in comments:
        logs.append(f"- {comment}\n")

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
            elif filename.endswith(".csv"):
                with open(save_path, "w", encoding="utf-8") as f:
                    f.write(str(content))

    results = {"n_factors": n_factors, "eigenvalues_df": eigenvalues_df}
    return ToolOutput(
        results=results,
        logs=logs,
        file_contents=file_contents,
        action=None
    )


def perform_pca_varimax_tool(
    data: pd.DataFrame,
    variables: list[Variable],
    params: dict
) -> ToolOutput:
    """
    Perform PCA with Varimax rotation for EFA analysis.

    Parameters:
        data: DataFrame with observed variables
        variables: list of Variable objects
        params: dictionary containing analysis parameters
            - output_dir (str): base output directory name (default: "efa_analysis")
            - save_files (bool): whether to save generated files to disk (default: False)
            - n_factors (int): number of factors to extract (required)
            - language (str): language for output messages - "en" or "vi" (default: "en")

    Returns:
        ToolOutput: Contains rotated factor loadings matrix and PCA diagnostics
    """
    # Extract parameters
    base_output_dir = params.get("output_dir", "efa_analysis")
    save_files = params.get("save_files", False)
    n_factors = params["n_factors"]
    language = params.get("language", "en")

    # Define translations dictionary
    translations = {
        "en": {
            "title": "### PCA with Varimax Rotation\n",
            "efa_msg": "EFA analysis with {} variables and {} factors (Varimax rotation).\n",
            "rotated_matrix": "\n**Rotated Factor Matrix**: `{}`\n",
            "analysis_comments": "\n**Analysis Comments**:\n"
        },
        "vi": {
            "title": "### PCA với Phép Quay Varimax\n",
            "efa_msg": "Phân tích EFA với {} biến và {} nhân tố (phép quay Varimax).\n",
            "rotated_matrix": "\n**Ma Trận Nhân Tố Đã Quay**: `{}`\n",
            "analysis_comments": "\n**Nhận Xét Phân Tích**:\n"
        }
    }

    # Get translations for selected language
    t = get_t_dict(translations.get(language, translations["en"]), language=language)
    
    # Generate timestamped output directory
    now = datetime.now()
    timestamp = f"{now.microsecond // 10000:02d}"
    output_dir = os.path.join(os.path.dirname(base_output_dir) or ".", f"{timestamp}_{os.path.basename(base_output_dir)}")
    rel_output_dir = os.path.relpath(output_dir, start=os.path.dirname(base_output_dir) or ".")
    
    logs = [t["title"]]
    file_contents = {}

    logs.append(t["efa_msg"].format(len(data.columns), n_factors))

    # Perform PCA with Varimax rotation
    loadings, loading_comments, pca_diagnostics = perform_pca_varimax(
        data=data, n_factors=n_factors, save_results=False, output_dir=output_dir, t=t
    )

    # Format loadings matrix
    rotated_matrix = loadings.round(3)
    rotated_matrix.index.name = "Variable"
    rotated_matrix.columns = [f"Factor {i+1}" for i in range(n_factors)]

    # Store file content
    matrix_filename = os.path.join(rel_output_dir, "rotated_component_matrix.csv")
    file_contents[matrix_filename] = rotated_matrix.to_csv(index=True)

    # Generate logs
    logs.append(t["rotated_matrix"].format(matrix_filename))
    logs.append(t["analysis_comments"])
    for comment in loading_comments:
        logs.append(f"- {comment}\n")

    # Save files if requested
    if save_files:
        os.makedirs(output_dir, exist_ok=True)
        for filename, content in file_contents.items():
            save_path = os.path.join(output_dir, os.path.basename(filename))
            if filename.endswith(".csv"):
                with open(save_path, "w", encoding="utf-8") as f:
                    f.write(str(content))

    results = {"loadings": rotated_matrix, "pca_diagnostics": pca_diagnostics}
    return ToolOutput(
        results=results,
        logs=logs,
        file_contents=file_contents,
        action=None
    )


def analyze_factor_loadings_tool(
    data: pd.DataFrame,
    variables: list[Variable],
    params: dict
) -> ToolOutput:
    """
    Analyze factor loadings to identify variables for removal based on low loadings or cross-loadings.

    Parameters:
        data: DataFrame with observed variables
        variables: list of Variable objects
        params: dictionary containing analysis parameters
            - output_dir (str): base output directory name (default: "efa_analysis")
            - save_files (bool): whether to save generated files to disk (default: False)
            - loadings (pd.DataFrame): factor loadings matrix (required)
            - variable_names (dict): mapping of variable codes to display names
            - target_latents:
            - language (str): language for output messages - "en" or "vi" (default: "en")

    Returns:
        ToolOutput: Contains items to remove and actions for variable removal with reflections
    """
    # Extract parameters
    base_output_dir = params.get("output_dir", "efa_analysis")
    save_files = params.get("save_files", False)
    loadings = params["loadings"]
    variable_names = params.get("variable_names", {v.code: v.name for v in variables})
    target_latents = params.get("target_latents", [])
    language = params.get("language", "en")
    count = params.get("count", 1)

    # Define translations dictionary
    translations = {
        "en": {
            "title": "### Factor Loading Analysis\n",
            "low_loading_msg": "- Variable `{}` has low loading (Max = {:.3f} < 0.4). Recommended for removal.\n",
            "cross_loading_msg": "- Variable `{}` shows cross-loading (Highest = {:.3f}, Second = {:.3f}, Difference = {:.3f} ≤ 0.3). Recommended for removal.\n",
            "removal_summary": "\n**Removal Recommendations**: {} variables: {}.\n",
            "no_removal": "\n**Result**: No variables require removal.\n",
            "remove_comment_low": "Remove variable due to insufficient factor loading",
            "remove_comment_cross": "Remove variable due to cross-loading",
            "rerun_reliability": "Re-run reliability analysis for factor `{}` after removing `{}`",
            "rerun_efa": "Re-run EFA after removing variables with low or cross-loadings",
            "reanalyze_comment": "Re-run EFA and reliability testing after variable removal",
            "low_loading_issue": "Low loading (Max = {:.3f} < 0.4)",
            "cross_loading_issue": "Cross-loading (Highest = {:.3f}, Second = {:.3f}, Diff = {:.3f} ≤ 0.3)",
            "some_low_cross": "Some variables exhibit low or cross-loadings"
        },
        "vi": {
            "title": "### Phân Tích Hệ Số Tải Nhân Tố\n",
            "low_loading_msg": "- Biến `{}` có hệ số tải thấp (Max = {:.3f} < 0.4). Đề xuất loại bỏ.\n",
            "cross_loading_msg": "- Biến `{}` có **tải chéo** (Cao nhất = {:.3f}, Thứ hai = {:.3f}, Chênh lệch = {:.3f} ≤ 0.3). Đề xuất loại bỏ.\n",
            "removal_summary": "\n**Đề xuất loại bỏ**: {} biến: {}.\n",
            "no_removal": "\n**Kết quả**: Không có biến nào cần loại bỏ.\n",
            "remove_comment_low": "Loại bỏ biến do hệ số tải nhân tố không đủ",
            "remove_comment_cross": "Loại bỏ biến do **tải chéo**",
            "rerun_reliability": "Chạy lại phân tích độ tin cậy cho nhân tố `{}` sau khi loại bỏ `{}`",
            "rerun_efa": "Chạy lại phân tích EFA sau khi loại bỏ các biến có tải thấp hoặc tải chéo",
            "reanalyze_comment": "Chạy lại EFA và kiểm tra độ tin cậy sau khi loại bỏ biến",
            "low_loading_issue": "Hệ số tải thấp (Max = {:.3f} < 0.4)",
            "cross_loading_issue": "**Tải chéo** (Cao nhất = {:.3f}, Thứ hai = {:.3f}, Chênh lệch = {:.3f} ≤ 0.3)",
            "some_low_cross": "Một số biến có tải thấp hoặc tải chéo"
        }
    }

    # Get translations for selected language
    t = get_t_dict(translations.get(language, translations["en"]), language=language)
    
    # Generate timestamped output directory
    now = datetime.now()
    timestamp = f"{now.microsecond // 10000:02d}"
    output_dir = os.path.join(os.path.dirname(base_output_dir) or ".", f"{timestamp}_{os.path.basename(base_output_dir)}")
    rel_output_dir = os.path.relpath(output_dir, start=os.path.dirname(base_output_dir) or ".")
    
    logs = [t["title"]]
    file_contents = {}

    n_factors = len(loadings.columns)
    items_to_remove = []
    actions = []

    # Map variables to their parent factors
    factor_mapping = {}
    if target_latents:
        # Use the provided target latents for mapping
        for var in variables:
            if var.variable_type == VariableType.OBSERVED and var.parent_code:
                if any(lat.code == var.parent_code for lat in target_latents):
                    factor_mapping[var.code] = var.parent_code
    else:
        # Fallback to original behavior
        for var in variables:
            if var.variable_type == VariableType.OBSERVED and var.parent_code:
                factor_mapping[var.code] = var.parent_code

    for var in variables:
        if var.variable_type == VariableType.OBSERVED and var.parent_code:
            factor_mapping[var.code] = var.parent_code

    # Analyze each variable's loadings
    for var in loadings.index:
        abs_loadings = abs(loadings.loc[var])
        max_loading = abs_loadings.max()
        parent_factor = factor_mapping.get(var, "Unknown")

        # Check for low loadings
        if max_loading < 0.4:
            comment = t["low_loading_issue"].format(max_loading)
            items_to_remove.append((var, comment))
            actions.append(
                Action(
                    action_type=ActionType.REMOVE_VARIABLE,
                    method="analyze_factor_loadings_tool",
                    issue=comment,
                    comment=t["remove_comment_low"],
                    status="pending",
                    action_params={"variable": var},
                    reflection_params={
                        "tool": "single_factor_scale_reliability_testing",
                        "parameters": {
                            "factor_key": parent_factor,
                            "language": language
                        },
                        "comment": t["rerun_reliability"].format(parent_factor, var)
                    }
                )
            )
            logs.append(t["low_loading_msg"].format(var, max_loading))
            continue

        # Check for cross-loadings (only if multiple factors)
        if n_factors > 1:
            sorted_loadings = abs_loadings.sort_values(ascending=False)
            highest = sorted_loadings.iloc[0]
            second_highest = sorted_loadings.iloc[1]
            diff = highest - second_highest

            if diff <= 0.3:
                comment = t["cross_loading_issue"].format(highest, second_highest, diff)
                items_to_remove.append((var, comment))
                actions.append(
                    Action(
                        action_type=ActionType.REMOVE_VARIABLE,
                        method="analyze_factor_loadings_tool",
                        issue=comment,
                        comment=t["remove_comment_cross"],
                        status="pending",
                        action_params={"variable": var},
                         reflection_params={
                            "tool": "single_factor_scale_reliability_testing",
                            "parameters": {
                                "factor_key": parent_factor,
                                "language": language
                            },
                            "comment": t["rerun_reliability"].format(parent_factor, var)
                        }
                    )
                )
                logs.append(t["cross_loading_msg"].format(var, highest, second_highest, diff))

    # Generate summary logs
    if items_to_remove:
        logs.append(t["removal_summary"].format(len(items_to_remove), ', '.join([var for var, _ in items_to_remove])))

        # Add reanalysis action - preserve target_role if it exists
        reanalysis_params = {"variable_names": variable_names, "language": language, "count": count + 1}
        if "target_role" in params:
            reanalysis_params["target_role"] = params["target_role"]

        actions.append(
            Action(
                action_type=ActionType.REANALYZE,
                method="analyze_factor_loadings_tool",
                issue=t["some_low_cross"],
                comment=t["reanalyze_comment"],
                status="pending",
                reflection_params={
                    "tool": "run_efa_analysis",
                    "parameters": reanalysis_params,
                    "comment": t["rerun_efa"]
                },
                reset_actions=True
            )
        )
    else:
        logs.append(t["no_removal"])

    # Save files if requested
    if save_files:
        os.makedirs(output_dir, exist_ok=True)
        for filename, content in file_contents.items():
            save_path = os.path.join(output_dir, os.path.basename(filename))
            if filename.endswith((".csv", ".txt")):
                with open(save_path, "w", encoding="utf-8") as f:
                    f.write(str(content))

    results = {"items_to_remove": items_to_remove}
    return ToolOutput(
        results=results,
        logs=logs,
        file_contents=file_contents,
        action=actions if actions else None
    )


def calculate_variance_explained_tool(
    data: pd.DataFrame,
    variables: list[Variable],
    params: dict
) -> ToolOutput:
    """
    Calculate variance explained by factors and validate against minimum criteria.

    Parameters:
        data: DataFrame with observed variables
        variables: list of Variable objects
        params: dictionary containing analysis parameters
            - output_dir (str): base output directory name (default: "efa_analysis")
            - save_files (bool): whether to save generated files to disk (default: False)
            - eigenvalues_df (pd.DataFrame): eigenvalues dataframe (required)
            - n_factors (int): number of factors (required)
            - pca_diagnostics (dict): PCA diagnostics from previous analysis (required)
            - language (str): language for output messages - "en" or "vi" (default: "en")

    Returns:
        ToolOutput: Contains variance explained results and actions if criteria not met
    """
    # Extract parameters
    base_output_dir = params.get("output_dir", "efa_analysis")
    save_files = params.get("save_files", False)
    eigenvalues_df = params["eigenvalues_df"]
    n_factors = params["n_factors"]
    pca_diagnostics = params["pca_diagnostics"]
    language = params.get("language", "en")

    # Define translations dictionary
    translations = {
        "en": {
            "title": "### Variance Explained Analysis\n",
            "total_variance_msg": "Total variance explained: {:.3f}% (requirement ≥ 50%).\n",
            "variance_table": "\n**Total Variance Explained Table**: `{}`\n",
            "warning_low_variance": "\n**Warning**: Total variance explained = {:.3f}% < 50%. Model is not suitable.\n",
            "result_meets": "\n**Result**: Total variance explained meets requirements.\n",
            "action_issue_low_variance": "Total variance explained = {variance:.3f}% < 50%",
            "action_comment": "Check variable list, collect more data, review scale content, or examine research model"
        },
        "vi": {
            "title": "### Phân Tích Phương Sai Giải Thích\n",
            "total_variance_msg": "Tổng phương sai giải thích: {:.3f}% (yêu cầu ≥ 50%).\n",
            "variance_table": "\n**Bảng Tổng Phương Sai Giải Thích**: `{}`\n",
            "warning_low_variance": "\n**Cảnh báo**: Tổng phương sai giải thích = {:.3f}% < 50%. Mô hình không phù hợp.\n",
            "result_meets": "\n**Kết quả**: Tổng phương sai giải thích đáp ứng yêu cầu.\n",
            "action_issue_low_variance": "Tổng phương sai giải thích = {variance:.3f}% < 50%",
            "action_comment": "Kiểm tra danh sách biến, thu thập thêm dữ liệu, xem xét nội dung thang đo, hoặc kiểm tra mô hình nghiên cứu"
        }
    }

    # Get translations for selected language
    t = get_t_dict(translations.get(language, translations["en"]), language=language)
    
    # Generate timestamped output directory
    now = datetime.now()
    timestamp = f"{now.microsecond // 10000:02d}"
    output_dir = os.path.join(os.path.dirname(base_output_dir) or ".", f"{timestamp}_{os.path.basename(base_output_dir)}")
    rel_output_dir = os.path.relpath(output_dir, start=os.path.dirname(base_output_dir) or ".")
    
    logs = [t["title"]]
    file_contents = {}
    actions = []

    # Generate variance table
    variance_table, full_variance_table = generate_variance_table(
        eigenvalues_df=eigenvalues_df, n_factors=n_factors, pca_diagnostics=pca_diagnostics, full_table=True
    )

    # Store file content
    variance_filename = os.path.join(rel_output_dir, "full_variance_table.csv")
    file_contents[variance_filename] = full_variance_table.to_csv(index=False)

    # Calculate total variance explained
    total_variance = float(variance_table["Extraction Sums of Squared Loadings - % of Variance"].sum())

    # Generate logs
    logs.append(t["total_variance_msg"].format(total_variance))
    logs.append(t["variance_table"].format(variance_filename))

    # Check variance criteria
    if total_variance < 50:
        logs.append(t["warning_low_variance"].format(total_variance))
        actions.append(
            Action(
                action_type=ActionType.RECHECK_DATA,
                method="calculate_variance_explained_tool",
                issue=t["action_issue_low_variance"].format(variance=total_variance),
                comment=t["action_comment"],
                status="pending"
            )
        )
    else:
        logs.append(t["result_meets"])

    # Save files if requested
    if save_files:
        os.makedirs(output_dir, exist_ok=True)
        for filename, content in file_contents.items():
            save_path = os.path.join(output_dir, os.path.basename(filename))
            if filename.endswith(".csv"):
                with open(save_path, "w", encoding="utf-8") as f:
                    f.write(str(content))

    results = {"total_variance": total_variance}
    return ToolOutput(
        results=results,
        logs=logs,
        file_contents=file_contents,
        action=actions if actions else None
    )


def assign_factors_and_compute_scores_tool(
    data: pd.DataFrame,
    variables: list[Variable],
    params: dict
) -> ToolOutput:
    """
    Assign variables to factors based on loadings and compute factor scores.

    Parameters:
        data: DataFrame with observed variables
        variables: list of Variable objects
        params: dictionary containing analysis parameters
            - output_dir (str): base output directory name (default: "efa_analysis")
            - save_files (bool): whether to save generated files to disk (default: False)
            - loadings (pd.DataFrame): factor loadings matrix (required)
            - items_to_remove (list): list of variables to exclude (required)
            - dependent_var (Variable): dependent variable object (required)
            - variable_names (dict): mapping of variable codes to display names
            - language (str): language for output messages - "en" or "vi" (default: "en")

    Returns:
        ToolOutput: Contains factor assignments, factor scores, and factor labels
    """
    # Extract parameters
    base_output_dir = params.get("output_dir", "efa_analysis")
    save_files = params.get("save_files", False)
    loadings = params["loadings"]
    items_to_remove = params["items_to_remove"]
    variable_names = params.get("variable_names", {v.code: v.name for v in variables})
    target_latents = params.get("target_latents", [])
    target_role = params.get("target_role", "independent")
    language = params.get("language", "en")

    # Define translations dictionary
    translations = {
        "en": {
            "title": "### Factor Assignment and Score Computation\n",
            "factor_vars": "**{}**: Variables included: {}\n",
            "factor_no_vars": "**{}**: No variables assigned.\n",
            "factor_scores_table": "\n**Factor Scores Table**: `{}`\n",
            "new_factor": "New Factor {}"
        },
        "vi": {
            "title": "### Gán Nhân Tố và Tính Điểm Số\n",
            "factor_vars": "**{}**: Các biến bao gồm: {}\n",
            "factor_no_vars": "**{}**: Không có biến nào được gán.\n",
            "factor_scores_table": "\n**Bảng Điểm Số Nhân Tố**: `{}`\n",
            "new_factor": "Nhân Tố Mới {}"
        }
    }

    # Get translations for selected language
    t = get_t_dict(translations.get(language, translations["en"]), language=language)

    
    # Generate timestamped output directory
    now = datetime.now()
    timestamp = f"{now.microsecond // 10000:02d}"
    output_dir = os.path.join(os.path.dirname(base_output_dir) or ".", f"{timestamp}_{os.path.basename(base_output_dir)}")
    rel_output_dir = os.path.relpath(output_dir, start=os.path.dirname(base_output_dir) or ".")
    
    logs = [t["title"]]
    file_contents = {}

    n_factors = len(loadings.columns)
    factor_mapping = defaultdict(list)
    factor_scores = pd.DataFrame(index=data.index)
    factor_labels = {}
    items_to_remove_set = set(var for var, _ in items_to_remove)

    # Assign variables to factors
    for i, factor_col in enumerate(loadings.columns):
        factor_label = f"Factor{i+1}"
        for var in loadings.index:
            if var in items_to_remove_set:
                continue
            if loadings.loc[var].abs().idxmax() == factor_col and abs(loadings.loc[var, factor_col]) >= 0.5:
                factor_mapping[factor_label].append(var)

        # Compute factor scores
        if factor_mapping[factor_label]:
            factor_scores[factor_label] = data[factor_mapping[factor_label]].mean(axis=1)
            logs.append(t["factor_vars"].format(factor_label, ', '.join(factor_mapping[factor_label])))
        else:
            logs.append(t["factor_no_vars"].format(factor_label))

    # Create final factor groups based on target latents
    factor_groups_final = {}
    if target_latents:
        # Use provided target latents
        factor_names = {var.code: var.name for var in target_latents}
    else:
        # Fallback to all latents with matching role
        if target_role == "dependent":
            matching_latents = [var for var in variables if var.variable_type == VariableType.LATENT and var.role == VariableRole.DEPENDENT]
        else:  # independent or all
            matching_latents = [var for var in variables if var.variable_type == VariableType.LATENT and var.role == VariableRole.INDEPENDENT]
        factor_names = {var.code: var.name for var in matching_latents}

    # Map factors to original factor names
    for factor_label, items in factor_mapping.items():
        if not items:
            continue
        
        max_overlap = 0
        best_factor_key = None
        
        latents_to_check = target_latents if target_latents else [var for var in variables if var.variable_type == VariableType.LATENT]
        
        for latent in latents_to_check:

            original_items = [var.code for var in variables if var.parent_code == latent.code and var.variable_type == VariableType.OBSERVED]
            overlap = len(set(items) & set(original_items))
            if overlap > max_overlap:
                max_overlap = overlap
                best_factor_key = latent.code
        
        if best_factor_key and max_overlap > 0:
            factor_groups_final[best_factor_key] = list(set(items))
            factor_labels[factor_label] = factor_names.get(best_factor_key, f"Factor {best_factor_key}")
        else:
            factor_labels[factor_label] = t["new_factor"].format(factor_label)
            factor_groups_final[factor_label] = list(set(items))

    # # Store factor scores
    # factor_scores_filename = os.path.join(rel_output_dir, "factor_scores.csv")
    # file_contents[factor_scores_filename] = factor_scores.to_csv(index=True)
    # logs.append(t["factor_scores_table"].format(factor_scores_filename))

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

    results = {
        "factor_groups_final": factor_groups_final,
        "factor_scores": factor_scores,
        "factor_labels": factor_labels,
        "target_role": target_role
    }
    return ToolOutput(
        results=results,
        logs=logs,
        file_contents=file_contents,
        action=None
    )


def run_efa_analysis(
    data: pd.DataFrame,
    variables: list[Variable],
    params: dict
) -> ToolOutput:
    """
    Orchestrate Exploratory Factor Analysis (EFA) using PCA with Varimax rotation.
    
    Parameters:
        data: Input DataFrame with observed variables
        variables: list of Variable objects
        params: dictionary containing analysis parameters
            - output_dir (str): base output directory name (default: "efa_analysis")
            - save_files (bool): whether to save generated files to disk (default: False)
            - variable_names (dict): mapping of variable codes to display names
            - language (str): "en" or "vi" (default: "en")
            - target_role (str): "independent", "dependent", "all"
            - specific_factors (list): optional list of factor codes to analyze only
    
    Returns:
        ToolOutput: Contains combined results, logs, file contents, and list of data-affecting actions
    """
    # Extract parameters
    base_output_dir = params.get("output_dir", "efa_analysis")
    save_files = params.get("save_files", False)
    variable_names = params.get("variable_names", {var.code: var.name for var in variables})
    target_role = params.get("target_role", "independent")
    specific_factors = params.get("specific_factors", None)
    language = params.get("language", "en")
    count = params.get("count", 1)

    # === Multilingual Support ===
    translations = {
        "en": {
            "title": "# Exploratory Factor Analysis (EFA) Report\n\n",
            "overview": "## Analysis Overview\n\n",
            "overview_desc": "This report documents the complete Exploratory Factor Analysis (EFA) process using Principal Component Analysis (PCA) with Varimax rotation.\n",
            "scope_specific": "**Analysis Scope**: Specific factors: {}\n",
            "scope_all": "**Analysis Scope**: All latent factors\n",
            "scope_dependent": "**Analysis Scope**: Dependent factors only\n",
            "scope_independent": "**Analysis Scope**: Independent factors only\n",
            "error_no_latents": "**ERROR**: No {} latent variables found for analysis.\n",
            "error_no_items": "**ERROR**: No observed variables found for the selected {} factors.\n",
            "vars_in_analysis": "**Variables in Analysis**: {} ({} variables)\n",
            "target_factors": "**Target Factors**: {}\n",
            "kmo_bartlett_fail": "\n**CRITICAL**: EFA suitability criteria not met (KMO={:.3f}, Bartlett p={:.3f}). Analysis cannot proceed.\n",
            "factors_adjusted": "\n**Warning**: Number of factors adjusted to {} due to data constraints.\n",
            "summary_title": "\n## Analysis Summary\n",
            "summary_target": "**Target Analysis**: {} factors\n",
            "summary_final_model": "**Final Model**: {} factors identified.\n",
            "summary_remove_vars": "**Variables for Removal**: {} variables recommended for removal. Re-analysis required after variable removal.\n",
            "summary_ready": "**Model Status**: All factors are ready for subsequent analysis.\n",
        },
        "vi": {
            "title": "# Báo Cáo Phân Tích Nhân Tố Khám Phá (EFA)\n\n",
            "overview": "## Tổng Quan Phân Tích\n\n",
            "overview_desc": "Báo cáo này ghi lại toàn bộ quá trình Phân tích Nhân tố Khám phá (EFA) sử dụng Phương pháp Thành phần Chính (PCA) với phép quay Varimax.\n",
            "scope_specific": "**Phạm vi phân tích**: Chỉ các nhân tố cụ thể: {}\n",
            "scope_all": "**Phạm vi phân tích**: Tất cả các nhân tố tiềm ẩn\n",
            "scope_dependent": "**Phạm vi phân tích**: Chỉ các nhân tố phụ thuộc\n",
            "scope_independent": "**Phạm vi phân tích**: Chỉ các nhân tố độc lập\n",
            "error_no_latents": "**LỖI**: Không tìm thấy nhân tố tiềm ẩn nào thuộc nhóm {} để phân tích.\n",
            "error_no_items": "**LỖI**: Không tìm thấy biến quan sát nào cho các nhân tố {} đã chọn.\n",
            "vars_in_analysis": "**Các biến đưa vào phân tích**: {} ({} biến)\n",
            "target_factors": "**Các nhân tố mục tiêu**: {}\n",
            "kmo_bartlett_fail": "\n**NGHIÊM TRỌNG**: Tiêu chí phù hợp cho EFA không đạt (KMO={:.3f}, Bartlett p={:.3f}). Không thể tiếp tục phân tích.\n",
            "factors_adjusted": "\n**Cảnh báo**: Số lượng nhân tố đã được điều chỉnh về {} do hạn chế dữ liệu.\n",
            "summary_title": "\n## Tóm Tắt Phân Tích\n",
            "summary_target": "**Đối tượng phân tích**: Các nhân tố {}\n",
            "summary_final_model": "**Mô hình cuối cùng**: Xác định được {} nhân tố.\n",
            "summary_remove_vars": "**Biến cần loại bỏ**: {} biến được đề xuất loại bỏ. Cần phân tích lại sau khi loại bỏ biến.\n",
            "summary_ready": "**Trạng thái mô hình**: Tất cả nhân tố đã sẵn sàng cho các phân tích tiếp theo.\n",
        }
    }
    t = get_t_dict(translations.get(language, translations["en"]), language=language)

    # Format title with iteration count if count > 1
    t["title"] = format_title_with_count(t["title"], count, language)

    # Generate timestamped output directory
    now = datetime.now()
    timestamp = f"{now.microsecond // 10000:02d}"
    output_dir = os.path.join(os.path.dirname(base_output_dir) or ".", f"{timestamp}_{os.path.basename(base_output_dir)}")
    rel_output_dir = os.path.relpath(output_dir, start=os.path.dirname(base_output_dir) or ".")

    logs = [
        t["title"],
        t["overview"],
        t["overview_desc"]
    ]
    file_contents = {}

    # Clear existing directory if saving files
    if save_files and os.path.exists(output_dir):
        shutil.rmtree(output_dir)
    if save_files:
        os.makedirs(output_dir, exist_ok=True)

    # Filter latent variables based on target_role and specific_factors
    if specific_factors:
        target_latents = [var for var in variables 
                         if var.variable_type == VariableType.LATENT 
                         and var.code in specific_factors]
        logs.append(t["scope_specific"].format(", ".join(specific_factors)))
    elif target_role == "all":
        # Analyze all latent variables
        target_latents = [var for var in variables if var.variable_type == VariableType.LATENT]
        logs.append(t["scope_all"])
    elif target_role == "dependent":
        # Analyze only dependent variables
        target_latents = [var for var in variables 
                         if var.variable_type == VariableType.LATENT 
                         and var.role == VariableRole.DEPENDENT]
        logs.append(t["scope_dependent"])
    else:  # target_role == "independent" (default)
        # Analyze only independent variables
        target_latents = [var for var in variables 
                         if var.variable_type == VariableType.LATENT 
                         and var.role == VariableRole.INDEPENDENT]
        logs.append(t["scope_independent"])

    if not target_latents:
        role_display = "all" if target_role == "all" else target_role
        logs.append(t["error_no_latents"].format(role_display))
        return ToolOutput(
            results={},
            logs=logs,
            file_contents=file_contents,
            action=None
        )

    # Prepare EFA data from target latent variables
    efa_items = []
    for latent in target_latents:
        latent_items = [var.code for var in variables 
                       if var.parent_code == latent.code 
                       and var.variable_type == VariableType.OBSERVED]
        efa_items.extend(latent_items)
    
    if not efa_items:
        logs.append(t["error_no_items"].format(target_role))
        return ToolOutput(
            results={},
            logs=logs,
            file_contents=file_contents,
            action=None
        )

    # Prepare EFA data
    efa_data = data[efa_items].dropna()
    logs.append(t["vars_in_analysis"].format(", ".join(efa_items), len(efa_items)))
    logs.append(t["target_factors"].format(", ".join([f'{lat.code} ({lat.name})' for lat in target_latents])))

    # Step 1: KMO and Bartlett's Test
    kmo_params = params.copy()
    kmo_params["output_dir"] = output_dir
    kmo_params["variable_names"] = variable_names
    kmo_params["language"] = language  # pass language down
    kmo_output = perform_kmo_bartlett_tool(efa_data, variables, kmo_params)
    logs.extend(kmo_output.logs)
    file_contents.update(kmo_output.file_contents)
    actions = kmo_output.action or []
    
    if kmo_output.results["kmo_value"] < 0.5 or kmo_output.results["bartlett_p"] > 0.05:
        logs.append(t["kmo_bartlett_fail"].format(
            kmo_output.results["kmo_value"],
            kmo_output.results["bartlett_p"]
        ))
        return ToolOutput(
            results={},
            logs=logs,
            file_contents=file_contents,
            action=actions if actions else None
        )

    # Step 2: Determine Number of Factors
    factors_params = params.copy()
    factors_params["output_dir"] = output_dir
    factors_params["language"] = language
    factors_output = determine_number_of_factors_tool(efa_data, variables, factors_params)
    logs.extend(factors_output.logs)
    file_contents.update(factors_output.file_contents)
    n_factors = factors_output.results["n_factors"]
    
    if n_factors == 0 or n_factors >= len(efa_items):
        n_factors = max(1, len(efa_items) // 3)
        logs.append(t["factors_adjusted"].format(n_factors))

    # Step 3: PCA with Varimax Rotation
    pca_params = params.copy()
    pca_params["output_dir"] = output_dir
    pca_params["n_factors"] = n_factors
    pca_params["language"] = language
    pca_output = perform_pca_varimax_tool(efa_data, variables, pca_params)
    logs.extend(pca_output.logs)
    file_contents.update(pca_output.file_contents)

    # Step 4: Analyze Factor Loadings
    analysis_params = params.copy()
    analysis_params["output_dir"] = output_dir
    analysis_params["loadings"] = pca_output.results["loadings"]
    analysis_params["variable_names"] = variable_names
    analysis_params["target_latents"] = target_latents
    analysis_params["language"] = language
    analysis_output = analyze_factor_loadings_tool(efa_data, variables, analysis_params)
    logs.extend(analysis_output.logs)
    file_contents.update(analysis_output.file_contents)
    items_to_remove = analysis_output.results["items_to_remove"]
    if analysis_output.action:
        actions.extend(analysis_output.action)

    # Step 5: Variance Explained
    variance_params = params.copy()
    variance_params["output_dir"] = output_dir
    variance_params["eigenvalues_df"] = factors_output.results["eigenvalues_df"]
    variance_params["n_factors"] = n_factors
    variance_params["pca_diagnostics"] = pca_output.results["pca_diagnostics"]
    variance_params["language"] = language
    variance_output = calculate_variance_explained_tool(efa_data, variables, variance_params)
    logs.extend(variance_output.logs)
    file_contents.update(variance_output.file_contents)
    if variance_output.action:
        actions.extend(variance_output.action)

    # Step 6: Assign Factors and Compute Scores
    scores_params = params.copy()
    scores_params["output_dir"] = output_dir
    scores_params["loadings"] = pca_output.results["loadings"]
    scores_params["items_to_remove"] = items_to_remove
    scores_params["variable_names"] = variable_names
    scores_params["target_latents"] = target_latents
    scores_params["target_role"] = target_role
    scores_params["language"] = language
    scores_output = assign_factors_and_compute_scores_tool(data, variables, scores_params)
    logs.extend(scores_output.logs)
    file_contents.update(scores_output.file_contents)

    # Final Summary
    logs.append(t["summary_title"])
    logs.append(t["summary_target"].format(target_role.title()))
    logs.append(t["summary_final_model"].format(len(scores_output.results['factor_groups_final'])))

    if items_to_remove:
        logs.append(t["summary_remove_vars"].format(len(items_to_remove)))
    else:
        logs.append(t["summary_ready"])

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
            elif filename.endswith((".csv", ".txt", ".md")):
                with open(save_path, "w", encoding="utf-8") as f:
                    f.write(str(content))
            else:
                print(f"Warning: Unknown file type for '{filename}'. Saving as text.")
                with open(save_path, "w", encoding="utf-8") as f:
                    f.write(str(content))

    results = {
        "factor_groups_final": scores_output.results["factor_groups_final"],
        "factor_scores": scores_output.results["factor_scores"],
        "items_to_remove": items_to_remove,
        "target_role": target_role,
        "analyzed_factors": [lat.code for lat in target_latents]
    }

    return ToolOutput(
        results=serialize_dict(results),
        logs=logs,
        file_contents=file_contents,
        action=actions if actions else None
    )
    
#####################################################
#####################################################
#####################################################

# ANOVA and T-Test Analysis
def compute_descriptive_stats_tool(
    data: pd.DataFrame,
    dependent_col: str,
    demo_col: str,
    value_map: dict,
    output_dir: str,
    save_files: bool,
    language: str = "en"
) -> ToolOutput:
    """
    Compute descriptive statistics for the dependent variable grouped by a demographic variable.

    Args:
        data: DataFrame with the data
        dependent_col: Column name of the dependent variable
        demo_col: Column name of the demographic variable
        value_map: dictionary mapping demographic values to labels
        output_dir: Directory to save output files (timestamped)
        save_files: Whether to save output files
        language: Language for output messages - "en" or "vi" (default: "en")

    Returns:
        ToolOutput with descriptive statistics, logs, and file contents
    """
    # Translation dictionary
    translations = {
        "en": {
            "error_no_data": "**ERROR**: No valid data for variable `{}`. Analysis skipped.",
            "desc_title": "**Descriptive Statistics for `{}` grouped by `{}` ({} groups: {})**",
            "sample_size": "Sample Size (N)",
            "mean": "Mean",
            "std": "Standard Deviation",
            "std_error": "Standard Error",
            "ci_lower": "CI Lower (95%)",
            "ci_upper": "CI Upper (95%)",
            "minimum": "Minimum",
            "maximum": "Maximum",
            "total": "Total",
            "desc_table": "Descriptive statistics table: `{}`"
        },
        "vi": {
            "error_no_data": "**LỖI**: Không có dữ liệu hợp lệ cho biến `{}`. Phân tích bị bỏ qua.",
            "desc_title": "**Thống Kê Mô Tả cho `{}` nhóm theo `{}` ({} nhóm: {})**",
            "sample_size": "Kích Thước Mẫu (N)",
            "mean": "Trung Bình",
            "std": "Độ Lệch Chuẩn",
            "std_error": "Sai Số Chuẩn",
            "ci_lower": "Giới Hạn Dưới CI (95%)",
            "ci_upper": "Giới Hạn Trên CI (95%)",
            "minimum": "Tối Thiểu",
            "maximum": "Tối Đa",
            "total": "Tổng",
            "desc_table": "Bảng thống kê mô tả: `{}`"
        }
    }

    # Get translations for selected language
    t = get_t_dict(translations.get(language, translations["en"]), language=language)

    # Extract parameters
    rel_output_dir = os.path.relpath(output_dir, start=os.path.dirname(output_dir) or ".")

    logs = []
    file_contents = {}

    # Filter data
    analysis_data = data[[demo_col, dependent_col]].dropna()
    if analysis_data.empty:
        logs.append(t["error_no_data"].format(demo_col))
        return ToolOutput(results={}, logs=logs, file_contents=file_contents, action=None)

    # Calculate descriptive statistics
    categories = sorted(analysis_data[demo_col].unique())
    category_labels = [f"{value_map.get(str(cat), cat)} ({cat})" for cat in categories]

    logs.append(t["desc_title"].format(dependent_col, demo_col, len(categories), ', '.join(category_labels)))

    desc_stats = analysis_data.groupby(demo_col)[dependent_col].agg(
        N='count',
        Mean='mean',
        Std='std',
        Min='min',
        Max='max'
    )
    desc_stats['SE'] = desc_stats['Std'] / np.sqrt(desc_stats['N'])
    desc_stats['CI_Lower'] = desc_stats['Mean'] - stats.t.ppf(1 - 0.025, desc_stats['N'] - 1) * desc_stats['SE']
    desc_stats['CI_Upper'] = desc_stats['Mean'] + stats.t.ppf(1 - 0.025, desc_stats['N'] - 1) * desc_stats['SE']

    # Rename columns with translations
    desc_stats = desc_stats.rename(columns={
        'N': t["sample_size"],
        'Mean': t["mean"],
        'Std': t["std"],
        'SE': t["std_error"],
        'CI_Lower': t["ci_lower"],
        'CI_Upper': t["ci_upper"],
        'Min': t["minimum"],
        'Max': t["maximum"]
    })

    # Map index to readable labels
    desc_stats.index = [value_map.get(str(idx), idx) for idx in desc_stats.index]

    # Calculate total statistics
    total_stats = analysis_data[dependent_col].agg(
        N='count',
        Mean='mean',
        Std='std',
        Min='min',
        Max='max'
    )
    total_stats['SE'] = total_stats['Std'] / np.sqrt(total_stats['N'])
    total_stats['CI_Lower'] = total_stats['Mean'] - stats.t.ppf(1 - 0.025, total_stats['N'] - 1) * total_stats['SE']
    total_stats['CI_Upper'] = total_stats['Mean'] + stats.t.ppf(1 - 0.025, total_stats['N'] - 1) * total_stats['SE']

    total_stats = pd.Series({
        t["sample_size"]: total_stats['N'],
        t["mean"]: total_stats['Mean'],
        t["std"]: total_stats['Std'],
        t["std_error"]: total_stats['SE'],
        t["ci_lower"]: total_stats['CI_Lower'],
        t["ci_upper"]: total_stats['CI_Upper'],
        t["minimum"]: total_stats['Min'],
        t["maximum"]: total_stats['Max']
    }, name=t["total"])

    desc_stats = pd.concat([desc_stats, total_stats.to_frame().T])

    # Prepare file content
    desc_filename = os.path.join(rel_output_dir, f"desc_stats_{demo_col}.csv")
    desc_content = desc_stats.to_csv(index=True, encoding='utf-8')
    file_contents[desc_filename] = desc_content

    logs.append(t["desc_table"].format(desc_filename))

    results = {"desc_stats": desc_stats}
    return ToolOutput(results=serialize_dict(results), logs=logs, file_contents=file_contents, action=None)

def perform_levene_test_tool(
    data: pd.DataFrame,
    dependent_col: str,
    demo_col: str,
    output_dir: str,
    save_files: bool,
    language: str = "en"
) -> ToolOutput:
    """
    Perform Levene's test for homogeneity of variances.

    Args:
        data: DataFrame with the data
        dependent_col: Column name of the dependent variable
        demo_col: Column name of the demographic variable
        output_dir: Directory to save output files (timestamped)
        save_files: Whether to save output files
        language: Language for output messages - "en" or "vi" (default: "en")

    Returns:
        ToolOutput with Levene's test results, logs, and file contents
    """
    # Translation dictionary
    translations = {
        "en": {
            "error_no_data": "**ERROR**: No valid data for variable `{}`. Analysis skipped.",
            "levene_title": "**Levene's Test for Homogeneity of Variances (`{}`)**",
            "levene_statistic": "Levene Statistic",
            "df1": "df1",
            "df2": "df2",
            "sig": "Sig.",
            "levene_result_reject": "Levene's test result: Sig. = {:.3f} < 0.05, reject H₀, variances are unequal.",
            "levene_result_accept": "Levene's test result: Sig. = {:.3f} ≥ 0.05, fail to reject H₀, variances are equal.",
            "equal_var": "Equal variances",
            "unequal_var": "Unequal variances"
        },
        "vi": {
            "error_no_data": "**LỖI**: Không có dữ liệu hợp lệ cho biến `{}`. Phân tích bị bỏ qua.",
            "levene_title": "**Kiểm Định Levene về Tính Đồng Nhất Phương Sai (`{}`)**",
            "levene_statistic": "Thống Kê Levene",
            "df1": "df1",
            "df2": "df2",
            "sig": "Mức Ý Nghĩa",
            "levene_result_reject": "Kết quả kiểm định Levene: Mức ý nghĩa = {:.3f} < 0.05, bác bỏ H₀, phương sai không đồng nhất.",
            "levene_result_accept": "Kết quả kiểm định Levene: Mức ý nghĩa = {:.3f} ≥ 0.05, không bác bỏ H₀, phương sai đồng nhất.",
            "equal_var": "Phương sai đồng nhất",
            "unequal_var": "Phương sai không đồng nhất"
        }
    }

    # Get translations for selected language
    t = get_t_dict(translations.get(language, translations["en"]), language=language)

    # Extract parameters
    rel_output_dir = os.path.relpath(output_dir, start=os.path.dirname(output_dir) or ".")

    logs = []
    file_contents = {}

    # Filter data
    analysis_data = data[[demo_col, dependent_col]].dropna()
    if analysis_data.empty:
        logs.append(t["error_no_data"].format(demo_col))
        return ToolOutput(results={}, logs=logs, file_contents=file_contents, action=None)

    # Perform Levene's test
    groups = [group[dependent_col].values for _, group in analysis_data.groupby(demo_col)]
    levene_stat, levene_p = stats.levene(*groups, center='median')
    levene_df1 = len(groups) - 1
    levene_df2 = len(analysis_data) - len(groups)
    equal_var = levene_p >= 0.05
    levene_decision = t["equal_var"] if equal_var else t["unequal_var"]

    # Create summary table using DataFrame
    levene_df = pd.DataFrame({
        t["levene_statistic"]: [f"{levene_stat:.3f}"],
        t["df1"]: [levene_df1],
        t["df2"]: [levene_df2],
        t["sig"]: [f"{levene_p:.3f}"]
    })

    logs.append(t["levene_title"].format(demo_col))
    logs.append("\n" + levene_df.to_markdown(index=False) + "\n")

    if levene_p < 0.05:
        logs.append(t["levene_result_reject"].format(levene_p))
    else:
        logs.append(t["levene_result_accept"].format(levene_p))

    results = {
        "F_statistic": levene_stat,
        "p_value": levene_p,
        "degrees_of_freedom": {"df1": levene_df1, "df2": levene_df2},
        "decision": levene_decision
    }
    return ToolOutput(results=results, logs=logs, file_contents=file_contents, action=None)

def perform_ttest_tool(
    data: pd.DataFrame,
    dependent_col: str,
    demo_col: str,
    value_map: dict,
    equal_var: bool,
    output_dir: str,
    save_files: bool,
    language: str = "en"
) -> ToolOutput:
    """
    Perform a two-sample t-test for a demographic variable with two groups.

    Args:
        data: DataFrame with the data
        dependent_col: Column name of the dependent variable
        demo_col: Column name of the demographic variable
        value_map: dictionary mapping demographic values to labels
        equal_var: Whether to assume equal variances (from Levene's test)
        output_dir: Directory to save output files (timestamped)
        save_files: Whether to save output files
        language: Language for output messages - "en" or "vi" (default: "en")

    Returns:
        ToolOutput with t-test results, logs, and file contents
    """
    # Translation dictionary
    translations = {
        "en": {
            "error_no_data": "**ERROR**: No valid data for variable `{}`. Analysis skipped.",
            "error_wrong_groups": "**ERROR**: Variable `{}` has {} groups, exactly 2 groups required for t-test. Analysis skipped.",
            "error_insufficient_samples": "**ERROR**: Insufficient sample sizes for `{}` (n1={}, n2={}). T-test skipped.",
            "ttest_title": "**Independent Samples T-Test for `{}` ({})**",
            "ttest_table": "T-test results table: `{}`",
            "ttest_result_reject": "T-test result: Sig. = {:.3f} < 0.05, reject H₀, significant difference exists.",
            "ttest_result_accept": "T-test result: Sig. = {:.3f} ≥ 0.05, fail to reject H₀, no significant difference.",
            "conclusion": "**Conclusion**:",
            "conclusion_significant": "Variable `{}` has a significant effect on `{}`.",
            "conclusion_not_significant": "Variable `{}` does not have a significant effect on `{}`.",
            "test_type": "Test Type",
            "equal_var": "Equal variances",
            "unequal_var": "Unequal variances",
            "t_stat": "t",
            "df": "df",
            "sig_2tailed": "Sig. (2-tailed)",
            "mean_diff": "Mean Difference",
            "std_error_diff": "Std. Error Difference",
            "ci_lower": "95% CI Lower",
            "ci_upper": "95% CI Upper",
            "sig_diff": "Significant difference",
            "no_sig_diff": "No significant difference"
        },
        "vi": {
            "error_no_data": "**LỖI**: Không có dữ liệu hợp lệ cho biến `{}`. Phân tích bị bỏ qua.",
            "error_wrong_groups": "**LỖI**: Biến `{}` có {} nhóm, cần chính xác 2 nhóm cho kiểm định t. Phân tích bị bỏ qua.",
            "error_insufficient_samples": "**LỖI**: Kích thước mẫu không đủ cho `{}` (n1={}, n2={}). Kiểm định t bị bỏ qua.",
            "ttest_title": "**Kiểm Định T Mẫu Độc Lập cho `{}` ({})**",
            "ttest_table": "Bảng kết quả kiểm định t: `{}`",
            "ttest_result_reject": "Kết quả kiểm định t: Mức ý nghĩa = {:.3f} < 0.05, bác bỏ H₀, có sự khác biệt có ý nghĩa.",
            "ttest_result_accept": "Kết quả kiểm định t: Mức ý nghĩa = {:.3f} ≥ 0.05, không bác bỏ H₀, không có sự khác biệt có ý nghĩa.",
            "conclusion": "**Kết Luận**:",
            "conclusion_significant": "Biến `{}` có tác động có ý nghĩa đến `{}`.",
            "conclusion_not_significant": "Biến `{}` không có tác động có ý nghĩa đến `{}`.",
            "test_type": "Loại Kiểm Định",
            "equal_var": "Phương sai đồng nhất",
            "unequal_var": "Phương sai không đồng nhất",
            "t_stat": "t",
            "df": "df",
            "sig_2tailed": "Mức Ý Nghĩa (2 phía)",
            "mean_diff": "Chênh Lệch Trung Bình",
            "std_error_diff": "Sai Số Chuẩn Chênh Lệch",
            "ci_lower": "Giới Hạn Dưới CI 95%",
            "ci_upper": "Giới Hạn Trên CI 95%",
            "sig_diff": "Có sự khác biệt có ý nghĩa",
            "no_sig_diff": "Không có sự khác biệt có ý nghĩa"
        }
    }

    # Get translations for selected language
    t = get_t_dict(translations.get(language, translations["en"]), language=language)

    # Extract parameters
    rel_output_dir = os.path.relpath(output_dir, start=os.path.dirname(output_dir) or ".")

    logs = []
    file_contents = {}

    # Filter data
    analysis_data = data[[demo_col, dependent_col]].dropna()
    if analysis_data.empty:
        logs.append(t["error_no_data"].format(demo_col))
        return ToolOutput(results={}, logs=logs, file_contents=file_contents, action=None)

    # Validate groups
    categories = sorted(analysis_data[demo_col].unique())
    if len(categories) != 2:
        logs.append(t["error_wrong_groups"].format(demo_col, len(categories)))
        return ToolOutput(results={}, logs=logs, file_contents=file_contents, action=None)

    # Prepare samples
    sample1 = analysis_data[analysis_data[demo_col] == categories[0]][dependent_col]
    sample2 = analysis_data[analysis_data[demo_col] == categories[1]][dependent_col]

    if len(sample1) < 2 or len(sample2) < 2:
        logs.append(t["error_insufficient_samples"].format(demo_col, len(sample1), len(sample2)))
        return ToolOutput(results={}, logs=logs, file_contents=file_contents, action=None)

    # Perform t-test
    t_stat, p_value = stats.ttest_ind(sample1, sample2, equal_var=equal_var)
    decision = t["sig_diff"] if p_value < 0.05 else t["no_sig_diff"]

    # Calculate additional statistics
    mean1, mean2 = sample1.mean(), sample2.mean()
    var1, var2 = sample1.var(), sample2.var()
    n1, n2 = len(sample1), len(sample2)
    mean_diff = mean1 - mean2
    se_diff = np.sqrt((var1 / n1) + (var2 / n2))

    if equal_var:
        df = n1 + n2 - 2
    else:
        df = ((var1 / n1 + var2 / n2) ** 2) / ((var1 / n1) ** 2 / (n1 - 1) + (var2 / n2) ** 2 / (n2 - 1))

    ci_lower, ci_upper = stats.t.interval(0.95, df, loc=mean_diff, scale=se_diff)

    # Create results table
    ttest_table = pd.DataFrame({
        t["test_type"]: [t["equal_var"] if equal_var else t["unequal_var"]],
        t["t_stat"]: [t_stat],
        t["df"]: [df],
        t["sig_2tailed"]: [p_value],
        t["mean_diff"]: [mean_diff],
        t["std_error_diff"]: [se_diff],
        t["ci_lower"]: [ci_lower],
        t["ci_upper"]: [ci_upper]
    })

    # Prepare file content
    ttest_filename = os.path.join(rel_output_dir, f"ttest_{demo_col}.csv")
    ttest_content = ttest_table.to_csv(index=False, encoding='utf-8')
    file_contents[ttest_filename] = ttest_content

    # Log results
    category_labels = [f"{value_map.get(str(cat), cat)} ({cat})" for cat in categories]
    logs.append(t["ttest_title"].format(demo_col, ', '.join(category_labels)))
    logs.append(t["ttest_table"].format(ttest_filename))

    if p_value < 0.05:
        logs.append(t["ttest_result_reject"].format(p_value))
    else:
        logs.append(t["ttest_result_accept"].format(p_value))

    conclusion = (
        t["conclusion_significant"].format(demo_col, dependent_col)
        if p_value < 0.05 else
        t["conclusion_not_significant"].format(demo_col, dependent_col)
    )
    logs.append(f"{t['conclusion']} {conclusion}")

    # Prepare diagnostics
    diagnostics = {
        "sample_means": {"mean1": mean1, "mean2": mean2},
        "sample_variances": {"var1": var1, "var2": var2},
        "sample_sizes": {"n1": n1, "n2": n2},
        "degrees_of_freedom": df,
        "confidence_interval": (ci_lower, ci_upper)
    }

    results = {
        "t_stat": t_stat,
        "p_value": p_value,
        "decision": decision,
        "diagnostics": diagnostics,
        "conclusion": conclusion
    }
    return ToolOutput(results=serialize_dict(results), logs=logs, file_contents=file_contents, action=None)

def perform_anova_tool(
    data: pd.DataFrame,
    dependent_col: str,
    demo_col: str,
    value_map: dict,
    output_dir: str,
    save_files: bool,
    language: str = "en"
) -> ToolOutput:
    """
    Perform one-way ANOVA for a demographic variable with three or more groups.

    Args:
        data: DataFrame with the data
        dependent_col: Column name of the dependent variable
        demo_col: Column name of the demographic variable
        value_map: dictionary mapping demographic values to labels
        output_dir: Directory to save output files (timestamped)
        save_files: Whether to save output files
        language: Language for output messages - "en" or "vi" (default: "en")

    Returns:
        ToolOutput with ANOVA results, logs, and file contents
    """
    # Translation dictionary
    translations = {
        "en": {
            "error_no_data": "**ERROR**: No valid data for variable `{}`. Analysis skipped.",
            "error_insufficient_groups": "**ERROR**: Variable `{}` has {} groups, at least 3 groups required for ANOVA. Analysis skipped.",
            "anova_title": "**One-Way ANOVA for `{}` ({})**",
            "anova_table": "ANOVA results table: `{}`",
            "anova_result_reject": "ANOVA result: Sig. = {:.3f} < 0.05, reject H₀, at least two groups have different means.",
            "anova_result_accept": "ANOVA result: Sig. = {:.3f} ≥ 0.05, fail to reject H₀, no significant difference.",
            "conclusion": "**Conclusion**:",
            "conclusion_significant": "Variable `{}` has a significant effect on `{}`.",
            "conclusion_not_significant": "Variable `{}` does not have a significant effect on `{}`.",
            "source": "Source",
            "between_groups": "Between Groups",
            "within_groups": "Within Groups",
            "total": "Total",
            "sum_of_squares": "Sum of Squares",
            "df": "df",
            "mean_square": "Mean Square",
            "f_stat": "F",
            "sig": "Sig.",
            "sig_diff": "Significant difference",
            "no_sig_diff": "No significant difference"
        },
        "vi": {
            "error_no_data": "**LỖI**: Không có dữ liệu hợp lệ cho biến `{}`. Phân tích bị bỏ qua.",
            "error_insufficient_groups": "**LỖI**: Biến `{}` có {} nhóm, cần ít nhất 3 nhóm cho ANOVA. Phân tích bị bỏ qua.",
            "anova_title": "**ANOVA Một Chiều cho `{}` ({})**",
            "anova_table": "Bảng kết quả ANOVA: `{}`",
            "anova_result_reject": "Kết quả ANOVA: Mức ý nghĩa = {:.3f} < 0.05, bác bỏ H₀, ít nhất hai nhóm có trung bình khác nhau.",
            "anova_result_accept": "Kết quả ANOVA: Mức ý nghĩa = {:.3f} ≥ 0.05, không bác bỏ H₀, không có sự khác biệt có ý nghĩa.",
            "conclusion": "**Kết Luận**:",
            "conclusion_significant": "Biến `{}` có tác động có ý nghĩa đến `{}`.",
            "conclusion_not_significant": "Biến `{}` không có tác động có ý nghĩa đến `{}`.",
            "source": "Nguồn",
            "between_groups": "Giữa Các Nhóm",
            "within_groups": "Trong Nhóm",
            "total": "Tổng",
            "sum_of_squares": "Tổng Bình Phương",
            "df": "df",
            "mean_square": "Trung Bình Bình Phương",
            "f_stat": "F",
            "sig": "Mức Ý Nghĩa",
            "sig_diff": "Có sự khác biệt có ý nghĩa",
            "no_sig_diff": "Không có sự khác biệt có ý nghĩa"
        }
    }

    # Get translations for selected language
    t = get_t_dict(translations.get(language, translations["en"]), language=language)

    # Extract parameters
    rel_output_dir = os.path.relpath(output_dir, start=os.path.dirname(output_dir) or ".")

    logs = []
    file_contents = {}

    # Filter data
    analysis_data = data[[demo_col, dependent_col]].dropna()
    if analysis_data.empty:
        logs.append(t["error_no_data"].format(demo_col))
        return ToolOutput(results={}, logs=logs, file_contents=file_contents, action=None)

    # Validate groups
    categories = sorted(analysis_data[demo_col].unique())
    if len(categories) < 3:
        logs.append(t["error_insufficient_groups"].format(demo_col, len(categories)))
        return ToolOutput(results={}, logs=logs, file_contents=file_contents, action=None)

    # Perform ANOVA
    anova_table_data = pg.anova(data=analysis_data, dv=dependent_col, between=demo_col, detailed=True)

    # Extract values
    anova_f = anova_table_data.loc[0, 'F']
    anova_p = anova_table_data.loc[0, 'p-unc']
    ss_between = anova_table_data.loc[0, 'SS']
    ss_within = anova_table_data.loc[1, 'SS']
    ss_total = ss_between + ss_within
    ms_between = anova_table_data.loc[0, 'MS']
    ms_within = anova_table_data.loc[1, 'MS']
    df1 = anova_table_data.loc[0, 'DF']
    df2 = anova_table_data.loc[1, 'DF']
    eta_squared = anova_table_data.loc[0, 'np2']
    anova_decision = t["sig_diff"] if anova_p < 0.05 else t["no_sig_diff"]

    # Calculate total sample size
    n = len(analysis_data)

    # Create ANOVA table
    anova_table = pd.DataFrame({
        t["source"]: [t["between_groups"], t["within_groups"], t["total"]],
        t["sum_of_squares"]: [f"{ss_between:.3f}", f"{ss_within:.3f}", f"{ss_total:.3f}"],
        t["df"]: [int(df1), int(df2), n - 1],
        t["mean_square"]: [f"{ms_between:.3f}", f"{ms_within:.3f}", ""],
        t["f_stat"]: [f"{anova_f:.3f}", "", ""],
        t["sig"]: [f"{anova_p:.3f}", "", ""]
    })

    # Prepare file content
    anova_filename = os.path.join(rel_output_dir, f"anova_{demo_col}.csv")
    anova_content = anova_table.to_csv(index=False, encoding='utf-8')
    file_contents[anova_filename] = anova_content

    # Log results
    category_labels = [f"{value_map.get(str(cat), cat)} ({cat})" for cat in categories]
    logs.append(t["anova_title"].format(demo_col, ', '.join(category_labels)))
    logs.append(t["anova_table"].format(anova_filename))

    if anova_p < 0.05:
        logs.append(t["anova_result_reject"].format(anova_p))
    else:
        logs.append(t["anova_result_accept"].format(anova_p))

    conclusion = (
        t["conclusion_significant"].format(demo_col, dependent_col)
        if anova_p < 0.05 else
        t["conclusion_not_significant"].format(demo_col, dependent_col)
    )
    logs.append(f"{t['conclusion']} {conclusion}")

    results = {
        "F_stat": anova_f,
        "p_value": anova_p,
        "eta_squared": eta_squared,
        "degrees_of_freedom": {"df1": df1, "df2": df2},
        "decision": anova_decision,
        "conclusion": conclusion
    }

    return ToolOutput(
        results=serialize_dict(results),
        logs=logs,
        file_contents=file_contents,
        action=None
    )

def generate_summary_table_tool(
    results: dict,
    demographic_cols: list[str],
    demographic_value_ranges: dict,
    output_dir: str,
    save_files: bool,
    language: str = "en"
) -> ToolOutput:
    """
    Generate a summary table of ANOVA and t-test results.

    Args:
        results: dictionary of analysis results for each demographic column
        demographic_cols: list of demographic column names
        demographic_value_ranges: dictionary of value maps for demographic variables
        output_dir: Directory to save output files (timestamped)
        save_files: Whether to save output files
        language: Language for output messages - "en" or "vi" (default: "en")

    Returns:
        ToolOutput with summary table, logs, and file contents
    """
    # Translation dictionary
    translations = {
        "en": {
            "summary_title": "### Summary of ANOVA and T-Test Results",
            "variable": "Variable",
            "levene_test": "Levene Test",
            "group_mean_test": "Group Mean Test",
            "conclusion": "Conclusion",
            "sig_less": "Sig. < 0.05",
            "sig_greater": "Sig. ≥ 0.05",
            "sig_diff": "Significant difference",
            "no_diff": "No difference",
            "summary_variance": "**Summary of Variance Analysis Results**",
            "summary_table": "Summary table: `{}`",
            "summary_sig_vars": "Variables with significant effects (p < 0.05): {}.",
            "none": "None",
            "regression_note": "Variables with significant effects on the dependent variable will be considered for regression modeling."
        },
        "vi": {
            "summary_title": "### Tổng Hợp Kết Quả ANOVA và Kiểm Định T",
            "variable": "Biến",
            "levene_test": "Kiểm Định Levene",
            "group_mean_test": "Kiểm Định Trung Bình Nhóm",
            "conclusion": "Kết Luận",
            "sig_less": "Mức ý nghĩa < 0.05",
            "sig_greater": "Mức ý nghĩa ≥ 0.05",
            "sig_diff": "Có sự khác biệt có ý nghĩa",
            "no_diff": "Không có sự khác biệt",
            "summary_variance": "**Tổng Hợp Kết Quả Phân Tích Phương Sai**",
            "summary_table": "Bảng tổng hợp: `{}`",
            "summary_sig_vars": "Các biến có tác động có ý nghĩa (p < 0.05): {}.",
            "none": "Không có",
            "regression_note": "Các biến có tác động có ý nghĩa đến biến phụ thuộc sẽ được xem xét cho mô hình hồi quy."
        }
    }

    # Get translations for selected language
    t = get_t_dict(translations.get(language, translations["en"]), language=language)

    # Extract parameters
    rel_output_dir = os.path.relpath(output_dir, start=os.path.dirname(output_dir) or ".")

    logs = []
    file_contents = {}

    logs.append(t["summary_title"])
    summary_data = []
    significant_cols = []

    for demo_col in demographic_cols:
        if demo_col not in results:
            continue

        test_results = results[demo_col]
        levene_p = test_results['Levene']['p_value']
        test_type = 't-test' if 't-test' in test_results else 'ANOVA'
        test_p = test_results[test_type]['p_value']
        conclusion = t["sig_diff"] if test_p < 0.05 else t["no_diff"]

        value_map = demographic_value_ranges.get(demo_col, {})
        categories = sorted(value_map.keys())
        group_labels = [value_map.get(str(cat), cat) for cat in categories]

        summary_data.append({
            t["variable"]: f"{demo_col} ({'/'.join(group_labels)})",
            t["levene_test"]: t["sig_less"] if levene_p < 0.05 else t["sig_greater"],
            t["group_mean_test"]: t["sig_less"] if test_p < 0.05 else t["sig_greater"],
            t["conclusion"]: conclusion
        })

        if test_p < 0.05:
            significant_cols.append(demo_col)

    summary_table = pd.DataFrame(summary_data)

    # Prepare file content
    summary_filename = os.path.join(rel_output_dir, "summary_anova_ttest.csv")
    summary_content = summary_table.to_csv(index=False, encoding='utf-8')
    file_contents[summary_filename] = summary_content

    logs.append(t["summary_variance"])
    logs.append(t["summary_table"].format(summary_filename))
    logs.append(summary_table.to_html(index=False))
    logs.append(f"**{t['conclusion'].replace('**', '')}**")
    logs.append(t["summary_sig_vars"].format(', '.join(significant_cols) if significant_cols else t["none"]))
    logs.append(t["regression_note"])

    results_dict = {
        "summary_table": summary_table,
        "significant_cols": significant_cols
    }
    return ToolOutput(results=serialize_dict(results_dict), logs=logs, file_contents=file_contents, action=None)

def run_anova_ttest_analysis(
    data: pd.DataFrame,
    variables: list[Variable],
    params: dict
) -> ToolOutput:
    """
    Perform t-tests and ANOVA to analyze the effect of demographic variables on the dependent variable.

    Parameters:
        data: Input DataFrame containing the data
        variables: list of Variable objects describing the data columns
        params: dictionary containing analysis parameters
            - output_dir (str): base output directory name (default: "anova_ttest_analysis")
            - demographic_cols (list[str]): list of demographic column names to analyze (default: auto-select nominal independent variables)
            - demographic_value_ranges (dict): mapping of demographic values to labels (default: parsed from variables)
            - save_files (bool): whether to save generated files to disk (default: False)
            - language (str): language for output messages - "en" or "vi" (default: "en")

    Returns:
        ToolOutput: Contains results with ANOVA/t-test outcomes, logs for reporting, file contents, and suggested actions for variable removal
    """
    # Extract parameters
    base_output_dir = params.get("output_dir", "anova_ttest")
    save_files = params.get("save_files", False)
    demographic_cols = params.get("demographic_cols", [])
    demographic_value_ranges = params.get("demographic_value_ranges", {})
    language = params.get("language", "en")

    # Translation dictionary
    translations = {
        "en": {
            "title": "# ANOVA and T-Test Analysis Report",
            "subtitle": "## Analysis of Categorical Variables' Effects on Dependent Variable",
            "description": "This section analyzes the differences in the dependent variable across categorical demographic groups.",
            "dependent_var": "Dependent variable: `{}` ({})",
            "error_no_demo": "**ERROR**: No valid demographic variables found in the data.",
            "warning_insufficient_groups": "**WARNING**: Variable `{}` has only {} group(s). At least 2 groups required. Analysis skipped.",
            "action_issue_non_significant": "Sig. = {p:.3f} ≥ 0.05",
            "remove_var_comment": "Remove variable `{}` due to no significant effect on `{}`"
        },
        "vi": {
            "title": "# Báo Cáo Phân Tích ANOVA và Kiểm Định T",
            "subtitle": "## Phân Tích Tác Động của Biến Phân Loại đến Biến Phụ Thuộc",
            "description": "Phần này phân tích sự khác biệt trong biến phụ thuộc giữa các nhóm nhân khẩu học phân loại.",
            "dependent_var": "Biến phụ thuộc: `{}` ({})",
            "error_no_demo": "**LỖI**: Không tìm thấy biến nhân khẩu học hợp lệ trong dữ liệu.",
            "warning_insufficient_groups": "**CẢNH BÁO**: Biến `{}` chỉ có {} nhóm. Cần ít nhất 2 nhóm. Phân tích bị bỏ qua.",
            "action_issue_non_significant": "Giá trị p = {p:.3f} ≥ 0.05",
            "remove_var_comment": "Loại bỏ biến `{}` do không có tác động có ý nghĩa đến `{}`"
        }
    }

    # Get translations for selected language
    t = get_t_dict(translations.get(language, translations["en"]), language=language)

    # Generate timestamped output directory
    now = datetime.now()
    timestamp = f"{now.microsecond // 10000:02d}"
    output_dir = os.path.join(os.path.dirname(base_output_dir) or ".", f"{timestamp}_{os.path.basename(base_output_dir)}")

    # Initialize outputs
    logs = []
    file_contents = {}
    results = {}
    actions = []

    # Auto-select demographic columns if not provided
    if not demographic_cols:
        demographic_cols = [
            var.code for var in variables
            if var.role == VariableRole.INDEPENDENT and var.scale == ScaleType.NOMINAL and var.code in data.columns
        ]

    # Parse variable values for value maps
    variable_value_maps = {
        var.code: parse_variable_values(var.values)
        for var in variables if var.values
    }

    # Find dependent variable
    dependent_vars = [var for var in variables if var.role == VariableRole.DEPENDENT and var.variable_type == VariableType.OBSERVED]
    if len(dependent_vars) != 1:
        raise ValueError("Expected exactly one dependent observed variable.")
    dependent_var = dependent_vars[0]
    dependent_col = dependent_var.code
    dependent_name = dependent_var.name or dependent_col

    # Validate demographic columns
    valid_demo_cols = [col for col in demographic_cols if col in data.columns]
    if not valid_demo_cols:
        logs.append(t["error_no_demo"])
        return ToolOutput(
            results={},
            logs=logs,
            file_contents=file_contents,
            action=None
        )

    # Initialize analysis logging
    logs.append(t["title"])
    logs.append(t["subtitle"])
    logs.append(t["description"])
    logs.append(t["dependent_var"].format(dependent_col, dependent_name))

    significant_cols = []

    # Analyze each demographic variable
    for demo_col in valid_demo_cols:
        # Get value map (prefer parsed values, fallback to params)
        value_map = variable_value_maps.get(demo_col, demographic_value_ranges.get(demo_col, {}))

        # Step 1: Descriptive Statistics
        desc_output = compute_descriptive_stats_tool(
            data=data,
            dependent_col=dependent_col,
            demo_col=demo_col,
            value_map=value_map,
            output_dir=output_dir,
            save_files=False,  # Save at the end
            language=language
        )
        logs.extend(desc_output.logs)
        file_contents.update(desc_output.file_contents)
        if not desc_output.results:
            continue
        results[demo_col] = {"desc_stats": desc_output.results["desc_stats"]}

        # Step 2: Levene's Test
        levene_output = perform_levene_test_tool(
            data=data,
            dependent_col=dependent_col,
            demo_col=demo_col,
            output_dir=output_dir,
            save_files=False,  # Save at the end
            language=language
        )
        logs.extend(levene_output.logs)
        file_contents.update(levene_output.file_contents)
        if not levene_output.results:
            continue
        equal_var = levene_output.results["p_value"] >= 0.05
        results[demo_col]["Levene"] = levene_output.results

        # Step 3: t-test or ANOVA
        categories = sorted(data[demo_col].dropna().unique())
        n_categories = len(categories)

        if n_categories < 2:
            logs.append(t["warning_insufficient_groups"].format(demo_col, n_categories))
            continue

        if n_categories == 2:
            # Perform t-test
            ttest_output = perform_ttest_tool(
                data=data,
                dependent_col=dependent_col,
                demo_col=demo_col,
                value_map=value_map,
                equal_var=equal_var,
                output_dir=output_dir,
                save_files=False,  # Save at the end
                language=language
            )
            logs.extend(ttest_output.logs)
            file_contents.update(ttest_output.file_contents)
            if ttest_output.results:
                results[demo_col]["t-test"] = ttest_output.results
                p_value = ttest_output.results["p_value"]
                if p_value < 0.05:
                    significant_cols.append(demo_col)
                else:
                    actions.append(
                        Action(
                            action_type=ActionType.REMOVE_VARIABLE,
                            method=run_anova_ttest_analysis.__name__,
                            issue=t["action_issue_non_significant"].format(p=p_value),
                            comment=t["remove_var_comment"].format(demo_col, dependent_col),
                            status="pending",
                            action_params={"variable": demo_col},
                            reflection_params=None
                        )
                    )
        else:
            # Perform ANOVA
            anova_output = perform_anova_tool(
                data=data,
                dependent_col=dependent_col,
                demo_col=demo_col,
                value_map=value_map,
                output_dir=output_dir,
                save_files=False,  # Save at the end
                language=language
            )
            logs.extend(anova_output.logs)
            file_contents.update(anova_output.file_contents)
            if anova_output.results:
                results[demo_col]["ANOVA"] = anova_output.results
                p_value = anova_output.results["p_value"]
                if p_value < 0.05:
                    significant_cols.append(demo_col)
                else:
                    actions.append(
                        Action(
                            action_type=ActionType.REMOVE_VARIABLE,
                            method=run_anova_ttest_analysis.__name__,
                            issue=f"Sig. = {p_value:.3f} ≥ 0.05",
                            comment=t["remove_var_comment"].format(demo_col, dependent_col),
                            status="pending",
                            action_params={"variable": demo_col},
                            reflection_params=None
                        )
                    )

    # Step 4: Generate Summary Table
    summary_output = generate_summary_table_tool(
        results=results,
        demographic_cols=valid_demo_cols,
        demographic_value_ranges=variable_value_maps,
        output_dir=output_dir,
        save_files=False,  # Save at the end
        language=language
    )
    logs.extend(summary_output.logs)
    file_contents.update(summary_output.file_contents)
    results["summary"] = summary_output.results

    # Save all files at once
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
    results_dict = {
        "anova_ttest_results": results,
        "significant_cols": significant_cols,
    }
    
    return ToolOutput(
        results=serialize_dict(results_dict),
        logs=logs,
        file_contents=file_contents,
        action=actions if actions else None
    )
            
######################################################
######################## CFA #########################
######################################################

def draw_cfa_path_diagram(
    variables: list['Variable'], 
    output_dir: str, 
    timestamp: str,
    
    # Text size configuration
    latent_fontsize: int = 16,
    observed_fontsize: int = 16,
    # Padding configuration (width_pad, height_pad)
    latent_padding: tuple = (0.15, 0.1),
    observed_padding: tuple = (0.12, 0.08),
    # Minimum box sizes
    latent_min_size: tuple = (0.5, 0.3),
    observed_min_size: tuple = (0.45, 0.25)
) -> tuple[str, str]:
    """
    Draw a CFA path diagram using the enhanced SEM function.
    """
    filename, base64_content = draw_sem_path_diagram(
        variables=variables,
        structural_paths=None,
        rel_output_dir=output_dir,
        diagram_type="CFA",
        latent_fontsize=latent_fontsize,
        observed_fontsize=observed_fontsize,
        latent_padding=latent_padding,
        observed_padding=observed_padding,
        latent_min_size=latent_min_size,
        observed_min_size=observed_min_size

    )
    if filename and base64_content:
        base_name = f'cfa_path_diagram_{timestamp}.png'
        return base_name, base64_content
    else:
        return None, None



def assess_data_suitability_for_cfa(
    data: pd.DataFrame,
    variables: list[Variable],
    params: dict
) -> ToolOutput:
    """
    Assess data suitability for CFA by checking sample size, correlations, distribution, KMO, and Bartlett's tests.

    Parameters:
        data: Input DataFrame containing observed variables
        variables: list of Variable objects with measurement types already set
        params: dictionary containing analysis parameters
            - output_dir (str): base output directory name (default: 'cfa_analysis')
            - save_files (bool): whether to save generated files to disk (default: False)
            - language (str): language for output messages - "en" or "vi" (default: "en")

    Returns:
        ToolOutput: Contains results, logs, file contents, and suggested actions
    """
    # Translation dictionary
    translations = {
        "en": {
            "error_no_observed": "**ERROR**: No observed variables linked to latent factors found. CFA cannot proceed.",
            "sample_size_assessment": "**Sample Size Assessment**: {n} observations with {p} observed variables.",
            "warning_sample_size": "**Warning**: Sample size {n} is less than recommended minimum of {min_n} (10 × variables). This may lead to unreliable CFA results.",
            "action_issue_sample_size": "Sample size {n} < 10 × {p}",
            "action_comment_sample_size": "Consider collecting more data or reducing the number of variables.",
            "corr_matrix": "**Correlation Matrix**: Inter-construct correlation patterns analyzed. Matrix saved as `{filename}`.",
            "construct_level_corr": "**Construct-Level Correlation Analysis**:",
            "high_corr_detected": "  - **{latent}**: High correlation (> 0.8) detected: {pairs}",
            "low_corr_detected": "  - **{latent}**: Low correlation (< 0.3) detected: {pairs}. May indicate poor convergent validity.",
            "high_vif_detected": "  - **{latent}**: High VIF (> 5) detected: {vif_str}",
            "sampling_adequacy_tests": "**Sampling Adequacy Tests**: KMO = {kmo:.3f}, Bartlett's p-value = {p:.3f}",
            "results_saved": "Results saved as `{filename}`.",
            "kmo_bartlett_explanation": "KMO measures sampling adequacy (≥ 0.6 acceptable); Bartlett tests correlation sufficiency (p ≤ 0.05 desired).",
            "warning_kmo_low": "**Warning**: KMO = {kmo:.3f} < 0.6. Data may not support factor analysis.",
            "action_issue_kmo": "KMO = {kmo:.3f} < 0.6",
            "action_comment_kmo": "Revise variable selection or collect more data.",
            "warning_bartlett": "**Warning**: Bartlett's p = {p:.3f} > 0.05. Variables may lack sufficient correlation.",
            "action_issue_bartlett": "Bartlett's p = {p:.3f} > 0.05",
            "action_comment_bartlett": "Review variable selection or data quality.",
            "dist_assessment": "**Distribution Assessment**: Non-normal distributions detected in: {issues}",
            "dist_recommendation": "Consider robust estimation methods (e.g., MLR) if proceeding with CFA."
        },
        "vi": {
            "error_no_observed": "**LỖI**: Không tìm thấy biến quan sát nào được liên kết với nhân tố tiềm ẩn. Không thể thực hiện CFA.",
            "sample_size_assessment": "**Đánh Giá Kích Thước Mẫu**: {n} quan sát với {p} biến quan sát.",
            "warning_sample_size": "**Cảnh báo**: Kích thước mẫu {n} nhỏ hơn mức tối thiểu khuyến nghị {min_n} (10 × số biến). Điều này có thể dẫn đến kết quả CFA không đáng tin cậy.",
            "action_issue_sample_size": "Kích thước mẫu {n} < 10 × {p}",
            "action_comment_sample_size": "Cân nhắc thu thập thêm dữ liệu hoặc giảm số lượng biến.",
            "corr_matrix": "**Ma Trận Tương Quan**: Phân tích mô hình tương quan giữa các cấu trúc. Ma trận đã lưu dưới dạng `{filename}`.",
            "construct_level_corr": "**Phân Tích Tương Quan Cấp Cấu Trúc**:",
            "high_corr_detected": "  - **{latent}**: Phát hiện tương quan cao (> 0.8): {pairs}",
            "low_corr_detected": "  - **{latent}**: Phát hiện tương quan thấp (< 0.3): {pairs}. Có thể chỉ ra tính hợp lệ hội tụ kém.",
            "high_vif_detected": "  - **{latent}**: Phát hiện VIF cao (> 5): {vif_str}",
            "sampling_adequacy_tests": "**Kiểm Định Tính Phù Hợp Lấy Mẫu**: KMO = {kmo:.3f}, Giá trị p Bartlett = {p:.3f}",
            "results_saved": "Kết quả đã lưu dưới dạng `{filename}`.",
            "kmo_bartlett_explanation": "KMO đo lường tính phù hợp lấy mẫu (≥ 0.6 chấp nhận được); Bartlett kiểm tra sự đủ tương quan (p ≤ 0.05 mong muốn).",
            "warning_kmo_low": "**Cảnh báo**: KMO = {kmo:.3f} < 0.6. Dữ liệu có thể không hỗ trợ phân tích nhân tố.",
            "action_issue_kmo": "KMO = {kmo:.3f} < 0.6",
            "action_comment_kmo": "Xem xét lại lựa chọn biến hoặc thu thập thêm dữ liệu.",
            "warning_bartlett": "**Cảnh báo**: Giá trị p Bartlett = {p:.3f} > 0.05. Các biến có thể thiếu tương quan đầy đủ.",
            "action_issue_bartlett": "Giá trị p Bartlett = {p:.3f} > 0.05",
            "action_comment_bartlett": "Xem xét lại lựa chọn biến hoặc chất lượng dữ liệu.",
            "dist_assessment": "**Đánh Giá Phân Phối**: Phát hiện phân phối không chuẩn trong: {issues}",
            "dist_recommendation": "Cân nhắc phương pháp ước lượng mạnh mẽ (ví dụ: MLR) nếu tiếp tục với CFA."
        }
    }

    # Extract parameters
    base_output_dir = params.get("output_dir", "cfa")
    save_files = params.get("save_files", False)
    language = params.get("language", "en")

    # Get translations for selected language
    t = get_t_dict(translations.get(language, translations["en"]), language=language)

    # Setup output directory with timestamp
    now = datetime.now()
    timestamp = f"{now.microsecond // 10000:02d}"
    output_dir = os.path.join(os.path.dirname(base_output_dir) or ".", f"{timestamp}_{os.path.basename(base_output_dir)}")

    # Initialize containers
    logs = []
    file_contents = {}
    actions = []

    # Identify observed variables linked to latent factors
    observed_vars = [var.code for var in variables if var.variable_type == VariableType.OBSERVED and var.parent_code]
    if not observed_vars:
        logs.append(t["error_no_observed"])
        return ToolOutput(results={}, logs=logs, file_contents=file_contents, action=None)

    # Check sample size
    n = len(data)
    p = len(observed_vars)
    logs.append(t["sample_size_assessment"].format(n=n, p=p))

    if n < 5 * p:
        logs.append(t["warning_sample_size"].format(n=n, min_n=10*p))
        actions.append(Action(
            action_type=ActionType.RECHECK_DATA,
            method="assess_data_suitability_for_cfa",
            issue=t["action_issue_sample_size"].format(n=n, p=p),
            comment=t["action_comment_sample_size"],
            status="pending"
        ))
    
    # Correlation and multicollinearity checks
    latents = [var for var in variables if var.variable_type == VariableType.LATENT]
    observed_per_latent = {
        latent.code: [var.code for var in variables if var.parent_code == latent.code and var.variable_type == VariableType.OBSERVED] 
        for latent in latents
    }
    
    observed_vars_in_model = [var.code for var in variables if var.variable_type == VariableType.OBSERVED and var.parent_code]
    all_available_indicators = [var for var in observed_vars_in_model if var in data.columns]
    
    if len(all_available_indicators) > 1:
        block_corr_matrix = create_structured_correlation_matrix(data, variables)
        block_corr_matrix = block_corr_matrix.round(3)

        corr_filename = f"correlation_matrix_{timestamp}.csv"
        file_contents[corr_filename] = block_corr_matrix.to_csv(index=True)
        logs.append(t["corr_matrix"].format(filename=corr_filename))

        # Perform targeted checks within each construct
        logs.append(t["construct_level_corr"])
        for latent in latents:
            measurement_type = latent.properties.get('measurement_type', 'reflective')
            indicators = [var for var in observed_per_latent[latent.code] if var in data.columns]

            if len(indicators) < 2:
                continue

            corr = data[indicators].corr()
            high_corr_pairs = [(v1, v2, corr.loc[v1, v2]) for i, v1 in enumerate(indicators)
                             for j, v2 in enumerate(indicators) if i < j and abs(corr.loc[v1, v2]) > 0.8]

            if high_corr_pairs:
                pairs_str = ', '.join([f'{v1}-{v2} ({val:.3f})' for v1, v2, val in high_corr_pairs])
                logs.append(t["high_corr_detected"].format(latent=latent.code, pairs=pairs_str))

            if measurement_type == 'reflective':
                low_corr_pairs = [(v1, v2, corr.loc[v1, v2]) for i, v1 in enumerate(indicators)
                                for j, v2 in enumerate(indicators) if i < j and abs(corr.loc[v1, v2]) < 0.3]
                if low_corr_pairs:
                    pairs_str = ', '.join([f'{v1}-{v2} ({val:.3f})' for v1, v2, val in low_corr_pairs])
                    logs.append(t["low_corr_detected"].format(latent=latent.code, pairs=pairs_str))

            elif measurement_type == 'formative':
                vif_data = {}
                for var in indicators:
                    other_vars = [v for v in indicators if v != var]
                    try:
                        model = OLS(data[var], add_constant(data[other_vars])).fit()
                        vif = 1 / (1 - model.rsquared) if model.rsquared < 1 else float('inf')
                        vif_data[var] = vif
                    except:
                        vif_data[var] = float('nan')

                high_vif_vars = [var for var, vif in vif_data.items() if not np.isnan(vif) and vif > 5]
                if high_vif_vars:
                    vif_str = ', '.join([f'{var} ({vif_data[var]:.2f})' for var in high_vif_vars])
                    logs.append(t["high_vif_detected"].format(latent=latent.code, vif_str=vif_str))

    # KMO and Bartlett's tests
    kmo_bartlett_table, kmo_comments = perform_kmo_and_bartlett_tests(
        data=data[observed_vars], save_results=False, output_dir=output_dir
    )
    
    kmo_filename = f"kmo_bartlett_results_{timestamp}.csv"
    kmo_bartlett_df = pd.DataFrame([{
        'KMO': float(kmo_bartlett_table['Kaiser-Meyer-Olkin Measure of Sampling Adequacy']),
        "Bartlett Chi-Square": float(kmo_bartlett_table["Bartlett's Test of Sphericity - Approx. Chi-Square"]),
        "Bartlett df": int(kmo_bartlett_table["Bartlett's Test of Sphericity - df"]),
        "Bartlett p-value": float(kmo_bartlett_table["Bartlett's Test of Sphericity - Sig."])
    }])
    file_contents[kmo_filename] = kmo_bartlett_df.to_csv(index=False)

    kmo_value = float(kmo_bartlett_table["Kaiser-Meyer-Olkin Measure of Sampling Adequacy"])
    bartlett_p = float(kmo_bartlett_table["Bartlett's Test of Sphericity - Sig."])

    logs.append(t["sampling_adequacy_tests"].format(kmo=kmo_value, p=bartlett_p))
    logs.append(t["results_saved"].format(filename=kmo_filename))
    logs.append(t["kmo_bartlett_explanation"])

    for comment in kmo_comments:
        logs.append(f"  - {comment}")

    if kmo_value < 0.6:
        logs.append(t["warning_kmo_low"].format(kmo=kmo_value))
        actions.append(Action(
            action_type=ActionType.RECHECK_DATA,
            method="assess_data_suitability_for_cfa",
            issue=t["action_issue_kmo"].format(kmo=kmo_value),
            comment=t["action_comment_kmo"],
            status="pending"
        ))

    if bartlett_p > 0.05:
        logs.append(t["warning_bartlett"].format(p=bartlett_p))
        actions.append(Action(
            action_type=ActionType.RECHECK_DATA,
            method="assess_data_suitability_for_cfa",
            issue=t["action_issue_bartlett"].format(p=bartlett_p),
            comment=t["action_comment_bartlett"],
            status="pending"
        ))

    # Check data distribution
    dist_issues = []
    for var in observed_vars:
        s = skew(data[var].dropna())
        k = kurtosis(data[var].dropna())
        if abs(s) > 2 or abs(k) > 7:
            dist_issues.append(f"{var} (Skewness={s:.2f}, Kurtosis={k:.2f})")

    if dist_issues:
        logs.append(t["dist_assessment"].format(issues=', '.join(dist_issues)))
        logs.append(t["dist_recommendation"])

    # Save files if requested
    if save_files:
        os.makedirs(output_dir, exist_ok=True)
        for filename, content in file_contents.items():
            save_path = os.path.join(output_dir, filename)
            if filename.endswith((".csv", ".txt")):
                with open(save_path, "w", encoding="utf-8") as f:
                    f.write(str(content))

    return ToolOutput(
        results={"sample_size": n, "n_variables": p, "kmo_value": kmo_value, "bartlett_p": bartlett_p},
        logs=logs,
        file_contents=file_contents,
        action=actions if actions else None
    )


def perform_cfa(
    data: pd.DataFrame,
    variables: list[Variable],
    params: dict
) -> ToolOutput:
    """
    Perform Confirmatory Factor Analysis on the measurement model.

    Parameters:
        data: Input DataFrame containing observed variables
        variables: list of Variable objects with measurement types set
        params: dictionary containing analysis parameters
            - output_dir (str): base output directory name (default: 'cfa_analysis')
            - save_files (bool): whether to save generated files to disk (default: False)
            - estimation_method (str): estimation method for semopy (MLW, ULS, GLS, WLS, DWLS, FIML) (default: 'MLW')
            - language (str): language for output messages - "en" or "vi" (default: "en")

    Returns:
        ToolOutput: Contains results, logs, file contents, and suggested actions
    """
    # Translation dictionary
    translations = {
        "en": {
            "model_spec": "**Model Specification**: Reflective measurement model with factor covariances:",
            "model_fitting_success": "**Model Fitting**: Successfully fitted using '{method}' estimation method.",
            "error_fitting": "**Error**: Model fitting failed - {error}",
            "action_comment_fitting": "Verify data quality or model specification.",
            "warning_no_stats": "**Warning**: Could not calculate model statistics. Skipping evaluation.",
            "fit_assessment": "**Model Fit Assessment**: Fit indices evaluated against standard thresholds.",
            "fit_table_saved": "Fit indices table saved as `{filename}`.",
            "overall_fit_good": "**Overall Fit**: Good fit achieved",
            "overall_fit_poor": "**Overall Fit**: Poor fit detected",
            "fit_criteria": "Acceptable fit requires: p > 0.05, CFI/TLI ≥ 0.90, RMSEA/SRMR ≤ 0.08",
            "mod_indices": "**Modification Suggestions**: Top 5 modification indices saved as `{filename}`.",
            "mod_indices_note": "Consider modifications only if theoretically justified.",
            "loadings_analysis": "**Factor Loadings Analysis**: All factor loadings saved as `{filename}`.",
            "loadings_criteria": "Loadings should be ≥ 0.4 and significant (p < 0.05) for adequate measurement.",
            "warning_low_loading": "**Warning**: Variable `{var}` on factor `{factor}` has loading={loading:.3f}, p={pval:.3f} (below threshold)",
            "action_comment_remove": "Consider removing this variable.",
            "action_comment_reanalyze": "Re-run CFA after removing problematic variables.",
            "reanalyze_comment": "Reanalyze with updated model.",
            "reliability": "**Reliability ({factor})**: Cronbach's α = {alpha:.3f} ({status})",
            "warning_alpha_low": "  Warning: Alpha < 0.7 for `{factor}` indicates insufficient reliability.",
            "action_issue_fitting_error": "Model fitting error: {error}",
            "action_issue_low_loading": "Low loading for {var} on {factor} (Loading={loading:.3f}, p={pval:.3f})",
            "action_issue_poor_loadings": "Problematic variable loadings identified",
            "construct_validity": "  **Construct Validity ({factor})**: AVE = {ave:.3f}, CR = {cr:.3f}",
            "validity_criteria": "  AVE ≥ 0.5 and CR ≥ 0.7 indicate good convergent validity and reliability.",
            "warning_validity": "    Warning: {issues} for `{factor}`",
            "reliability_summary": "**Reliability Summary**: Reliability analysis saved as `{filename}`.",
            "adequate": "Adequate",
            "poor": "Poor"
        },
        "vi": {
            "model_spec": "**Đặc Tả Mô Hình**: Mô hình đo lường phản ánh với hiệp phương sai nhân tố:",
            "model_fitting_success": "**Ước Lượng Mô Hình**: Ước lượng thành công bằng phương pháp '{method}'.",
            "error_fitting": "**Lỗi**: Ước lượng mô hình thất bại - {error}",
            "action_comment_fitting": "Kiểm tra chất lượng dữ liệu hoặc đặc tả mô hình.",
            "warning_no_stats": "**Cảnh báo**: Không thể tính toán thống kê mô hình. Bỏ qua đánh giá.",
            "fit_assessment": "**Đánh Giá Độ Phù Hợp Mô Hình**: Chỉ số độ phù hợp được đánh giá theo các ngưỡng tiêu chuẩn.",
            "fit_table_saved": "Bảng chỉ số độ phù hợp đã lưu dưới dạng `{filename}`.",
            "overall_fit_good": "**Độ Phù Hợp Tổng Thể**: Đạt độ phù hợp tốt",
            "overall_fit_poor": "**Độ Phù Hợp Tổng Thể**: Phát hiện độ phù hợp kém",
            "fit_criteria": "Độ phù hợp chấp nhận được yêu cầu: p > 0.05, CFI/TLI ≥ 0.90, RMSEA/SRMR ≤ 0.08",
            "mod_indices": "**Đề Xuất Điều Chỉnh**: 5 chỉ số điều chỉnh hàng đầu đã lưu dưới dạng `{filename}`.",
            "mod_indices_note": "Chỉ xem xét điều chỉnh nếu có cơ sở lý thuyết.",
            "loadings_analysis": "**Phân Tích Hệ Số Tải Nhân Tố**: Tất cả hệ số tải đã lưu dưới dạng `{filename}`.",
            "loadings_criteria": "Hệ số tải nên ≥ 0.4 và có ý nghĩa (p < 0.05) để đo lường phù hợp.",
            "warning_low_loading": "**Cảnh báo**: Biến `{var}` trên nhân tố `{factor}` có hệ số tải={loading:.3f}, p={pval:.3f} (dưới ngưỡng)",
            "action_comment_remove": "Cân nhắc loại bỏ biến này.",
            "action_comment_reanalyze": "Chạy lại CFA sau khi loại bỏ các biến có vấn đề.",
            "reanalyze_comment": "Phân tích lại với mô hình cập nhật.",
            "reliability": "**Độ Tin Cậy ({factor})**: Cronbach's α = {alpha:.3f} ({status})",
            "warning_alpha_low": "  Cảnh báo: Alpha < 0.7 cho `{factor}` cho thấy độ tin cậy không đủ.",
            "action_issue_fitting_error": "Lỗi ước lượng mô hình: {error}",
            "construct_validity": "  **Giá Trị Cấu Trúc ({factor})**: AVE = {ave:.3f}, CR = {cr:.3f}",
            "validity_criteria": "  AVE ≥ 0.5 và CR ≥ 0.7 cho thấy giá trị hội tụ và độ tin cậy tốt.",
            "warning_validity": "    Cảnh báo: {issues} cho `{factor}`",
            "reliability_summary": "**Tóm Tắt Độ Tin Cậy**: Phân tích độ tin cậy đã lưu dưới dạng `{filename}`.",
            "adequate": "Đạt yêu cầu",
            "poor": "Kém",
            "action_issue_low_loading": "Hệ số tải thấp cho {var} trên {factor} (Tải={loading:.3f}, p={pval:.3f})",
            "action_issue_poor_loadings": "Đã xác định các biến có hệ số tải kém"
        }
    }

    # Extract parameters
    base_output_dir = params.get("output_dir", "cfa_analysis")
    save_files = params.get("save_files", False)
    estimation_method = params.get("estimation_method", "MLW")
    language = params.get("language", "en")
    count = params.get("count", 1)

    # Get translations for selected language
    t = get_t_dict(translations.get(language, translations["en"]), language=language)

    # Setup output directory with timestamp
    now = datetime.now()
    timestamp = f"{now.microsecond // 10000:02d}"
    output_dir = os.path.join(os.path.dirname(base_output_dir) or ".", f"{timestamp}_{os.path.basename(base_output_dir)}")

    # Initialize containers
    logs = []
    file_contents = {}
    actions = []

    # Define CFA model
    latents = [var for var in variables if var.variable_type == VariableType.LATENT]
    observed_vars_by_factor = {
        latent.code: [var.code for var in variables if var.parent_code == latent.code and var.variable_type == VariableType.OBSERVED]
        for latent in latents
    }
    
    model_desc = "\n".join([f"{latent.code} =~ {' + '.join(observed_vars_by_factor[latent.code])}"
                            for latent in latents if observed_vars_by_factor[latent.code]])

    if len(latents) > 1:
        for i in range(len(latents)):
            for j in range(i + 1, len(latents)):
                model_desc += f"\n{latents[i].code} ~~ {latents[j].code}"

    logs.append(t["model_spec"])
    logs.append(f"```\n{model_desc}\n```")

    # Fit the model
    model = SemopyModel(model_desc)

    try:
        model.fit(data, obj=estimation_method)
        logs.append(t["model_fitting_success"].format(method=estimation_method))
    except Exception as e:
        logs.append(t["error_fitting"].format(error=str(e)))
        actions.append(Action(
            action_type=ActionType.RECHECK_DATA,
            method="perform_cfa",
            issue=t["action_issue_fitting_error"].format(error=str(e)),
            comment=t["action_comment_fitting"],
            status="pending"
        ))
        return ToolOutput(results={}, logs=logs, file_contents=file_contents, action=actions)

    # Evaluate model fit
    stats = calc_stats(model)
    if stats.empty:
        logs.append(t["warning_no_stats"])
        return ToolOutput(results={}, logs=logs, file_contents=file_contents, action=actions)

    fit_stats_series = pd.Series(dtype=float)
    if 'Value' in stats.columns:
        fit_stats_series = pd.to_numeric(stats['Value'], errors='coerce')
        fit_stats_series.index = stats.index
    elif 'Value' in stats.index:
        fit_stats_series = pd.to_numeric(stats.loc['Value'], errors='coerce')

    fit_indices = {
        "Chi-Square": fit_stats_series.get('chi2', np.nan),
        "df": fit_stats_series.get('DoF', np.nan),
        "p-value": fit_stats_series.get('chi2 p-value', np.nan),
        "CFI": fit_stats_series.get('CFI', np.nan),
        "TLI": fit_stats_series.get('TLI', np.nan),
        "RMSEA": fit_stats_series.get('RMSEA', np.nan),
        "SRMR": fit_stats_series.get('SRMR', np.nan)
    }
    
    # Create fit indices table
    fit_indices_filename = f"model_fit_indices_{timestamp}.csv"
    fit_indices_df = pd.DataFrame([{
        'Index': key,
        'Value': f"{value:.3f}" if pd.notna(value) else "N/A",
        'Acceptable_Threshold': ('> 0.05' if key == 'p-value' 
                               else '≥ 0.90' if key in ['CFI', 'TLI'] 
                               else '≤ 0.08' if key in ['RMSEA', 'SRMR']
                               else 'N/A')
    } for key, value in fit_indices.items()])
    file_contents[fit_indices_filename] = fit_indices_df.to_csv(index=False)

    logs.append(t["fit_assessment"])
    logs.append(t["fit_table_saved"].format(filename=fit_indices_filename))

    # Assess overall fit
    fit_good = (
        pd.notna(fit_indices["p-value"]) and fit_indices["p-value"] > 0.05 and
        pd.notna(fit_indices["CFI"]) and fit_indices["CFI"] >= 0.90 and
        pd.notna(fit_indices["TLI"]) and fit_indices["TLI"] >= 0.90 and
        pd.notna(fit_indices["RMSEA"]) and fit_indices["RMSEA"] <= 0.08 and
        pd.notna(fit_indices["SRMR"]) and fit_indices["SRMR"] <= 0.08
    )

    logs.append(t["overall_fit_good"] if fit_good else t["overall_fit_poor"])
    logs.append(t["fit_criteria"])

    # Modification indices if poor fit
    if not fit_good:
        mi = model.inspect(what='modindices')
        if mi is not None and not mi.empty and 'MI' in mi.columns:
            mi = mi.sort_values('MI', ascending=False).head(5)
            mi_filename = f"modification_indices_{timestamp}.csv"
            file_contents[mi_filename] = mi.to_csv(index=False)
            logs.append(t["mod_indices"].format(filename=mi_filename))
            logs.append(t["mod_indices_note"])

    # Examine factor loadings
    params_df = model.inspect()
    loadings = params_df[params_df['op'] == '=~']
    loadings_filename = f"factor_loadings_{timestamp}.csv"
    file_contents[loadings_filename] = loadings.to_csv(index=False)

    logs.append(t["loadings_analysis"].format(filename=loadings_filename))
    logs.append(t["loadings_criteria"])

    # Identify problematic loadings
    remove_candidates = []
    for _, row in loadings.iterrows():
        var, factor, loading, pval = row['rval'], row['lval'], row['Estimate'], row['p-value']
        if loading < 0.4 or pval > 0.05:
            logs.append(t["warning_low_loading"].format(var=var, factor=factor, loading=loading, pval=pval))
            actions.append(Action(
                action_type=ActionType.REMOVE_VARIABLE,
                method="perform_cfa",
                issue=t["action_issue_low_loading"].format(var=var, factor=factor, loading=loading, pval=pval),
                comment=t["action_comment_remove"],
                status="pending",
                action_params={'variable': var}
            ))
            remove_candidates.append(var)

    if remove_candidates:
        actions.append(Action(
            action_type=ActionType.REANALYZE,
            method="perform_cfa",
            issue=t["action_issue_poor_loadings"],
            comment=t["action_comment_reanalyze"],
            status="pending",
            reflection_params={
                "tool": "run_cfa_analysis",
                "parameters": {"excluded_variables": remove_candidates, "language": language, "count": count + 1},
                "comment": t["reanalyze_comment"]
            },
            reset_actions=True
        ))

    # Reliability and validity assessment
    reliability_results = []
    for latent in latents:
        factor_vars = observed_vars_by_factor.get(latent.code, [])
        if len(factor_vars) > 1:
            alpha = pg.cronbach_alpha(data[factor_vars])[0]
            status = t["adequate"] if alpha >= 0.7 else t["poor"]
            reliability_results.append({
                'Factor': latent.code,
                'Cronbach_Alpha': alpha,
                'Reliability_Status': status
            })

            logs.append(t["reliability"].format(factor=latent.code, alpha=alpha, status=status))

            if alpha < 0.7:
                logs.append(t["warning_alpha_low"].format(factor=latent.code))

            # Calculate construct validity measures
            factor_loadings = loadings[loadings['lval'] == latent.code]['Estimate']
            error_vars_df = params_df[(params_df['op'] == '~~') & (params_df['lval'] == params_df['rval']) &
                                      params_df['lval'].isin(factor_vars)]

            if not factor_loadings.empty and not error_vars_df.empty:
                error_vars_map = error_vars_df.set_index('lval')['Estimate']
                aligned_error_vars = error_vars_map.reindex(factor_vars).dropna()

                if len(factor_loadings) == len(aligned_error_vars):
                    sum_loadings_sq = (factor_loadings ** 2).sum()
                    sum_error_vars = aligned_error_vars.sum()

                    if (sum_loadings_sq + sum_error_vars) > 0:
                        ave = sum_loadings_sq / (sum_loadings_sq + sum_error_vars)
                        cr_denominator = (factor_loadings.sum()) ** 2 + sum_error_vars
                        if cr_denominator > 0:
                            cr = (factor_loadings.sum()) ** 2 / cr_denominator
                            logs.append(t["construct_validity"].format(factor=latent.code, ave=ave, cr=cr))
                            logs.append(t["validity_criteria"])

                            if ave < 0.5 or cr < 0.7:
                                issues = []
                                if ave < 0.5:
                                    issues.append("AVE < 0.5")
                                if cr < 0.7:
                                    issues.append("CR < 0.7")
                                logs.append(t["warning_validity"].format(issues=' and '.join(issues), factor=latent.code))

    # Save reliability results
    if reliability_results:
        reliability_filename = f"reliability_analysis_{timestamp}.csv"
        reliability_df = pd.DataFrame(reliability_results)
        file_contents[reliability_filename] = reliability_df.to_csv(index=False)
        logs.append(t["reliability_summary"].format(filename=reliability_filename))

    # Save files if requested
    if save_files:
        os.makedirs(output_dir, exist_ok=True)
        for filename, content in file_contents.items():
            save_path = os.path.join(output_dir, filename)
            if filename.endswith((".csv", ".txt")):
                with open(save_path, "w", encoding="utf-8") as f:
                    f.write(str(content))

    # Clean fit indices for return
    fit_indices_clean = {k: (v if pd.notna(v) else None) for k, v in fit_indices.items()}
        
    return ToolOutput(
        results={"fit_indices": fit_indices_clean},
        logs=logs,
        file_contents=file_contents,
        action=actions if actions else None
    )


def run_cfa_analysis(
    data: pd.DataFrame,
    variables: list[Variable],
    params: dict
) -> ToolOutput:
    """
    Perform comprehensive Confirmatory Factor Analysis (CFA) with data assessment and model evaluation.

    Parameters:
        data: Input DataFrame containing observed variables
        variables: list of Variable objects defining the measurement model
        params: dictionary containing analysis parameters
            - output_dir (str): base output directory name (default: 'cfa_analysis')
            - save_files (bool): whether to save generated files to disk (default: False)
            - estimation_method (str): estimation method for semopy (MLW, ULS, GLS, WLS, DWLS, FIML) (default: 'MLW')
            - excluded_variables (list[str]): variables to exclude from analysis (default: [])
            - language (str): language for output messages - "en" or "vi" (default: "en")

    Returns:
        ToolOutput: Contains combined results, logs, file contents, and suggested actions
    """
    # Translation dictionary
    translations = {
        "en": {
            "report_title": "# Confirmatory Factor Analysis (CFA) Report\n",
            "model_spec_validation": "## Model Specification and Validation\n",
            "measurement_type_set": "Latent variable '{var}' measurement type set to 'reflective' (CFA default).",
            "error_formative": "**FATAL ERROR**: Latent variable '{var}' is formative. CFA requires all latent variables to be reflective.",
            "cfa_assumption": "**CFA Model Assumption**: All latent constructs are reflective (measurement model focus).\n",
            "excluded_vars": "**Excluded Variables**: {vars} removed from analysis.\n",
            "data_suitability": "## Data Suitability Assessment\n",
            "critical_issues": "\n**CRITICAL**: Data suitability issues detected. Address suggested actions before proceeding.",
            "cfa_fitting": "\n## CFA Model Fitting and Evaluation\n",
            "path_diagram": "\n## Path Diagram\n",
            "path_diagram_desc": "**CFA Path Diagram**: Visual representation of the measurement model showing latent variables and their reflective indicators. `{filename}`\n",
            "warning_no_diagram": "**Warning**: Could not generate path diagram.\n",
            "warning_diagram_failed": "**Warning**: Path diagram generation failed: {error}\n",
            "analysis_summary": "## Analysis Summary\n",
            "model_structure": "**Model Structure**: {latent_count} latent factors measured by {observed_count} observed variables.",
            "fit_summary": "**Model Fit Summary**: {summary}.",
            "data_quality_summary": "**Data Quality**: KMO = {kmo:.3f} ({status}), Sample size = {n}.",
            "critical_issues_count": "**Critical Issues**: {count} data quality issues require attention.",
            "model_refinement": "**Model Refinement**: {count} suggestions for improving model specification.",
            "status_acceptable": "**Status**: Model meets basic acceptability criteria for CFA.",
            "next_steps": "\n**Recommended Next Steps**:",
            "step_data_quality": "1. Address data quality issues before proceeding with analysis.",
            "step_modifications": "2. Consider model modifications as suggested in the analysis.",
            "step_sem_integration": "1. Model is suitable for integration into full SEM analysis.",
            "step_validation": "2. Consider cross-validation with independent sample if available.",
            "good": "Good",
            "poor": "Poor",
            "adequate": "Adequate"
        },
        "vi": {
            "report_title": "# Báo Cáo Phân Tích Nhân Tố Khẳng Định (CFA)\n",
            "model_spec_validation": "## Đặc Tả và Kiểm Định Mô Hình\n",
            "measurement_type_set": "Loại đo lường của biến tiềm ẩn '{var}' được đặt thành 'phản ánh' (mặc định CFA).",
            "error_formative": "**LỖI NGHIÊM TRỌNG**: Biến tiềm ẩn '{var}' là hình thành. CFA yêu cầu tất cả biến tiềm ẩn phải phản ánh.",
            "cfa_assumption": "**Giả Định Mô Hình CFA**: Tất cả cấu trúc tiềm ẩn đều phản ánh (tập trung vào mô hình đo lường).\n",
            "excluded_vars": "**Các Biến Loại Trừ**: {vars} đã được loại bỏ khỏi phân tích.\n",
            "data_suitability": "## Đánh Giá Tính Phù Hợp Dữ Liệu\n",
            "critical_issues": "\n**QUAN TRỌNG**: Phát hiện vấn đề về tính phù hợp dữ liệu. Xử lý các hành động đề xuất trước khi tiếp tục.",
            "cfa_fitting": "\n## Ước Lượng và Đánh Giá Mô Hình CFA\n",
            "path_diagram": "\n## Sơ Đồ Đường Dẫn\n",
            "path_diagram_desc": "**Sơ Đồ Đường Dẫn CFA**: Biểu diễn trực quan của mô hình đo lường hiển thị các biến tiềm ẩn và chỉ báo phản ánh. `{filename}`\n",
            "warning_no_diagram": "**Cảnh báo**: Không thể tạo sơ đồ đường dẫn.\n",
            "warning_diagram_failed": "**Cảnh báo**: Tạo sơ đồ đường dẫn thất bại: {error}\n",
            "analysis_summary": "## Tóm Tắt Phân Tích\n",
            "model_structure": "**Cấu Trúc Mô Hình**: {latent_count} nhân tố tiềm ẩn được đo lường bởi {observed_count} biến quan sát.",
            "fit_summary": "**Tóm Tắt Độ Phù Hợp Mô Hình**: {summary}.",
            "data_quality_summary": "**Chất Lượng Dữ Liệu**: KMO = {kmo:.3f} ({status}), Kích thước mẫu = {n}.",
            "critical_issues_count": "**Vấn Đề Nghiêm Trọng**: {count} vấn đề chất lượng dữ liệu cần được chú ý.",
            "model_refinement": "**Cải Tiến Mô Hình**: {count} đề xuất để cải thiện đặc tả mô hình.",
            "status_acceptable": "**Trạng Thái**: Mô hình đáp ứng tiêu chí chấp nhận được cơ bản cho CFA.",
            "next_steps": "\n**Các Bước Tiếp Theo Được Khuyến Nghị**:",
            "step_data_quality": "1. Xử lý các vấn đề chất lượng dữ liệu trước khi tiếp tục phân tích.",
            "step_modifications": "2. Xem xét các điều chỉnh mô hình như đề xuất trong phân tích.",
            "step_sem_integration": "1. Mô hình phù hợp để tích hợp vào phân tích SEM đầy đủ.",
            "step_validation": "2. Xem xét xác thực chéo với mẫu độc lập nếu có sẵn.",
            "good": "Tốt",
            "poor": "Kém",
            "adequate": "Đạt yêu cầu"
        }
    }

    # Extract parameters
    base_output_dir = params.get("output_dir", "cfa_analysis")
    save_files = params.get("save_files", False)
    estimation_method = params.get("estimation_method", "MLW")
    excluded_vars = params.get("excluded_variables", [])
    language = params.get("language", "en")
    count = params.get("count", 1)

    # Get translations for selected language
    t = get_t_dict(translations.get(language, translations["en"]), language=language)

    # Format title with iteration count if count > 1
    t["report_title"] = format_title_with_count(t["report_title"], count, language)

    # Setup output directory with timestamp
    now = datetime.now()
    timestamp = f"{now.microsecond // 10000:02d}"
    output_dir = os.path.join(os.path.dirname(base_output_dir) or ".", f"{timestamp}_{os.path.basename(base_output_dir)}")

    # Initialize containers
    logs = [t["report_title"]]
    file_contents = {}
    actions = []
    combined_results = {}

    # Clean existing output directory
    if save_files and os.path.exists(output_dir):
        shutil.rmtree(output_dir)

    # Process variables: set default measurement type and validate
    variables_processed = copy.deepcopy(variables)
    logs.append(t["model_spec_validation"])

    for var in variables_processed:
        if var.variable_type == VariableType.LATENT:
            if 'measurement_type' not in var.properties:
                var.properties['measurement_type'] = 'reflective'
                logs.append(t["measurement_type_set"].format(var=var.code))
            elif var.properties['measurement_type'] == 'formative':
                error_msg = t["error_formative"].format(var=var.code)
                logs.append(error_msg)
                raise ValueError(error_msg)

    logs.append(t["cfa_assumption"])

    # Filter excluded variables
    active_variables = [var for var in variables_processed if var.code not in excluded_vars]
    if excluded_vars:
        logs.append(t["excluded_vars"].format(vars=', '.join(excluded_vars)))

    # Step 1: Data suitability assessment
    logs.append(t["data_suitability"])
    suitability_params = {
        "output_dir": output_dir,
        "save_files": False,  # Handle saving centrally
        "language": language
    }
    
    suitability_output = assess_data_suitability_for_cfa(data, active_variables, suitability_params)
    logs.extend(suitability_output.logs)
    file_contents.update(suitability_output.file_contents)
    combined_results.update(suitability_output.results)
    
    if suitability_output.action:
        actions.extend(suitability_output.action)
        if any(a.action_type == ActionType.RECHECK_DATA for a in suitability_output.action):
            logs.append(t["critical_issues"])
            
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
            
            return ToolOutput(results=serialize_dict(combined_results), logs=logs, file_contents=file_contents, action=actions)

    # Step 2: Perform CFA
    logs.append(t["cfa_fitting"])
    cfa_params = {
        "output_dir": output_dir,
        "save_files": False,  # Handle saving centrally
        "estimation_method": estimation_method,
        "language": language
    }
    
    cfa_output = perform_cfa(data, active_variables, cfa_params)
    logs.extend(cfa_output.logs)
    file_contents.update(cfa_output.file_contents)
    combined_results.update(cfa_output.results)
    
    if cfa_output.action:
        actions.extend(cfa_output.action)

    # Step 3: Generate path diagram
    logs.append(t["path_diagram"])
    try:
        diagram_filename, base64_content = draw_cfa_path_diagram(active_variables, output_dir, timestamp)
        if diagram_filename and base64_content:
            diagram_key = os.path.join(output_dir, diagram_filename)
            file_contents[diagram_key] = base64_content
            logs.append(t["path_diagram_desc"].format(filename=diagram_key))
        else:
            logs.append(t["warning_no_diagram"])
    except Exception as e:
        logs.append(t["warning_diagram_failed"].format(error=str(e)))

    # Step 4: Summary and recommendations
    logs.append(t["analysis_summary"])
    
    # Count latent factors and observed variables
    latent_count = len([var for var in active_variables if var.variable_type == VariableType.LATENT])
    observed_count = len([var for var in active_variables if var.variable_type == VariableType.OBSERVED and var.parent_code])

    logs.append(t["model_structure"].format(latent_count=latent_count, observed_count=observed_count))

    # Fit assessment summary
    if 'fit_indices' in combined_results:
        fit_indices = combined_results['fit_indices']
        fit_summary = []

        if fit_indices.get('CFI') is not None:
            cfi_status = t["good"] if fit_indices['CFI'] >= 0.90 else t["poor"]
            fit_summary.append(f"CFI = {fit_indices['CFI']:.3f} ({cfi_status})")

        if fit_indices.get('RMSEA') is not None:
            rmsea_status = t["good"] if fit_indices['RMSEA'] <= 0.08 else t["poor"]
            fit_summary.append(f"RMSEA = {fit_indices['RMSEA']:.3f} ({rmsea_status})")

        if fit_indices.get('SRMR') is not None:
            srmr_status = t["good"] if fit_indices['SRMR'] <= 0.08 else t["poor"]
            fit_summary.append(f"SRMR = {fit_indices['SRMR']:.3f} ({srmr_status})")

        if fit_summary:
            logs.append(t["fit_summary"].format(summary=', '.join(fit_summary)))

    # Data quality summary
    if 'kmo_value' in combined_results:
        kmo_status = t["adequate"] if combined_results['kmo_value'] >= 0.6 else t["poor"]
        logs.append(t["data_quality_summary"].format(
            kmo=combined_results['kmo_value'],
            status=kmo_status,
            n=combined_results.get('sample_size', 'N/A')
        ))

    # Actions summary
    if actions:
        critical_actions = [a for a in actions if a.action_type == ActionType.RECHECK_DATA]
        model_actions = [a for a in actions if a.action_type in [ActionType.REMOVE_VARIABLE, ActionType.REANALYZE]]

        if critical_actions:
            logs.append(t["critical_issues_count"].format(count=len(critical_actions)))
        if model_actions:
            logs.append(t["model_refinement"].format(count=len(model_actions)))
    else:
        logs.append(t["status_acceptable"])

    # Next steps recommendations
    logs.append(t["next_steps"])
    if actions:
        if any(a.action_type == ActionType.RECHECK_DATA for a in actions):
            logs.append(t["step_data_quality"])
        if any(a.action_type in [ActionType.REMOVE_VARIABLE, ActionType.REANALYZE] for a in actions):
            logs.append(t["step_modifications"])
    else:
        logs.append(t["step_sem_integration"])
        logs.append(t["step_validation"])
    
    # Save all files if requested
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

    return ToolOutput(
        results=serialize_dict(combined_results),
        logs=logs,
        file_contents=file_contents,
        action=actions if actions else None
    )
    
######################################################
###################### CB-SEM ########################
######################################################
def draw_sem_path_diagram(
    variables: list['Variable'],
    structural_paths: list[tuple[str, str]] = None,
    rel_output_dir: str = ".",
    diagram_type: str = "SEM",
    # Text size configuration
    latent_fontsize: int = 16,
    observed_fontsize: int = 16,
    # Padding configuration (width_pad, height_pad)
    latent_padding: tuple = (0.15, 0.1),
    observed_padding: tuple = (0.12, 0.08),
    # Minimum box sizes
    latent_min_size: tuple = (0.5, 0.3),
    observed_min_size: tuple = (0.45, 0.25)
) -> tuple[str, str]:

    """
    Generates a professional SEM/CFA path diagram with improved layout and sizing.
    """
    try:
        # Set modern matplotlib style
        plt.style.use('default')

        G = nx.DiGraph()
        # If no structural paths provided, treat as CFA
        if structural_paths is None:
            structural_paths = []
            diagram_type = "CFA"

        latents = {var.code: var for var in variables if var.variable_type.value == 'latent'}
        observed = {var.code: var for var in variables if var.variable_type.value == 'observed'}

        # Add nodes with attributes
        for code, var in latents.items():
            G.add_node(code, type='latent', var=var)

        for code, var in observed.items():
            G.add_node(code, type='observed', var=var)
            # Find orphan observed variables (no latent parent)
        orphan_observed = [
            obs_code for obs_code, obs_var in observed.items()
            if not obs_var.parent_code or obs_var.parent_code not in latents
        ]

        # Measurement model edges
        for obs_code, obs_var in observed.items():
            if obs_var.parent_code and obs_var.parent_code in latents:
                parent = obs_var.parent_code
                measurement_type = latents[parent].properties.get('measurement_type', 'reflective')
                if measurement_type == 'reflective':
                    G.add_edge(parent, obs_code, kind='measurement')
                else:
                    G.add_edge(obs_code, parent, kind='measurement')

        # Structural paths (only for SEM)
        if diagram_type == "SEM":
            for from_code, to_code in structural_paths:
                if from_code in latents and to_code in latents:
                    G.add_edge(from_code, to_code, kind='structural')

        # IMPROVED NODE POSITIONING LOGIC
        latent_nodes = list(latents.keys())
        # Group observed variables by their parent latent factor
        latent_indicators = {}
        for latent in latent_nodes:
            latent_indicators[latent] = [
                obs for obs in observed.keys() 
                if observed[obs].parent_code == latent
            ]
        
        if diagram_type == "CFA":
            pos = _create_cfa_layout(latent_nodes, latent_indicators, orphan_observed)
        else:
            pos = _create_sem_layout(latent_nodes, latent_indicators, structural_paths, orphan_observed)

         # Calculate optimal figure size
        fig_width, fig_height = _calculate_figure_size(pos)
        
        # Create figure with calculated size
        fig, ax = plt.subplots(figsize=(fig_width, fig_height))

        ax.set_facecolor('#fafbfc')
        ax.set_aspect('equal')
        ax.axis('off')

        # Draw edges with enhanced styling
        structural_edges = [(u, v) for u, v, d in G.edges(data=True) if d.get('kind') == 'structural']
        measurement_edges = [(u, v) for u, v, d in G.edges(data=True) if d.get('kind') == 'measurement']

        # Structural edges (bold blue arrows) - only for SEM
        if structural_edges and diagram_type == "SEM":
            nx.draw_networkx_edges(G, pos, 
                                 edgelist=structural_edges,
                                 edge_color='#2980b9',
                                 width=3,
                                 arrowsize=25,
                                 arrowstyle='->',
                                 connectionstyle="arc3,rad=0.1",
                                 ax=ax)

        # Measurement edges (dashed purple arrows)
        if measurement_edges:
            nx.draw_networkx_edges(G, pos,
                                 edgelist=measurement_edges,
                                 edge_color='#8e44ad',
                                 width=2,
                                 style='dashed',
                                 arrowsize=20,
                                 arrowstyle='->',
                                 ax=ax)

        # Draw nodes with professional styling and adaptive sizing
        for node, (x, y) in pos.items():
            var = latents.get(node) or observed.get(node)
            if node in latents:
                # Calculate text dimensions for latent variables
                text_width, text_height = _calculate_text_dimensions(var.code, fontsize=latent_fontsize, fontweight='bold')
                
                # Minimum size with configurable padding
                min_width = max(latent_min_size[0], text_width + latent_padding[0])
                min_height = max(latent_min_size[1], text_height + latent_padding[1])
                
                # Latent variables as adaptive ellipses
                ellipse = Ellipse((x, y), min_width, min_height,
                                facecolor='#3498db',
                                edgecolor='#2980b9',
                                linewidth=2.5,
                                alpha=0.9)
                ax.add_patch(ellipse)
                
                # Add text with configurable font size
                display_fontsize = min(latent_fontsize, max(8, 120 // len(var.code)))
                ax.text(x, y, var.code,
                       ha='center', va='center',
                       fontsize=display_fontsize, fontweight='bold',
                       color='white')

            else:
                # Calculate text dimensions for observed variables
                text_width, text_height = _calculate_text_dimensions(var.code, fontsize=observed_fontsize, fontweight='bold')
                
                # Minimum size with reasonable padding
                min_width = max(observed_min_size[0], text_width + observed_padding[0])  # Just add small padding
                min_height = max(observed_min_size[1], text_height + observed_padding[1])  # Just add small padding
                
                # Observed variables as adaptive rounded rectangles
                rect = FancyBboxPatch((x - min_width/2, y - min_height/2), 
                                    min_width, min_height,
                                    boxstyle="round,pad=0.02",
                                    facecolor='#ecf0f1',
                                    edgecolor='#34495e',
                                    linewidth=2,
                                    alpha=0.95)
                ax.add_patch(rect)
                
                # Add text with adaptive font size
                fontsize = min(10, max(7, 100 // len(var.code)))
                ax.text(x, y, var.code,
                       ha='center', va='center',
                       fontsize=fontsize, fontweight='bold',
                       color='#2c3e50')

        # Set axis limits to ensure all elements are visible
        if pos:
            x_coords = [x for x, y in pos.values()]
            y_coords = [y for x, y in pos.values()]
            
            margin = 1.0
            ax.set_xlim(min(x_coords) - margin, max(x_coords) + margin)
            ax.set_ylim(min(y_coords) - margin, max(y_coords) + margin)

        # Add title with modern styling
        title = f'{diagram_type} Path Diagram'
        ax.text(0.5, 0.95, title,
               transform=ax.transAxes,
               ha='center', va='top',
               fontsize=16, fontweight='bold',
               color='#2c3e50')

        # Add legend
        legend_elements = []
        if diagram_type == "SEM" and structural_edges:
            legend_elements.append(plt.Line2D([0], [0], color='#2980b9', lw=3, label='Structural Path'))
        
        legend_elements.extend([
            plt.Line2D([0], [0], color='#8e44ad', lw=2, linestyle='--', label='Measurement Path'),
            patches.Ellipse((0, 0), 1, 1, facecolor='#3498db', label='Latent Variable'),
            patches.Rectangle((0, 0), 1, 1, facecolor='#ecf0f1', edgecolor='#34495e', label='Observed Variable')
        ])

        if orphan_observed:
            legend_elements.append(plt.Line2D([0], [0], color='gray', lw=1, 
                                            label='Orphan Observed'))
        
        ax.legend(handles=legend_elements, 
                 loc='upper right',
                 bbox_to_anchor=(0.98, 0.90),
                 frameon=True,
                 fancybox=True,
                 shadow=True,
                 fontsize=9)

        # Adjust layout and save
        plt.tight_layout()
        # Save to base64
        buffer = io.BytesIO()
        plt.savefig(buffer, format='png', 
                   bbox_inches='tight', 
                   dpi=300,
                   facecolor='white', 
                   edgecolor='none',
                   pad_inches=0.2)

        plt.close(fig)
        buffer.seek(0)
        image_base64 = base64.b64encode(buffer.read()).decode('utf-8')

        filename = os.path.join(rel_output_dir, f'{diagram_type.lower()}_path_diagram.png')
        return filename, image_base64

    except Exception as e:
        print(f"Error generating {diagram_type} diagram: {e}")
        return None, None


def run_cb_sem_analysis(data: pd.DataFrame, variables: list[Variable], params: dict) -> ToolOutput:
    """
    Performs Covariance-Based Structural Equation Modeling (CB-SEM) analysis.

    Supports both full SEM and Confirmatory Factor Analysis (CFA). If structural paths
    are provided, runs a full SEM; otherwise, runs CFA to test measurement model
    with all latent variables allowed to covary. Enforces reflective measurement
    models as required by CB-SEM.

    Parameters:
        data: Input DataFrame containing observed variables
        variables: list of Variable objects defining the model structure
        params: dictionary containing analysis parameters:
            - output_dir (str): Base output directory name (default: "cb_sem_analysis")
            - save_files (bool): Whether to save generated files to disk (default: False)
            - structural_paths (list[tuple[str, str]]): Optional structural paths between latents
            - estimation_method (str): Estimation method for semopy - MLW, ULS, GLS, WLS, DWLS, FIML (default: "MLW")
            - language (str): language for output messages - "en" or "vi" (default: "en")

    Returns:
        ToolOutput: Contains results, logs, file contents, and suggested actions
    """
    # Extract parameters
    base_output_dir = params.get("output_dir", "cb_sem")
    save_files = params.get("save_files", False)
    structural_paths = params.get("structural_paths", [])
    estimation_method = params.get("estimation_method", "MLW")
    language = params.get("language", "en")

    # Translation dictionary
    translations = {
        "en": {
            "title": "# CB-SEM Analysis Report\n\n",
            "section1": "## 1. Model and Data Validation\n",
            "fatal_error_formative": "**FATAL ERROR**: Latent variable '{var_code}' is formative. CB-SEM requires reflective models only. Use PLS-SEM for formative models.",
            "measurement_type_defaulted": "Measurement type for '{var_code}' defaulted to reflective for CB-SEM.\n",
            "cbsem_assumption": "**CB-SEM Assumption**: All measurement models are treated as reflective.\n",
            "analysis_type": "**Analysis Type**: {analysis_type}\n",
            "path_diagram": "**Path Diagram**: `{diagram_filename}`\n",
            "warning_path_diagram": "**Warning**: Could not generate path diagram. Error: {error}\n",
            "section2": "\n## 2. Model Specification and Fitting\n",
            "no_structural_paths": "No structural paths specified. Testing measurement structure (CFA) with all latent factors allowed to covary.\n",
            "model_specification": "**Model Specification (semopy syntax)**:\n```\n{model_desc}\n```\n",
            "fitting_success": "Model fitting successful using '{estimation_method}' estimator.\n",
            "fatal_error_fitting": "**FATAL ERROR**: Model fitting failed: {error}. Check for non-positive definite covariance matrices, low variance, or model misspecification.\n",
            "action_comment_fitting": "Review data quality or model specification.",
            "section3": "\n## 3. Model Evaluation\n",
            "warning_no_stats": "**Warning**: Could not calculate model statistics. Skipping evaluation.\n",
            "warning_parse_stats": "**Warning**: Could not parse model statistics: {error}. Fit indices may be incomplete.\n",
            "fit_indices_title": "**Overall Model Fit Indices**:\n",
            "guideline_chi2": "-",
            "guideline_p_value": "> 0.05 (non-significant desired)",
            "guideline_cfi": "≥ 0.90 (acceptable), ≥ 0.95 (good)",
            "guideline_tli": "≥ 0.90 (acceptable), ≥ 0.95 (good)",
            "guideline_rmsea": "≤ 0.08 (acceptable), ≤ 0.06 (good)",
            "guideline_srmr": "≤ 0.08 (acceptable)",
            "parameter_estimates": "\n**Parameter Estimates**: `{params_filename}`\n",
            "non_significant_paths": "\n**Non-significant structural paths detected (p > 0.05)**:\n",
            "path_non_significant": "- Path `{rval} -> {lval}` (p = {p_value:.3f})\n",
            "warning_poor_fit": "\n**Warning**: Overall model fit is not acceptable. The model may not represent the data well.\n",
            "modification_indices": "**Modification Indices**: `{mi_filename}`\n",
            "warning_mi_generation": "**Warning**: Could not generate modification indices: {error}\n",
            "suggested_modifications": "**Suggested modifications (MI > 10.0)**:\n",
            "modification_suggestion": "- Consider adding: `{lval} {op} {rval}` (MI = {mi:.3f})\n",
            "section4": "\n## 4. Summary & Conclusion\n",
            "conclusion_acceptable": "The {analysis_type} model demonstrates acceptable fit to the data based on conventional fit indices.\n",
            "conclusion_poor": "The {analysis_type} model does not achieve acceptable fit to the data. Consider model respecification or data quality improvements.\n",
            "full_sem": "Full SEM",
            "cfa": "Confirmatory Factor Analysis (CFA)",
            "action_issue_fitting_error": "Model fitting error: {error}",
        },
        "vi": {
            "title": "# Báo Cáo Phân Tích CB-SEM\n\n",
            "section1": "## 1. Kiểm Tra Mô Hình và Dữ Liệu\n",
            "fatal_error_formative": "**LỖI NGHIÊM TRỌNG**: Biến tiềm ẩn '{var_code}' là dạng hình thành (formative). CB-SEM chỉ hỗ trợ mô hình phản ánh (reflective). Vui lòng sử dụng PLS-SEM cho mô hình hình thành.",
            "measurement_type_defaulted": "Loại đo lường cho '{var_code}' được mặc định là phản ánh (reflective) cho CB-SEM.\n",
            "cbsem_assumption": "**Giả Định CB-SEM**: Tất cả các mô hình đo lường được xem là phản ánh (reflective).\n",
            "analysis_type": "**Loại Phân Tích**: {analysis_type}\n",
            "path_diagram": "**Sơ Đồ Đường Dẫn**: `{diagram_filename}`\n",
            "warning_path_diagram": "**Cảnh báo**: Không thể tạo sơ đồ đường dẫn. Lỗi: {error}\n",
            "section2": "\n## 2. Đặc Tả và Ước Lượng Mô Hình\n",
            "no_structural_paths": "Không có đường dẫn cấu trúc được chỉ định. Kiểm tra cấu trúc đo lường (CFA) với tất cả các nhân tố tiềm ẩn được phép đồng biến.\n",
            "model_specification": "**Đặc Tả Mô Hình (cú pháp semopy)**:\n```\n{model_desc}\n```\n",
            "fitting_success": "Ước lượng mô hình thành công sử dụng phương pháp '{estimation_method}'.\n",
            "fatal_error_fitting": "**LỖI NGHIÊM TRỌNG**: Ước lượng mô hình thất bại: {error}. Kiểm tra ma trận hiệp phương sai không xác định dương, phương sai thấp, hoặc sai đặc tả mô hình.\n",
            "action_comment_fitting": "Xem xét lại chất lượng dữ liệu hoặc đặc tả mô hình.",
            "section3": "\n## 3. Đánh Giá Mô Hình\n",
            "warning_no_stats": "**Cảnh báo**: Không thể tính toán các thống kê mô hình. Bỏ qua đánh giá.\n",
            "warning_parse_stats": "**Cảnh báo**: Không thể phân tích các thống kê mô hình: {error}. Chỉ số phù hợp có thể không đầy đủ.\n",
            "fit_indices_title": "**Chỉ Số Phù Hợp Tổng Thể Của Mô Hình**:\n",
            "guideline_chi2": "-",
            "guideline_p_value": "> 0.05 (mong muốn không có ý nghĩa)",
            "guideline_cfi": "≥ 0.90 (chấp nhận được), ≥ 0.95 (tốt)",
            "guideline_tli": "≥ 0.90 (chấp nhận được), ≥ 0.95 (tốt)",
            "guideline_rmsea": "≤ 0.08 (chấp nhận được), ≤ 0.06 (tốt)",
            "guideline_srmr": "≤ 0.08 (chấp nhận được)",
            "parameter_estimates": "\n**Ước Lượng Tham Số**: `{params_filename}`\n",
            "non_significant_paths": "\n**Phát hiện đường dẫn cấu trúc không có ý nghĩa thống kê (p > 0.05)**:\n",
            "path_non_significant": "- Đường dẫn `{rval} -> {lval}` (p = {p_value:.3f})\n",
            "warning_poor_fit": "\n**Cảnh báo**: Độ phù hợp tổng thể của mô hình không chấp nhận được. Mô hình có thể không đại diện tốt cho dữ liệu.\n",
            "modification_indices": "**Chỉ Số Điều Chỉnh**: `{mi_filename}`\n",
            "warning_mi_generation": "**Cảnh báo**: Không thể tạo chỉ số điều chỉnh: {error}\n",
            "suggested_modifications": "**Đề xuất điều chỉnh (MI > 10.0)**:\n",
            "modification_suggestion": "- Cân nhắc thêm: `{lval} {op} {rval}` (MI = {mi:.3f})\n",
            "section4": "\n## 4. Tóm Tắt & Kết Luận\n",
            "conclusion_acceptable": "Mô hình {analysis_type} cho thấy độ phù hợp chấp nhận được với dữ liệu dựa trên các chỉ số phù hợp thông thường.\n",
            "conclusion_poor": "Mô hình {analysis_type} không đạt được độ phù hợp chấp nhận được với dữ liệu. Cân nhắc đặc tả lại mô hình hoặc cải thiện chất lượng dữ liệu.\n",
            "full_sem": "Mô hình SEM Đầy Đủ",
            "cfa": "Phân Tích Nhân Tố Khẳng Định (CFA)",
            "action_issue_fitting_error": "Lỗi ước lượng mô hình: {error}",
        }
    }

    # Get translations for selected language
    t = get_t_dict(translations.get(language, translations["en"]), language=language)
    
    # Setup output directory with timestamp
    now = datetime.now()
    timestamp = f"{now.microsecond // 10000:02d}"
    output_dir = os.path.join(os.path.dirname(base_output_dir) or ".", f"{timestamp}_{os.path.basename(base_output_dir)}")
    rel_output_dir = os.path.relpath(output_dir, start=os.path.dirname(base_output_dir) or ".")

    logs = []
    file_contents = {}
    actions = []

    # Start analysis
    logs.append(t["title"])
    logs.append(t["section1"])

    # Pre-process and validate variables
    variables_processed = copy.deepcopy(variables)
    for var in variables_processed:
        if var.variable_type == VariableType.LATENT:
            if var.properties.get('measurement_type') == 'formative':
                error_msg = t["fatal_error_formative"].format(var_code=var.code)
                logs.append(error_msg)
                raise ValueError(error_msg)
            if 'measurement_type' not in var.properties:
                var.properties['measurement_type'] = 'reflective'
                logs.append(t["measurement_type_defaulted"].format(var_code=var.code))

    logs.append(t["cbsem_assumption"])

    # Determine analysis type
    analysis_type = t["full_sem"] if structural_paths else t["cfa"]
    logs.append(t["analysis_type"].format(analysis_type=analysis_type))

    # Generate path diagram
    try:
        diagram_filename, base64_content = draw_sem_path_diagram(variables_processed, structural_paths, rel_output_dir)
        if diagram_filename and base64_content:
            file_contents[diagram_filename] = base64_content
            logs.append(t["path_diagram"].format(diagram_filename=diagram_filename))
    except Exception as e:
        logs.append(t["warning_path_diagram"].format(error=e))

    # Model specification and fitting
    logs.append(t["section2"])
    
    latents = [var for var in variables_processed if var.variable_type == VariableType.LATENT]
    observed_vars_by_factor = {
        latent.code: [var.code for var in variables_processed if var.parent_code == latent.code and var.variable_type == VariableType.OBSERVED]
        for latent in latents
    }

    # Build measurement model
    measurement_model = "\n".join([f"{latent_code} =~ {' + '.join(indicators)}"
                                  for latent_code, indicators in observed_vars_by_factor.items() if indicators])

    # Build full model specification
    if structural_paths:
        structural_model = "\n".join([f"{to_code} ~ {from_code}" for from_code, to_code in structural_paths])
        model_desc = f"{measurement_model}\n{structural_model}"
    else:
        model_desc = measurement_model
        logs.append(t["no_structural_paths"])

    logs.append(t["model_specification"].format(model_desc=model_desc))

    # Fit the model
    model = SemopyModel(model_desc)
    try:
        model.fit(data, obj=estimation_method)
        logs.append(t["fitting_success"].format(estimation_method=estimation_method))
    except Exception as e:
        logs.append(t["fatal_error_fitting"].format(error=str(e)))
        actions.append(Action(
            action_type=ActionType.RECHECK_DATA,
            method="run_cb_sem_analysis",
            issue=t["action_issue_fitting_error"].format(error=e),
            comment=t["action_comment_fitting"],
            status="pending"
        ))
        return ToolOutput(results={}, logs=logs, file_contents=file_contents, action=actions)

    # Model evaluation
    logs.append(t["section3"])
    
    stats = calc_stats(model)
    if stats.empty:
        logs.append(t["warning_no_stats"])
        return ToolOutput(results={}, logs=logs, file_contents=file_contents, action=actions)

    # Parse fit statistics
    fit_stats_series = pd.Series(dtype=float)
    try:
        if 'Value' in stats.columns:
            fit_stats_series = pd.to_numeric(stats['Value'], errors='coerce')
            fit_stats_series.index = stats.index
        elif 'Value' in stats.index:
            fit_stats_series = pd.to_numeric(stats.loc['Value'], errors='coerce')
    except Exception as e:
        logs.append(t["warning_parse_stats"].format(error=e))

    # Extract fit indices
    fit_indices = {
        "Chi-Square (χ²)": fit_stats_series.get('chi2', np.nan),
        "Degrees of Freedom (df)": fit_stats_series.get('DoF', np.nan),
        "p-value (χ²)": fit_stats_series.get('chi2 p-value', np.nan),
        "CFI": fit_stats_series.get('CFI', np.nan),
        "TLI": fit_stats_series.get('TLI', np.nan),
        "RMSEA": fit_stats_series.get('RMSEA', np.nan),
        "SRMR": fit_stats_series.get('SRMR', np.nan)
    }
    
    # Extract fit indices and create DataFrame for display
    fit_indices_data = [
        {"Index": "Chi-Square (χ²)", "Value": fit_stats_series.get('chi2', np.nan), "Guideline": t["guideline_chi2"]},
        {"Index": "p-value (χ²)", "Value": fit_stats_series.get('chi2 p-value', np.nan), "Guideline": t["guideline_p_value"]},
        {"Index": "CFI", "Value": fit_stats_series.get('CFI', np.nan), "Guideline": t["guideline_cfi"]},
        {"Index": "TLI", "Value": fit_stats_series.get('TLI', np.nan), "Guideline": t["guideline_tli"]},
        {"Index": "RMSEA", "Value": fit_stats_series.get('RMSEA', np.nan), "Guideline": t["guideline_rmsea"]},
        {"Index": "SRMR", "Value": fit_stats_series.get('SRMR', np.nan), "Guideline": t["guideline_srmr"]},
    ]

    fit_indices_df = pd.DataFrame(fit_indices_data)

    # Format values: 3 decimal places or '-' for NaN
    fit_indices_df['Value'] = fit_indices_df['Value'].apply(
        lambda x: f'{x:.3f}' if pd.notna(x) else '-'
    )

    # Display fit indices table
    logs.append(t["fit_indices_title"])
    logs.append(fit_indices_df.to_markdown(index=False) + "\n")

    # Get parameter estimates
    params_df = model.inspect()
    if 'p-value' in params_df.columns:
        params_df['p-value'] = pd.to_numeric(params_df['p-value'], errors='coerce')

    # Save parameter estimates
    params_filename = os.path.join(rel_output_dir, "sem_parameter_estimates.csv")
    file_contents[params_filename] = params_df.fillna('-').to_csv(index=False)
    logs.append(t["parameter_estimates"].format(params_filename=params_filename))

    # Check for non-significant structural paths
    if structural_paths:
        structural_paths_df = params_df[params_df['op'] == '~']
        if 'p-value' in structural_paths_df.columns:
            non_significant_paths = structural_paths_df[structural_paths_df['p-value'] > 0.05]
            if not non_significant_paths.empty:
                logs.append(t["non_significant_paths"])
                for _, row in non_significant_paths.iterrows():
                    logs.append(t["path_non_significant"].format(rval=row['rval'], lval=row['lval'], p_value=row['p-value']))

    # Evaluate overall model fit
    sem_fit_good = (
        pd.notna(fit_indices["CFI"]) and fit_indices["CFI"] >= 0.90 and
        pd.notna(fit_indices["RMSEA"]) and fit_indices["RMSEA"] <= 0.08 and
        pd.notna(fit_indices["SRMR"]) and fit_indices["SRMR"] <= 0.08
    )

    # Generate modification indices if fit is poor
    if not sem_fit_good:
        logs.append(t["warning_poor_fit"])

        try:
            mi = model.inspect(what='modindices')
            if mi is not None and not mi.empty and 'MI' in mi.columns:
                mi['MI'] = pd.to_numeric(mi['MI'], errors='coerce')
                mi.dropna(subset=['MI'], inplace=True)
                mi = mi.sort_values('MI', ascending=False).head(10)

                mi_filename = os.path.join(rel_output_dir, "modification_indices.csv")
                file_contents[mi_filename] = mi.fillna('-').to_csv(index=False)
                logs.append(t["modification_indices"].format(mi_filename=mi_filename))

                high_mi = mi[mi['MI'] > 10]
                if not high_mi.empty:
                    logs.append(t["suggested_modifications"])
                    for _, row in high_mi.iterrows():
                        logs.append(t["modification_suggestion"].format(lval=row['lval'], op=row['op'], rval=row['rval'], mi=row['MI']))
        except Exception as e:
            logs.append(t["warning_mi_generation"].format(error=e))

    # Summary and conclusion
    logs.append(t["section4"])
    if sem_fit_good:
        logs.append(t["conclusion_acceptable"].format(analysis_type=analysis_type))
    else:
        logs.append(t["conclusion_poor"].format(analysis_type=analysis_type))

    # Save all files at once
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
    fit_indices_for_output = {k: ('-' if pd.isna(v) else v) for k, v in fit_indices.items()}
    
    results = {
        "analysis_type": analysis_type,
        "model_specification": model_desc,
        "estimation_method": estimation_method,
        "sem_fit_indices": fit_indices_for_output,
        "model_fit_acceptable": sem_fit_good,
        "parameter_count": len(params_df) if not params_df.empty else 0
    }

    return ToolOutput(
        results=serialize_dict(results),
        logs=["".join(logs)],
        file_contents=file_contents,
        action=actions if actions else None
    )
    
######################################################
###################### PLS-SEM #######################
######################################################

def create_structured_correlation_matrix(
    data: pd.DataFrame,
    variables: list[Variable]
) -> pd.DataFrame:
    """
    Creates a correlation matrix that only shows values for indicators belonging
    to the same latent construct. All other cells are NaN.
    """
    latents = [var for var in variables if var.variable_type == VariableType.LATENT]
    observed_per_latent = {
        latent.code: [
            var.code for var in variables
            if var.parent_code == latent.code and var.variable_type == VariableType.OBSERVED
        ]
        for latent in latents
    }

    all_indicators = [code for sublist in observed_per_latent.values() for code in sublist]
    available_indicators = [code for code in all_indicators if code in data.columns]

    # Create a reverse map from indicator to its parent latent
    indicator_to_latent = {
        obs_code: latent_code
        for latent_code, obs_list in observed_per_latent.items()
        for obs_code in obs_list
    }

    # Start with a full correlation matrix of available indicators
    full_corr = data[available_indicators].corr()

    # Create a new DataFrame of the same size, filled with NaNs
    structured_corr = pd.DataFrame(np.nan, index=full_corr.index, columns=full_corr.columns)

    # Populate the new DataFrame only where indicators share a parent
    for r_ind in structured_corr.index:
        for c_ind in structured_corr.columns:
            # Check if both indicators are in our map and have the same parent
            if indicator_to_latent.get(r_ind) == indicator_to_latent.get(c_ind):
                structured_corr.loc[r_ind, c_ind] = full_corr.loc[r_ind, c_ind]

    return structured_corr


def build_plspm_config(
    variables: list[Variable],
    structural_paths: list[tuple[str, str]],
    data: pd.DataFrame
) -> plspm_config.Config:
    """
    Builds the configuration for the PLS-PM model.

    This function correctly initializes the plspm Structure and Config objects, ensuring
    that the final path matrix includes all latent variables and that only indicators
    present in the data are added to the model.

    Args:
        variables: A list of all Variable objects in the model.
        structural_paths: A list of tuples representing structural paths ('from', 'to').
        data: The input DataFrame, used to verify the existence of indicators.

    Returns:
        A plspm_config.Config object ready for model fitting.
    """
    all_latent_codes_set = {var.code for var in variables if var.variable_type == VariableType.LATENT}
    if not all_latent_codes_set:
        raise ValueError("No latent variables found to build a model.")

    # Topological sort to order latent variables according to structural paths
    # This ensures the path matrix is lower triangular
    # Build adjacency list and in-degree count
    graph = defaultdict(list)
    in_degree = {code: 0 for code in all_latent_codes_set}

    for from_var, to_var in structural_paths:
        if from_var in all_latent_codes_set and to_var in all_latent_codes_set:
            graph[from_var].append(to_var)
            in_degree[to_var] += 1

    # Kahn's algorithm for topological sorting
    queue = deque([node for node in all_latent_codes_set if in_degree[node] == 0])
    all_latent_codes = []

    while queue:
        # Sort queue for deterministic ordering when multiple nodes have in-degree 0
        current_batch = sorted(list(queue))
        queue.clear()

        for node in current_batch:
            all_latent_codes.append(node)
            for neighbor in graph[node]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

    # Check for cycles
    if len(all_latent_codes) != len(all_latent_codes_set):
        # There's a cycle - fall back to sorted order and let the error propagate
        # This will give a more informative error to the user
        remaining = sorted(all_latent_codes_set - set(all_latent_codes))
        raise ValueError(
            f"Circular dependency detected in structural paths. "
            f"The following variables are part of a cycle: {remaining}. "
            f"PLS-SEM requires a non-cyclic (recursive) model structure."
        )

    structure = plspm_config.Structure()
    if structural_paths:
        for from_var, to_var in structural_paths:
            structure.add_path([from_var], [to_var])

    # Create the path matrix
    path_matrix_data = {col: {row: 0 for row in all_latent_codes} for col in all_latent_codes}
    for from_var, to_var in structural_paths:
        if from_var in path_matrix_data and to_var in path_matrix_data[from_var]:
            path_matrix_data[to_var][from_var] = 1
    final_path_matrix = pd.DataFrame(path_matrix_data, index=all_latent_codes, columns=all_latent_codes).T

    config = plspm_config.Config(final_path_matrix, scaled=False)

    latents = [var for var in variables if var.variable_type == VariableType.LATENT]
    for latent in latents:
        try:
            measurement_type = latent.properties['measurement_type']
            mode = Mode.A if measurement_type == 'reflective' else Mode.B

            # Get all indicators defined for this latent
            defined_indicators = [var.code for var in variables
                                  if var.parent_code == latent.code and var.variable_type == VariableType.OBSERVED]

            # Filter to only include indicators that are actually in the dataset
            available_indicators = [code for code in defined_indicators if code in data.columns]

            if not defined_indicators:
                continue

            if not available_indicators:
                continue

            config.add_lv(latent.code, mode, *[plspm_config.MV(var) for var in available_indicators])

        except Exception as e:
            continue

    return config


def assess_data_suitability_for_pls_sem(
    data: pd.DataFrame,
    variables: list[Variable],
    params: dict
) -> ToolOutput:
    """
    Assesses data suitability for PLS-SEM analysis, focusing on sample size, correlations within constructs,
    and multicollinearity for formative constructs.

    Parameters:
        data: Input DataFrame containing the data
        variables: list of Variable objects describing the data columns
        params: dictionary containing analysis parameters
            - output_dir (str): base output directory name (default: "pls_sem_analysis")
            - save_files (bool): whether to save generated files to disk (default: False)
            - language (str): language for output messages - "en" or "vi" (default: "en")

    Returns:
        ToolOutput: Contains results, logs, file contents, and suggested actions
    """
    # Extract parameters
    base_output_dir = params.get("output_dir", "pls_sem")
    save_files = params.get("save_files", False)

    # Translation dictionary
    translations = {
        "en": {
            "title": "### Data Suitability Assessment for PLS-SEM\n",
            "no_observed_vars": "**ERROR**: No observed variables linked to latent constructs found.\n",
            "sample_size_analysis": "**Sample Size Analysis:**\n",
            "current_sample": "- Current sample size: {n}\n",
            "required_sample": "- Required sample size: ≥ {required_n} (based on 10 × {max_obs} indicators for construct '{most_complex_construct}')\n",
            "sample_warning": "- **Warning**: Sample size {n} < {required_n}. Results may be unreliable.\n",
            "corr_matrix": "**Intra-Construct Correlation Matrix:** `{corr_filename}`\n",
            "construct_analysis": "**Construct-Level Analysis:**\n",
            "construct_header": "- **{latent_code}** ({measurement_type} measurement):\n",
            "high_corr": "  - High correlation (> 0.8): {pairs_str}\n",
            "low_corr": "  - Low correlation (< 0.3): {pairs_str} - may indicate poor convergent validity\n",
            "high_vif": "  - High VIF (> 5): {vif_str}\n",
            "reflective": "reflective",
            "formative": "formative"
        },
        "vi": {
            "title": "### Đánh Giá Mức Độ Phù Hợp Của Dữ Liệu Cho PLS-SEM\n",
            "no_observed_vars": "**LỖI**: Không tìm thấy biến quan sát nào liên kết với các cấu trúc tiềm ẩn.\n",
            "sample_size_analysis": "**Phân Tích Kích Thước Mẫu:**\n",
            "current_sample": "- Kích thước mẫu hiện tại: {n}\n",
            "required_sample": "- Kích thước mẫu yêu cầu: ≥ {required_n} (dựa trên 10 × {max_obs} chỉ báo cho cấu trúc '{most_complex_construct}')\n",
            "sample_warning": "- **Cảnh báo**: Kích thước mẫu {n} < {required_n}. Kết quả có thể không đáng tin cậy.\n",
            "corr_matrix": "**Ma Trận Tương Quan Nội Bộ Cấu Trúc:** `{corr_filename}`\n",
            "construct_analysis": "**Phân Tích Theo Từng Cấu Trúc:**\n",
            "construct_header": "- **{latent_code}** (đo lường {measurement_type}):\n",
            "high_corr": "  - Tương quan cao (> 0.8): {pairs_str}\n",
            "low_corr": "  - Tương quan thấp (< 0.3): {pairs_str} - có thể cho thấy giá trị hội tụ kém\n",
            "high_vif": "  - VIF cao (> 5): {vif_str}\n",
            "reflective": "phản ánh",
            "formative": "hình thành"
        }
    }

    language = params.get("language", "en")
    t = get_t_dict(translations.get(language, translations["en"]), language=language)

    # Setup output directory with timestamp
    now = datetime.now()
    timestamp = f"{now.microsecond // 10000:02d}"
    output_dir = os.path.join(os.path.dirname(base_output_dir) or ".", f"{timestamp}_{os.path.basename(base_output_dir)}")
    rel_output_dir = os.path.relpath(output_dir, start=os.path.dirname(base_output_dir) or ".")

    logs = [t["title"]]
    file_contents = {}
    actions = []

    observed_vars_in_model = [var.code for var in variables if var.variable_type == VariableType.OBSERVED and var.parent_code]
    if not observed_vars_in_model:
        logs.append(t["no_observed_vars"])
        return ToolOutput(results={}, logs=logs, file_contents=file_contents, action=None)

    latents = [var for var in variables if var.variable_type == VariableType.LATENT]
    observed_per_latent = {latent.code: [var.code for var in variables if var.parent_code == latent.code and var.variable_type == VariableType.OBSERVED] for latent in latents}

    # Sample Size Assessment
    max_obs = max(len(obs) for obs in observed_per_latent.values()) if observed_per_latent else 0
    most_complex_construct = max(observed_per_latent, key=lambda k: len(observed_per_latent[k]), default=None)
    n = len(data)
    required_n = max(10 * max_obs, 30)

    logs.append(t["sample_size_analysis"])
    logs.append(t["current_sample"].format(n=n))
    logs.append(t["required_sample"].format(required_n=required_n, max_obs=max_obs, most_complex_construct=most_complex_construct))

    if n < required_n:
        logs.append(t["sample_warning"].format(n=n, required_n=required_n))

    # Correlation and Multicollinearity Assessment
    all_available_indicators = [var for var in observed_vars_in_model if var in data.columns]
    if len(all_available_indicators) > 1:
        block_corr_matrix = create_structured_correlation_matrix(data, variables)
        block_corr_matrix = block_corr_matrix.round(3)

        corr_filename = os.path.join(rel_output_dir, "intra_construct_correlation_matrix.csv")
        file_contents[corr_filename] = block_corr_matrix.to_csv(index=True)
        logs.append(t["corr_matrix"].format(corr_filename=corr_filename))

        # Construct-specific analysis
        logs.append(t["construct_analysis"])
        for latent in latents:
            measurement_type = latent.properties['measurement_type']
            # Translate measurement type
            measurement_type_translated = t.get(measurement_type, measurement_type)
            indicators = [var for var in observed_per_latent[latent.code] if var in data.columns]

            if len(indicators) < 2:
                continue

            logs.append(t["construct_header"].format(latent_code=latent.code, measurement_type=measurement_type_translated))

            corr = data[indicators].corr()
            high_corr_pairs = [(v1, v2, corr.loc[v1, v2]) for i, v1 in enumerate(indicators) for j, v2 in enumerate(indicators) if i < j and abs(corr.loc[v1, v2]) > 0.8]

            if high_corr_pairs:
                pairs_str = ', '.join([f'{v1}-{v2} ({val:.3f})' for v1, v2, val in high_corr_pairs])
                logs.append(t["high_corr"].format(pairs_str=pairs_str))

            if measurement_type == 'reflective':
                low_corr_pairs = [(v1, v2, corr.loc[v1, v2]) for i, v1 in enumerate(indicators) for j, v2 in enumerate(indicators) if i < j and abs(corr.loc[v1, v2]) < 0.3]
                if low_corr_pairs:
                    pairs_str = ', '.join([f'{v1}-{v2} ({val:.3f})' for v1, v2, val in low_corr_pairs])
                    logs.append(t["low_corr"].format(pairs_str=pairs_str))

            elif measurement_type == 'formative':
                vif_data = {}
                for var in indicators:
                    other_vars = [v for v in indicators if v != var]
                    try:
                        model = OLS(data[var], add_constant(data[other_vars])).fit()
                        vif = 1 / (1 - model.rsquared) if model.rsquared < 1 else float('inf')
                        vif_data[var] = vif
                    except:
                        vif_data[var] = float('nan')

                high_vif_vars = [var for var, vif in vif_data.items() if not np.isnan(vif) and vif > 5]
                if high_vif_vars:
                    vif_str = ', '.join([f'{var} ({vif_data[var]:.2f})' for var in high_vif_vars])
                    logs.append(t["high_vif"].format(vif_str=vif_str))

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

    return ToolOutput(results={"sample_size": n, "required_n": required_n}, logs=logs, file_contents=file_contents, action=actions if actions else None)


def analyze_pls_sem_measurement_model(
    plspm_model: Plspm,
    variables: list[Variable],
    params: dict,
    data: pd.DataFrame
) -> ToolOutput:
    """
    Analyzes the measurement model, checking reliability and validity for reflective
    and formative constructs. Generates separate tables for loadings and weights.

    Parameters:
        plspm_model: Fitted PLS-SEM model object
        variables: list of Variable objects describing the data columns
        params: dictionary containing analysis parameters
            - output_dir (str): base output directory name (default: "pls_sem_analysis")
            - save_files (bool): whether to save generated files to disk (default: False)
            - language (str): language for output messages - "en" or "vi" (default: "en")
        data: Original DataFrame for additional calculations

    Returns:
        ToolOutput: Contains results, logs, file contents, and suggested actions
    """
    # Extract parameters
    base_output_dir = params.get("output_dir", "pls_sem_analysis")
    save_files = params.get("save_files", False)

    # Translation dictionary
    translations = {
        "en": {
            "title": "### Measurement Model Analysis\n",
            "construct_header": "**{latent_code} ({measurement_type} Measurement)**\n",
            "no_results": "- No measurement model results found for '{latent_code}'\n",
            "cronbach_alpha": "- Cronbach's Alpha: {alpha:.3f} (≥ 0.7 desired)\n",
            "alpha_low": "  - Alpha below threshold suggests reliability concerns\n",
            "alpha_insufficient": "- Cronbach's Alpha: Insufficient indicators in data\n",
            "alpha_error": "- Cronbach's Alpha: Could not compute ({error})\n",
            "composite_reliability": "- Composite Reliability (CR): {cr:.3f} (≥ 0.7 required)\n",
            "ave": "- Average Variance Extracted (AVE): {ave:.3f} (≥ 0.5 required)\n",
            "cr_low": "  - CR below threshold indicates reliability concerns\n",
            "ave_low": "  - AVE below threshold suggests convergent validity issues\n",
            "individual_loadings": "- Individual Loadings:\n",
            "loading_value": "  - {indicator}: {loading:.3f}\n",
            "loading_low": "    - Loading below 0.7 threshold\n",
            "indicator_weights": "- Indicator Weights:\n",
            "weight_value": "  - {indicator}: {weight:.3f}\n",
            "weight_weak": "    - Very weak contribution to construct\n",
            "vif_analysis": "- VIF Analysis (Multicollinearity Check):\n",
            "vif_value": "  - {var}: {vif:.2f}\n",
            "vif_high": "    - VIF > 5 indicates high multicollinearity\n",
            "vif_error": "  - {var}: Could not calculate VIF ({error})\n",
            "loadings_table": "**Loadings Table (Reflective Constructs):** `{filename}`\n",
            "weights_table": "**Weights Table (Formative Constructs):** `{filename}`\n",
            "htmt_matrix": "**HTMT Matrix (Discriminant Validity):** `{filename}`\n",
            "htmt_assessment": "- HTMT Discriminant Validity Assessment:\n",
            "htmt_concern": "  - HTMT({l1}, {l2}) = {val:.3f} > 0.85 (discriminant validity concern)\n",
            "htmt_error": "HTMT matrix could not be computed: {error}\n",
            "analysis_error": "**Error**: Could not analyze measurement model: {error}\n",
            "reflective": "Reflective",
            "formative": "Formative"
        },
        "vi": {
            "title": "### Phân Tích Mô Hình Đo Lường\n",
            "construct_header": "**{latent_code} (Đo Lường {measurement_type})**\n",
            "no_results": "- Không tìm thấy kết quả mô hình đo lường cho '{latent_code}'\n",
            "cronbach_alpha": "- Cronbach's Alpha: {alpha:.3f} (≥ 0.7 mong muốn)\n",
            "alpha_low": "  - Alpha thấp hơn ngưỡng cho thấy vấn đề về độ tin cậy\n",
            "alpha_insufficient": "- Cronbach's Alpha: Không đủ chỉ báo trong dữ liệu\n",
            "alpha_error": "- Cronbach's Alpha: Không thể tính toán ({error})\n",
            "composite_reliability": "- Độ Tin Cậy Tổng Hợp (CR): {cr:.3f} (≥ 0.7 yêu cầu)\n",
            "ave": "- Phương Sai Trích Trung Bình (AVE): {ave:.3f} (≥ 0.5 yêu cầu)\n",
            "cr_low": "  - CR thấp hơn ngưỡng cho thấy vấn đề về độ tin cậy\n",
            "ave_low": "  - AVE thấp hơn ngưỡng cho thấy vấn đề về giá trị hội tụ\n",
            "individual_loadings": "- Hệ Số Tải Từng Chỉ Báo:\n",
            "loading_value": "  - {indicator}: {loading:.3f}\n",
            "loading_low": "    - Hệ số tải thấp hơn ngưỡng 0.7\n",
            "indicator_weights": "- Trọng Số Chỉ Báo:\n",
            "weight_value": "  - {indicator}: {weight:.3f}\n",
            "weight_weak": "    - Đóng góp rất yếu vào cấu trúc\n",
            "vif_analysis": "- Phân Tích VIF (Kiểm Tra Đa Cộng Tuyến):\n",
            "vif_value": "  - {var}: {vif:.2f}\n",
            "vif_high": "    - VIF > 5 cho thấy đa cộng tuyến cao\n",
            "vif_error": "  - {var}: Không thể tính VIF ({error})\n",
            "loadings_table": "**Bảng Hệ Số Tải (Cấu Trúc Phản Ánh):** `{filename}`\n",
            "weights_table": "**Bảng Trọng Số (Cấu Trúc Hình Thành):** `{filename}`\n",
            "htmt_matrix": "**Ma Trận HTMT (Giá Trị Phân Biệt):** `{filename}`\n",
            "htmt_assessment": "- Đánh Giá Giá Trị Phân Biệt HTMT:\n",
            "htmt_concern": "  - HTMT({l1}, {l2}) = {val:.3f} > 0.85 (vấn đề về giá trị phân biệt)\n",
            "htmt_error": "Ma trận HTMT không thể tính toán: {error}\n",
            "analysis_error": "**Lỗi**: Không thể phân tích mô hình đo lường: {error}\n",
            "reflective": "Phản Ánh",
            "formative": "Hình Thành"
        }
    }

    language = params.get("language", "en")
    t = get_t_dict(translations.get(language, translations["en"]), language=language)

    # Setup output directory with timestamp
    now = datetime.now()
    timestamp = f"{now.microsecond // 10000:02d}"
    output_dir = os.path.join(os.path.dirname(base_output_dir) or ".", f"{timestamp}_{os.path.basename(base_output_dir)}")
    rel_output_dir = os.path.relpath(output_dir, start=os.path.dirname(base_output_dir) or ".")

    logs = [t["title"]]
    file_contents = {}
    actions = []

    try:
        outer_model_df = plspm_model.outer_model()
        latents = [var for var in variables if var.variable_type == VariableType.LATENT]

        loadings_data = []
        weights_data = []

        # Analyze each latent construct
        for latent in latents:
            latent_code = latent.code
            measurement_type = latent.properties.get('measurement_type', 'reflective')
            # Translate measurement type
            measurement_type_translated = t.get(measurement_type, measurement_type)

            logs.append(t["construct_header"].format(latent_code=latent_code, measurement_type=measurement_type_translated))

            defined_indicators = [var.code for var in variables
                                  if var.parent_code == latent_code and var.variable_type == VariableType.OBSERVED]
            indicators_in_model = [ind for ind in defined_indicators if ind in outer_model_df.index]

            if not indicators_in_model:
                logs.append(t["no_results"].format(latent_code=latent_code))
                continue

            latent_outer_df = outer_model_df.loc[indicators_in_model]

            if measurement_type == 'reflective':
                # Reliability Analysis
                if len(indicators_in_model) > 1:
                    try:
                        alpha_indicators = [ind for ind in indicators_in_model if ind in data.columns]
                        if len(alpha_indicators) > 1:
                            alpha = pg.cronbach_alpha(data[alpha_indicators])[0]
                            logs.append(t["cronbach_alpha"].format(alpha=alpha))
                            if alpha < 0.7:
                                logs.append(t["alpha_low"])
                        else:
                            logs.append(t["alpha_insufficient"])
                    except Exception as e:
                        logs.append(t["alpha_error"].format(error=str(e)))

                # Composite Reliability and AVE
                loadings = latent_outer_df['loading'].values
                if len(loadings) > 0:
                    sum_loadings_sq = (loadings ** 2).sum()
                    sum_error_vars = (1 - (loadings ** 2)).sum()
                    cr = sum_loadings_sq / (sum_loadings_sq + sum_error_vars) if (sum_loadings_sq + sum_error_vars) != 0 else 0
                    ave = np.mean(loadings ** 2)

                    logs.append(t["composite_reliability"].format(cr=cr))
                    logs.append(t["ave"].format(ave=ave))

                    if cr < 0.7:
                        logs.append(t["cr_low"])
                    if ave < 0.5:
                        logs.append(t["ave_low"])

                # Individual loadings
                logs.append(t["individual_loadings"])
                for indicator_name, row in latent_outer_df.iterrows():
                    loading = row['loading']
                    logs.append(t["loading_value"].format(indicator=indicator_name, loading=loading))
                    if abs(loading) < 0.7:
                        logs.append(t["loading_low"])
                    loadings_data.append({'Latent': latent_code, 'Indicator': indicator_name, 'Loading': loading})

            elif measurement_type == 'formative':
                # Weights analysis
                logs.append(t["indicator_weights"])
                for indicator_name, row in latent_outer_df.iterrows():
                    weight = row['weight']
                    logs.append(t["weight_value"].format(indicator=indicator_name, weight=weight))
                    if abs(weight) < 0.1:
                        logs.append(t["weight_weak"])
                    weights_data.append({'Latent': latent_code, 'Indicator': indicator_name, 'Weight': weight})

                # VIF analysis for multicollinearity
                if len(indicators_in_model) > 1:
                    logs.append(t["vif_analysis"])
                    for var in indicators_in_model:
                        other_vars = [v for v in indicators_in_model if v != var]
                        try:
                            model = OLS(data[var], add_constant(data[other_vars])).fit()
                            vif = 1 / (1 - model.rsquared) if model.rsquared < 1 else float('inf')
                            logs.append(t["vif_value"].format(var=var, vif=vif))
                            if vif > 5:
                                logs.append(t["vif_high"])
                        except Exception as e:
                            logs.append(t["vif_error"].format(var=var, error=e))

        # Generate output tables
        if loadings_data:
            loadings_df = pd.DataFrame(loadings_data).pivot(index='Latent', columns='Indicator', values='Loading')
            loadings_filename = os.path.join(rel_output_dir, "loadings.csv")
            file_contents[loadings_filename] = loadings_df.to_csv()
            logs.append(t["loadings_table"].format(filename=loadings_filename))

        if weights_data:
            weights_df = pd.DataFrame(weights_data).pivot(index='Latent', columns='Indicator', values='Weight')
            weights_filename = os.path.join(rel_output_dir, "weights.csv")
            file_contents[weights_filename] = weights_df.to_csv()
            logs.append(t["weights_table"].format(filename=weights_filename))

        # HTMT Analysis for discriminant validity
        reflective_latents = [latent.code for latent in latents if latent.properties.get('measurement_type', 'reflective') == 'reflective' and latent.code in plspm_model.inner_summary().index]
        if len(reflective_latents) > 1:
            if hasattr(plspm_model, 'htmt'):
                try:
                    htmt = plspm_model.htmt()
                    htmt_filename = os.path.join(rel_output_dir, "htmt_matrix.csv")
                    file_contents[htmt_filename] = htmt.to_csv(index=True)
                    logs.append(t["htmt_matrix"].format(filename=htmt_filename))

                    # Check HTMT thresholds
                    logs.append(t["htmt_assessment"])
                    for i in range(len(htmt.index)):
                        for j in range(i + 1, len(htmt.columns)):
                            l1, l2 = htmt.index[i], htmt.columns[j]
                            if l1 in htmt.index and l2 in htmt.columns and not pd.isna(htmt.loc[l1, l2]):
                                val = htmt.loc[l1, l2]
                                if val > 0.85:
                                    logs.append(t["htmt_concern"].format(l1=l1, l2=l2, val=val))
                except Exception as e:
                    logs.append(t["htmt_error"].format(error=str(e)))

    except Exception as e:
        logs.append(t["analysis_error"].format(error=str(e)))

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

    return ToolOutput(results={}, logs=logs, file_contents=file_contents, action=actions if actions else None)


def analyze_pls_sem_structural_model(
    plspm_model: Plspm,
    params: dict
) -> ToolOutput:
    """
    Analyzes the structural model, evaluating R-squared values and path coefficients.

    Parameters:
        plspm_model: Fitted PLS-SEM model object
        params: dictionary containing analysis parameters
            - output_dir (str): base output directory name (default: "pls_sem_analysis")
            - save_files (bool): whether to save generated files to disk (default: False)
            - language (str): language for output messages - "en" or "vi" (default: "en")

    Returns:
        ToolOutput: Contains results, logs, file contents, and suggested actions
    """
    # Extract parameters
    base_output_dir = params.get("output_dir", "pls_sem_analysis")
    save_files = params.get("save_files", False)

    # Translation dictionary
    translations = {
        "en": {
            "title": "### Structural Model Analysis\n",
            "r_squared_table": "**R² Values (Coefficient of Determination):** `{filename}`\n",
            "explained_variance": "- Explained Variance by Construct:\n",
            "construct_r_squared": "  - {construct}: {value:.3f} ({interpretation} explanatory power)\n",
            "path_coefficients_table": "**Path Coefficients:** `{filename}`\n",
            "structural_relationships": "- Structural Relationships:\n",
            "path_relationship": "  - {source} → {target}: {coef:.3f} ({effect_size} effect)\n",
            "analysis_error": "**Error**: Could not analyze structural model: {error}\n",
            "strong": "strong",
            "moderate": "moderate",
            "weak": "weak",
            "very_weak": "very weak",
            "large": "large",
            "medium": "medium",
            "small": "small"
        },
        "vi": {
            "title": "### Phân Tích Mô Hình Cấu Trúc\n",
            "r_squared_table": "**Giá Trị R² (Hệ Số Xác Định):** `{filename}`\n",
            "explained_variance": "- Phương Sai Được Giải Thích Theo Cấu Trúc:\n",
            "construct_r_squared": "  - {construct}: {value:.3f} (sức mạnh giải thích {interpretation})\n",
            "path_coefficients_table": "**Hệ Số Đường Dẫn:** `{filename}`\n",
            "structural_relationships": "- Mối Quan Hệ Cấu Trúc:\n",
            "path_relationship": "  - {source} → {target}: {coef:.3f} (hiệu ứng {effect_size})\n",
            "analysis_error": "**Lỗi**: Không thể phân tích mô hình cấu trúc: {error}\n",
            "strong": "mạnh",
            "moderate": "trung bình",
            "weak": "yếu",
            "very_weak": "rất yếu",
            "large": "lớn",
            "medium": "trung bình",
            "small": "nhỏ"
        }
    }

    language = params.get("language", "en")
    t = get_t_dict(translations.get(language, translations["en"]), language=language)

    # Setup output directory with timestamp
    now = datetime.now()
    timestamp = f"{now.microsecond // 10000:02d}"
    output_dir = os.path.join(os.path.dirname(base_output_dir) or ".", f"{timestamp}_{os.path.basename(base_output_dir)}")
    rel_output_dir = os.path.relpath(output_dir, start=os.path.dirname(base_output_dir) or ".")

    logs = [t["title"]]
    file_contents = {}
    actions = []

    try:
        # R-squared Analysis
        inner_summary = plspm_model.inner_summary()
        r_squared_df = inner_summary[['r_squared']]
        r_squared_filename = os.path.join(rel_output_dir, "r_squared.csv")
        file_contents[r_squared_filename] = r_squared_df.to_csv()
        logs.append(t["r_squared_table"].format(filename=r_squared_filename))

        logs.append(t["explained_variance"])
        for idx, row in inner_summary.iterrows():
            val = row['r_squared']
            if val > 0.75:
                interpretation = t["strong"]
            elif val > 0.50:
                interpretation = t["moderate"]
            elif val > 0.25:
                interpretation = t["weak"]
            else:
                interpretation = t["very_weak"]
            logs.append(t["construct_r_squared"].format(construct=idx, value=val, interpretation=interpretation))

        # Path Coefficients Analysis
        path_coef = plspm_model.path_coefficients()
        path_coef_filename = os.path.join(rel_output_dir, "structural_path_coefficients.csv")
        file_contents[path_coef_filename] = path_coef.to_csv()
        logs.append(t["path_coefficients_table"].format(filename=path_coef_filename))

        logs.append(t["structural_relationships"])
        for idx, row in path_coef.iterrows():
            for col in path_coef.columns:
                if idx != col and path_coef.loc[idx, col] != 0:
                    coef = path_coef.loc[idx, col]
                    if abs(coef) > 0.35:
                        effect_size = t["large"]
                    elif abs(coef) > 0.15:
                        effect_size = t["medium"]
                    else:
                        effect_size = t["small"]
                    logs.append(t["path_relationship"].format(source=idx, target=col, coef=coef, effect_size=effect_size))

    except Exception as e:
        logs.append(t["analysis_error"].format(error=str(e)))

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

    return ToolOutput(results={}, logs=logs, file_contents=file_contents, action=actions if actions else None)


def check_data_variance(
    data: pd.DataFrame,
    variables: list[Variable],
    language: str = "en"
) -> tuple[bool, list[str]]:
    """
    Check if the data has sufficient variance for PLS-SEM analysis.

    Returns:
        tuple: (is_valid, warnings_list) where is_valid is True if data has variance,
               and warnings_list contains warning messages for problematic variables
    """
    translations = {
        "en": {
            "zero_variance": "**ERROR**: Variable '{var}' has zero variance (all values are identical). PLS-SEM requires variance in the data.\n",
            "low_variance": "**WARNING**: Variable '{var}' has very low variance (std={std:.6f}). This may cause numerical instability.\n",
            "constant_data": "**ERROR**: All variables have constant values. Please check your data - PLS-SEM cannot be performed on data without variance.\n",
            "identical_rows": "**WARNING**: {n_unique} unique rows out of {n_total} total rows detected. Your data may have insufficient variability.\n"
        },
        "vi": {
            "zero_variance": "**LỖI**: Biến '{var}' có phương sai bằng 0 (tất cả giá trị giống nhau). PLS-SEM yêu cầu có sự biến thiên trong dữ liệu.\n",
            "low_variance": "**CẢNH BÁO**: Biến '{var}' có phương sai rất thấp (std={std:.6f}). Điều này có thể gây mất ổn định số học.\n",
            "constant_data": "**LỖI**: Tất cả các biến có giá trị không đổi. Vui lòng kiểm tra dữ liệu - không thể thực hiện PLS-SEM trên dữ liệu không có sự biến thiên.\n",
            "identical_rows": "**CẢNH BÁO**: Phát hiện {n_unique} hàng duy nhất trên tổng số {n_total} hàng. Dữ liệu của bạn có thể thiếu tính đa dạng.\n"
        }
    }

    t = get_t_dict(translations.get(language, translations["en"]), language=language)
    warnings = []

    # Get observed variables used in the model
    observed_vars = [var.code for var in variables
                     if var.variable_type == VariableType.OBSERVED and var.parent_code]

    # Filter to only variables that exist in data
    observed_vars = [var for var in observed_vars if var in data.columns]

    if not observed_vars:
        return True, warnings

    # Check for zero variance
    zero_variance_vars = []
    low_variance_vars = []

    for var in observed_vars:
        try:
            var_std = data[var].std()
            if pd.isna(var_std) or var_std == 0:
                zero_variance_vars.append(var)
                warnings.append(t["zero_variance"].format(var=var))
            elif var_std < 1e-10:
                low_variance_vars.append(var)
                warnings.append(t["low_variance"].format(var=var, std=var_std))
        except Exception:
            # If we can't calculate std, it's likely a data issue
            zero_variance_vars.append(var)
            warnings.append(t["zero_variance"].format(var=var))

    # Check for duplicate rows
    n_total = len(data)
    n_unique = data[observed_vars].drop_duplicates().shape[0]

    if n_unique < n_total * 0.5:  # Less than 50% unique rows
        warnings.append(t["identical_rows"].format(n_unique=n_unique, n_total=n_total))

    # Check if all data is constant
    if len(zero_variance_vars) == len(observed_vars):
        warnings.append(t["constant_data"])
        return False, warnings

    # If we have any zero variance variables, it's invalid
    if zero_variance_vars:
        return False, warnings

    return True, warnings


def run_pls_sem_analysis(
    data: pd.DataFrame,
    variables: list[Variable],
    params: dict
) -> ToolOutput:
    """
    Performs complete PLS-SEM analysis including data assessment, model fitting,
    and evaluation of measurement and structural models.

    Parameters:
        data: Input DataFrame containing the data
        variables: list of Variable objects describing the data columns
        params: dictionary containing analysis parameters
            - structural_paths (list[tuple[str, str]]): required structural relationships between latent variables
            - output_dir (str): base output directory name (default: "pls_sem_analysis")
            - save_files (bool): whether to save generated files to disk (default: False)
            - n_boot (int): number of bootstrap iterations for significance testing (default: 0)
            - language (str): language for output messages - "en" or "vi" (default: "en")

    Returns:
        ToolOutput: Contains results, logs, file contents, and suggested actions
    """
    # Extract parameters
    structural_paths = params.get("structural_paths", [])
    base_output_dir = params.get("output_dir", "pls_sem_analysis")
    save_files = params.get("save_files", False)
    n_boot = params.get("n_boot", 0)

    # Translation dictionary
    translations = {
        "en": {
            "title": "# PLS-SEM Analysis\n\n",
            "path_diagram": "**Model Path Diagram:** `{filename}`\n\n",
            "path_diagram_error": "Path diagram could not be generated: {error}\n\n",
            "no_paths_error": "Structural paths must be provided for the analysis. Please define the relationships between latent variables in the 'structural_paths' parameter.",
            "invalid_path_error": "Path at index {index} is invalid: {path}. Must be a list/tuple of 2 strings [source, target].",
            "empty_path_error": "Path at index {index} contains empty strings: {path}. Both Source and Target variables must be named.",
            "model_fit_failed": "\n**Model Fitting Failed:** No latent variables could be constructed. This typically occurs when indicator variables are not found in the dataset. Please verify data and variable definitions.\n",
            "model_estimated_bootstrap": "\n**Model Estimation:** PLS-SEM model fitted with {n_boot} bootstrap iterations for significance testing.\n",
            "model_estimated_no_bootstrap": "\n**Model Estimation:** PLS-SEM model fitted without bootstrap.\n",
            "model_fit_error": "\n**Model Fitting Failed:** {error}\n",
            "quality_title": "## Overall Model Quality Assessment\n",
            "avg_r_squared": "**Average R² (Explained Variance):** {value:.3f}\n",
            "overall_quality": "**Overall Model Quality:** {quality} explanatory power\n",
            "gof": "**Goodness of Fit Index:** {value:.3f}\n",
            "bootstrap_results": "**Bootstrap Path Results:** `{filename}`\n",
            "bootstrap_error": "Bootstrap results could not be generated: {error}\n",
            "quality_error": "Model quality assessment could not be completed: {error}\n",
            "variance_check_failed": "\n**Data Validation Failed:** Cannot proceed with PLS-SEM analysis due to insufficient variance in the data. Please ensure your data has sufficient variability (all variables should not have identical values).\n",
            "missing_data_error": "\n**Model Fitting Failed:** The model encountered NaN or Inf values during calculation. This typically occurs when:\n- Variables have zero or very low variance (all or most values are identical)\n- Data contains duplicate rows with identical values\n- Factor scores cannot be properly calculated due to data quality issues\n\nPlease check your data for sufficient variability and remove any duplicate or constant-value rows.\n",
            "strong": "strong",
            "moderate": "moderate",
            "weak": "weak"
        },
        "vi": {
            "title": "# Phân Tích PLS-SEM\n\n",
            "path_diagram": "**Sơ Đồ Đường Dẫn Mô Hình:** `{filename}`\n\n",
            "path_diagram_error": "Không thể tạo sơ đồ đường dẫn: {error}\n\n",
            "no_paths_error": "Phải cung cấp đường dẫn cấu trúc cho phân tích. Vui lòng định nghĩa các mối quan hệ giữa các biến tiềm ẩn trong tham số 'structural_paths'.",
            "invalid_path_error": "Đường dẫn tại chỉ số {index} không hợp lệ: {path}. Phải là danh sách/tuple gồm 2 chuỗi [nguồn, đích].",
            "empty_path_error": "Đường dẫn tại chỉ số {index} chứa chuỗi rỗng: {path}. Cả biến Nguồn và Đích đều phải được đặt tên.",
            "model_fit_failed": "\n**Ước Lượng Mô Hình Thất Bại:** Không thể xây dựng biến tiềm ẩn nào. Điều này thường xảy ra khi không tìm thấy các biến chỉ báo trong tập dữ liệu. Vui lòng kiểm tra dữ liệu và định nghĩa biến.\n",
            "model_estimated_bootstrap": "\n**Ước Lượng Mô Hình:** Mô hình PLS-SEM đã được ước lượng với {n_boot} lần lặp bootstrap để kiểm định ý nghĩa.\n",
            "model_estimated_no_bootstrap": "\n**Ước Lượng Mô Hình:** Mô hình PLS-SEM đã được ước lượng không có bootstrap.\n",
            "model_fit_error": "\n**Ước Lượng Mô Hình Thất Bại:** {error}\n",
            "quality_title": "## Đánh Giá Chất Lượng Mô Hình Tổng Thể\n",
            "avg_r_squared": "**R² Trung Bình (Phương Sai Được Giải Thích):** {value:.3f}\n",
            "overall_quality": "**Chất Lượng Mô Hình Tổng Thể:** sức mạnh giải thích {quality}\n",
            "gof": "**Chỉ Số Độ Phù Hợp:** {value:.3f}\n",
            "bootstrap_results": "**Kết Quả Bootstrap Đường Dẫn:** `{filename}`\n",
            "bootstrap_error": "Không thể tạo kết quả bootstrap: {error}\n",
            "quality_error": "Không thể hoàn thành đánh giá chất lượng mô hình: {error}\n",
            "variance_check_failed": "\n**Xác Thực Dữ Liệu Thất Bại:** Không thể tiến hành phân tích PLS-SEM do dữ liệu thiếu sự biến thiên. Vui lòng đảm bảo dữ liệu của bạn có đủ tính đa dạng (các biến không nên có giá trị giống hệt nhau).\n",
            "missing_data_error": "\n**Ước Lượng Mô Hình Thất Bại:** Mô hình gặp phải giá trị NaN hoặc Inf trong quá trình tính toán. Điều này thường xảy ra khi:\n- Các biến có phương sai bằng 0 hoặc rất thấp (tất cả hoặc hầu hết các giá trị giống nhau)\n- Dữ liệu chứa các hàng trùng lặp với giá trị giống hệt nhau\n- Không thể tính toán điểm số yếu tố đúng cách do vấn đề chất lượng dữ liệu\n\nVui lòng kiểm tra dữ liệu của bạn để đảm bảo có đủ tính đa dạng và loại bỏ các hàng trùng lặp hoặc có giá trị không đổi.\n",
            "strong": "mạnh",
            "moderate": "trung bình",
            "weak": "yếu"
        }
    }

    language = params.get("language", "en")
    t = get_t_dict(translations.get(language, translations["en"]), language=language)

    # Setup output directory with timestamp
    now = datetime.now()
    timestamp = f"{now.microsecond // 10000:02d}"
    output_dir = os.path.join(os.path.dirname(base_output_dir) or ".", f"{timestamp}_{os.path.basename(base_output_dir)}")
    rel_output_dir = os.path.relpath(output_dir, start=os.path.dirname(base_output_dir) or ".")

    logs = [t["title"]]
    file_contents = {}
    actions = []

    # Validate required parameters
    if not structural_paths:
        raise ValueError(t["no_paths_error"])

    # Check for malformed paths (empty strings or incorrect length)
    for i, path in enumerate(structural_paths):
        if len(path) != 2:
            raise ValueError(t["invalid_path_error"].format(index=i, path=path))
        if not path[0] or not path[1]:
            raise ValueError(t["empty_path_error"].format(index=i, path=path))

    # Process variables - ensure measurement types are set
    variables_processed = copy.deepcopy(variables)
    for var in variables_processed:
        if var.variable_type == VariableType.LATENT:
            if 'measurement_type' not in var.properties:
                var.properties['measurement_type'] = 'reflective'

    # Generate path diagram
    try:
        diagram_filename, diagram_base64 = draw_sem_path_diagram(variables=variables_processed, structural_paths=structural_paths, rel_output_dir=rel_output_dir)
        if diagram_filename and diagram_base64:
            file_contents[diagram_filename] = diagram_base64
            logs.append(t["path_diagram"].format(filename=diagram_filename))
    except Exception as e:
        logs.append(t["path_diagram_error"].format(error=str(e)))

    # Data suitability assessment
    suitability_output = assess_data_suitability_for_pls_sem(data, variables_processed, params)
    logs.extend(suitability_output.logs)
    file_contents.update(suitability_output.file_contents)
    if suitability_output.action:
        actions.extend(suitability_output.action)

    # Check data variance before model fitting
    is_valid, variance_warnings = check_data_variance(data, variables_processed, language)
    if variance_warnings:
        logs.extend(variance_warnings)
    if not is_valid:
        logs.append(t["variance_check_failed"])
        return ToolOutput(results={}, logs=logs, file_contents=file_contents, action=actions)

    # Model fitting
    try:
        config = build_plspm_config(variables_processed, structural_paths, data)

        if not config._Config__mvs:
            logs.append(t["model_fit_failed"])
            return ToolOutput(results={}, logs=logs, file_contents=file_contents, action=actions)

        if n_boot > 0:
            plspm_model = Plspm(data, config, Scheme.CENTROID, bootstrap=True, bootstrap_iterations=n_boot)
            logs.append(t["model_estimated_bootstrap"].format(n_boot=n_boot))
        else:
            plspm_model = Plspm(data, config, Scheme.CENTROID, bootstrap=False)
            logs.append(t["model_estimated_no_bootstrap"])

    except MissingDataError as e:
        # This specific error occurs when factor scores contain NaN or Inf values
        # Usually caused by insufficient variance or problematic data patterns
        logs.append(t["missing_data_error"])
        # print(f"Traceback: {traceback.format_exc()}")
        return ToolOutput(results={}, logs=logs, file_contents=file_contents, action=actions)
    except Exception as e:
        logs.append(t["model_fit_error"].format(error=str(e)))
        print(f"Traceback: {traceback.format_exc()}")
        return ToolOutput(results={}, logs=logs, file_contents=file_contents, action=actions)

    # Measurement model analysis
    measurement_output = analyze_pls_sem_measurement_model(plspm_model, variables_processed, params, data)
    logs.extend(measurement_output.logs)
    file_contents.update(measurement_output.file_contents)
    if measurement_output.action:
        actions.extend(measurement_output.action)

    # Structural model analysis
    structural_output = analyze_pls_sem_structural_model(plspm_model, params)
    logs.extend(structural_output.logs)
    file_contents.update(structural_output.file_contents)
    if structural_output.action:
        actions.extend(structural_output.action)

    # Model quality summary
    try:
        inner_summary = plspm_model.inner_summary()

        # Overall model quality assessment
        logs.append(t["quality_title"])

        # Average R-squared
        avg_r_squared = inner_summary['r_squared'].mean()
        logs.append(t["avg_r_squared"].format(value=avg_r_squared))

        if avg_r_squared > 0.67:
            model_quality = t["strong"]
        elif avg_r_squared > 0.33:
            model_quality = t["moderate"]
        else:
            model_quality = t["weak"]

        logs.append(t["overall_quality"].format(quality=model_quality))

        # Model fit indices if available
        if hasattr(plspm_model, 'gof'):
            try:
                gof = plspm_model.gof()
                logs.append(t["gof"].format(value=gof))
            except:
                pass

        # Bootstrap results if available
        if n_boot > 0:
            try:
                bootstrap_results = plspm_model.bootstrap_paths()
                bootstrap_filename = os.path.join(rel_output_dir, "bootstrap_path_results.csv")
                file_contents[bootstrap_filename] = bootstrap_results.to_csv()
                logs.append(t["bootstrap_results"].format(filename=bootstrap_filename))
            except Exception as e:
                logs.append(t["bootstrap_error"].format(error=str(e)))

    except Exception as e:
        logs.append(t["quality_error"].format(error=str(e)))

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

    return ToolOutput(
        results=serialize_dict({
            "model_quality": model_quality if 'model_quality' in locals() else "unknown",
            "avg_r_squared": avg_r_squared if 'avg_r_squared' in locals() else 0,
            "measurement": measurement_output.results,
            "structural": structural_output.results,
            "n_latent_variables": len([v for v in variables_processed if v.variable_type == VariableType.LATENT]),
            "n_indicators": len([v for v in variables_processed if v.variable_type == VariableType.OBSERVED and v.parent_code]),
            "bootstrap_iterations": n_boot
        }),
        logs=logs,
        file_contents=file_contents,
        action=actions if actions else None
    )
                                       
######################################################
######################## GSCA ########################
######################################################
def convert_paths_to_formula_strings(structural_paths: list[tuple[str, str]]) -> list[str]:
    """
    Converts a list of (source, target) tuples into a list of formula strings
    (e.g., 'target ~ source1 + source2').

    Args:
        structural_paths: A list of tuples, where each tuple is ('source', 'target').

    Returns:
        A list of R-style formula strings.
    """
    # Group sources by their common target
    paths_by_target = defaultdict(list)
    for source, target in structural_paths:
        paths_by_target[target].append(source)

    # Build the formula strings
    formula_strings = []
    for target, sources in paths_by_target.items():
        # Sort sources for consistent output
        sorted_sources = sorted(sources)
        formula = f"{target} ~ {' + '.join(sorted_sources)}"
        formula_strings.append(formula)

    return sorted(formula_strings)  # Sort final list for consistency


def build_gsca_model_spec(variables: list[Variable], structural_paths: Optional[list[str]] = None) -> str:
    """
    Builds GSCA model specification string from variables and structural paths.
    
    Args:
        variables: list of Variable objects
        structural_paths: Optional list of structural path formula strings
    
    Returns:
        Complete GSCA model specification string
    """
    latents = [var for var in variables if var.variable_type == VariableType.LATENT]
    observed_per_latent = {
        latent.code: [v.code for v in variables if v.parent_code == latent.code and v.variable_type == VariableType.OBSERVED]
        for latent in latents
    }
    
    model_lines = []
    
    # Measurement model
    for latent in latents:
        observed_vars = observed_per_latent[latent.code]
        if not observed_vars:
            continue
        # Changed default from 'formative' to 'reflective'
        measurement_type = latent.properties.get('measurement_type', 'reflective')
        operator = '=~'
        indicator_type = '(1)' if measurement_type == 'reflective' else '(0)'
        line = f"{latent.code}{indicator_type} {operator} " + " + ".join(observed_vars)
        model_lines.append(line)
    
    # Structural model (only included if provided)
    if structural_paths:
        model_lines.extend(structural_paths)
    
    return "\n".join(model_lines)


def assess_data_suitability_for_gsca(
    data: pd.DataFrame,
    variables: list[Variable],
    params: dict
) -> ToolOutput:
    """
    Assess data suitability for GSCA analysis including sample size, missing values, and multicollinearity.

    Parameters:
        data: Input DataFrame containing the data
        variables: list of Variable objects describing the data columns
        params: dictionary containing analysis parameters
            - output_dir (str): base output directory name (default: "gsca_analysis")
            - save_files (bool): whether to save generated files to disk
            - language (str): language for output messages - "en" or "vi" (default: "en")

    Returns:
        ToolOutput: Contains assessment results, content for report, file contents, and suggested actions
    """
    # Extract parameters
    base_output_dir = params.get("output_dir", "gsca")
    save_files = params.get("save_files", False)

    # Translation dictionary
    translations = {
        "en": {
            "title": "## Data Suitability Assessment for GSCA",
            "no_observed_error": "**ERROR**: No observed variables linked to latent constructs found.",
            "sample_size_title": "**Sample Size Analysis**",
            "current_sample": "- Current sample size: {n}",
            "required_sample": "- Required sample size: ≥ {required_n} (10 × {max_obs} indicators for '{most_complex_construct}')",
            "sample_warning": "- **Warning**: Sample size {n} < {required_n}. Results may be unstable.",
            "sample_adequate": "- Sample size is adequate for GSCA analysis.",
            "missing_title": "**Missing Values Analysis**",
            "missing_detected": "- Missing values detected in {len_missing_vars} variables:",
            "missing_item": "  - {var}: {count} missing values ({pct})",
            "missing_none": "**Missing Values Analysis**: No missing values detected.",
            "corr_title": "**Correlation Analysis**",
            "corr_matrix": "- Correlation matrix of observed variables: `{corr_filename}`",
            "low_corr": "- Low correlations (< 0.3) detected in {len_low_corr_pairs} indicator pairs.",
            "high_corr": "- **Warning**: High correlations (> 0.8) detected in {len_high_corr_pairs} pairs, indicating possible multicollinearity.",
            "vif_title": "**VIF Assessment for Formative Constructs**",
            "vif_construct": "- {latent_code} construct:",
            "vif_item": "  - {var}: VIF = {vif}",
            "vif_warning": "  - **Warning**: High VIF (> 5) detected in '{latent_code}' for: {vars}",
            "action_sample_comment": "Collect more data or simplify the model",
            "action_missing_comment": "Impute or remove missing values",
            "action_vif_comment": "Consider removing to reduce multicollinearity",
            "action_issue_sample_size": "Sample size {n} < {required_n}",
            "action_issue_missing_values": "Missing values in data",
            "action_issue_vif": "High VIF ({vif:.2f} > 5) for {var}"
        },
        "vi": {
            "title": "## Đánh Giá Tính Phù Hợp Dữ Liệu cho GSCA",
            "no_observed_error": "**LỖI**: Không tìm thấy biến quan sát nào được liên kết với cấu trúc tiềm ẩn.",
            "sample_size_title": "**Phân Tích Cỡ Mẫu**",
            "current_sample": "- Cỡ mẫu hiện tại: {n}",
            "required_sample": "- Cỡ mẫu yêu cầu: ≥ {required_n} (10 × {max_obs} chỉ báo cho '{most_complex_construct}')",
            "sample_warning": "- **Cảnh báo**: Cỡ mẫu {n} < {required_n}. Kết quả có thể không ổn định.",
            "sample_adequate": "- Cỡ mẫu đủ cho phân tích GSCA.",
            "missing_title": "**Phân Tích Giá Trị Thiếu**",
            "missing_detected": "- Phát hiện giá trị thiếu trong {len_missing_vars} biến:",
            "missing_item": "  - {var}: {count} giá trị thiếu ({pct})",
            "missing_none": "**Phân Tích Giá Trị Thiếu**: Không phát hiện giá trị thiếu.",
            "corr_title": "**Phân Tích Tương Quan**",
            "corr_matrix": "- Ma trận tương quan của biến quan sát: `{corr_filename}`",
            "low_corr": "- Phát hiện tương quan thấp (< 0.3) trong {len_low_corr_pairs} cặp chỉ báo.",
            "high_corr": "- **Cảnh báo**: Phát hiện tương quan cao (> 0.8) trong {len_high_corr_pairs} cặp, cho thấy khả năng đa cộng tuyến.",
            "vif_title": "**Đánh Giá VIF cho Cấu Trúc Hình Thành**",
            "vif_construct": "- Cấu trúc {latent_code}:",
            "vif_item": "  - {var}: VIF = {vif}",
            "vif_warning": "  - **Cảnh báo**: Phát hiện VIF cao (> 5) trong '{latent_code}' cho: {vars}",
            "action_sample_comment": "Thu thập thêm dữ liệu hoặc đơn giản hóa mô hình",
            "action_missing_comment": "Điền giá trị thiếu hoặc loại bỏ",
            "action_vif_comment": "Xem xét loại bỏ để giảm đa cộng tuyến",
            "action_issue_sample_size": "Cỡ mẫu {n} < {required_n}",
            "action_issue_missing_values": "Dữ liệu có giá trị thiếu",
            "action_issue_vif": "VIF cao ({vif:.2f} > 5) cho biến {var}"
        }
    }

    language = params.get("language", "en")
    t = get_t_dict(translations.get(language, translations["en"]), language=language)
    
    # Setup output directory and timestamp
    now = datetime.now()
    timestamp = f"{now.microsecond // 10000:02d}"
    output_dir = os.path.join(os.path.dirname(base_output_dir) or ".", f"{timestamp}_{os.path.basename(base_output_dir)}")
    rel_output_dir = os.path.relpath(output_dir, start=os.path.dirname(base_output_dir) or ".")
    
    logs = [t["title"]]
    file_contents = {}
    actions = []

    observed_vars = [var.code for var in variables if var.variable_type == VariableType.OBSERVED and var.parent_code]
    if not observed_vars:
        logs.append(t["no_observed_error"])
        return ToolOutput(results={}, logs=logs, file_contents={}, action=None)

    latents = [var for var in variables if var.variable_type == VariableType.LATENT]
    observed_per_latent = {
        latent.code: [v.code for v in variables if v.parent_code == latent.code and v.variable_type == VariableType.OBSERVED]
        for latent in latents
    }
    max_obs = max(len(obs) for obs in observed_per_latent.values()) if observed_per_latent else 0
    most_complex_construct = max(observed_per_latent, key=lambda k: len(observed_per_latent[k]), default=None)

    # Sample size assessment
    n = len(data)
    required_n = max(10 * max_obs, 30)
    logs.append(t["sample_size_title"])
    logs.append(t["current_sample"].format(n=n))
    logs.append(t["required_sample"].format(required_n=required_n, max_obs=max_obs, most_complex_construct=most_complex_construct))

    if n < required_n:
        logs.append(t["sample_warning"].format(n=n, required_n=required_n))
        actions.append(Action(
            action_type=ActionType.RECHECK_DATA,
            method="assess_data_suitability_for_gsca",
            issue=t["action_issue_sample_size"].format(n=n, required_n=required_n),
            comment=t["action_sample_comment"],
            status="pending"
        ))
    else:
        logs.append(t["sample_adequate"])

    # Missing values check
    if data[observed_vars].isnull().any().any():
        missing_counts = data[observed_vars].isnull().sum()
        missing_vars = missing_counts[missing_counts > 0]
        logs.append(t["missing_title"])
        logs.append(t["missing_detected"].format(len_missing_vars=len(missing_vars)))
        for var, count in missing_vars.items():
            logs.append(t["missing_item"].format(var=var, count=count, pct=f"{count/n:.1%}"))
        actions.append(Action(
            action_type=ActionType.HANDLE_MISSING_VALUES,
            method="assess_data_suitability_for_gsca",
            issue=t["action_issue_missing_values"],
            comment=t["action_missing_comment"],
            status="pending",
            action_params={"variables": observed_vars}
        ))
    else:
        logs.append(t["missing_none"])

    # Correlation analysis
    corr = data[observed_vars].corr()
    corr_filename = os.path.join(rel_output_dir, "correlation_matrix.csv")
    file_contents[corr_filename] = corr.to_csv(index=True)
    logs.append(t["corr_title"])
    logs.append(t["corr_matrix"].format(corr_filename=corr_filename))

    low_corr_pairs = [(v1, v2) for v1 in observed_vars for v2 in observed_vars if v1 < v2 and abs(corr.loc[v1, v2]) < 0.3]
    high_corr_pairs = [(v1, v2) for v1 in observed_vars for v2 in observed_vars if v1 < v2 and abs(corr.loc[v1, v2]) > 0.8]

    if low_corr_pairs:
        logs.append(t["low_corr"].format(len_low_corr_pairs=len(low_corr_pairs)))
    if high_corr_pairs:
        logs.append(t["high_corr"].format(len_high_corr_pairs=len(high_corr_pairs)))

    # VIF check for formative constructs only
    formative_latents = [latent for latent in latents if latent.properties.get('measurement_type', 'reflective') == 'formative']
    if formative_latents:
        logs.append(t["vif_title"])
        for latent in formative_latents:
            formative_vars = observed_per_latent[latent.code]
            if len(formative_vars) > 1:
                logs.append(t["vif_construct"].format(latent_code=latent.code))
                vif_data = {}
                for var in formative_vars:
                    other_vars = [v for v in formative_vars if v != var]
                    model = OLS(data[var], add_constant(data[other_vars])).fit()
                    r2 = model.rsquared
                    vif = 1 / (1 - r2) if r2 < 1 else float('inf')
                    vif_data[var] = vif
                    logs.append(t["vif_item"].format(var=var, vif=f"{vif:.2f}"))

                high_vif_vars = [var for var, vif in vif_data.items() if vif > 5]
                if high_vif_vars:
                    logs.append(t["vif_warning"].format(latent_code=latent.code, vars=', '.join(high_vif_vars)))
                    for var in high_vif_vars:
                        actions.append(Action(
                            action_type=ActionType.REMOVE_VARIABLE,
                            method="assess_data_suitability_for_gsca",
                            issue=t["action_issue_vif"].format(vif=vif_data[var], var=var),
                            comment=t["action_vif_comment"],
                            status="pending",
                            action_params={'variable': var}
                        ))

    # Save files if requested
    if save_files:
        os.makedirs(output_dir, exist_ok=True)
        for filename, content in file_contents.items():
            save_path = os.path.join(output_dir, os.path.basename(filename))
            if filename.endswith((".csv", ".txt")):
                with open(save_path, "w", encoding="utf-8") as f:
                    f.write(str(content))

    return ToolOutput(
        results={"sample_size": n, "required_n": required_n},
        logs=logs,
        file_contents=file_contents,
        action=actions if actions else None
    )


def analyze_gsca_measurement_model(
    gsca_result: dict,
    variables: list[Variable],
    data: pd.DataFrame,
    params: dict
) -> ToolOutput:
    """
    Analyze GSCA measurement model including reliability, validity, and factor loadings/weights.

    Parameters:
        gsca_result: dictionary containing GSCA analysis results
        variables: list of Variable objects describing the data columns
        data: Input DataFrame containing the data
        params: dictionary containing analysis parameters
            - output_dir (str): base output directory name (default: "gsca_analysis")
            - save_files (bool): whether to save generated files to disk
            - language (str): language for output messages - "en" or "vi" (default: "en")

    Returns:
        ToolOutput: Contains measurement model analysis results, content for report, file contents, and suggested actions
    """
    # Extract parameters
    base_output_dir = params.get("output_dir", "gsca_analysis")
    save_files = params.get("save_files", False)

    # Translation dictionary
    translations = {
        "en": {
            "title": "## Measurement Model Analysis",
            "construct_title": "**{latent_code} ({measurement_type} Construct)**",
            "reliability_metrics": "- Reliability and Validity Metrics:",
            "cronbach_alpha": "  - Cronbach's Alpha: {alpha} (≥ 0.7 desired)",
            "composite_reliability": "  - Composite Reliability (CR): {cr} (≥ 0.7 required)",
            "ave": "  - Average Variance Extracted (AVE): {ave} (≥ 0.5 required)",
            "reliability_warning": "  - **Warning**: Reliability or validity issues detected for '{latent_code}'",
            "factor_loadings": "- Factor Loadings:",
            "loading_weak": " (weak, consider removing)",
            "loading_acceptable": " (acceptable)",
            "loading_good": " (good)",
            "indicator_weights": "- Indicator Weights:",
            "weight_very_weak": " (very weak)",
            "weight_weak": " (weak)",
            "weight_significant": " (significant)",
            "vif_analysis": "- VIF Analysis:",
            "vif_high": " (high multicollinearity)",
            "vif_acceptable": " (acceptable)",
            "loadings_table": "**Factor Loadings Table (Reflective Constructs)**: `{loadings_filename}`",
            "weights_table": "**Indicator Weights Table (Formative Constructs)**: `{weights_filename}`",
            "reliability_summary": "**Reliability and Validity Summary**: `{reliability_filename}`",
            "overall_fit": "**Overall Measurement Model Fit**",
            "fit_m": "- FIT_M: {fitm} (≥ 0.36 desired)",
            "fit_poor": "- **Note**: FIT_M < 0.36 suggests poor measurement model fit",
            "action_loading_comment": "Low contribution to '{latent_code}'",
            "action_vif_comment": "Reduce multicollinearity in '{latent_code}'",
            "action_issue_low_loading": "Loading {loading:.3f} < 0.5 for {var}",
            "action_issue_high_vif": "High VIF ({vif:.2f} > 5) for {var}"
        },
        "vi": {
            "title": "## Phân Tích Mô Hình Đo Lường",
            "construct_title": "**{latent_code} (Cấu Trúc {measurement_type})**",
            "reliability_metrics": "- Các Chỉ Số Độ Tin Cậy và Giá Trị:",
            "cronbach_alpha": "  - Cronbach's Alpha: {alpha} (≥ 0.7 mong muốn)",
            "composite_reliability": "  - Độ Tin Cậy Tổng Hợp (CR): {cr} (≥ 0.7 yêu cầu)",
            "ave": "  - Phương Sai Trích Trung Bình (AVE): {ave} (≥ 0.5 yêu cầu)",
            "reliability_warning": "  - **Cảnh báo**: Phát hiện vấn đề về độ tin cậy hoặc giá trị cho '{latent_code}'",
            "factor_loadings": "- Hệ Số Tải Nhân Tố:",
            "loading_weak": " (yếu, xem xét loại bỏ)",
            "loading_acceptable": " (chấp nhận được)",
            "loading_good": " (tốt)",
            "indicator_weights": "- Trọng Số Chỉ Báo:",
            "weight_very_weak": " (rất yếu)",
            "weight_weak": " (yếu)",
            "weight_significant": " (có ý nghĩa)",
            "vif_analysis": "- Phân Tích VIF:",
            "vif_high": " (đa cộng tuyến cao)",
            "vif_acceptable": " (chấp nhận được)",
            "loadings_table": "**Bảng Hệ Số Tải Nhân Tố (Cấu Trúc Phản Ánh)**: `{loadings_filename}`",
            "weights_table": "**Bảng Trọng Số Chỉ Báo (Cấu Trúc Hình Thành)**: `{weights_filename}`",
            "reliability_summary": "**Tổng Hợp Độ Tin Cậy và Giá Trị**: `{reliability_filename}`",
            "overall_fit": "**Độ Phù Hợp Tổng Thể Mô Hình Đo Lường**",
            "fit_m": "- FIT_M: {fitm} (≥ 0.36 mong muốn)",
            "fit_poor": "- **Lưu ý**: FIT_M < 0.36 cho thấy mô hình đo lường kém phù hợp",
            "action_loading_comment": "Đóng góp thấp cho '{latent_code}'",
            "action_vif_comment": "Giảm đa cộng tuyến trong '{latent_code}'",
            "action_issue_low_loading": "Hệ số tải {loading:.3f} < 0.5 cho {var}",
            "action_issue_high_vif": "VIF cao ({vif:.2f} > 5) cho {var}"
        }
    }

    language = params.get("language", "en")
    t = get_t_dict(translations.get(language, translations["en"]), language=language)
    
    # Setup output directory and timestamp
    now = datetime.now()
    timestamp = f"{now.microsecond // 10000:02d}"
    output_dir = os.path.join(os.path.dirname(base_output_dir) or ".", f"{timestamp}_{os.path.basename(base_output_dir)}")
    rel_output_dir = os.path.relpath(output_dir, start=os.path.dirname(base_output_dir) or ".")
    
    logs = [t["title"]]
    file_contents = {}
    actions = []

    latents = [var for var in variables if var.variable_type == VariableType.LATENT]
    observed_per_latent = {
        latent.code: [v.code for v in variables if v.parent_code == latent.code and v.variable_type == VariableType.OBSERVED]
        for latent in latents
    }

    loadings_data = []
    weights_data = []
    reliability_data = []

    for latent in latents:
        latent_code = latent.code
        measurement_type = latent.properties.get('measurement_type', 'reflective')
        observed_vars = observed_per_latent[latent_code]
        if not observed_vars:
            continue

        logs.append(t["construct_title"].format(latent_code=latent_code, measurement_type=measurement_type.capitalize()))

        if measurement_type == 'reflective':
            # Reflective constructs: Assess reliability and validity
            alpha = gsca_result['alpha'].get(latent_code, 0.0)
            cr = gsca_result['rho'].get(latent_code, 0.0)
            ave = gsca_result['ave'].get(latent_code, 0.0)

            logs.append(t["reliability_metrics"])
            logs.append(t["cronbach_alpha"].format(alpha=f"{alpha:.3f}"))
            logs.append(t["composite_reliability"].format(cr=f"{cr:.3f}"))
            logs.append(t["ave"].format(ave=f"{ave:.3f}"))

            reliability_data.append({
                'Construct': latent_code,
                'Cronbach_Alpha': alpha,
                'Composite_Reliability': cr,
                'AVE': ave
            })

            if cr < 0.7 or ave < 0.5:
                logs.append(t["reliability_warning"].format(latent_code=latent_code))

            # Process loadings
            loadings_dict = gsca_result['loadings'].get(latent_code, {})
            logs.append(t["factor_loadings"])
            for var in observed_vars:
                loading = loadings_dict.get(var, 0)
                log_line = f"  - {var}: {loading:.3f}"
                if loading < 0.5:
                    log_line += t["loading_weak"]
                    logs.append(log_line)
                    actions.append(Action(
                        action_type=ActionType.REMOVE_VARIABLE,
                        method="analyze_gsca_measurement_model",
                        issue=t["action_issue_low_loading"].format(loading=loading, var=var),
                        comment=t["action_loading_comment"].format(latent_code=latent_code),
                        status="pending",
                        action_params={'variable': var}
                    ))
                elif loading < 0.7:
                    log_line += t["loading_acceptable"]
                    logs.append(log_line)
                else:
                    log_line += t["loading_good"]
                    logs.append(log_line)
                loadings_data.append({'Latent': latent_code, 'Indicator': var, 'Loading': loading})

        elif measurement_type == 'formative':
            # Formative constructs: Assess weights and multicollinearity
            weights_dict = gsca_result['weights'].get(latent_code, {})
            logs.append(t["indicator_weights"])
            for var in observed_vars:
                weight = weights_dict.get(var, 0)
                log_line = f"  - {var}: {weight:.3f}"
                if abs(weight) < 0.1:
                    log_line += t["weight_very_weak"]
                elif abs(weight) < 0.3:
                    log_line += t["weight_weak"]
                else:
                    log_line += t["weight_significant"]
                logs.append(log_line)
                weights_data.append({'Latent': latent_code, 'Indicator': var, 'Weight': weight})

            # Calculate VIF for formative constructs with multiple indicators
            if len(observed_vars) > 1:
                logs.append(t["vif_analysis"])
                vif_data = {}
                for var in observed_vars:
                    other_vars = [v for v in observed_vars if v != var]
                    model = OLS(data[var], add_constant(data[other_vars])).fit()
                    r2 = model.rsquared
                    vif = 1 / (1 - r2) if r2 < 1 else float('inf')
                    vif_data[var] = vif

                for var, vif in vif_data.items():
                    log_line = f"  - {var}: VIF = {vif:.2f}"
                    if vif > 5:
                        log_line += t["vif_high"]
                        logs.append(log_line)
                        actions.append(Action(
                            action_type=ActionType.REMOVE_VARIABLE,
                            method="analyze_gsca_measurement_model",
                            issue=t["action_issue_high_vif"].format(vif=vif, var=var),
                            comment=t["action_vif_comment"].format(latent_code=latent_code),
                            status="pending",
                            action_params={'variable': var}
                        ))
                    else:
                        log_line += t["vif_acceptable"]
                        logs.append(log_line)

    # Save analysis results
    if loadings_data:
        loadings_df = pd.DataFrame(loadings_data)
        loadings_pivot = loadings_df.pivot(index='Latent', columns='Indicator', values='Loading')
        loadings_filename = os.path.join(rel_output_dir, "factor_loadings.csv")
        file_contents[loadings_filename] = loadings_pivot.to_csv()
        logs.append(t["loadings_table"].format(loadings_filename=loadings_filename))

    if weights_data:
        weights_df = pd.DataFrame(weights_data)
        weights_pivot = weights_df.pivot(index='Latent', columns='Indicator', values='Weight')
        weights_filename = os.path.join(rel_output_dir, "indicator_weights.csv")
        file_contents[weights_filename] = weights_pivot.to_csv()
        logs.append(t["weights_table"].format(weights_filename=weights_filename))

    if reliability_data:
        reliability_df = pd.DataFrame(reliability_data)
        reliability_filename = os.path.join(rel_output_dir, "reliability_validity.csv")
        file_contents[reliability_filename] = reliability_df.to_csv(index=False)
        logs.append(t["reliability_summary"].format(reliability_filename=reliability_filename))

    # Overall measurement model fit
    fitm = gsca_result['fit_indices'].get('FIT_M', 0)
    logs.append(t["overall_fit"])
    logs.append(t["fit_m"].format(fitm=f"{fitm:.3f}"))
    if fitm < 0.36:
        logs.append(t["fit_poor"])

    # Save files if requested
    if save_files:
        os.makedirs(output_dir, exist_ok=True)
        for filename, content in file_contents.items():
            save_path = os.path.join(output_dir, os.path.basename(filename))
            if filename.endswith((".csv", ".txt")):
                with open(save_path, "w", encoding="utf-8") as f:
                    f.write(str(content))

    return ToolOutput(
        results={"reliability_data": reliability_data, "loadings_data": loadings_data, "weights_data": weights_data},
        logs=logs,
        file_contents=file_contents,
        action=actions if actions else None
    )


def analyze_gsca_structural_model(
    gsca_result: dict,
    params: dict
) -> ToolOutput:
    """
    Analyze GSCA structural model including path coefficients, R-squared values, and model fit indices.

    Parameters:
        gsca_result: dictionary containing GSCA analysis results
        params: dictionary containing analysis parameters
            - output_dir (str): base output directory name (default: "gsca_analysis")
            - save_files (bool): whether to save generated files to disk
            - language (str): language for output messages - "en" or "vi" (default: "en")

    Returns:
        ToolOutput: Contains structural model analysis results, content for report, file contents, and suggested actions
    """
    # Extract parameters
    base_output_dir = params.get("output_dir", "gsca_analysis")
    save_files = params.get("save_files", False)

    # Translation dictionary
    translations = {
        "en": {
            "title": "## Structural Model Analysis",
            "no_paths": "**Path Coefficients**: No structural paths specified (measurement model only)",
            "path_title": "**Path Coefficients**",
            "effect_weak": " (weak effect)",
            "effect_moderate": " (moderate effect)",
            "effect_strong": " (strong effect)",
            "paths_table": "**Path Coefficients Table**: `{paths_filename}`",
            "r2_title": "**Explained Variance (R²)**",
            "r2_very_low": " (very low explanatory power)",
            "r2_low": " (low explanatory power)",
            "r2_moderate": " (moderate explanatory power)",
            "r2_high": " (high explanatory power)",
            "r2_table": "**R-Squared Values Table**: `{r2_filename}`",
            "fit_title": "**Model Fit Indices**",
            "fit_poor": " (poor fit)",
            "fit_marginal": " (marginal fit)",
            "fit_good": " (good fit)",
            "fit_acceptable": " (acceptable fit)",
            "fit_measurement_poor": " (poor measurement model fit)",
            "fit_measurement_acceptable": " (acceptable measurement model fit)",
            "fit_table": "**Model Fit Indices Table**: `{fit_filename}`",
            "effect_sizes_title": "**Effect Sizes (Cohen's f²)**",
            "effect_sizes_table": "**Effect Sizes Table**: `{effect_filename}`"
        },
        "vi": {
            "title": "## Phân Tích Mô Hình Cấu Trúc",
            "no_paths": "**Hệ Số Đường Dẫn**: Không có đường dẫn cấu trúc nào được chỉ định (chỉ mô hình đo lường)",
            "path_title": "**Hệ Số Đường Dẫn**",
            "effect_weak": " (ảnh hưởng yếu)",
            "effect_moderate": " (ảnh hưởng trung bình)",
            "effect_strong": " (ảnh hưởng mạnh)",
            "paths_table": "**Bảng Hệ Số Đường Dẫn**: `{paths_filename}`",
            "r2_title": "**Phương Sai Giải Thích (R²)**",
            "r2_very_low": " (khả năng giải thích rất thấp)",
            "r2_low": " (khả năng giải thích thấp)",
            "r2_moderate": " (khả năng giải thích trung bình)",
            "r2_high": " (khả năng giải thích cao)",
            "r2_table": "**Bảng Giá Trị R-Squared**: `{r2_filename}`",
            "fit_title": "**Các Chỉ Số Độ Phù Hợp Mô Hình**",
            "fit_poor": " (phù hợp kém)",
            "fit_marginal": " (phù hợp biên)",
            "fit_good": " (phù hợp tốt)",
            "fit_acceptable": " (phù hợp chấp nhận được)",
            "fit_measurement_poor": " (mô hình đo lường phù hợp kém)",
            "fit_measurement_acceptable": " (mô hình đo lường phù hợp chấp nhận được)",
            "fit_table": "**Bảng Chỉ Số Độ Phù Hợp Mô Hình**: `{fit_filename}`",
            "effect_sizes_title": "**Kích Thước Hiệu Ứng (Cohen's f²)**",
            "effect_sizes_table": "**Bảng Kích Thước Hiệu Ứng**: `{effect_filename}`"
        }
    }

    language = params.get("language", "en")
    t = get_t_dict(translations.get(language, translations["en"]), language=language)
    
    # Setup output directory and timestamp
    now = datetime.now()
    timestamp = f"{now.microsecond // 10000:02d}"
    output_dir = os.path.join(os.path.dirname(base_output_dir) or ".", f"{timestamp}_{os.path.basename(base_output_dir)}")
    rel_output_dir = os.path.relpath(output_dir, start=os.path.dirname(base_output_dir) or ".")
    
    logs = [t["title"]]
    file_contents = {}
    actions = []

    # Path coefficients analysis
    if not gsca_result['paths']:
        logs.append(t["no_paths"])
    else:
        paths_data = []
        logs.append(t["path_title"])
        for (from_var, to_var), coef in gsca_result['paths'].items():
            paths_data.append({'From': from_var, 'To': to_var, 'Coefficient': coef})
            log_line = f"- {from_var} → {to_var}: {coef:.3f}"
            if abs(coef) < 0.1:
                log_line += t["effect_weak"]
            elif abs(coef) < 0.3:
                log_line += t["effect_moderate"]
            else:
                log_line += t["effect_strong"]
            logs.append(log_line)

        if paths_data:
            paths_df = pd.DataFrame(paths_data)
            paths_filename = os.path.join(rel_output_dir, "path_coefficients.csv")
            file_contents[paths_filename] = paths_df.to_csv(index=False)
            logs.append(t["paths_table"].format(paths_filename=paths_filename))

    # R-squared analysis
    logs.append(t["r2_title"])
    r2_data = []
    for latent, val in gsca_result['r_squared'].items():
        r2_data.append({'Construct': latent, 'R_Squared': val})
        log_line = f"- {latent}: R² = {val:.3f}"
        if val < 0.1:
            log_line += t["r2_very_low"]
        elif val < 0.25:
            log_line += t["r2_low"]
        elif val < 0.5:
            log_line += t["r2_moderate"]
        else:
            log_line += t["r2_high"]
        logs.append(log_line)

    if r2_data:
        r2_df = pd.DataFrame(r2_data)
        r2_filename = os.path.join(rel_output_dir, "r_squared_values.csv")
        file_contents[r2_filename] = r2_df.to_csv(index=False)
        logs.append(t["r2_table"].format(r2_filename=r2_filename))

    # Model fit indices
    logs.append(t["fit_title"])
    fit_data = []
    for name, value in gsca_result['fit_indices'].items():
        fit_data.append({'Index': name, 'Value': value})
        log_line = f"- {name}: {value:.3f}"

        if name in ['FIT', 'GFI']:
            if value < 0.36:
                log_line += t["fit_poor"]
            elif value < 0.5:
                log_line += t["fit_marginal"]
            else:
                log_line += t["fit_good"]
        elif name == 'SRMR':
            if value > 0.08:
                log_line += t["fit_poor"]
            elif value > 0.05:
                log_line += t["fit_acceptable"]
            else:
                log_line += t["fit_good"]
        elif name == 'FIT_M':
            if value < 0.36:
                log_line += t["fit_measurement_poor"]
            else:
                log_line += t["fit_measurement_acceptable"]
        logs.append(log_line)

    if fit_data:
        fit_df = pd.DataFrame(fit_data)
        fit_filename = os.path.join(rel_output_dir, "model_fit_indices.csv")
        file_contents[fit_filename] = fit_df.to_csv(index=False)
        logs.append(t["fit_table"].format(fit_filename=fit_filename))

    # Effect sizes analysis
    if gsca_result['effect_sizes']:
        logs.append(t["effect_sizes_title"])
        effect_data = []
        for construct, (f2, interpretation) in gsca_result['effect_sizes'].items():
            effect_data.append({'Construct': construct, 'Effect_Size_f2': f2, 'Interpretation': interpretation})
            logs.append(f"- {construct}: f² = {f2:.3f} ({interpretation})")

        if effect_data:
            effect_df = pd.DataFrame(effect_data)
            effect_filename = os.path.join(rel_output_dir, "effect_sizes.csv")
            file_contents[effect_filename] = effect_df.to_csv(index=False)
            logs.append(t["effect_sizes_table"].format(effect_filename=effect_filename))

    # Save files if requested
    if save_files:
        os.makedirs(output_dir, exist_ok=True)
        for filename, content in file_contents.items():
            save_path = os.path.join(output_dir, os.path.basename(filename))
            if filename.endswith((".csv", ".txt")):
                with open(save_path, "w", encoding="utf-8") as f:
                    f.write(str(content))

    return ToolOutput(
        results=serialize_dict({
            "paths": gsca_result['paths'],
            "r_squared": gsca_result['r_squared'],
            "effect_sizes": gsca_result['effect_sizes'],
            "fit_indices": gsca_result['fit_indices']
        }),
        logs=logs,
        file_contents=file_contents,
        action=actions if actions else None
    )


def run_gsca(data: pd.DataFrame, model_spec: str, n_boot: int = 100) -> dict[str, Any]:
    """
    Run GSCA analysis using the R `gesca` package via RPy2.

    Args:
        data: pandas DataFrame with observed variables.
        model_spec: GSCA model string like 'eta1(1) =~ X1 + X2 + X3'.
        n_boot: Number of bootstrap samples (0 = none).

    Returns:
        dictionary with GSCA results: loadings, weights, paths, r_squared, effect_sizes, fit_indices,
        ave, alpha, rho.
    """
    gesca = importr('gesca')
    base = importr('base')

    with ro.conversion.localconverter(ro.default_converter + pandas2ri.converter):
        r_df = ro.conversion.py2rpy(data)

    try:
        result = gesca.gesca_run(myModel=model_spec, data=r_df, nbt=n_boot)
        
        logger.info("Result keys: %s", list(result.names))

        wname = list(result.rx2('wname'))
        lname = list(result.rx2('lname'))
        WR = np.array(result.rx2('WR'))
        CR = np.array(result.rx2('CR'))
        BR = np.array(result.rx2('BR'))
        R2 = np.array(result.rx2('R2'))
        AVE = np.array(result.rx2('AVE'))
        Alpha = np.array(result.rx2('Alpha'))
        rho = np.array(result.rx2('rho'))

        weights = {}
        for i, lv in enumerate(lname):
            weights[lv] = {wname[j]: WR[j, i] for j in range(len(wname))}

        loadings = {}
        for i, lv in enumerate(lname):
            loadings[lv] = {wname[j]: CR[j, i] for j in range(len(wname))}

        paths = {}
        for i in range(len(lname)):
            for j in range(len(lname)):
                if BR[i, j] != 0:
                    paths[(lname[j], lname[i])] = BR[i, j]

        r_squared = {lname[i]: R2[0, i] for i in range(len(lname))}

        effect_sizes = {}
        for lv, r2 in r_squared.items():
            if r2 > 0:
                f2 = r2 / (1 - r2) if r2 < 1 else float('inf')
                if f2 >= 0.35:
                    interpretation = "large"
                elif f2 >= 0.15:
                    interpretation = "medium"
                elif f2 >= 0.02:
                    interpretation = "small"
                else:
                    interpretation = "negligible"
                effect_sizes[lv] = (f2, interpretation)
            else:
                effect_sizes[lv] = (0.0, "none")

        fit_indices = {
            'FIT': float(result.rx2('FIT')[0]),
            'FIT_M': float(result.rx2('FIT_M')[0]),
            'FIT_S': float(result.rx2('FIT_S')[0]),
            'AFIT': float(result.rx2('AFIT')[0]),
            'GFI': float(result.rx2('GFI')[0]),
            'SRMR': float(result.rx2('SRMR')[0])
        }

        ave = {lname[i]: float(AVE[0, i]) for i in range(len(lname))}
        alpha = {lname[i]: float(Alpha[0, i]) for i in range(len(lname))}
        rho = {lname[i]: float(rho[0, i]) for i in range(len(lname))}

        output = {
            "loadings": loadings,
            "weights": weights,
            "paths": paths,
            "r_squared": r_squared,
            "effect_sizes": effect_sizes,
            "fit_indices": fit_indices,
            "ave": ave,
            "alpha": alpha,
            "rho": rho
        }
        return output

    except Exception as e:
        logger.exception("Error running GSCA: %s", e)
        raise RuntimeError(f"GSCA execution failed: {e}")


def run_gsca_analysis(
    data: pd.DataFrame,
    variables: list[Variable],
    params: dict
) -> ToolOutput:
    """
    Perform comprehensive GSCA analysis including data assessment, model fitting, and evaluation.

    Parameters:
        data: Input DataFrame containing the data
        variables: list of Variable objects describing the data columns
        params: dictionary containing analysis parameters
            - structural_paths (list[tuple[str, str]]): list of (source, target) structural paths
            - output_dir (str): Base output directory name (default: "gsca_analysis")
            - save_files (bool): Whether to save generated files to disk (default: False)
            - n_boot (int): Number of bootstrap samples (default: 0)
            - language (str): language for output messages - "en" or "vi" (default: "en")

    Returns:
        ToolOutput: Contains GSCA results, analysis content, file contents, and suggested actions
    """
    # Extract parameters
    structural_paths_tuples = params.get("structural_paths", [])
    base_output_dir = params.get("output_dir", "gsca_analysis")
    save_files = params.get("save_files", False)
    n_boot = params.get("n_boot", 0)

    # Translation dictionary
    translations = {
        "en": {
            "title": "# GSCA Analysis",
            "model_measurement_only": "**Model Type**: Measurement model only (no structural paths specified)",
            "model_structural": "**Model Type**: Structural equation model with paths:",
            "path_diagram": "**Path Diagram**: {diagram_filename}",
            "diagram_warning": "**Warning**: Could not generate path diagram: {error}",
            "model_spec_title": "**Model Specification**:",
            "analysis_completed": "**GSCA Analysis Completed** (Bootstrap samples: {n_boot})",
            "summary_title": "## Analysis Summary",
            "overall_fit": "**Overall Model Fit**:",
            "gfi": "- Global Fit Index (GFI): {gfi}",
            "srmr": "- Standardized Root Mean Square Residual (SRMR): {srmr}",
            "afit": "- Adjusted Fit Index (AFIT): {afit}",
            "key_structural": "**Key Structural Relationships**: {count} significant paths identified",
            "measurement_quality": "**Measurement Quality**: {count} constructs with adequate reliability",
            "model_spec_file": "**Model Specification**: {spec_filename}",
            "results_summary_file": "**Complete Results Summary**: {results_filename}",
            "error_failed": "**Error**: GSCA analysis failed: {error}",
            "action_error_comment": "Review data quality and model specification",
            "action_issue_removal": "Variables suggested for removal based on measurement model analysis",
            "action_comment_rerun_gsca": "Re-run GSCA after removing problematic variables",
            "action_reflection_comment": "Reanalyze after measurement model adjustments",
            "action_issue_execution_error": "GSCA execution error: {error}"
        },
        "vi": {
            "title": "# Phân Tích GSCA",
            "model_measurement_only": "**Loại Mô Hình**: Chỉ mô hình đo lường (không có đường dẫn cấu trúc nào được chỉ định)",
            "model_structural": "**Loại Mô Hình**: Mô hình phương trình cấu trúc với các đường dẫn:",
            "path_diagram": "**Sơ Đồ Đường Dẫn**: {diagram_filename}",
            "diagram_warning": "**Cảnh báo**: Không thể tạo sơ đồ đường dẫn: {error}",
            "model_spec_title": "**Đặc Tả Mô Hình**:",
            "analysis_completed": "**Hoàn Thành Phân Tích GSCA** (Mẫu bootstrap: {n_boot})",
            "summary_title": "## Tổng Hợp Phân Tích",
            "overall_fit": "**Độ Phù Hợp Tổng Thể Mô Hình**:",
            "gfi": "- Chỉ Số Phù Hợp Toàn Cục (GFI): {gfi}",
            "srmr": "- Căn Bậc Hai Trung Bình Phần Dư Chuẩn Hóa (SRMR): {srmr}",
            "afit": "- Chỉ Số Phù Hợp Điều Chỉnh (AFIT): {afit}",
            "key_structural": "**Các Mối Quan Hệ Cấu Trúc Chính**: {count} đường dẫn có ý nghĩa được xác định",
            "measurement_quality": "**Chất Lượng Đo Lường**: {count} cấu trúc có độ tin cậy đầy đủ",
            "model_spec_file": "**Đặc Tả Mô Hình**: {spec_filename}",
            "results_summary_file": "**Tổng Hợp Kết Quả Hoàn Chỉnh**: {results_filename}",
            "error_failed": "**Lỗi**: Phân tích GSCA thất bại: {error}",
            "action_error_comment": "Xem xét chất lượng dữ liệu và đặc tả mô hình",
            "action_issue_removal": "Các biến được đề xuất loại bỏ dựa trên phân tích mô hình đo lường",
            "action_comment_rerun_gsca": "Chạy lại GSCA sau khi loại bỏ các biến có vấn đề",
            "action_reflection_comment": "Phân tích lại sau khi điều chỉnh mô hình đo lường",
            "action_issue_execution_error": "Lỗi thực thi GSCA: {error}"
        }
    }

    language = params.get("language", "en")
    count = params.get("count", 1)
    t = get_t_dict(translations.get(language, translations["en"]), language=language)

    # Format title with iteration count if count > 1
    t["title"] = format_title_with_count(t["title"], count, language)

    # Setup output directory with timestamp
    now = datetime.now()
    timestamp = f"{now.microsecond // 10000:02d}"
    output_dir = os.path.join(os.path.dirname(base_output_dir) or ".", f"{timestamp}_{os.path.basename(base_output_dir)}")
    rel_output_dir = os.path.relpath(output_dir, start=os.path.dirname(base_output_dir) or ".")

    logs = [t["title"]]
    file_contents = {}
    actions = []

    # Clean up existing output directory if save_files is enabled
    if save_files and os.path.exists(output_dir):
        shutil.rmtree(output_dir)

    # Handle structural paths
    if not structural_paths_tuples:
        structural_paths_formulas = []
        logs.append(t["model_measurement_only"])
    else:
        logs.append(t["model_structural"])
        structural_paths_formulas = convert_paths_to_formula_strings(structural_paths_tuples)
        for path in structural_paths_formulas:
            logs.append(f"- {path}")

    # Generate path diagram
    try:
        diagram_filename, diagram_bytes = draw_sem_path_diagram(
            variables=variables,
            structural_paths=structural_paths_tuples,
            rel_output_dir=rel_output_dir
        )
        if diagram_filename and diagram_bytes:
            file_contents[diagram_filename] = diagram_bytes
            logs.append(t["path_diagram"].format(diagram_filename=diagram_filename))
    except Exception as e:
        logs.append(t["diagram_warning"].format(error=str(e)))
    
    # Data suitability assessment
    suitability_output = assess_data_suitability_for_gsca(data, variables, params)
    logs.extend(suitability_output.logs)
    file_contents.update(suitability_output.file_contents)
    if suitability_output.action:
        actions.extend(suitability_output.action)
    
    # Build and run GSCA model
    full_model_spec = build_gsca_model_spec(variables, structural_paths_formulas)
    
    try:
        logs.append(t["model_spec_title"])
        for line in full_model_spec.split('\n'):
            logs.append(f"- {line}")

        gsca_result = run_gsca(data, full_model_spec, n_boot=n_boot)
        logs.append(t["analysis_completed"].format(n_boot=n_boot))
        
        # Analyze measurement model
        meas_output = analyze_gsca_measurement_model(gsca_result, variables, data, params)
        logs.extend(meas_output.logs)
        file_contents.update(meas_output.file_contents)
        if meas_output.action:
            actions.extend(meas_output.action)
            
            # Check for variable removal suggestions
            remove_vars = [a.action_params['variable'] for a in meas_output.action 
                          if a.action_type == ActionType.REMOVE_VARIABLE]
            if remove_vars:
                actions.append(Action(
                    action_type=ActionType.REANALYZE,
                    method="run_gsca_analysis",
                    issue=t["action_issue_removal"],
                    comment=t["action_comment_rerun_gsca"],
                    status="pending",
                    reflection_params={
                        "tool": "run_gsca_analysis",
                        "parameters": {"excluded_variables": remove_vars, "language": language, "count": count + 1},
                        "comment": t["action_reflection_comment"]
                    },
                    reset_actions=True
                ))

        # Analyze structural model
        struct_output = analyze_gsca_structural_model(gsca_result, params)
        logs.extend(struct_output.logs)
        file_contents.update(struct_output.file_contents)
        if struct_output.action:
            actions.extend(struct_output.action)
        
        # Generate comprehensive summary
        logs.append(t["summary_title"])

        # Model fit summary
        fit_indices = gsca_result['fit_indices']
        logs.append(t["overall_fit"])
        logs.append(t["gfi"].format(gfi=f"{fit_indices['GFI']:.3f}"))
        logs.append(t["srmr"].format(srmr=f"{fit_indices['SRMR']:.3f}"))
        logs.append(t["afit"].format(afit=f"{fit_indices['AFIT']:.3f}"))

        # Key findings
        if gsca_result['paths']:
            significant_paths = [(k, v) for k, v in gsca_result['paths'].items() if abs(v) >= 0.1]
            logs.append(t["key_structural"].format(count=len(significant_paths)))

        constructs_with_good_reliability = [k for k, v in gsca_result['rho'].items() if v >= 0.7]
        logs.append(t["measurement_quality"].format(count=len(constructs_with_good_reliability)))

        # Save model specification
        spec_filename = os.path.join(rel_output_dir, "model_specification.txt")
        file_contents[spec_filename] = full_model_spec
        logs.append(t["model_spec_file"].format(spec_filename=spec_filename))
        
        # Save complete results
        results_filename = os.path.join(rel_output_dir, "gsca_results_summary.txt")
        results_summary = f"""GSCA Analysis Results Summary
==============================

Model Fit Indices:
- GFI: {fit_indices['GFI']:.3f}
- SRMR: {fit_indices['SRMR']:.3f}
- AFIT: {fit_indices['AFIT']:.3f}
- FIT: {fit_indices['FIT']:.3f}
- FIT_M: {fit_indices['FIT_M']:.3f}
- FIT_S: {fit_indices['FIT_S']:.3f}

Construct Reliability:
"""
        for construct, reliability in gsca_result['rho'].items():
            results_summary += f"- {construct}: {reliability:.3f}\n"
        
        if gsca_result['paths']:
            results_summary += "\nPath Coefficients:\n"
            for (source, target), coeff in gsca_result['paths'].items():
                results_summary += f"- {source} → {target}: {coeff:.3f}\n"
        
        file_contents[results_filename] = results_summary
        logs.append(t["results_summary_file"].format(results_filename=results_filename))

    except Exception as e:
        logs.append(t["error_failed"].format(error=str(e)))
        actions.append(Action(
            action_type=ActionType.RECHECK_DATA,
            method="run_gsca_analysis",
            issue=t["action_issue_execution_error"].format(error=str(e)),
            comment=t["action_error_comment"],
            status="pending"
        ))
        
        # Return with error information
        return ToolOutput(
            results={"error": str(e)},
            logs=logs,
            file_contents=file_contents,
            action=actions
        )
    
    # Save all files at once
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
    
    return ToolOutput(
        results=serialize_dict({
            "gsca_result": gsca_result,
            "model_specification": full_model_spec,
            "fit_indices": gsca_result['fit_indices'],
            "construct_reliability": gsca_result['rho'],
            "path_coefficients": gsca_result['paths'],
            "r_squared": gsca_result['r_squared']
        }),
        logs=logs,
        file_contents=file_contents,
        action=actions if actions else None
    )
