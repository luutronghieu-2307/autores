import pandas as pd
import numpy as np
from scipy import stats
from sklearn.preprocessing import MinMaxScaler, StandardScaler
from typing import Any
import logging

logger = logging.getLogger(__name__)

# --- Log Transform ---
def apply_log_transform(series: pd.Series) -> pd.Series:
    """Applies natural logarithm transformation. Handles non-positive values by adding a small constant."""
    if (series <= 0).any():
        min_positive = series[series > 0].min()
        # If all are non-positive or no positive values, log transform is problematic
        if pd.isna(min_positive): 
            logger.warning(f"Series '{series.name}' contains no positive values. Log transform cannot be applied directly. Returning original series.")
            return series.copy() # Or raise error
        
        # Add a small constant to make all values positive, based on smallest positive value or 1 if none.
        # This is a common heuristic but might not always be appropriate.
        constant_to_add = min_positive * 0.01 if min_positive > 0.01 else 0.001 
        series_transformed = np.log(series + constant_to_add)
        logger.warning(f"Series '{series.name}' contains non-positive values. Added {constant_to_add} before log transform.")
    else:
        series_transformed = np.log(series)
    logger.info(f"Log transform applied to series '{series.name}'.")
    return series_transformed.rename(f"{series.name}_log")

def inverse_log_transform(series: pd.Series) -> pd.Series:
    """Applies exponential function to inverse log transformation."""
    # Note: If a constant was added in apply_log_transform for non-positive values,
    # subtracting it here would require storing that constant.
    # For simplicity, this inverse assumes no constant was added or that its effect is acceptable.
    # A more robust system would pass the constant in inversion_state.
    original_name = series.name.replace("_log", "") if series.name and "_log" in series.name else f"{series.name}_orig"
    logger.info(f"Inverse log transform applied to series '{series.name}'.")
    return np.exp(series).rename(original_name)

# --- Square Root Transform ---
def apply_sqrt_transform(series: pd.Series) -> pd.Series:
    """Applies square root transformation. Handles negative values by returning NaN or original."""
    if (series < 0).any():
        logger.warning(f"Series '{series.name}' contains negative values. Sqrt transform will result in NaNs for these. Consider Box-Cox or other methods.")
        # Option: return series.copy() or raise error, or proceed with NaNs
    series_transformed = np.sqrt(series)
    logger.info(f"Square root transform applied to series '{series.name}'.")
    return series_transformed.rename(f"{series.name}_sqrt")

def inverse_sqrt_transform(series: pd.Series) -> pd.Series:
    """Applies squaring to inverse square root transformation."""
    original_name = series.name.replace("_sqrt", "") if series.name and "_sqrt" in series.name else f"{series.name}_orig"
    logger.info(f"Inverse square root transform applied to series '{series.name}'.")
    return np.square(series).rename(original_name)

# --- Box-Cox Transform ---
def apply_box_cox_transform(series: pd.Series) -> tuple[pd.Series, float]:
    """
    Applies Box-Cox transformation. Series must be positive.
    Adds a small constant if series contains zeros or negative values, though Box-Cox is ideally for positive data.
    """
    s_copy = series.copy()
    if (s_copy <= 0).any():
        min_val = s_copy.min()
        # Shift data to be positive. This is a common heuristic.
        shift = abs(min_val) + 1e-6 if min_val <= 0 else 1e-6 # Add small constant if min is 0
        s_copy = s_copy + shift
        logger.warning(f"Series '{series.name}' contains non-positive values. Shifted by {shift} before Box-Cox transform.")
    
    try:
        transformed_data, lambda_val = stats.boxcox(s_copy.dropna()) # Drop NA for fitting lambda
        transformed_series = pd.Series(transformed_data, index=s_copy.dropna().index)
        # Reindex to original series index, filling NaNs if any were present initially
        transformed_series = transformed_series.reindex(series.index)

        logger.info(f"Box-Cox transform applied to series '{series.name}' with lambda = {lambda_val:.4f}.")
        return transformed_series.rename(f"{series.name}_boxcox"), lambda_val
    except ValueError as e: # e.g. if all values are identical after shift
        logger.error(f"Box-Cox transformation failed for series '{series.name}': {e}. Returning original series.")
        return series.copy(), np.nan # Or some indicator of failure

def inverse_box_cox_transform(series: pd.Series, lambda_val: float) -> pd.Series:
    """Applies inverse Box-Cox transformation."""
    if pd.isna(lambda_val):
        logger.warning(f"Lambda for Box-Cox inverse is NaN for series '{series.name}'. Returning series as is.")
        return series.copy()
        
    from scipy.special import inv_boxcox # Available in SciPy 1.0.0+
    
    # Note: If data was shifted in apply_box_cox_transform, that shift should be subtracted here.
    # This requires storing the shift amount. For simplicity, this is omitted here.
    # A more robust system would pass the shift in inversion_state.
    
    original_name = series.name.replace("_boxcox", "") if series.name and "_boxcox" in series.name else f"{series.name}_orig"
    try:
        if lambda_val == 0:
            inverted_series_data = np.exp(series.dropna())
        else:
            inverted_series_data = inv_boxcox(series.dropna(), lambda_val)
        
        inverted_series = pd.Series(inverted_series_data, index=series.dropna().index)
        inverted_series = inverted_series.reindex(series.index) # Reindex to original series index

        logger.info(f"Inverse Box-Cox transform applied to series '{series.name}' with lambda = {lambda_val:.4f}.")
        return inverted_series.rename(original_name)
    except Exception as e:
        logger.error(f"Inverse Box-Cox transformation failed for series '{series.name}': {e}. Returning series as is.")
        return series.copy()


# --- Differencing ---
def _get_head_values_for_inversion(series: pd.Series, d: int, D: int, m: int) -> pd.Series:
    """Helper to get initial values needed for inverse differencing."""
    num_seasonal_diff_values = D * m
    num_total_initial_values = d + num_seasonal_diff_values
    if len(series) < num_total_initial_values:
        raise ValueError(
            f"Series is too short (len {len(series)}) to extract {num_total_initial_values} initial values "
            f"for differencing (d={d}, D={D}, m={m})."
        )
    return series.iloc[:num_total_initial_values]


def apply_differencing(series: pd.Series, d: int = 1, D: int = 0, m: int = 0) -> tuple[pd.Series, dict[str, Any]]:
    """
    Applies regular (d) and/or seasonal (D) differencing.

    Args:
        series (pd.Series): Input time series.
        d (int): Order of regular differencing.
        D (int): Order of seasonal differencing.
        m (int): Seasonal period (required if D > 0).

    Returns:
        tuple[pd.Series, dict[str, Any]]:
            - Differenced series.
            - inversion_state_dict: {'d', 'D', 'm', 'original_head_values'}.
    """
    if D > 0 and m <= 0:
        raise ValueError("Seasonal period 'm' must be positive if seasonal differencing 'D' > 0.")
    if d < 0 or D < 0:
        raise ValueError("Differencing orders 'd' and 'D' must be non-negative.")

    s_diff = series.copy()
    original_head_values = _get_head_values_for_inversion(series, d, D, m)
    
    # Apply seasonal differencing first
    if D > 0:
        for _ in range(D):
            s_diff = s_diff.diff(m)
    
    # Apply regular differencing
    if d > 0:
        for _ in range(d):
            s_diff = s_diff.diff(1)
            
    s_diff = s_diff.dropna()
    
    inversion_state = {
        'd': d,
        'D': D,
        'm': m,
        'original_head_values': original_head_values
    }
    logger.info(f"Differencing applied to series '{series.name}' (d={d}, D={D}, m={m}).")
    return s_diff.rename(f"{series.name}_diff_d{d}_D{D}"), inversion_state

def inverse_differencing(differenced_series: pd.Series, inversion_state: dict[str, Any]) -> pd.Series:
    """
    Reconstructs the original series from a differenced series using stored head values.
    This implementation is inspired by pmdarima.utils.diff_inv but simplified.
    It iteratively reconstructs.
    """
    d = inversion_state['d']
    D = inversion_state['D']
    m = inversion_state['m']
    original_head_values = inversion_state['original_head_values']

    if d < 0 or D < 0:
        raise ValueError("Differencing orders 'd' and 'D' must be non-negative.")
    if D > 0 and m <= 0:
        raise ValueError("Seasonal period 'm' must be positive if D > 0 for inverse differencing.")

    # Start with the differenced series, prepending the necessary head values
    # The `original_head_values` contains enough initial values from the *original* series
    # to reconstruct. The differenced_series starts *after* these initial values were "lost"
    # due to differencing.

    # Length of the part of original_head_values that corresponds to the "differenced away" part
    n_head_diff_away = d + D * m 
    
    # The part of head_values that will be used as the actual starting points for reconstruction
    # These are values from the original series.
    reconstruction_base = original_head_values.iloc[:n_head_diff_away].copy()
    
    # The differenced series needs to be appended after these base values
    # The full length of the reconstructed series will be len(reconstruction_base) + len(differenced_series)
    
    # Create a target series of the final length, initialized with NaNs
    # The first part will be filled by reconstruction_base, the rest by iterative reconstruction
    full_length = len(reconstruction_base) + len(differenced_series)
    y = pd.Series(np.nan, index=pd.RangeIndex(full_length)) # Use a generic index for reconstruction ease
    
    # Place the known initial values (from original_head_values)
    y.iloc[:len(reconstruction_base)] = reconstruction_base.values

    # Place the differenced values that we need to "undifference"
    # These start right after the reconstruction_base values
    y.iloc[len(reconstruction_base):] = differenced_series.values
    
    # Inverse regular differencing (undo d applications of diff(1))
    if d > 0:
        for _ in range(d):
            # y[i] = y[i-1] + diff_y[i]
            # Here, y already contains the diff_y part for i >= d
            # and the original values for i < d.
            # We need to cumsum starting from the (d-1)th original value.
            # Example: if d=1, head is y[0]. diff_y starts at index 1.
            # y[1] = y[0] + diff_y[1]
            # y[2] = y[1] + diff_y[2] = (y[0]+diff_y[1]) + diff_y[2]
            # This is essentially a cumulative sum starting from an initial point.
            
            # The loop should reconstruct values from index `d` onwards
            for i in range(d, len(y)):
                y.iloc[i] = y.iloc[i-1] + y.iloc[i] # y.iloc[i] is currently the differenced value

    # Inverse seasonal differencing (undo D applications of diff(m))
    if D > 0:
        for _ in range(D):
            # y[i] = y[i-m] + seasonal_diff_y[i]
            # Similar to above, y contains seasonal_diff_y for i >= D*m
            # and partially reconstructed values for i < D*m.
            
            # The loop should reconstruct values from index `D*m` onwards
            # (More precisely, from `m` for the first seasonal undiff, then `2m` etc.
            # but the combined effect with regular diff means we iterate from `D*m` overall)
            # The values in y up to D*m (or d + D*m if d>0) are already set from original_head_values
            # or reconstructed by regular inverse diff.
            
            # The seasonal reconstruction starts from the m-th value of the current y
            for i in range(m, len(y)): # Iterate over the current state of y
                 y.iloc[i] = y.iloc[i-m] + y.iloc[i] # y.iloc[i] is the (partially) seasonally differenced value

    # Set the index from the original head values and extend it
    if isinstance(original_head_values.index, pd.DatetimeIndex) and original_head_values.index.freq:
        final_index = pd.date_range(start=original_head_values.index[0], periods=len(y), freq=original_head_values.index.freq)
        y.index = final_index
    else: # If no freq or not datetime, keep generic index or try to infer
        logger.warning("Original series index for inverse differencing was not a DatetimeIndex with frequency. Reconstructed series will have a RangeIndex.")

    original_name = differenced_series.name.replace(f"_diff_d{d}_D{D}", "") if differenced_series.name else "series_inverted_diff"
    logger.info(f"Inverse differencing applied to series '{differenced_series.name}' (d={d}, D={D}, m={m}).")
    return y.rename(original_name)


# --- Scaling ---
def apply_scaling(series: pd.Series, method: str = 'minmax') -> tuple[pd.Series, object]:
    """
    Applies scaling to the series.

    Args:
        series (pd.Series): Input time series.
        method (str): Scaling method ('minmax' or 'standard').

    Returns:
        tuple[pd.Series, object]:
            - Scaled series.
            - Fitted scaler object (from scikit-learn).
    """
    if not pd.api.types.is_numeric_dtype(series):
        logger.warning(f"Scaling is typically applied to numeric data. Series '{series.name}' is not numeric. Returning original.")
        return series.copy(), None

    s_values = series.dropna().values.reshape(-1, 1) # Scaler expects 2D array, handle NaNs by scaling non-NaN part
    if s_values.shape[0] == 0: # All NaNs
        logger.warning(f"Series '{series.name}' contains all NaNs. Cannot scale. Returning original.")
        return series.copy(), None

    if method == 'minmax':
        scaler = MinMaxScaler()
    elif method == 'standard':
        scaler = StandardScaler()
    else:
        logger.error(f"Invalid scaling method: {method}")
        raise ValueError(f"Invalid scaling method: {method}")

    scaled_values = scaler.fit_transform(s_values)
    
    # Create a new series for scaled data, aligning with original NaNs
    scaled_series = pd.Series(np.nan, index=series.index, name=f"{series.name}_{method}scaled")
    scaled_series[series.notna()] = scaled_values.flatten()
    
    logger.info(f"{method.capitalize()} scaling applied to series '{series.name}'.")
    return scaled_series, scaler

def inverse_scaling(scaled_series: pd.Series, scaler_object: object) -> pd.Series:
    """
    Applies inverse scaling using the fitted scaler object.

    Args:
        scaled_series (pd.Series): Scaled time series.
        scaler_object (object): Fitted scaler object (from scikit-learn's MinMaxScaler or StandardScaler).

    Returns:
        pd.Series: Original scale series.
    """
    if scaler_object is None:
        logger.warning(f"Scaler object is None for series '{scaled_series.name}'. Cannot inverse scale. Returning as is.")
        return scaled_series.copy()

    s_values = scaled_series.dropna().values.reshape(-1, 1)
    if s_values.shape[0] == 0: # All NaNs
        logger.info(f"Scaled series '{scaled_series.name}' is all NaNs. Returning as is.")
        return scaled_series.copy()

    try:
        original_values = scaler_object.inverse_transform(s_values)
        
        original_series = pd.Series(np.nan, index=scaled_series.index)
        original_series[scaled_series.notna()] = original_values.flatten()

        original_name = scaled_series.name
        if original_name:
            if "_minmaxscaled" in original_name:
                original_name = original_name.replace("_minmaxscaled", "_orig")
            elif "_standardscaled" in original_name:
                original_name = original_name.replace("_standardscaled", "_orig")
            else:
                original_name = f"{original_name}_orig"
        else:
            original_name = "series_inversed_scaled"

        logger.info(f"Inverse scaling applied to series '{scaled_series.name}'.")
        return original_series.rename(original_name)
    except Exception as e:
        logger.error(f"Error during inverse scaling for series '{scaled_series.name}': {e}")
        return scaled_series.copy() # Return original on error