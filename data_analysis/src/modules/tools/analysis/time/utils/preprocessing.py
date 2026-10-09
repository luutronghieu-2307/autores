import pandas as pd
import numpy as np
from typing import Optional, Union, Callable
from statsmodels.tsa.seasonal import seasonal_decompose
import logging

logger = logging.getLogger(__name__)

def handle_missing_values(
    series: pd.Series,
    method: str,
    seasonal_period: Optional[int] = None,
    fill_value: Optional[any] = None,
    series_scale: Optional[str] = None # Currently not used for logic, but kept for API consistency
) -> pd.Series:
    """
    Handles missing values in a pandas Series.

    Args:
        series (pd.Series): Input Series.
        method (str): Method to handle missing values.
                      Options: 'mean', 'median', 'mode', 'ffill', 'bfill',
                               'linear_interpolate', 'seasonal_mean', 'fill_value',
                               'remove_rows' (returns series with NaNs, caller handles removal).
        seasonal_period (Optional[int]): Seasonal period for 'seasonal_mean'.
        fill_value (Optional[any]): Value to use for 'fill_value' method.
        series_scale (Optional[str]): Scale of the series (e.g., 'nominal', 'ratio').
                                      Currently for informational purposes or future expansion.

    Returns:
        pd.Series: Series with missing values handled.
    """
    s_out = series.copy()
    if not s_out.isnull().any():
        logger.info(f"No missing values to handle in series '{s_out.name}'.")
        return s_out

    if method == 'mean':
        if pd.api.types.is_numeric_dtype(s_out):
            s_out = s_out.fillna(s_out.mean())
        else:
            logger.warning(f"Cannot apply 'mean' imputation to non-numeric series '{s_out.name}'. Returning original.")
            return series
    elif method == 'median':
        if pd.api.types.is_numeric_dtype(s_out):
            s_out = s_out.fillna(s_out.median())
        else:
            logger.warning(f"Cannot apply 'median' imputation to non-numeric series '{s_out.name}'. Returning original.")
            return series
    elif method == 'mode':
        s_out = s_out.fillna(s_out.mode().iloc[0] if not s_out.mode().empty else np.nan) # Use first mode if multiple
    elif method == 'ffill':
        s_out = s_out.ffill()
    elif method == 'bfill':
        s_out = s_out.bfill()
    elif method == 'linear_interpolate':
        s_out = s_out.interpolate(method='linear')
    elif method == 'seasonal_mean':
        if seasonal_period is None or seasonal_period <= 0:
            logger.error("Seasonal period must be provided and positive for 'seasonal_mean' imputation.")
            raise ValueError("Seasonal period must be provided and positive for 'seasonal_mean'.")
        if not isinstance(s_out.index, pd.DatetimeIndex):
            logger.error("Series index must be DatetimeIndex for 'seasonal_mean' imputation.")
            raise TypeError("Series index must be DatetimeIndex for 'seasonal_mean'.")
        
        # Calculate mean for each period in the season
        seasonal_means = s_out.groupby(s_out.index.month if seasonal_period == 12 else  # Common cases
                                       s_out.index.dayofweek if seasonal_period == 7 else
                                       s_out.index.quarter if seasonal_period == 4 else
                                       (s_out.index.to_series().dt.isocalendar().week if seasonal_period == 52 else
                                       (s_out.index.year * seasonal_period + (s_out.index.dayofyear // (365.25/seasonal_period))) # Generic
                                       )).transform('mean')
        s_out = s_out.fillna(seasonal_means)
        # If some seasonal means are still NaN (e.g., a whole season is missing), ffill/bfill
        s_out = s_out.ffill().bfill()

    elif method == 'fill_value':
        if fill_value is None:
            logger.error("'fill_value' cannot be None if method is 'fill_value'.")
            raise ValueError("'fill_value' cannot be None if method is 'fill_value'.")
        s_out = s_out.fillna(fill_value)
    elif method == 'remove_rows':
        # This function doesn't remove rows from a DataFrame, it just ensures NaNs are present.
        # The calling Tool function will handle row removal from the DataFrame.
        logger.info(f"Method 'remove_rows' selected for series '{s_out.name}'. NaNs will be returned for missing values.")
        # No action needed as NaNs are already there, or this method implies the caller will drop.
        pass # Series remains as is with NaNs
    else:
        logger.error(f"Invalid missing value handling method: {method}")
        raise ValueError(f"Invalid missing value handling method: {method}")

    if s_out.isnull().any() and method not in ['remove_rows']:
        logger.warning(f"Series '{s_out.name}' still contains NaNs after '{method}' imputation. Consider ffill/bfill as a final step if needed.")
    else:
        logger.info(f"Missing values handled for series '{s_out.name}' using method '{method}'.")
    return s_out

def detect_outliers(
    series: pd.Series,
    method: str = 'iqr',
    threshold: float = 1.5, # For IQR
    z_score_threshold: float = 3.0 # For Z-score
) -> pd.Series:
    """
    Detects outliers in a pandas Series.

    Args:
        series (pd.Series): Input Series.
        method (str): Method for outlier detection ('iqr' or 'zscore').
        threshold (float): IQR multiplier.
        z_score_threshold (float): Z-score threshold.

    Returns:
        pd.Series: Boolean Series, True where outliers are detected.
    """
    if not pd.api.types.is_numeric_dtype(series):
        logger.warning(f"Outlier detection skipped for non-numeric series '{series.name}'.")
        return pd.Series([False] * len(series), index=series.index)

    s_cleaned = series.dropna() # Perform on non-NA values
    if s_cleaned.empty:
        return pd.Series([False] * len(series), index=series.index)

    if method == 'iqr':
        q1 = s_cleaned.quantile(0.25)
        q3 = s_cleaned.quantile(0.75)
        iqr_val = q3 - q1
        lower_bound = q1 - threshold * iqr_val
        upper_bound = q3 + threshold * iqr_val
        outlier_mask = (series < lower_bound) | (series > upper_bound)
    elif method == 'zscore':
        mean_val = s_cleaned.mean()
        std_val = s_cleaned.std()
        if std_val == 0: # Avoid division by zero if all values are the same
            outlier_mask = pd.Series([False] * len(series), index=series.index)
        else:
            z_scores = (series - mean_val) / std_val
            outlier_mask = z_scores.abs() > z_score_threshold
    else:
        logger.error(f"Invalid outlier detection method: {method}")
        raise ValueError(f"Invalid outlier detection method: {method}")
    
    logger.info(f"{outlier_mask.sum()} outliers detected in series '{series.name}' using method '{method}'.")
    return outlier_mask

def treat_outliers(
    series: pd.Series,
    outlier_mask: pd.Series, # Boolean series indicating outliers
    method: str = 'cap_floor_iqr',
    threshold: float = 1.5, # For IQR capping
    z_score_threshold: float = 3.0, # For Z-score capping
    replacement_value: Optional[float] = None
) -> pd.Series:
    """
    Treats outliers in a pandas Series based on a provided outlier mask.

    Args:
        series (pd.Series): Input Series.
        outlier_mask (pd.Series): Boolean Series (True for outliers).
        method (str): Method for treating outliers ('cap_floor_iqr', 'cap_floor_zscore',
                      'replace_with_value', 'remove' (marks as NaN)).
        threshold (float): IQR multiplier for capping.
        z_score_threshold (float): Z-score for capping.
        replacement_value (Optional[float]): Value for 'replace_with_value'.

    Returns:
        pd.Series: Series with outliers treated.
    """
    s_out = series.copy()
    if not outlier_mask.any():
        logger.info(f"No outliers to treat in series '{s_out.name}'.")
        return s_out
    
    if not pd.api.types.is_numeric_dtype(s_out):
        logger.warning(f"Outlier treatment skipped for non-numeric series '{s_out.name}'.")
        return series

    if method == 'cap_floor_iqr':
        q1 = s_out[~outlier_mask].quantile(0.25) # Calculate on non-outliers if possible, or all data
        q3 = s_out[~outlier_mask].quantile(0.75)
        iqr_val = q3 - q1
        lower_bound = q1 - threshold * iqr_val
        upper_bound = q3 + threshold * iqr_val
        s_out[s_out < lower_bound] = lower_bound
        s_out[s_out > upper_bound] = upper_bound
    elif method == 'cap_floor_zscore':
        mean_val = s_out[~outlier_mask].mean()
        std_val = s_out[~outlier_mask].std()
        if std_val == 0:
             logger.warning(f"Std deviation is zero for series '{s_out.name}' (non-outlier part). Cannot cap with Z-score.")
        else:
            lower_bound = mean_val - z_score_threshold * std_val
            upper_bound = mean_val + z_score_threshold * std_val
            s_out[s_out < lower_bound] = lower_bound
            s_out[s_out > upper_bound] = upper_bound
    elif method == 'replace_with_value':
        if replacement_value is None:
            logger.error("Replacement value must be provided for 'replace_with_value' method.")
            raise ValueError("Replacement value must be provided for 'replace_with_value' method.")
        s_out[outlier_mask] = replacement_value
    elif method == 'remove': # Marks as NaN, actual row removal is handled by caller
        s_out[outlier_mask] = np.nan
    else:
        logger.error(f"Invalid outlier treatment method: {method}")
        raise ValueError(f"Invalid outlier treatment method: {method}")

    logger.info(f"Outliers treated for series '{s_out.name}' using method '{method}'.")
    return s_out

def create_dummy_variables_for_events(
    series_index: pd.DatetimeIndex,
    event_dates: list[Union[str, pd.Timestamp]],
    event_name_prefix: str = "event_",
    window_before: int = 0,
    window_after: int = 0
) -> pd.DataFrame:
    """
    Creates dummy variables for specified event dates, aligned with a series index.

    Args:
        series_index (pd.DatetimeIndex): Index of the time series to align dummies with.
        event_dates (list[Union[str, pd.Timestamp]]): list of event dates.
        event_name_prefix (str): Prefix for dummy variable column names.
        window_before (int): Number of periods before the event to mark as 1.
        window_after (int): Number of periods after the event to mark as 1.

    Returns:
        pd.DataFrame: DataFrame containing the dummy variable columns.
    """
    if not isinstance(series_index, pd.DatetimeIndex):
        raise TypeError("series_index must be a pandas DatetimeIndex.")

    parsed_event_dates = pd.to_datetime(event_dates)
    dummy_df = pd.DataFrame(index=series_index)

    for i, event_date in enumerate(parsed_event_dates):
        col_name = f"{event_name_prefix}{i+1}_{event_date.strftime('%Y%m%d')}"
        dummy_series = pd.Series(0, index=series_index, dtype=int)
        
        # Find closest index points if exact match is not there (especially with windows)
        # This requires the index to have a frequency for offset operations
        if series_index.freq:
            try:
                event_loc = series_index.get_loc(event_date, method='nearest')
                actual_event_time_in_index = series_index[event_loc]

                start_date = actual_event_time_in_index - pd.Timedelta(days=window_before) if series_index.freq.name in ['D', 'B'] else actual_event_time_in_index - pd.offsets.Day(window_before) # More generic
                end_date = actual_event_time_in_index + pd.Timedelta(days=window_after) if series_index.freq.name in ['D', 'B'] else actual_event_time_in_index + pd.offsets.Day(window_after)
                
                # Adjust for frequency if not daily
                if series_index.freq not in ['D', 'B']: # e.g. 'MS', 'M', 'QS', 'Q', 'AS', 'A'
                    # This needs more careful handling based on the specific frequency
                    # For simplicity, we'll mark the periods that contain these dates
                    # A more robust way would be to use offsets based on the index frequency
                    # e.g., actual_event_time_in_index - window_before * series_index.freq
                    # However, this can be complex if window_before is not an integer multiple of freq.
                    # The current approach marks the single period for the event_date and windows around it.
                    
                    # For window, we find the range in the index
                    start_idx = series_index.searchsorted(start_date, side='left')
                    end_idx = series_index.searchsorted(end_date, side='right') # exclusive for slicing
                    
                    if start_idx < len(series_index) and end_idx > start_idx :
                         dummy_series.iloc[start_idx:end_idx] = 1
                    elif actual_event_time_in_index in series_index: # Fallback if window calc is tricky
                         dummy_series[actual_event_time_in_index] = 1

                else: # Daily or business daily frequency
                    mask = (series_index >= start_date) & (series_index <= end_date)
                    dummy_series[mask] = 1

            except KeyError:
                logger.warning(f"Event date {event_date} (or nearest) not found in series_index. Skipping for dummy '{col_name}'.")
                continue
            except Exception as e:
                logger.error(f"Error processing event {event_date} for dummy '{col_name}': {e}")
                continue

        elif event_date in series_index: # No frequency, exact match only, no window
             dummy_series[event_date] = 1
             if window_before > 0 or window_after > 0:
                 logger.warning(f"Windows for event dummies ignored for series_index without frequency for event {event_date}.")
        else:
            logger.warning(f"Event date {event_date} not found in series_index (and index has no freq). Skipping for dummy '{col_name}'.")
            continue
            
        dummy_df[col_name] = dummy_series
    
    logger.info(f"Created {len(dummy_df.columns)} dummy variables for events.")
    return dummy_df

def create_dummy_variables_from_categorical(
    data: pd.DataFrame,
    column_name: str,
    prefix: Optional[str] = None,
    drop_first: bool = False
) -> tuple[pd.DataFrame, list[str]]:
    """
    Creates dummy variables from a categorical column.

    Args:
        data (pd.DataFrame): Input DataFrame.
        column_name (str): Name of the categorical column.
        prefix (Optional[str]): Prefix for the new dummy columns.
        drop_first (bool): Whether to drop the first category to avoid multicollinearity.

    Returns:
        tuple[pd.DataFrame, list[str]]:
            - DataFrame with original column dropped and new dummy columns added.
            - list of names of the created dummy columns.
    """
    if column_name not in data.columns:
        logger.error(f"Column '{column_name}' not found in DataFrame for dummy creation.")
        raise ValueError(f"Column '{column_name}' not found for dummy creation.")

    df_out = data.copy()
    dummies = pd.get_dummies(df_out[column_name], prefix=prefix or column_name, drop_first=drop_first, dtype=int)
    dummy_col_names = list(dummies.columns)
    
    df_out = pd.concat([df_out.drop(columns=[column_name]), dummies], axis=1)
    
    logger.info(f"Created {len(dummy_col_names)} dummy variables from column '{column_name}'. New columns: {dummy_col_names}")
    return df_out, dummy_col_names

def aggregate_series_to_frequency(
    series: pd.Series,
    target_frequency: str,
    aggregation_method: Union[str, Callable] = 'sum'
) -> pd.Series:
    """
    Aggregates a time series to a new, typically lower, frequency.

    Args:
        series (pd.Series): Input time series with a DatetimeIndex.
        target_frequency (str): Target frequency string (e.g., 'M', 'Q', 'A').
        aggregation_method (Union[str, Callable]): Aggregation method ('sum', 'mean', 'first', 'last', etc.).

    Returns:
        pd.Series: Aggregated time series.
    """
    if not isinstance(series.index, pd.DatetimeIndex):
        logger.error("Series index must be a DatetimeIndex for frequency aggregation.")
        raise TypeError("Series index must be a DatetimeIndex.")
    
    try:
        aggregated_series = series.resample(target_frequency).agg(aggregation_method)
        logger.info(f"Series '{series.name}' aggregated to frequency '{target_frequency}' using method '{aggregation_method}'.")
        return aggregated_series
    except Exception as e:
        logger.error(f"Error aggregating series '{series.name}' to frequency '{target_frequency}': {e}")
        raise

def decompose_time_series(
    series: pd.Series,
    model_type: str = 'additive', # 'additive' or 'multiplicative'
    period: Optional[int] = None,
    extrapolate_trend: Union[str, int] = 'freq'
) -> tuple[pd.DataFrame, dict[str,str]]:
    """
    Decomposes a time series into trend, seasonal, and residual components.

    Args:
        series (pd.Series): Input time series.
        model_type (str): Type of decomposition ('additive' or 'multiplicative').
        period (Optional[int]): Seasonal period. If None, inferred if possible.
        extrapolate_trend (Union[str, int]): Method for extrapolating trend at ends.

    Returns:
        tuple[pd.DataFrame, dict[str,str]]:
            - DataFrame with 'trend', 'seasonal', 'resid' components.
            - Mapping of generic component names to actual output column names.
    """
    if not isinstance(series.index, pd.DatetimeIndex):
        logger.warning("Series index is not DatetimeIndex. Decomposition might be less meaningful or fail.")

    try:
        # statsmodels seasonal_decompose requires period for series with no freq or non-standard freq
        if period is None and (series.index.freq is None or not hasattr(series.index, 'freqstr')):
             # Try to infer period if common frequencies are present in index diffs
            if len(series.index) > 2:
                diffs = (series.index[1:] - series.index[:-1]).to_series()
                common_diff = diffs.mode()
                if not common_diff.empty:
                    # This is a very basic inference, might need refinement
                    # e.g. for monthly data, common_diff might be ~30 days.
                    # For now, this is a placeholder for more robust period inference.
                    # A common approach is to check ACF for peaks.
                    logger.warning(f"Period for decomposition not provided and index frequency is ambiguous. Attempting basic inference (this may not be robust).")
                    # This part is tricky; for now, we'll let seasonal_decompose raise error if period is truly needed and not inferable by it.
        
        decomposition = seasonal_decompose(
            series.dropna(), # Decompose on non-NA values
            model=model_type,
            period=period,
            extrapolate_trend=extrapolate_trend
        )
        
        comp_df = pd.DataFrame({
            'trend': decomposition.trend,
            'seasonal': decomposition.seasonal,
            'resid': decomposition.resid,
            'observed': decomposition.observed # often same as input series if no NaNs initially
        })
        
        # Create prefixed column names for clarity if series has a name
        prefix = f"{series.name}_" if series.name else ""
        col_mapping = {
            'trend': f"{prefix}trend",
            'seasonal': f"{prefix}seasonal",
            'resid': f"{prefix}resid",
            'observed': f"{prefix}observed"
        }
        comp_df.columns = [col_mapping[col] for col in comp_df.columns]

        logger.info(f"Time series '{series.name}' decomposed (model: {model_type}, period: {period}).")
        return comp_df, col_mapping
    except Exception as e:
        logger.error(f"Error decomposing series '{series.name}': {e}")
        raise

def combine_variables(
    data: pd.DataFrame,
    input_columns: list[str],
    output_column_name: str,
    method: str = 'sum', # 'sum', 'mean', 'weighted_sum'
    weights: Optional[list[float]] = None
) -> pd.DataFrame:
    """
    Combines multiple input columns into a single output column.

    Args:
        data (pd.DataFrame): Input DataFrame.
        input_columns (list[str]): list of column names to combine.
        output_column_name (str): Name for the new combined column.
        method (str): Combination method ('sum', 'mean', 'weighted_sum').
        weights (Optional[list[float]]): Weights for 'weighted_sum', must match len(input_columns).

    Returns:
        pd.DataFrame: DataFrame with the new combined column.
    """
    df_out = data.copy()
    if not all(col in df_out.columns for col in input_columns):
        missing_cols = [col for col in input_columns if col not in df_out.columns]
        logger.error(f"Input columns not found for combination: {missing_cols}")
        raise ValueError(f"Input columns not found: {missing_cols}")

    if method == 'sum':
        df_out[output_column_name] = df_out[input_columns].sum(axis=1)
    elif method == 'mean':
        df_out[output_column_name] = df_out[input_columns].mean(axis=1)
    elif method == 'weighted_sum':
        if weights is None or len(weights) != len(input_columns):
            logger.error("Weights must be provided and match the number of input columns for 'weighted_sum'.")
            raise ValueError("Invalid weights for 'weighted_sum'.")
        df_out[output_column_name] = np.average(df_out[input_columns], axis=1, weights=weights)
    else:
        logger.error(f"Invalid combination method: {method}")
        raise ValueError(f"Invalid combination method: {method}")

    logger.info(f"Variables {input_columns} combined into '{output_column_name}' using method '{method}'.")
    return df_out