"""
Log cleaning module for preprocessing analysis logs before fusion writing.

This module provides robust cleaning of raw analysis logs to remove:
- Statistical markers and diagnostic text
- Log structure headers
- Section markers
- Markdown headers that interfere with document structure
"""

import re
from typing import Optional
from pydantic import BaseModel, Field


class LogCleaningConfig(BaseModel):
    """
    Configuration for log cleaning behavior.

    Attributes:
        remove_statistical_markers: Remove markers like `: ```, diagnostic column names
        remove_log_headers: Remove "## Raw report" style headers
        remove_diagnostic_columns: Filter table headers with diagnostic terms
        remove_section_markers: Remove technical numbering like "5.3.6.1"
        strip_markdown_headers: Convert # ## ### to bold text
        filter_by_step_type: Filter by TOOL/ACTION/REFLECTION types (optional)
    """
    remove_statistical_markers: bool = Field(
        default=True,
        description="Remove statistical markers like `: ```, Cronbach's Alpha columns"
    )
    remove_log_headers: bool = Field(
        default=True,
        description="Remove log structure headers like '## Raw report of log 1'"
    )
    remove_diagnostic_columns: bool = Field(
        default=True,
        description="Remove table headers containing diagnostic terminology"
    )
    remove_section_markers: bool = Field(
        default=True,
        description="Remove technical section markers like '5.3.6.1'"
    )
    strip_markdown_headers: bool = Field(
        default=True,
        description="Convert markdown headers (# ## ###) to bold text"
    )
    filter_by_step_type: Optional[list[str]] = Field(
        default=None,
        description="Filter logs by step_type (e.g., ['TOOL', 'ACTION']). None means include all."
    )


class LogCleaner:
    """
    Handles preprocessing of raw logs before fusion writing.

    This class provides methods to clean log content by removing technical
    metadata, statistical markers, and structural elements that should not
    appear in final academic content.
    """

    # Statistical markers and diagnostic terms to remove
    STATISTICAL_PATTERNS = [
        r': ``.*?``',  # Markers like ': ``value``'
        r'Cronbach\'?s?\s+Alpha\s+if\s+Item\s+Deleted',
        r'Scale\s+Mean\s+if\s+Item\s+Deleted',
        r'Scale\s+Variance\s+if\s+Item\s+Deleted',
        r'Corrected\s+Item-Total\s+Correlation',
        r'Squared\s+Multiple\s+Correlation',
        r'Chi-Square\s+Contribution',
        r'Standardized\s+Residuals?',
        r'Mahalanobis\s+Distance',
    ]

    # Log structure headers to remove
    LOG_HEADER_PATTERNS = [
        r'##\s+Raw\s+report\s+of\s+log\s+\d+',
        r'##\s+AI\s+report\s+of\s+log\s+\d+',
        r'#{1,4}\s+Execution\s+Logs:?',
        r'\*\*Type:\*\*\s+(TOOL|ACTION|REFLECTION)',
        r'Type:\s+(TOOL|ACTION|REFLECTION)',
    ]

    # Section markers to remove
    SECTION_MARKERS = [
        r'\d+\.\d+\.\d+\.\d+\s+',  # e.g., "5.3.6.1 "
        r'Log\s+\d+:',
        r'Step\s+\d+:',
    ]

    def __init__(self, config: LogCleaningConfig):
        """
        Initialize the LogCleaner with a configuration.

        Args:
            config: LogCleaningConfig specifying which cleaning operations to perform
        """
        self.config = config

        # Pre-compile regex patterns for efficiency
        self._statistical_patterns_compiled = [
            re.compile(pattern, re.IGNORECASE) for pattern in self.STATISTICAL_PATTERNS
        ] if config.remove_statistical_markers else []

        self._log_header_patterns_compiled = [
            re.compile(pattern, re.IGNORECASE) for pattern in self.LOG_HEADER_PATTERNS
        ] if config.remove_log_headers else []

        self._section_markers_compiled = [
            re.compile(pattern) for pattern in self.SECTION_MARKERS
        ] if config.remove_section_markers else []

    def clean_log(self, log_content: str) -> str:
        """
        Clean a single log string by applying all configured cleaning operations.

        Args:
            log_content: Raw log content string

        Returns:
            Cleaned log content with technical markers removed
        """
        if not log_content:
            return log_content

        cleaned = log_content

        # Remove log headers
        if self.config.remove_log_headers:
            for pattern in self._log_header_patterns_compiled:
                cleaned = pattern.sub('', cleaned)

        # Remove statistical markers
        if self.config.remove_statistical_markers:
            for pattern in self._statistical_patterns_compiled:
                cleaned = pattern.sub('', cleaned)

        # Remove section markers
        if self.config.remove_section_markers:
            for pattern in self._section_markers_compiled:
                cleaned = pattern.sub('', cleaned)

        # Remove diagnostic columns from tables
        if self.config.remove_diagnostic_columns:
            cleaned = self._clean_table_headers(cleaned)

        # Strip markdown headers
        if self.config.strip_markdown_headers:
            cleaned = self._strip_headers(cleaned)

        # Normalize whitespace
        cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)
        cleaned = re.sub(r' {2,}', ' ', cleaned)
        cleaned = cleaned.strip()

        return cleaned

    def _clean_table_headers(self, text: str) -> str:
        """
        Remove diagnostic column names from markdown tables.

        This method identifies table rows containing diagnostic terminology
        and removes them to prevent technical metadata from appearing in
        academic content.

        Args:
            text: Text containing markdown tables

        Returns:
            Text with diagnostic table headers removed
        """
        if not text or '|' not in text:
            return text

        # Diagnostic terms that indicate a table header should be removed
        diagnostic_terms = [
            'Cronbach', 'Deleted', 'Correlation', 'Item-Total',
            'Scale Mean', 'Scale Variance', 'Standardized', 'Residual'
        ]

        lines = text.split('\n')
        cleaned_lines = []

        for line in lines:
            # Check if line is a table row with diagnostic terms
            if '|' in line:
                has_diagnostic = any(term in line for term in diagnostic_terms)
                if has_diagnostic:
                    # Skip this diagnostic table header row
                    continue

            cleaned_lines.append(line)

        return '\n'.join(cleaned_lines)

    def _strip_headers(self, text: str) -> str:
        """
        Remove or convert markdown headers (# ## ###) from content.

        Markdown headers in log content interfere with document structure
        when parsed by the UI. This method converts headers to bold text
        to preserve emphasis while removing structural markup.

        Args:
            text: Text containing markdown headers

        Returns:
            Text with headers converted to bold text
        """
        if not text:
            return text

        lines = text.split('\n')
        cleaned_lines = []

        for line in lines:
            # Match markdown headers (# through ######)
            match = re.match(r'^(#{1,6})\s+(.+)$', line)
            if match:
                # Convert to bold text instead of header
                content = match.group(2).strip()
                cleaned_lines.append(f"**{content}**")
            else:
                cleaned_lines.append(line)

        return '\n'.join(cleaned_lines)

    def filter_logs_by_type(self, logs: list[str], log_entries: list) -> list[str]:
        """
        Filter logs by step_type before they become strings.

        This is an optional feature that can filter logs based on their
        type (TOOL, ACTION, REFLECTION) if specified in the configuration.

        Args:
            logs: List of log strings
            log_entries: List of LogEntry objects with step_type field

        Returns:
            Filtered list of logs matching the configured step_type filter
        """
        if not self.config.filter_by_step_type:
            return logs

        filtered = []
        for log, entry in zip(logs, log_entries):
            if hasattr(entry, 'step_type'):
                if entry.step_type.value in self.config.filter_by_step_type:
                    filtered.append(log)
            else:
                # If no step_type, include by default
                filtered.append(log)

        return filtered
