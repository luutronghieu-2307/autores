import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
from datetime import datetime
import os
import base64
from io import BytesIO
import json
import logging

from typing import Dict, Any, Optional, Tuple
from data_analysis.src.schemas.analyzer_states import Variable, ScaleType, VariableType, ToolOutput
from data_analysis.src.modules.utils import serialize_dict, parse_variable_values

# Set up logging
logger = logging.getLogger(__name__)

def run_overview_charts_analysis(
    data: pd.DataFrame,
    variables: list[Variable],
    params: dict
) -> ToolOutput:
    """
    Perform an overview analysis with visualization charts for different variable types.
    
    Targets:
    - Nominal variables: Pie charts showing category distributions.
    - Latent variables: Grouped bar charts for their indicators' response distributions.
    - Continuous variables (interval/ratio): Histograms for distributions.
    
    Parameters:
        data: Input DataFrame containing the data.
        variables: List of Variable objects describing the data columns.
        params: Dictionary containing analysis parameters.
            - output_dir (str): Base output directory name (default: "overview_charts").
            - save_files (bool): Whether to save generated files to disk (default: False).
    
    Returns:
        ToolOutput: Contains results with chart summaries, logs for reporting, and file contents (base64-encoded images).
    """
    # Extract parameters
    base_output_dir = params.get("output_dir", "overview_charts")
    save_files = params.get("save_files", False)

    # Translation dictionary
    translations = {
        "en": {
            "report_title": "# Overview Charts Analysis Report",
            "section_title": "## Variable Distributions and Profiles",
            "section_description": "This section provides visual overviews of variable distributions based on their types.",
            "insight_nominal_two_categories": "The distribution for `{var_name}` shows the highest proportion in '{max_label}' at {max_pct:.1f}%, followed by '{second_label}' at {second_pct:.1f}%.",
            "insight_nominal_one_category": "The distribution for `{var_name}` is dominated by '{max_label}' at {max_pct:.1f}%.",
            "insight_latent_positive": "For the construct `{latent_name}`, responses lean towards agreement, with {total_agree} counts in positive categories across {n_cats} indicators (vs. {total_disagree} in negative).",
            "insight_latent_balanced": "For the construct `{latent_name}`, responses show balanced or negative leanings, with {total_agree} positive and {total_disagree} negative counts across {n_cats} indicators.",
            "insight_latent_no_response": "For the construct `{latent_name}`, no responses recorded across {n_cats} indicators.",
            "warning_no_valid_numeric": "**WARNING**: No valid numeric data available for continuous variable `{var_code}` after cleaning. Skipping.",
            "insight_distribution_symmetric": "The distribution of `{var_name}` is approximately symmetric around the mean of {mean_val:.2f} ({unit}), with a standard deviation of {std_val:.2f}.",
            "insight_distribution_right_skew": "The distribution of `{var_name}` shows right-skewness (skew = {skewness:.2f}), with mean {mean_val:.2f} ({unit}) and std {std_val:.2f}.",
            "insight_distribution_left_skew": "The distribution of `{var_name}` shows left-skewness (skew = {skewness:.2f}), with mean {mean_val:.2f} ({unit}) and std {std_val:.2f}.",
            "analysis_completed": "Overview charts analysis completed. Generated {count} visualization files."
        },
        "vi": {
            "report_title": "# Báo Cáo Phân Tích Biểu Đồ Tổng Quan",
            "section_title": "## Phân Phối Và Hồ Sơ Biến",
            "section_description": "Phần này cung cấp cái nhìn tổng quan trực quan về phân phối biến dựa trên loại của chúng.",
            "insight_nominal_two_categories": "Phân phối của `{var_name}` cho thấy tỷ lệ cao nhất ở '{max_label}' là {max_pct:.1f}%, tiếp theo là '{second_label}' ở {second_pct:.1f}%.",
            "insight_nominal_one_category": "Phân phối của `{var_name}` bị chi phối bởi '{max_label}' ở {max_pct:.1f}%.",
            "insight_latent_positive": "Đối với cấu trúc `{latent_name}`, các phản hồi nghiêng về sự đồng ý, với {total_agree} lượt đếm trong các danh mục tích cực trên {n_cats} chỉ báo (so với {total_disagree} ở tiêu cực).",
            "insight_latent_balanced": "Đối với cấu trúc `{latent_name}`, các phản hồi cho thấy xu hướng cân bằng hoặc tiêu cực, với {total_agree} tích cực và {total_disagree} tiêu cực trên {n_cats} chỉ báo.",
            "insight_latent_no_response": "Đối với cấu trúc `{latent_name}`, không có phản hồi nào được ghi nhận trên {n_cats} chỉ báo.",
            "warning_no_valid_numeric": "**CẢNH BÁO**: Không có dữ liệu số hợp lệ cho biến liên tục `{var_code}` sau khi làm sạch. Bỏ qua.",
            "insight_distribution_symmetric": "Phân phối của `{var_name}` gần như đối xứng xung quanh trung bình {mean_val:.2f} ({unit}), với độ lệch chuẩn {std_val:.2f}.",
            "insight_distribution_right_skew": "Phân phối của `{var_name}` cho thấy độ lệch phải (skew = {skewness:.2f}), với trung bình {mean_val:.2f} ({unit}) và độ lệch chuẩn {std_val:.2f}.",
            "insight_distribution_left_skew": "Phân phối của `{var_name}` cho thấy độ lệch trái (skew = {skewness:.2f}), với trung bình {mean_val:.2f} ({unit}) và độ lệch chuẩn {std_val:.2f}.",
            "analysis_completed": "Phân tích biểu đồ tổng quan đã hoàn tất. Đã tạo {count} tệp hình ảnh."
        }
    }
    language = params.get("language", "en")
    t = translations.get(language, translations["en"])

    # Generate timestamped output directory
    now = datetime.now()
    timestamp = f"{now.microsecond // 10000:02d}"
    output_dir = f"{timestamp}_{os.path.basename(base_output_dir)}"
    
    # Initialize outputs
    logs = []
    file_contents: Dict[str, str] = {}
    results: Dict[str, Any] = {}
    
    # Set up font for Vietnamese characters
    plt.rcParams['font.family'] = 'DejaVu Sans'
    plt.rcParams['axes.unicode_minus'] = False
    
    # Parse variable values into maps (improved handling for JSON-like strings)
    value_maps: Dict[str, Dict[str, str]] = {}
    for var in variables:
        if var.values:
            try:
                # Try JSON parsing for quoted formats like "{\"1\":\"Label\"}"
                if var.values.startswith('{"') and var.values.endswith('"}'):
                    value_maps[var.code] = json.loads(var.values)
                else:
                    # Fallback to original parser
                    value_maps[var.code] = parse_variable_values(var.values)
            except (json.JSONDecodeError, Exception):
                value_maps[var.code] = parse_variable_values(var.values)
    
    # Initialize analysis logging
    logs.append(t["report_title"])
    logs.append(t["section_title"])
    logs.append(t["section_description"])
    
    # 1. Nominal Variables: Pie Charts (exclude indicators)
    nominal_vars = [
        var for var in variables 
        if var.scale == ScaleType.NOMINAL.value 
        and var.code in data.columns
        and var.parent_code is None
    ]
    for var in nominal_vars:
        col = var.code
        non_null_data = data[col].dropna()
        if len(non_null_data) == 0:
            logger.warning(f"**WARNING**: No data available for nominal variable `{col}`. Skipping.")
            continue
        
        vc = non_null_data.astype(str).value_counts()
        labels = [str(k) for k in vc.index]
        sizes = (vc.values / len(non_null_data)) * 100  # Percentages
        
        fig, ax = plt.subplots(figsize=(8, 6))
        colors = plt.cm.Set3(np.linspace(0, 1, len(labels)))
        
        wedges, texts, autotexts = ax.pie(
            sizes, 
            labels=None,
            colors=colors,
            autopct='%1.1f%%',
            startangle=90,
            textprops={'fontsize': 12, 'weight': 'bold'}
        )
        
        # Customize percentage text
        for autotext in autotexts:
            autotext.set_color('white')
            autotext.set_fontsize(14)
            autotext.set_weight('bold')
        
        # Legend with parsed labels
        val_map = value_maps.get(col, {lbl: lbl for lbl in labels})
        legend_labels = [val_map.get(lbl, lbl) for lbl in labels]
        ax.legend(wedges, legend_labels, loc='upper left', bbox_to_anchor=(1, 1), frameon=False, fontsize=11)
        
        title = f"{var.name or col}\n{len(non_null_data)} observations"
        ax.set_title(title, fontsize=14, loc='left', pad=20)
        ax.axis('equal')
        
        # Save to base64
        buf = BytesIO()
        plt.savefig(buf, format='png', bbox_inches='tight', dpi=150)
        buf.seek(0)
        img_base64 = base64.b64encode(buf.read()).decode('utf-8')
        filename = f"{output_dir}/{col}_distribution_pie.png"
        file_contents[filename] = img_base64
        plt.close(fig)
        
        # Generate insightful report content
        if len(sizes) > 0:
            max_idx = np.argmax(sizes)
            max_label = legend_labels[max_idx]
            max_pct = sizes[max_idx]
            if len(sizes) > 1:
                second_idx = np.argsort(sizes)[-2]
                second_label = legend_labels[second_idx]
                second_pct = sizes[second_idx]
                logs.append(t["insight_nominal_two_categories"].format(
                    var_name=var.name or col, max_label=max_label, max_pct=max_pct,
                    second_label=second_label, second_pct=second_pct
                ))
            else:
                logs.append(t["insight_nominal_one_category"].format(
                    var_name=var.name or col, max_label=max_label, max_pct=max_pct
                ))
        results[col] = {
            "type": "nominal_pie",
            "n_categories": len(labels),
            "distribution": {lbl: float(sz) for lbl, sz in zip(labels, sizes)}
        }
    
    # 2. Latent Variables: Grouped Bar Charts for Indicators
    latent_vars = [var for var in variables if var.variable_type == VariableType.LATENT]
    for latent in latent_vars:
        indicators = [
            v for v in variables 
            if v.parent_code == latent.code and v.code in data.columns
        ]
        if not indicators:
            logger.warning(f"**WARNING**: No indicators found for latent variable `{latent.code}`. Skipping.")
            continue
        
        # Assume all indicators share the same response scale; use first one's map
        ind_code = indicators[0].code
        response_map = value_maps.get(ind_code, {})
        if not response_map:
            # Default for 5-point Likert (adjustable)
            response_map = {
                "1": "Rất không đồng ý", "2": "Không đồng ý", "3": "Trung lập", 
                "4": "Đồng ý", "5": "Rất đồng ý"
            }
        
        response_levels = sorted(response_map.keys(), key=lambda x: (x.isdigit(), int(x) if x.isdigit() else 0))
        labels = [response_map[lvl] for lvl in response_levels]
        
        # Categories: Use statements or names, shortened
        categories = []
        for ind in indicators:
            stmt = ind.statement or ind.name or ind.code
            if len(stmt) > 40:  # Shorten long statements
                stmt = stmt[:37] + "..."
            categories.append(stmt)
        
        # Prepare data: counts for each indicator and response level
        n_cats = len(categories)
        x = np.arange(n_cats)
        n_levels = len(response_levels)
        width = 0.8 / n_levels
        
        fig, ax = plt.subplots(figsize=(max(12, n_cats * 1.2), 7))
        
        # Colors: Likert scale progression (disagree red -> neutral gray -> agree green)
        if n_levels == 5:
            colors = ['#D73027', '#F46D43', '#BEBEBE', '#74C476', '#238B45']
        else:
            colors = plt.cm.RdYlGn(np.linspace(0, 1, n_levels))
        
        max_count = 0
        all_counts = []
        for i, lvl in enumerate(response_levels):
            counts = []
            for ind in indicators:
                col = ind.code
                vc = data[col].astype(str).value_counts()
                count = vc.get(str(lvl), 0)
                counts.append(count)
                all_counts.extend(counts)
            offset = (i - (n_levels - 1) / 2) * width
            ax.bar(x + offset, counts, width, label=labels[i], color=colors[i])
            max_count = max(max_count, max(counts))
        
        ax.set_xlabel('Indicators')
        ax.set_ylabel('Count')
        ax.set_title(f'{latent.name or latent.code} - Indicator Responses\n{n_cats} indicators', fontsize=16, pad=20)
        ax.set_xticks(x)
        ax.set_xticklabels(categories, fontsize=9, ha='right', rotation=45)
        ax.legend(loc='upper right', bbox_to_anchor=(1.18, 1), frameon=False, fontsize=10)
        ax.set_ylim(0, max_count * 1.1 if max_count > 0 else 1)
        ax.grid(axis='y', alpha=0.3, linestyle='-', linewidth=0.5)
        ax.set_axisbelow(True)
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        
        # Save to base64
        buf = BytesIO()
        plt.savefig(buf, format='png', bbox_inches='tight', dpi=150)
        buf.seek(0)
        img_base64 = base64.b64encode(buf.read()).decode('utf-8')
        filename = f"{output_dir}/{latent.code}_indicators_bar.png"
        file_contents[filename] = img_base64
        plt.close(fig)
        
        # Generate insightful report content
        total_responses = np.sum(all_counts)
        if total_responses > 0:
            pos_mask = [i // n_cats >= n_levels // 2 for i in range(len(all_counts))]
            neg_mask = [i // n_cats < n_levels // 2 for i in range(len(all_counts))]
            total_agree = np.sum(np.array(all_counts)[pos_mask])
            total_disagree = np.sum(np.array(all_counts)[neg_mask])
            if total_agree > total_disagree:
                logs.append(t["insight_latent_positive"].format(
                    latent_name=latent.name or latent.code, total_agree=total_agree,
                    n_cats=n_cats, total_disagree=total_disagree
                ))
            else:
                logs.append(t["insight_latent_balanced"].format(
                    latent_name=latent.name or latent.code, total_agree=total_agree,
                    total_disagree=total_disagree, n_cats=n_cats
                ))
        else:
            logs.append(t["insight_latent_no_response"].format(
                latent_name=latent.name or latent.code, n_cats=n_cats
            ))
        results[latent.code] = {
            "type": "latent_bar",
            "n_indicators": n_cats,
            "response_levels": labels,
            "n_responses": len(response_levels)
        }
    
    # 3. Other Variables (Interval/Ratio): Histograms (exclude indicators)
    continuous_vars = [
        var for var in variables 
        if var.scale in [ScaleType.INTERVAL.value, ScaleType.RATIO.value] 
        and var.variable_type == VariableType.OBSERVED
        and var.code in data.columns
        and var.parent_code is None
    ]
    for var in continuous_vars:
        col = var.code
        data_col = data[col].dropna()
        if len(data_col) == 0:
            logger.warning(f"**WARNING**: No data available for continuous variable `{col}`. Skipping.")
            continue
        
        # Convert to numeric, coercing invalid values (e.g., 'x') to NaN, then drop NaNs
        data_col = pd.to_numeric(data_col, errors='coerce').dropna()
        if len(data_col) == 0:
            logs.append(t["warning_no_valid_numeric"].format(var_code=col))
            continue
        
        fig, ax = plt.subplots(figsize=(10, 6))
        n_bins = min(20, int(np.sqrt(len(data_col))))
        ax.hist(data_col, bins=n_bins, alpha=0.7, color='skyblue', edgecolor='black')
        ax.set_title(f'Distribution Histogram: {var.name or col}', fontsize=14, pad=20)
        ax.set_xlabel(f'{col} ({var.unit or ""})')
        ax.set_ylabel('Frequency')
        ax.grid(axis='y', alpha=0.3)
        
        # Save to base64
        buf = BytesIO()
        plt.savefig(buf, format='png', bbox_inches='tight', dpi=150)
        buf.seek(0)
        img_base64 = base64.b64encode(buf.read()).decode('utf-8')
        filename = f"{output_dir}/{col}_distribution_hist.png"
        file_contents[filename] = img_base64
        plt.close(fig)
        
        # Generate insightful report content
        mean_val = data_col.mean()
        std_val = data_col.std()
        skewness = (data_col - mean_val).skew() if len(data_col) > 2 else 0
        if abs(skewness) < 0.5:
            logs.append(t["insight_distribution_symmetric"].format(
                var_name=var.name or col, mean_val=mean_val, unit=var.unit or '', std_val=std_val
            ))
        elif skewness > 0:
            logs.append(t["insight_distribution_right_skew"].format(
                var_name=var.name or col, skewness=skewness, mean_val=mean_val,
                unit=var.unit or '', std_val=std_val
            ))
        else:
            logs.append(t["insight_distribution_left_skew"].format(
                var_name=var.name or col, skewness=skewness, mean_val=mean_val,
                unit=var.unit or '', std_val=std_val
            ))
        results[col] = {
            "type": "continuous_histogram",
            "n_observations": len(data_col),
            "mean": float(mean_val),
            "std": float(std_val),
            "min": float(data_col.min()),
            "max": float(data_col.max()),
            "skewness": float(skewness)
        }
    
    # Save files to disk if requested (similar to example tools)
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
                    logs.append(f"**ERROR**: Failed to save image {filename}: {e}")
            else:
                logger.warning(f"**WARNING**: Unknown file type for '{filename}'.")
    
    logs.append(t["analysis_completed"].format(count=len(file_contents)))
    
    # Prepare final results (serialize if needed, assuming serialize_dict handles it)
    final_results = {
        "charts_summary": {
            "nominal_pies": len(nominal_vars),
            "latent_bars": len(latent_vars),
            "continuous_hists": len(continuous_vars),
            "total_charts": len(file_contents)
        },
        "variable_details": results
    }
    
    return ToolOutput(
        results=serialize_dict(final_results) if 'serialize_dict' in globals() else final_results,
        logs=logs,
        file_contents=file_contents,
        action=None
    )