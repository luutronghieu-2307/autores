import base64
import io
import pandas as pd
from matplotlib.figure import Figure
from typing import Any, Optional
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def fig_to_base64(fig: Figure) -> str:
    """
    Converts a matplotlib figure to a base64 encoded string.
    """
    if not isinstance(fig, Figure):
        raise TypeError("Input 'fig' must be a matplotlib.figure.Figure object.")
        
    buf = io.BytesIO()
    fig.savefig(buf, format='png', bbox_inches='tight')
    buf.seek(0)
    img_str = base64.b64encode(buf.read()).decode('utf-8')
    plt.close(fig) # Close the figure to free memory
    return img_str

def dataframe_to_markdown(df: pd.DataFrame, index: bool = True, **kwargs) -> str:
    """
    Converts a pandas DataFrame to a Markdown table string.
    Additional kwargs are passed to df.to_markdown().
    """
    if not isinstance(df, pd.DataFrame):
        raise TypeError("Input 'df' must be a pandas DataFrame.")
    return df.to_html(index=index, **kwargs)

def format_interpretation_string(
    test_name: str,
    statistic: Optional[float],
    p_value: Optional[float],
    alpha: float = 0.05,
    null_hypothesis: str = "",
    alt_hypothesis: str = "",
    decision_rule_note: str = "" # e.g. "Low p-value (< alpha) rejects H0."
) -> str:
    """
    Generates a human-readable interpretation of a statistical test result.
    """
    interpretation = f"**{test_name}**\n"
    if null_hypothesis:
        interpretation += f"- Null Hypothesis (H0): {null_hypothesis}\n"
    if alt_hypothesis:
        interpretation += f"- Alternative Hypothesis (H1): {alt_hypothesis}\n"
    if statistic is not None:
        interpretation += f"- Test Statistic: {statistic:.4f}\n"
    if p_value is not None:
        interpretation += f"- P-value: {p_value:.4f}\n"
    interpretation += f"- Significance Level (alpha): {alpha}\n"
    
    if p_value is not None:
        if p_value < alpha:
            interpretation += f"- Decision: Reject H0 at {alpha*100}% significance.\n"
            if alt_hypothesis:
                interpretation += f"- Conclusion: There is evidence to support the alternative hypothesis ({alt_hypothesis}).\n"
            else:
                interpretation += f"- Conclusion: There is evidence against the null hypothesis.\n"
        else:
            interpretation += f"- Decision: Fail to reject H0 at {alpha*100}% significance.\n"
            if null_hypothesis:
                 interpretation += f"- Conclusion: There is not enough evidence to reject the null hypothesis ({null_hypothesis}).\n"
            else:
                interpretation += f"- Conclusion: There is not enough evidence to make a conclusion against H0.\n"
    else:
        interpretation += "- Decision/Conclusion: P-value not available for automated decision.\n"
        
    if decision_rule_note:
        interpretation += f"- Note: {decision_rule_note}\n"
        
    return interpretation


def initialize_tool_output() -> dict[str, Any]:
    """
    Creates a basic structure for ToolOutput components.
    (This is a simplified version based on typical needs.
    Your Pydantic models might define a more specific structure.)
    """
    return {
        "results": {},          # For structured data like dicts, DataFrames (as dicts/json)
        "summary_text": [],     # List of strings for textual summaries, interpretations
        "log_messages": [],     # For operational logs
        "file_contents": {},    # For base64 images, CSV strings, etc. (filename: content)
        "status": "SUCCESS",    # or "FAILURE", "PARTIAL_SUCCESS"
        "error_message": None   # If status is not SUCCESS
    }

def add_log_entry(
    tool_output_dict: dict[str, Any], # The dict from initialize_tool_output()
    message: str,
    level: str = "INFO" # e.g., INFO, WARNING, ERROR
):
    """Appends a formatted log message to the 'log_messages' list in tool_output_dict."""
    if "log_messages" not in tool_output_dict or not isinstance(tool_output_dict["log_messages"], list):
        tool_output_dict["log_messages"] = [] # Initialize if not present
    
    # You could add timestamps or more formatting here
    tool_output_dict["log_messages"].append(f"[{level}] {message}")

def add_file_content(
    tool_output_dict: dict[str, Any], # The dict from initialize_tool_output()
    file_name: str,
    content: str, # Could be base64 string, CSV string, markdown string etc.
    content_type: str = "text/plain" # e.g., "image/png;base64", "text/csv", "text/markdown"
):
    """Adds content to the 'file_contents' dictionary in tool_output_dict."""
    if "file_contents" not in tool_output_dict or not isinstance(tool_output_dict["file_contents"], dict):
        tool_output_dict["file_contents"] = {} # Initialize if not present
        
    # You might want to store content_type as well if your consumer needs it
    tool_output_dict["file_contents"][file_name] = {
        "content": content,
        "type": content_type
    }

def add_text_summary(
    tool_output_dict: dict[str, Any],
    text: str
):
    """Appends a string to the 'summary_text' list."""
    if "summary_text" not in tool_output_dict or not isinstance(tool_output_dict["summary_text"], list):
        tool_output_dict["summary_text"] = []
    tool_output_dict["summary_text"].append(text)

def add_structured_result(
    tool_output_dict: dict[str, Any],
    key: str,
    value: Any # e.g., a dict, a list, a DataFrame converted to dict
):
    """Adds a key-value pair to the 'results' dictionary."""
    if "results" not in tool_output_dict or not isinstance(tool_output_dict["results"], dict):
        tool_output_dict["results"] = {}
    tool_output_dict["results"][key] = value