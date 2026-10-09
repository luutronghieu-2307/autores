import pandas as pd
from typing import Optional, Union, Callable
import logging

logger = logging.getLogger(__name__)

def load_data(source_path: str, csv_load_kwargs: Optional[dict] = None, column_dtypes: Optional[dict[str, str]] = None) -> pd.DataFrame:
    """
    Loads data from a CSV file.

    Args:
        source_path (str): Path to the CSV file.
        csv_load_kwargs (Optional[dict]): Keyword arguments for pd.read_csv.
        column_dtypes (Optional[dict[str, str]]): dictionary mapping column names to dtypes.

    Returns:
        pd.DataFrame: Loaded DataFrame.
    """
    if csv_load_kwargs is None:
        csv_load_kwargs = {}
    try:
        df = pd.read_csv(source_path, dtype=column_dtypes, **csv_load_kwargs)
        logger.info(f"Data loaded successfully from {source_path}. Shape: {df.shape}")
        return df
    except FileNotFoundError:
        logger.error(f"File not found: {source_path}")
        raise
    except Exception as e:
        logger.error(f"Error loading data from {source_path}: {e}")
        raise

def identify_time_index_column_candidates(
    df_columns: list[str],
    explicit_candidates: Optional[list[str]] = None,
    common_names: Optional[list[str]] = None
) -> list[str]:
    """
    Suggests potential time index columns from a list of DataFrame columns.

    Args:
        df_columns (list[str]): All columns in the DataFrame.
        explicit_candidates (Optional[list[str]]): User-provided list of potential time index column names.
        common_names (Optional[list[str]]): A predefined list of common time index column names.

    Returns:
        list[str]: A list of candidate column names, prioritized by explicit_candidates then common_names.
    """
    candidates = []
    df_cols_lower = [col.lower() for col in df_columns]

    if explicit_candidates:
        for cand_col in explicit_candidates:
            if cand_col in df_columns:
                candidates.append(cand_col)
            elif cand_col.lower() in df_cols_lower:
                 # Match case-insensitively if direct match fails
                original_case_col = df_columns[df_cols_lower.index(cand_col.lower())]
                candidates.append(original_case_col)


    if common_names is None:
        common_names = ['date', 'time', 'timestamp', 'event_date', 'year', 'month', 'day', 'period']

    for common_col_name in common_names:
        for df_col in df_columns:
            if common_col_name.lower() in df_col.lower() and df_col not in candidates:
                candidates.append(df_col)
    
    # Add any remaining columns that weren't picked up if no candidates found yet
    # This is less ideal but provides a fallback.
    if not candidates:
        logger.warning("No strong time index candidates identified based on explicit or common names.")
        # Heuristic: often the first column if not specified
        # Or columns that look like dates/times by name parts
        # This part can be made more sophisticated if needed
        # For now, we return what we have, or an empty list.

    return list(dict.fromkeys(candidates)) # Remove duplicates while preserving order

def assemble_and_parse_time_index(
    data: pd.DataFrame,
    time_col_names: Union[str, list[str]],
    date_format_hint: Optional[str] = None,
    date_parse_kwargs: Optional[dict] = None,
    new_index_name: str = "datetime_index"
) -> tuple[pd.DataFrame, str, list[str]]:
    """
    Assembles and parses time index from specified columns, sets it as DataFrame index.

    Args:
        data (pd.DataFrame): Input DataFrame.
        time_col_names (Union[str, list[str]]): Name(s) of the column(s) to form the time index.
        date_format_hint (Optional[str]): Format string for pd.to_datetime.
        date_parse_kwargs (Optional[dict]): Additional kwargs for pd.to_datetime.
        new_index_name (str): Name for the new DatetimeIndex.

    Returns:
        tuple[pd.DataFrame, str, list[str]]:
            - DataFrame with DatetimeIndex.
            - Name of the new index column.
            - list of log messages.
    """
    df = data.copy()
    logs = []
    original_cols_to_drop = []

    if date_parse_kwargs is None:
        date_parse_kwargs = {}

    try:
        if isinstance(time_col_names, str):
            if time_col_names not in df.columns:
                logs.append(f"ERROR: Time index column '{time_col_names}' not found in DataFrame.")
                raise ValueError(f"Time index column '{time_col_names}' not found.")
            
            time_series = pd.to_datetime(df[time_col_names], format=date_format_hint, **date_parse_kwargs)
            original_cols_to_drop.append(time_col_names)
            logs.append(f"Parsed single time column '{time_col_names}'.")

        elif isinstance(time_col_names, list):
            if not all(col in df.columns for col in time_col_names):
                missing = [col for col in time_col_names if col not in df.columns]
                logs.append(f"ERROR: Time index component columns not found: {missing}.")
                raise ValueError(f"Time index component columns not found: {missing}.")

            if len(time_col_names) > 1: # Attempt to combine if multiple columns like Year, Month, Day
                # Heuristic for common combinations
                if all(col.lower() in ['year', 'month', 'day', 'hour', 'minute', 'second'] for col in [c.lower() for c in time_col_names]):
                    # Ensure correct order for pd.to_datetime if columns are like 'Year', 'Month', 'Day'
                    # This requires a more robust assembly logic if column names are not standard
                    # For simplicity, we assume they can be concatenated into a parseable string or directly used by pd.to_datetime
                    # A common approach is to create a combined string column first
                    df_temp_time_col = df[time_col_names].astype(str).agg('-'.join, axis=1)
                    time_series = pd.to_datetime(df_temp_time_col, format=date_format_hint, **date_parse_kwargs)
                    logs.append(f"Combined and parsed multiple time columns: {time_col_names}.")
                else: # Generic case for multiple columns, try to let pd.to_datetime handle it with a dict of columns
                    time_series = pd.to_datetime(df[time_col_names], format=date_format_hint, **date_parse_kwargs)
                    logs.append(f"Parsed multiple time columns using dictionary: {time_col_names}.")
            elif len(time_col_names) == 1: # list with one element
                time_series = pd.to_datetime(df[time_col_names[0]], format=date_format_hint, **date_parse_kwargs)
                logs.append(f"Parsed single time column from list: '{time_col_names[0]}'.")
            else: # Empty list
                logs.append("ERROR: Empty list provided for time_col_names.")
                raise ValueError("Empty list provided for time_col_names.")
            original_cols_to_drop.extend(time_col_names)
        else:
            logs.append(f"ERROR: Invalid type for time_col_names: {type(time_col_names)}.")
            raise TypeError("time_col_names must be a string or a list of strings.")

        df.index = time_series
        df.index.name = new_index_name
        
        # Drop original time columns if they are not the new index itself
        # and were successfully used.
        cols_to_drop_final = [col for col in original_cols_to_drop if col in df.columns and col != new_index_name]
        if cols_to_drop_final:
            df = df.drop(columns=cols_to_drop_final)
            logs.append(f"Dropped original time column(s): {cols_to_drop_final}.")
        
        logs.append(f"Time index '{new_index_name}' set successfully.")

    except Exception as e:
        logs.append(f"ERROR: Failed to assemble/parse time index: {e}")
        # Potentially re-raise or return df in its current state depending on desired error handling
        raise ValueError(f"Failed to assemble/parse time index: {e}") from e
        
    return df, new_index_name, logs

def analyze_time_index_regularity(idx: pd.DatetimeIndex, expected_freq_str: Optional[str] = None) -> dict:
    """
    Analyzes the regularity of a DatetimeIndex.

    Args:
        idx (pd.DatetimeIndex): The DatetimeIndex to analyze.
        expected_freq_str (Optional[str]): An expected frequency string (e.g., 'D', 'MS').

    Returns:
        dict: A dictionary containing regularity analysis results.
    """
    if not isinstance(idx, pd.DatetimeIndex):
        raise TypeError("Input must be a pandas DatetimeIndex.")

    results = {}
    results['is_monotonic_increasing'] = idx.is_monotonic_increasing
    results['has_duplicates'] = idx.has_duplicates
    results['num_duplicates'] = idx.duplicated().sum()
    
    inferred_freq = pd.infer_freq(idx)
    results['inferred_freq'] = inferred_freq

    num_gaps = 0
    gap_details = []
    is_regular = False

    target_freq_for_gap_check = expected_freq_str if expected_freq_str else inferred_freq

    if target_freq_for_gap_check:
        try:
            full_range = pd.date_range(start=idx.min(), end=idx.max(), freq=target_freq_for_gap_check)
            missing_dates = full_range.difference(idx)
            num_gaps = len(missing_dates)
            if num_gaps > 0:
                gap_details = [str(date) for date in missing_dates[:10]] # Show first 10 gaps
                if num_gaps > 10:
                    gap_details.append(f"... and {num_gaps - 10} more gaps.")
            
            # A series is regular if it has an inferable frequency, no duplicates, and no gaps according to that frequency.
            if inferred_freq and not results['has_duplicates'] and num_gaps == 0:
                 is_regular = True
            elif target_freq_for_gap_check and not results['has_duplicates'] and num_gaps == 0 and idx.freqstr == target_freq_for_gap_check:
                 is_regular = True


        except Exception as e: # Handle cases where date_range might fail (e.g. with some business day freqs if not aligned)
            logger.warning(f"Could not create full date range for gap analysis with freq '{target_freq_for_gap_check}': {e}")
            results['gap_analysis_error'] = str(e)
            # If we can't check gaps, regularity is harder to confirm robustly based on this check
            if inferred_freq and not results['has_duplicates']: # Fallback: regular if freq inferred and no duplicates
                is_regular = True


    results['num_gaps'] = num_gaps
    results['gap_details'] = gap_details
    results['is_regular'] = is_regular
    
    if not results['is_monotonic_increasing']:
        logger.warning("Time index is not monotonically increasing.")
    if results['has_duplicates']:
        logger.warning(f"Time index has {results['num_duplicates']} duplicate values.")
    if not inferred_freq:
        logger.warning("Could not infer frequency for the time index. It might be irregular.")
    if num_gaps > 0:
        logger.warning(f"Time index has {num_gaps} gaps according to frequency '{target_freq_for_gap_check}'.")

    return results

def set_and_validate_frequency(
    data: pd.DataFrame,
    target_freq_str: Optional[str] = None,
    resample_if_mismatch: bool = False,
    resample_agg_methods: Optional[dict[str, Union[str, Callable]]] = None
) -> tuple[pd.DataFrame, str, list[str]]:
    """
    Sets and validates the frequency of the DataFrame's DatetimeIndex.

    Args:
        data (pd.DataFrame): DataFrame with a DatetimeIndex.
        target_freq_str (Optional[str]): Desired frequency string (e.g., "MS", "D").
        resample_if_mismatch (bool): If True, resample data if frequency doesn't match target_freq_str.
        resample_agg_methods (Optional[dict[str, Union[str, Callable]]]): Aggregation methods for resampling.

    Returns:
        tuple[pd.DataFrame, str, list[str]]:
            - Processed DataFrame.
            - Confirmed frequency string.
            - list of log messages.
    """
    df = data.copy()
    logs = []

    if not isinstance(df.index, pd.DatetimeIndex):
        logs.append("ERROR: DataFrame index is not a DatetimeIndex.")
        raise TypeError("DataFrame index must be a DatetimeIndex.")

    current_inferred_freq = pd.infer_freq(df.index)
    logs.append(f"Initial inferred frequency: {current_inferred_freq}")

    confirmed_freq = current_inferred_freq

    if target_freq_str:
        logs.append(f"Target frequency specified: {target_freq_str}")
        if current_inferred_freq == target_freq_str and df.index.freqstr == target_freq_str:
            logs.append(f"Current index frequency matches target frequency '{target_freq_str}'. No change needed.")
            confirmed_freq = target_freq_str
        else:
            logs.append(f"Current frequency '{current_inferred_freq}' does not match target '{target_freq_str}' or is not set explicitly.")
            try:
                # Try asfreq first - this fills with NaNs if dates are missing
                df_asfreq = df.asfreq(target_freq_str)
                nan_introduced = df_asfreq.isnull().sum().sum() - df.isnull().sum().sum()
                logs.append(f"Attempted df.asfreq('{target_freq_str}'). Introduced {nan_introduced} new NaN values.")
                
                # Check if asfreq resulted in a fully NaN dataframe for some columns, which might happen if no dates align
                if df_asfreq.empty or df_asfreq.isnull().all().all():
                    logs.append(f"WARNING: df.asfreq('{target_freq_str}') resulted in an empty or all-NaN DataFrame. This might indicate no alignment.")
                    if resample_if_mismatch:
                        logs.append(f"Proceeding with resampling due to asfreq issue and resample_if_mismatch=True.")
                    else:
                        logs.append(f"Keeping original data as resample_if_mismatch=False or asfreq failed severely.")
                        # Potentially return original df or raise error
                        return data, current_inferred_freq or "Irregular", logs


                # If asfreq worked (didn't empty df) and freq is now correct
                if df_asfreq.index.freqstr == target_freq_str:
                    df = df_asfreq
                    confirmed_freq = target_freq_str
                    logs.append(f"Successfully set frequency to '{target_freq_str}' using asfreq.")
                elif resample_if_mismatch: # asfreq didn't set freq correctly, or user wants resampling anyway
                    logs.append(f"Frequency still not '{target_freq_str}' after asfreq, or resampling explicitly requested. Attempting resampling.")
                    
                    if resample_agg_methods is None:
                        resample_agg_methods = {}
                        for col in df.columns:
                            if pd.api.types.is_numeric_dtype(df[col]):
                                resample_agg_methods[col] = 'sum' # Default for numeric
                            else:
                                resample_agg_methods[col] = 'first' # Default for non-numeric
                        logs.append(f"Using default resampling aggregation methods: {resample_agg_methods}")
                    
                    df = df.resample(target_freq_str).agg(resample_agg_methods)
                    confirmed_freq = df.index.freqstr # Should be target_freq_str now
                    logs.append(f"Resampled data to '{target_freq_str}'. New frequency: {confirmed_freq}.")
                else:
                    logs.append(f"Could not set frequency to '{target_freq_str}' using asfreq, and resampling is disabled.")
                    # Keep df as is, confirmed_freq remains current_inferred_freq
            except Exception as e:
                logs.append(f"ERROR: Failed to set or resample frequency to '{target_freq_str}': {e}")
                # Keep df as is, confirmed_freq remains current_inferred_freq

    elif not current_inferred_freq:
        logs.append("WARNING: No target frequency specified and current index frequency is irregular (could not be inferred).")
        confirmed_freq = "Irregular"
    else: # No target_freq_str, but current_inferred_freq exists
        df = df.asfreq(current_inferred_freq) # Ensure the freq attribute is set on the index
        confirmed_freq = df.index.freqstr
        logs.append(f"No target frequency specified. Using inferred frequency: {confirmed_freq}.")

    # Final validation
    if df.index.freq is None and confirmed_freq != "Irregular":
        logs.append(f"WARNING: Final index frequency attribute is None, but expected '{confirmed_freq}'. The index might still be irregular.")
    elif df.index.freq is not None:
        logs.append(f"Final validated index frequency: {df.index.freqstr}")
        confirmed_freq = df.index.freqstr # Update with the actual freqstr

    return df, confirmed_freq, logs

def get_descriptive_stats(data: pd.DataFrame, include_dtypes: Optional[list[str]] = None) -> pd.DataFrame:
    """
    Calculates descriptive statistics for the DataFrame.

    Args:
        data (pd.DataFrame): Input DataFrame.
        include_dtypes (Optional[list[str]]): list of dtypes to include (e.g., ['number', 'object']).
                                            If None, uses pandas default.

    Returns:
        pd.DataFrame: DataFrame containing descriptive statistics.
    """
    try:
        if include_dtypes:
            stats = data.describe(include=include_dtypes)
        else:
            stats = data.describe(include='all')
        return stats
    except Exception as e:
        logger.error(f"Error generating descriptive statistics: {e}")
        return pd.DataFrame() # Return empty DataFrame on error

def get_missing_value_summary(data: pd.DataFrame) -> pd.DataFrame:
    """
    Summarizes missing values per column (count and percentage).

    Args:
        data (pd.DataFrame): Input DataFrame.

    Returns:
        pd.DataFrame: DataFrame with missing value counts and percentages.
    """
    missing_counts = data.isnull().sum()
    missing_percentages = (missing_counts / len(data)) * 100
    summary_df = pd.DataFrame({
        'Missing Count': missing_counts,
        'Missing Percentage': missing_percentages
    })
    summary_df = summary_df[summary_df['Missing Count'] > 0].sort_values(by='Missing Percentage', ascending=False)
    if summary_df.empty:
        logger.info("No missing values found in the dataset.")
    else:
        logger.info("Missing value summary generated.")
    return summary_df