summarized_content = """
# Summary of Research Methodology Document

## Data Types
- **Time Series**: Data collected sequentially over regular intervals (e.g., monthly revenue, daily temperature). Key characteristics: Analyzes trends, forecasts, and causal relationships.
- **Cross-Sectional**: Observations at a single point in time (e.g., income across households). Key characteristics: Examines relationships and group differences.
- **Categorical Quantitative**: Likert-scale or continuous data for factor analysis. Key characteristics: Explores latent structures and validates scales.
- **Panel Data**: Combines cross-sectional and time series, tracking entities over time (e.g., firm revenue across years). Key characteristics: Captures temporal and cross-sectional dynamics.
- **Spatial Data**: Geographically referenced data (points, lines, regions). Key characteristics: Analyzes spatial patterns and dependencies.
- **Event Data**: Tracks time to events (e.g., company bankruptcy). Key characteristics: Studies survival probabilities and influencing factors.

## Analytical Methods
- **Time Series**:
  - **ARIMA/SARIMA**: Forecasting; suits stationary or seasonal time series.
  - **ETS**: Forecasting; handles trends and seasonality with exponential smoothing.
  - **VAR/VECM**: Causal analysis; examines dynamic relationships among multiple time series.
  - **Granger Causality**: Tests predictive relationships; requires stationary data.
  - **ARIMAX/SARIMAX**: Enhanced forecasting with exogenous variables.
  - **Z-score/IQR**: Anomaly detection; identifies outliers in near-normal or skewed data.
- **Cross-Sectional**:
  - **Linear Regression**: Predicts or analyzes impacts; assumes linear relationships.
  - **Logistic Regression**: Predicts binary outcomes; estimates probabilities.
  - **Clustering**: Groups similar objects; unsupervised pattern discovery.
- **Categorical Quantitative**:
  - **EFA/CFA**: Explores or confirms latent factor structures.
  - **CB-SEM/PLS-SEM/GSCA**: Tests complex relationships in structural models; varies by sample size and data normality.
- **Panel Data**:
  - **Pooled OLS/FEM/REM**: Models panel data; addresses heterogeneity.
  - **GLS/FGLS/IV/2SLS/GMM**: Corrects violations like endogeneity or autocorrelation.
- **Spatial Data**:
  - **Moran’s I/GWR/Spatial 2SLS**: Detects spatial dependencies and heterogeneity.
- **Event Data**:
  - **Kaplan-Meier/Cox/AFT**: Analyzes survival times; handles censoring and competing risks.

## Applications
- **Economics**: Forecasting inflation (ARIMA), analyzing policy impacts (VAR, panel data), studying spatial price patterns (GWR).
- **Business Management**: Predicting sales (ETS), segmenting customers (clustering), assessing advertising effects (ARIMAX).
- **Tourism**: Forecasting visitor numbers (SARIMA), analyzing destination preferences (logistic regression), studying spatial tourism patterns (Moran’s I).
- **Health/Medicine**: Predicting hospital admissions (ETS), analyzing treatment survival (Cox), studying disease spread (spatial models).
- **Environment/Sociology**: Spatial analysis of ecological patterns, survival analysis of unemployment durations.
"""

keywords = ['AFT model', 'ARIMA', 'ARIMAX', 'CB-SEM', 'CFA', 'Cox model', 'EFA', 'ETS', 'FEM',
            'FGLS', 'GLS', 'GMM', 'GSCA', 'GWR', 'Granger Causality', 'Hausman-Taylor', 'IQR', 'IV/2SLS',
            'Kaplan-Meier', 'Likert', 'Moran’s I', 'PLS-SEM', 'Pooled OLS', 'Quantile Regression', 'REM', 'SARIMA',
            'Spatial 2SLS', 'Spatial GMM', 'VAR', 'VECM', 'WLS', 'Z-score', 'anomaly detection', 'binary variable',
            'categorical', 'causal analysis', 'causality', 'clustering', 'cointegration', 'component-based', 'covariance',
            'cross-sectional', 'data reduction', 'dependent variable', 'event data', 'exogenous variables', 'forecasting',
            'independent variable', 'latent factors', 'latent variables', 'linear regression', 'logistic regression', 'model fit',
            'multivariate', 'non-normal data', 'outliers', 'panel data', 'probability', 'quantitative', 'regression', 'reliability',
            'scale development', 'seasonality', 'segmentation', 'small sample', 'spatial data', 'stationarity', 'structural model',
            'survival analysis', 'theory-driven', 'time series', 'trend', 'unsupervised learning', 'variance']

method_keywords = [
    'AFT model', 'ARIMA', 'ARIMAX', 'CB-SEM', 'CFA', 'Cox model', 'EFA', 'ETS', 'FEM',
    'FGLS', 'GLS', 'GMM', 'GSCA', 'GWR', 'Granger Causality', 'Hausman-Taylor', 'IV/2SLS',
    'Kaplan-Meier', 'Moran’s I', 'PLS-SEM', 'Pooled OLS', 'Quantile Regression', 'REM', 'SARIMA',
    'Spatial 2SLS', 'Spatial GMM', 'VAR', 'VECM', 'WLS'
]


TOOLS_DOCUMENT = [
  {
    "name": "single_factor_scale_reliability_testing",
    "description": "Performs reliability analysis for a single independent factor, calculating Cronbach's Alpha to assess scale reliability. Analyzes observed variables, generates diagnostic tables, and suggests actions like removing variables with low CITC (< 0.3) or discarding the factor if unreliable.",
    "params": {
      "factor_key": "str, The identifier for the factor to analyze"
    },
    "keywords": ["Cronbach's Alpha", "Reliability Analysis", "Scale Reliability", "CITC"]
  },
  {
    "name": "run_reliability_analysis",
    "description": "Orchestrates reliability analysis for multiple independent latent factors and includes the dependent variable without analysis. Calls single_factor_scale_reliability_testing for each factor and suggests actions like removing variables.",
    "params": {},
    "keywords": ["Cronbach's Alpha", "Reliability Analysis", "Scale Reliability", "Latent Variables"]
  },
  {
    "name": "run_efa_analysis",
    "description": "Conducts Exploratory Factor Analysis (EFA) using PCA with Varimax rotation to identify latent factors. Performs KMO and Bartlett's tests, determines the number of factors, analyzes factor loadings, calculates variance explained, and assigns factors to compute scores. Suggests removing problematic items.",
    "params": {
        # target_role = params.get("target_role", "independent")  # "independent", "dependent", "all"
        # specific_factors = params.get("specific_factors", None)  # Optional: analyze specific factors only
      },
    "keywords": ["EFA", "PCA", "Varimax Rotation", "KMO", "Bartlett's Test", "Factor Loadings", "Variance Explained"]
  },
  {
    "name": "run_anova_ttest_analysis",
    "description": "Performs t-tests and ANOVA to evaluate the effect of demographic (nominal) variables on a dependent variable. Includes descriptive statistics, Levene's test for variance homogeneity, and suggests removing non-significant variables based on p-values.",
    "params": {
      # "demographic_cols": "List[str], List of column names for demographic variables to analyze (optional, defaults to nominal independent variables)",
    },
    "keywords": ["t-test", "ANOVA", "Levene's Test", "Descriptive Statistics"]
  },
  {
    "name": "run_regression_analysis",
    "description": "Conducts multiple regression analysis using OLS to assess the impact of independent variables (including latent variables) on a dependent variable. Evaluates model fit, checks multicollinearity (VIF), performs diagnostic tests (F-test, t-test, Durbin-Watson), and generates a residual plot. Suggests discarding non-significant factors or removing variables.",
    "params": {},
    "keywords": ["Multiple Regression", "OLS", "Durbin-Watson", "Fisher's F-test", "Student's t-test", "VIF", "Heteroscedasticity"]
  },
  {
    "name": "run_logistic_regression_analysis",
    "description": "Performs logistic regression analysis for binary dependent variables. Provides coefficients, odds ratios, fit metrics, and diagnostics. Suitable when dependent variable is binary/categorical.",
    "params": {},
    "keywords": ["Logistic Regression", "Binary Classification", "Odds Ratios", "Classification Metrics"]
  },
  {
    "name": "run_clustering_analysis",
    "description": "Performs clustering analysis to identify groups/segments in data. Supports multiple algorithms and evaluates optimal number of clusters.",
    "params": {
      "algorithm": "str, Clustering algorithm - 'kmeans', 'gmm', 'hierarchical', 'dbscan' (default: 'kmeans')",
      # "k_range": "List[int], Range of k values to test (default: [2-12])",
      # "eps": "float, Epsilon parameter for DBSCAN (default: 'auto')",
      # "min_samples": "int, Minimum samples for DBSCAN (default: 5)"
    },
    "keywords": ["Clustering", "K-means", "GMM", "Hierarchical", "DBSCAN", "Segmentation"]
  },
  {
    "name": "run_cfa_analysis",
    "description": "Performs Confirmatory Factor Analysis (CFA) to test predefined measurement models. Validates factor structure with fit indices and provides modification suggestions.",
    "params": {
      "estimation_method": "str, Estimation method - 'MLW', 'ULS', 'GLS', 'WLS', 'DWLS', 'FIML' (default: 'MLW')",
      # "excluded_variables": "List[str], Variables to exclude from analysis (default: [])"
    },
    "keywords": ["CFA", "Confirmatory Factor Analysis", "Fit Indices", "Measurement Model", "Factor Structure"]
  },
  {
    "name": "run_cb_sem_analysis",
    "description": "Performs Covariance-Based Structural Equation Modeling (CB-SEM). Supports both full SEM with structural paths and CFA-only analysis. Enforces reflective measurement models.",
    "params": {
      "structural_paths": "List[Tuple[str, str]], Structural paths between latent variables (optional, if not provided runs CFA)",
      "estimation_method": "str, Estimation method - 'MLW', 'ULS', 'GLS', 'WLS', 'DWLS', 'FIML' (default: 'MLW')"
    },
    "keywords": ["CB-SEM", "Structural Equation Modeling", "Covariance-Based", "Structural Paths", "Reflective Model"]
  },
  {
    "name": "run_pls_sem_analysis",
    "description": "Performs Partial Least Squares Structural Equation Modeling (PLS-SEM). Suitable for predictive modeling and complex models with formative constructs.",
    "params": {
      "structural_paths": "List[Tuple[str, str]], Required structural relationships between latent variables",
      # "n_boot": "int, Number of bootstrap iterations for significance testing (default: 0)"
    },
    "keywords": ["PLS-SEM", "Partial Least Squares", "Predictive Modeling", "Bootstrap", "Formative Constructs"]
  },
  {
    "name": "run_gsca_analysis",
    "description": "Performs Generalized Structured Component Analysis (GSCA). Alternative to PLS-SEM with different estimation approach for component-based modeling.",
    "params": {
      "structural_paths": "List[Tuple[str, str]], Required structural paths between latent variables",
      # "n_boot": "int, Number of bootstrap samples (default: 0)"
    },
    "keywords": ["GSCA", "Component Analysis", "Structural Paths", "Bootstrap"]
  },
  {
    "name": "run_stationarity_assessment",
    "description": "Tests time series data for stationarity using statistical tests (ADF, KPSS) and suggests differencing transformations. Essential preprocessing for time series analysis.",
    "params": {
      # "target_variables": "List[str], Variables to test for stationarity (default: dependent/endogenous variables)",
      # "tests_to_run": "List[str], Statistical tests to perform - ['adf', 'kpss'] (default: ['adf', 'kpss'])",
      # "significance_level": "float, Significance level for tests (default: 0.05)",
      # "max_d": "int, Maximum regular differencing order (default: 2)",
      # "max_D": "int, Maximum seasonal differencing order (default: 1)",
      # "seasonal_period": "int, Seasonal period for differencing (default: inferred from frequency)"
    },
    "keywords": ["Stationarity", "ADF Test", "KPSS Test", "Differencing", "Time Series Preprocessing"]
  },
  {
    "name": "run_model_structure_identification",
    "description": "Identifies optimal model structures and parameters for time series analysis. Suggests specifications for ARIMA, SARIMA, ETS, VAR, VECM, and tests Granger causality.",
    "params": {
      "model_family": "str, Model type - 'ARIMA', 'SARIMA', 'ARIMAX', 'SARIMAX', 'ETS', 'VAR', 'VECM', 'GRANGER'",
      # "target_variables": "List[str], Target variable codes to analyze (default: all endogenous and dependent variables)",
      # "exogenous_variables": "List[str], Exogenous variable codes for ARIMAX/SARIMAX (optional, default: all indepenedent vars)",
      # "differencing_orders": "Dict, Differencing orders for each variable {var_code: {'d': int, 'D': int, 'm': int}} (optional)",
      # "seasonal_periods": "Dict, Seasonal periods for each variable {var_code: int} (optional)",
      "info_criterion": "str, Information criterion for model selection - 'AIC', 'BIC', 'HQIC' (default: 'AIC')"
    },
    "keywords": ["Model Selection", "ARIMA", "SARIMA", "ETS", "VAR", "VECM", "Granger Causality", "Time Series"]
  },
  {
    "name": "run_model_estimation_and_diagnostics",
    "description": "Fits specified time series models and performs comprehensive diagnostics. Combines model estimation with residual analysis, autocorrelation tests, and validation.",
    "params": {
      "model_family": "str, Model type - 'ARIMA', 'SARIMA', 'ARIMAX', 'SARIMAX', 'ETS', 'VAR', 'VECM'",
      # "target_variables_codes": "List[str], Target variable codes (default: dependent var)",
      # "target_variable_code": "str, Single target variable code (alternative to above)",
      # "exogenous_variables": "List[str], Exogenous variable codes (optional) (default: all independent variables)",
      # "model_order": "Tuple, ARIMA order (p, d, q) for SARIMAX",
      # "seasonal_order": "Tuple, Seasonal order (P, D, Q, s) for SARIMAX",
      # "trend": "str, Trend component ('c', 'ct', 'n') for SARIMAX",
      # "var_lags": "int, Number of lags for VAR model (default: 1)",
      # "significance_level_ljung_box": "float, P-value threshold for Ljung-Box test (default: 0.05)"
    },
    "keywords": ["Model Estimation", "Diagnostics", "SARIMAX", "ETS", "VAR", "VECM", "Ljung-Box", "Residual Analysis"]
  },
  {
    "name": "run_panel_model_selection",
    "description": "Comprehensive panel data analysis workflow. Implements econometric tests to choose between Pooled OLS, Fixed Effects, and Random Effects models. Includes diagnostic testing and robust standard errors.",
    "params": {
      # "significance_level": "float, Significance level for tests (default: 0.05)"
    },
    "keywords": ["Panel Data", "Fixed Effects", "Random Effects", "Pooled OLS", "Hausman Test", "Breusch-Pagan", "F-test"]
  },
  {
    "name": "run_advanced_panel_analysis",
    "description": "Advanced panel data analysis building on initial model selection. Performs IV/2SLS for endogeneity and GMM for dynamic panels. Includes non-linearity testing.",
    "params": {
      "analysis_type": "str, Type of analysis - 'IV' or 'GMM' (default: 'IV')",
      # "endogenous_vars": "List[str], Endogenous variables for IV analysis (default: all endogenous vars)",
      # "instrument_vars": "List[str], Instrument variables for IV analysis (default: all independent vars)",
      "test_non_linearity": "bool, Whether to test for non-linearity (default: False)",
      # "significance_level": "float, Significance level for tests (default: 0.05)"
    },
    "keywords": ["IV Regression", "2SLS", "GMM", "Dynamic Panel", "Endogeneity", "Instrumental Variables", "Non-linearity"]
  }
]


JSON_DOCUMENT = [
  {
    "id": "1",
    "title": "Số liệu chuỗi thời gian (Time Series Data)",
    "keywords": ["time series", "trend", "forecasting", "causal analysis"],
    "content": "Dữ liệu thu thập theo thứ tự thời gian, thường ở các khoảng đều đặn. Ví dụ: Doanh thu hàng tháng, nhiệt độ hàng ngày. Ứng dụng: Phân tích xu hướng, dự báo. Trong các lĩnh vực Kinh tế, Quản trị kinh doanh, Du lịch, Sức khỏe, và Y tế, các phương pháp phân tích phụ thuộc vào mục tiêu nghiên cứu (dự báo, phân tích xu hướng, kiểm định quan hệ nhân quả).",
    "subsections": [
      { "id": "1.1", "title": "Phân tích dự báo (Forecasting)" },
      { "id": "1.2", "title": "Phân tích quan hệ và nhân quả (Causal Analysis)" },
      { "id": "1.3", "title": "Phát hiện bất thường (Anomaly Detection)" }
    ]
  },
  {
    "id": "1.1",
    "title": "Phân tích dự báo (Forecasting)",
    "keywords": ["forecasting", "ARIMA", "SARIMA", "ETS"],
    "content": "Dự đoán giá trị tương lai dựa trên dữ liệu lịch sử. Phương pháp chủ đạo: ARIMA/SARIMA (phù hợp với chuỗi thời gian có hoặc không có mùa vụ), ETS (phù hợp với dữ liệu có xu hướng và mùa vụ). Công cụ đề xuất: R (gói forecast, tseries), Python (statsmodels, pmdarima), SPSS/Stata. Thực hành: Chia dữ liệu thành tập huấn luyện và kiểm tra để đánh giá mô hình.",
    "subsections": [
      { "id": "1.1.1", "title": "Các bước thực hiện phân tích ARIMA" },
      { "id": "1.1.2", "title": "Các bước thực hiện phân tích SARIMA" },
      { "id": "1.1.3", "title": "ETS (Exponential Smoothing)" }
    ]
  },
  {
    "id": "1.1.1",
    "title": "Các bước thực hiện phân tích ARIMA",
    "keywords": ["ARIMA", "stationarity", "forecasting"],
    "content": "Quy trình phân tích ARIMA bao gồm các bước: Chuẩn bị dữ liệu, kiểm tra tính dừng, xác định tham số p,d,q, ước lượng mô hình, kiểm tra mô hình, dự báo, báo cáo. Lưu ý: Nếu dữ liệu có mùa vụ, sử dụng SARIMA. Kiểm tra và xử lý giá trị ngoại lai trước khi xây dựng mô hình. Ứng dụng: Dự báo lạm phát (Kinh tế), doanh thu cửa hàng (Quản trị kinh doanh), lượng khách du lịch (Du lịch), số ca bệnh (Sức khỏe/Y tế). Công cụ: R (forecast, tseries), Python (statsmodels, pmdarima), SPSS/Stata.",
    "subsections": []
  },
  {
    "id": "1.1.2",
    "title": "Các bước thực hiện phân tích SARIMA",
    "keywords": ["SARIMA", "seasonality", "forecasting"],
    "content": "SARIMA là mở rộng của ARIMA, dùng cho chuỗi thời gian có mùa vụ. Quy trình tương tự ARIMA nhưng bổ sung xác định chu kỳ mùa vụ (m). Lưu ý: Xác định đúng chu kỳ mùa vụ, xử lý giá trị ngoại lai trước khi chạy mô hình. Ứng dụng: Dự báo chỉ số giá tiêu dùng (Kinh tế), doanh thu bán lẻ (Quản trị kinh doanh), lượng khách du lịch (Du lịch), số ca nhập viện (Sức khỏe/Y tế). Thực hành: Chia dữ liệu thành tập huấn luyện và kiểm tra.",
    "subsections": []
  },
  {
    "id": "1.1.3",
    "title": "ETS (Exponential Smoothing)",
    "keywords": ["ETS", "trend", "seasonality"],
    "content": "Phương pháp ETS (Error, Trend, Seasonality) phù hợp với dữ liệu có xu hướng và mùa vụ. Sử dụng trọng số giảm dần theo cấp số nhân để dự báo. Lưu ý: Xác định đúng thành phần xu hướng/mùa vụ (cộng hay nhân), xử lý giá trị ngoại lai. Ứng dụng: Dự báo chỉ số giá tiêu dùng (Kinh tế), doanh thu bán lẻ (Quản trị kinh doanh), lượng khách du lịch (Du lịch), số ca nhập viện (Sức khỏe/Y tế). Thực hành: Chia dữ liệu thành tập huấn luyện và kiểm tra.",
    "subsections": []
  },
  {
    "id": "1.2",
    "title": "Phân tích quan hệ và nhân quả (Causal Analysis)",
    "keywords": ["causal analysis", "VAR", "Granger Causality", "ARIMAX"],
    "content": "Kiểm tra mối quan hệ hoặc tác động giữa các chuỗi thời gian. Phương pháp: VAR (phân tích quan hệ nhiều chuỗi), Granger Causality (kiểm tra ảnh hưởng), ARIMAX (kết hợp ARIMA với biến độc lập). Ứng dụng: Tác động chính sách tiền tệ (Kinh tế), ảnh hưởng quảng cáo đến doanh số (Quản trị kinh doanh), tác động sự kiện văn hóa đến lượng khách (Du lịch), quan hệ chi tiêu y tế và tỷ lệ tử vong (Sức khỏe/Y tế). Công cụ: R (vars, tseries), Python (statsmodels), Stata.",
    "subsections": [
      { "id": "1.2.1", "title": "VAR (Vector AutoRegression)" },
      { "id": "1.2.2", "title": "VECM (Vector Error Correction Model)" },
      { "id": "1.2.3", "title": "Granger Causality" },
      { "id": "1.2.4", "title": "ARIMAX" }
    ]
  },
  {
    "id": "1.2.1",
    "title": "VAR (Vector AutoRegression)",
    "keywords": ["VAR", "multivariate", "time series"],
    "content": "Phân tích quan hệ động giữa nhiều chuỗi thời gian (ví dụ: lãi suất và lạm phát). Yêu cầu tất cả chuỗi dừng; nếu có đồng tích hợp, xem xét VECM. Lưu ý: Giới hạn số lượng biến (2-5), xử lý giá trị ngoại lai. Ứng dụng: Quan hệ GDP, lạm phát, lãi suất (Kinh tế), tác động chi phí quảng cáo và giá bán lên doanh thu (Quản trị kinh doanh), ảnh hưởng giá vé và sự kiện đến lượng khách (Du lịch), quan hệ chi tiêu y tế và tỷ lệ tử vong (Sức khỏe/Y tế).",
    "subsections": []
  },
  {
    "id": "1.2.2",
    "title": "VECM (Vector Error Correction Model)",
    "keywords": ["VECM", "cointegration", "time series"],
    "content": "Phân tích quan hệ động giữa các chuỗi thời gian có đồng tích hợp, tức có mối quan hệ cân bằng dài hạn. Yêu cầu kiểm tra đồng tích hợp trước. Lưu ý: Giới hạn số lượng biến (2-5), xử lý giá trị ngoại lai. Ứng dụng: Quan hệ dài hạn giữa GDP, lạm phát, lãi suất (Kinh tế), doanh thu và chi phí quảng cáo (Quản trị kinh doanh), lượng khách và chi tiêu du lịch (Du lịch), chi tiêu y tế và tỷ lệ tử vong (Sức khỏe/Y tế).",
    "subsections": []
  },
  {
    "id": "1.2.3",
    "title": "Granger Causality",
    "keywords": ["Granger Causality", "causality", "time series"],
    "content": "Kiểm tra xem một chuỗi thời gian có khả năng dự đoán chuỗi khác không (theo nghĩa thống kê). Yêu cầu chuỗi dừng; nếu không dừng, sai phân hoặc xem xét VECM. Lưu ý: Không chứng minh nhân quả thực sự, có thể bỏ sót yếu tố ẩn. Ứng dụng: Lãi suất dự đoán lạm phát (Kinh tế), chi phí quảng cáo dự đoán doanh thu (Quản trị kinh doanh), giá vé dự đoán lượng khách (Du lịch), chi tiêu y tế dự đoán tỷ lệ tử vong (Sức khỏe/Y tế).",
    "subsections": []
  },
  {
    "id": "1.2.4",
    "title": "ARIMAX",
    "keywords": ["ARIMAX", "exogenous variables", "forecasting"],
    "content": "Kết hợp ARIMA với biến độc lập ngoại sinh để cải thiện dự báo hoặc phân tích quan hệ. Nếu có mùa vụ, sử dụng SARIMAX. Lưu ý: Chọn biến ngoại sinh có ý nghĩa, xử lý giá trị ngoại lai. Ứng dụng: Dự báo lạm phát với lãi suất và giá dầu (Kinh tế), doanh thu với chi phí quảng cáo và giá bán (Quản trị kinh doanh), lượng khách với giá vé và sự kiện (Du lịch), số ca bệnh với chi tiêu y tế và nhiệt độ (Sức khỏe/Y tế).",
    "subsections": []
  },
  {
    "id": "1.3",
    "title": "Phát hiện bất thường (Anomaly Detection)",
    "keywords": ["anomaly detection", "Z-score", "IQR"],
    "content": "Xác định các điểm bất thường hoặc sự kiện đột biến trong chuỗi thời gian. Phương pháp: Z-score (phát hiện giá trị ngoại lệ, phù hợp dữ liệu gần chuẩn), IQR (phát hiện giá trị ngoại lệ, phù hợp dữ liệu lệch).",
    "subsections": [
      { "id": "1.3.1", "title": "Z-score" },
      { "id": "1.3.2", "title": "IQR: Phát hiện giá trị ngoại lệ" }
    ]
  },
  {
    "id": "1.3.1",
    "title": "Z-score",
    "keywords": ["Z-score", "outliers", "anomaly detection"],
    "content": "Phát hiện giá trị ngoại lệ bằng cách đo độ lệch của điểm dữ liệu so với trung bình, tính bằng số độ lệch chuẩn. Phù hợp với dữ liệu gần chuẩn. Lưu ý: Điều chỉnh ngưỡng Z-score (±2 hoặc ±3) tùy độ nhạy; xem xét mùa vụ/sự kiện trong chuỗi thời gian. Ứng dụng: Phát hiện giá cổ phiếu bất thường (Kinh tế), doanh thu bất thường do khuyến mãi (Quản trị kinh doanh), lượng khách tăng đột biến do sự kiện (Du lịch), số ca bệnh bất thường do dịch bệnh (Sức khỏe/Y tế).",
    "subsections": []
  },
  {
    "id": "1.3.2",
    "title": "IQR: Phát hiện giá trị ngoại lệ",
    "keywords": ["IQR", "outliers", "anomaly detection"],
    "content": "Phát hiện giá trị ngoại lệ dựa trên khoảng tứ phân vị, hiệu quả với dữ liệu lệch hoặc không chuẩn. Lưu ý: Ngưỡng 1.5 × IQR là tiêu chuẩn, có thể điều chỉnh; xem xét mùa vụ/sự kiện trong chuỗi thời gian. Ứng dụng: Phát hiện giá cổ phiếu bất thường (Kinh tế), doanh thu bất thường do khuyến mãi (Quản trị kinh doanh), lượng khách tăng đột biến do sự kiện (Du lịch), số ca bệnh bất thường do dịch bệnh (Sức khỏe/Y tế).",
    "subsections": []
  },
  {
    "id": "2",
    "title": "Dữ liệu cắt ngang (Cross-Sectional Data)",
    "keywords": ["cross-sectional", "regression", "clustering"],
    "content": "Dữ liệu cắt ngang được sử dụng để phân tích các quan sát tại một thời điểm cụ thể, thường áp dụng trong Kinh   các lĩnh vực như Kinh tế, Quản trị kinh doanh, Du lịch, Sức khỏe, và Y tế. Các phương pháp chính bao gồm hồi quy tuyến tính, hồi quy logistic, và phân cụm.",
    "subsections": [
      { "id": "2.1", "title": "Hồi quy tuyến tính" },
      { "id": "2.2", "title": "Hồi quy logistic" },
      { "id": "2.3", "title": "Phân cụm (clustering)" }
    ]
  },
  {
    "id": "2.1",
    "title": "Hồi quy tuyến tính",
    "keywords": ["linear regression", "dependent variable", "independent variable"],
    "content": "Phân tích hồi quy tuyến tính mô hình hóa mối quan hệ giữa một biến phụ thuộc (Y) và một hoặc nhiều biến độc lập (X), thường áp dụng trong Kinh tế, Quản trị kinh doanh, Du lịch, Sức khỏe, và Y tế để dự đoán, phân tích tác động, hoặc hiểu các yếu tố ảnh hưởng. Quy trình bao gồm: chuẩn bị dữ liệu, chọn biến, ước lượng mô hình, kiểm tra giả định, và diễn giải kết quả. Lưu ý: Hồi quy không chứng minh nhân quả, cần mẫu đủ lớn, và chỉ đưa các biến có cơ sở lý thuyết vào mô hình. Ứng dụng: Phân tích tác động của học vấn, kinh nghiệm lên thu nhập (Kinh tế); chi phí quảng cáo, giá bán lên doanh thu (Quản trị kinh doanh); giá vé, dịch vụ lên lượng khách (Du lịch); chi tiêu y tế, tuổi lên tỷ lệ hồi phục (Sức khỏe/Y tế).",
    "subsections": []
  },
  {
    "id": "2.2",
    "title": "Hồi quy logistic",
    "keywords": ["logistic regression", "binary variable", "probability"],
    "content": "Hồi quy logistic mô hình hóa mối quan hệ giữa một biến phụ thuộc nhị phân (Y, ví dụ: 0/1, Có/Không) và một hoặc nhiều biến độc lập (X), thường dùng để dự đoán xác suất hoặc phân tích yếu tố ảnh hưởng trong Kinh tế, Quản trị kinh doanh, Du lịch, Sức khỏe, và Y tế. Quy trình bao gồm: chuẩn bị dữ liệu, chọn biến, ước lượng mô hình, kiểm tra độ phù hợp, và diễn giải kết quả. Lưu ý: Không chứng minh nhân quả, cần mẫu đủ lớn (10-20 quan sát mỗi X), và chỉ đưa biến có cơ sở lý thuyết. Ứng dụng: Dự đoán khả năng vay nợ dựa trên thu nhập, học vấn (Kinh tế); khách hàng mua sản phẩm dựa trên chi phí quảng cáo, giá cả (Quản trị kinh doanh); quyết định đi du lịch dựa trên thu nhập, giá vé (Du lịch); nguy cơ mắc bệnh dựa trên tuổi, lối sống, điều kiện sức khỏe (Sức khỏe/Y tế).",
    "subsections": []
  },
  {
    "id": "2.3",
    "title": "Phân cụm (clustering)",
    "keywords": ["clustering", "unsupervised learning", "segmentation"],
    "content": "Phân tích phân cụm là phương pháp học máy không giám sát, nhóm các đối tượng thành cụm dựa trên sự tương đồng, không cần nhãn dữ liệu trước, hữu ích trong Kinh tế, Quản trị kinh doanh, Du lịch, Sức khỏe, và Y tế để khám phá mẫu, phân đoạn thị trường, hoặc nhận diện nhóm đối tượng. Quy trình bao gồm: chuẩn bị dữ liệu, chọn biến, xác định số cụm, thực hiện phân cụm, và đánh giá kết quả. Lưu ý: Chọn biến có ý nghĩa, số cụm hợp lý, và cần dữ liệu sạch. Ứng dụng: Phân nhóm quốc gia theo GDP, lạm phát, thất nghiệp (Kinh tế); phân đoạn khách hàng theo thu nhập, tần suất mua, sở thích (Quản trị kinh doanh); nhóm điểm đến theo lượng khách, chi phí, loại hình du lịch (Du lịch); phân nhóm bệnh nhân theo huyết áp, cân nặng, tiền sử bệnh (Sức khỏe/Y tế).",
    "subsections": []
  },
  {
    "id": "3",
    "title": "Số liệu phân loại (Categorical Quantitative Data)",
    "keywords": ["categorical", "quantitative", "Likert", "latent factors"],
    "content": " ",
    "subsections": [
      { "id": "3.1", "title": "Exploratory Factor Analysis (EFA)"},
      { "id": "3.2", "title": "Confirmatory Factor Analysis (CFA)"},
      { "id": "3.3", "title": "Phân tích mô cấu trúc tuyến tính dạng CB-SEM" },
      { "id": "3.4", "title": "Phân tích mô cấu trúc tuyến tính dạng PLS-SEM"},
      { "id": "3.5", "title": "Phân tích mô hình cấu trúc tuyến tính tổng quát dạng GSCA"}
    ]
  },
  {
    "id": "3.1",
    "title": "Exploratory Factor Analysis (EFA)",
    "keywords": ["EFA", "latent factors", "Likert", "data reduction", "scale development"],
    "content": "Exploratory Factor Analysis (EFA) là phương pháp thống kê để xác định các yếu tố tiềm ẩn từ biến quan sát (thường là dữ liệu Likert hoặc định lượng liên tục), nhằm khám phá cấu trúc cơ bản của dữ liệu. EFA hữu ích trong Kinh tế, Quản trị kinh doanh, Du lịch, Sức khỏe, Y tế để giảm chiều dữ liệu hoặc xây dựng thang đo. Lưu ý: Yêu cầu dữ liệu có tương quan, mẫu đủ lớn; diễn giải yếu tố dựa trên lý thuyết, tránh chủ quan; EFA để khám phá, không kiểm định giả thuyết (dùng CFA). Ứng dụng: Kinh tế (nhận thức chính sách), Quản trị (thang đo hài lòng), Du lịch (trải nghiệm), Sức khỏe (chất lượng y tế).",
    "analysis_steps": "",
    "actions_": "",
    "subsections": []
  },
  {
    "id": "3.2",
    "title": "Confirmatory Factor Analysis (CFA)",
    "keywords": ["CFA", "latent factors", "model fit", "theory-driven", "Likert"],
    "content": "Confirmatory Factor Analysis (CFA) kiểm định cấu trúc yếu tố tiềm ẩn giả định có phù hợp dữ liệu quan sát. Dựa trên lý thuyết, áp dụng trong Kinh tế, Quản trị kinh doanh, Du lịch, Sức khỏe, Y tế để xác nhận thang đo. Khác EFA, CFA cần lý thuyết rõ ràng. Lưu ý: Dữ liệu sạch, mẫu lớn, kết hợp chỉ số CFI, TLI, RMSEA, SRMR để đánh giá mô hình, không chỉ dựa vào Chi-Square. Ứng dụng: Kinh tế (thang đo chính sách thuế), Quản trị (hài lòng khách hàng), Du lịch (trải nghiệm), Sức khỏe (chất lượng y tế).",
    "subsections": []
  },
  {
    "id": "3.3",
    "title": "Phân tích mô cấu trúc tuyến tính dạng CB-SEM",
    "keywords": ["CB-SEM", "latent variables", "covariance", "structural model", "reliability"],
    "content": "CB-SEM (Covariance-Based Structural Equation Modeling) kiểm định mối quan hệ phức tạp giữa yếu tố tiềm ẩn và biến quan sát, dựa trên ma trận hiệp phương sai. Áp dụng trong Kinh tế, Quản trị, Du lịch, Sức khỏe để kiểm tra mô hình lý thuyết (hài lòng, lòng trung thành, chất lượng). Lưu ý: Kiểm tra độ tin cậy thang đo (Cronbach’s Alpha, Composite Reliability, AVE) bắt buộc; cần lý thuyết mạnh, dữ liệu sạch, mẫu lớn; đánh giá mô hình bằng CFI, TLI, RMSEA, SRMR. Ứng dụng: Kinh tế (chính sách đến tiêu dùng), Quản trị (chất lượng dịch vụ), Du lịch (hài lòng), Sức khỏe (chất lượng y tế).",
    "subsections": []
  },
  {
    "id": "3.4",
    "title": "Phân tích mô cấu trúc tuyến tính dạng PLS-SEM",
    "keywords": ["PLS-SEM", "variance", "small sample", "non-normal data", "reliability"],
    "content": "PLS-SEM (Partial Least Squares Structural Equation Modeling) kiểm định mối quan hệ phức tạp giữa yếu tố tiềm ẩn và biến quan sát, dựa trên phương sai. Phù hợp mẫu nhỏ, dữ liệu không chuẩn, mô hình phức tạp, áp dụng trong Kinh tế, Quản trị, Du lịch, Sức khỏe. Lưu ý: Kiểm tra độ tin cậy thang đo (Cronbach’s Alpha, Composite Reliability, AVE) bắt buộc; phân biệt reflective/formative; linh hoạt nhưng thiếu chỉ số độ phù hợp toàn cục. Ứng dụng: Kinh tế (nhận thức chính sách), Quản trị (chất lượng dịch vụ), Du lịch (trải nghiệm), Sức khỏe (chất lượng y tế).",
    "subsections": []
  },
  {
    "id": "3.5",
    "title": "Phân tích mô hình cấu trúc tuyến tính tổng quát dạng GSCA",
    "keywords": ["GSCA", "component-based", "model fit", "small sample", "non-normal data"],
    "content": "GSCA (Generalized Structured Component Analysis) kiểm định mối quan hệ giữa yếu tố tiềm ẩn và biến quan sát, kết hợp ưu điểm PLS-SEM (linh hoạt mẫu nhỏ, dữ liệu không chuẩn) và CB-SEM (chỉ số độ phù hợp toàn cục). Áp dụng trong Kinh tế, Quản trị, Du lịch, Sức khỏe. Lưu ý: Kiểm tra độ tin cậy thang đo (Cronbach’s Alpha, Composite Reliability, AVE); đánh giá FITm, FITs, GoF, AFIT (≥ 0.36); phân biệt reflective/formative. Ứng dụng: Kinh tế (nhận thức chính sách), Quản trị (chất lượng dịch vụ), Du lịch (trải nghiệm), Sức khỏe (chất lượng y tế).",
    "subsections": []
  },
  {
    "id": "4",
    "title": "Dữ liệu bảng",
    "keywords": ["panel data", "Pooled OLS", "FEM", "REM", "GLS", "FGLS", "IV/2SLS", "GMM", "Hausman-Taylor", "WLS", "Quantile Regression"],
    "content": "Phân tích dữ liệu bảng dài (Panel Data) là quá trình phức tạp, yêu cầu lựa chọn phương pháp phù hợp và xử lý các vấn đề vi phạm giả thiết để đảm bảo kết quả đáng tin cậy. Dữ liệu bảng dài được thu thập từ cùng một nhóm đối tượng (như cá nhân, công ty, khu vực, v.v.) qua nhiều thời điểm, kết hợp đặc điểm của dữ liệu cắt ngang và chuỗi thời gian. Các phương pháp hồi quy phổ biến bao gồm Pooled OLS, FEM, REM, nhưng khi giả thiết bị vi phạm, cần áp dụng GLS, FGLS, IV/2SLS, GMM động, Hausman-Taylor, WLS, hoặc Quantile Regression. Quy trình phân tích tập trung vào chuẩn bị dữ liệu, lựa chọn phương pháp, kiểm tra giả thiết, khắc phục vi phạm, và diễn giải kết quả trong các lĩnh vực như Kinh tế, Quản trị kinh doanh, Du lịch, Sức khỏe, và Y tế. Các vấn đề vi phạm giả thiết và phương pháp khắc phục bao gồm: Unobserved Heterogeneity (Pooled OLS): FEM, REM, kiểm tra bằng F-test/Breusch-Pagan Test. Tự tương quan: Sai số chuẩn mạnh, GLS/FGLS, GMM động, kiểm tra bằng Durbin-Watson/Wooldridge Test. Phương sai không đồng nhất: Sai số chuẩn mạnh, GLS/FGLS, WLS, Quantile Regression, kiểm tra bằng Breusch-Pagan/White Test. Nội sinh: IV/2SLS, GMM động, Hausman-Taylor, kiểm tra bằng Durbin-Wu-Hausman Test. Tương quan hiệu ứng ngẫu nhiên (REM): FEM, Hausman-Taylor, kiểm tra bằng Hausman Test. Mối quan hệ phi tuyến: Thêm biến phi tuyến, Quantile Regression, kiểm tra bằng Ramsey RESET Test. Panel ngắn hoặc dài: System GMM (short panel), FEM/REM với sai số mạnh, GLS/FGLS (long panel). Ứng dụng: Kinh tế: Phân tích tác động của chính sách thuế đến thu nhập hộ gia đình qua 5 năm, dùng 2SLS với biến công cụ như thay đổi luật thuế nếu phát hiện nội sinh. Quản trị kinh doanh: Đánh giá tác động của chi phí quảng cáo đến doanh thu cửa hàng qua 4 quý, dùng sai số chuẩn cụm trong FEM hoặc System GMM nếu có tự tương quan. Du lịch: Phân tích tác động của giá vé đến lượng khách qua các mùa, dùng GLS hoặc sai số chuẩn mạnh trong FEM nếu phương sai không đồng nhất. Sức khỏe/Y tế: Đánh giá tác động của chi tiêu y tế đến tỷ lệ tử vong qua các năm, dùng Hausman-Taylor thay vì REM nếu học vấn tương quan với hiệu ứng ngẫu nhiên. Phân tích dữ liệu bảng dài bắt đầu từ chuẩn bị dữ liệu, lựa chọn giữa Pooled OLS, FEM, và REM dựa trên các kiểm định (F-test, Breusch-Pagan, Hausman). Khi giả thiết bị vi phạm, các phương pháp như GLS, FGLS, IV/2SLS, GMM động, Hausman-Taylor, WLS, và Quantile Regression được sử dụng. Quy trình đòi hỏi kiểm tra giả thiết cẩn thận, lựa chọn phương pháp phù hợp, và diễn giải kết quả trong bối cảnh thực tiễn.",
    "subsections": []
  },
  {
    "id": "5",
    "title": "Số liệu không gian (Spatial Data)",
    "keywords": ["spatial data", "Moran’s I", "GWR", "Spatial 2SLS", "Spatial GMM"],
    "content": "Phân tích số liệu không gian xử lý dữ liệu có thông tin vị trí địa lý (tọa độ, khu vực, vùng lãnh thổ) để khám phá mẫu không gian, phụ thuộc không gian, hoặc tác động địa lý. Dữ liệu bao gồm điểm (vị trí cửa hàng), đường (đường giao thông), hoặc vùng (ranh giới tỉnh). Phương pháp xem xét phụ thuộc không gian (khu vực gần nhau tương tự) và dị biệt không gian (mối quan hệ thay đổi theo khu vực). Ứng dụng trong Kinh tế, Quản trị kinh doanh, Du lịch, Sức khỏe, Y tế, và Môi trường. Phụ thuộc không gian: Kiểm định Moran’s I và Lagrange Multiplier để phát hiện và xử lý, nếu bỏ qua có thể sai lệch kết quả. Dị biệt không gian: Hồi quy trọng số địa lý (GWR) xử lý mối quan hệ thay đổi theo khu vực, cần dữ liệu lớn. Ma trận lân cận: Chọn và chuẩn hóa ảnh hưởng kết quả, thử nghiệm dạng khoảng cách hoặc tiếp giáp. Nội sinh: Spatial 2SLS hoặc Spatial GMM xử lý, cần chọn biến công cụ cẩn thận. Ứng dụng: Kinh tế: Phân tích giá bất động sản theo khu vực, dùng mô hình trễ không gian để xem tác động giá nhà lân cận. Quản trị kinh doanh: Phân tích doanh thu cửa Artillery hàng theo vị trí, dùng GWR để xem tác động dân số thay đổi theo khu vực. Du lịch: Phân tích lượng khách du lịch theo điểm đến, dùng mô hình Durbin để xem tác động điểm lân cận. Sức khỏe/Y tế: Phân tích tỷ lệ mắc bệnh theo khu vực, dùng mô hình sai số không gian để xử lý tự tương quan.",
    "subsections": []
  },
  {
    "id": "6",
    "title": "Số liệu sự kiện (Event Data)",
    "keywords": ["event data", "survival analysis", "Kaplan-Meier", "Cox model", "AFT model"],
    "content": "Phân tích số liệu sự kiện nghiên cứu thời gian xảy ra sự kiện, xác suất, hoặc yếu tố ảnh hưởng, phổ biến trong Kinh tế (phá sản công ty), Quản trị kinh doanh (khách hàng rời bỏ), Du lịch (khách quay lại), Sức khỏe/Y tế (sống sót sau điều trị), và Xã hội học (thất nghiệp). Sử dụng phân tích sinh tồn hoặc mô hình thời gian đến sự kiện để xử lý dữ liệu kiểm duyệt. Kiểm duyệt: Kaplan-Meier và Cox xử lý kiểm duyệt hiệu quả. Giả thiết mô hình: Kiểm tra tỷ lệ nguy cơ tỷ lệ (Cox) hoặc phân phối thời gian (AFT/parametric) để đảm bảo mô hình phù hợp. Nội sinh: Xử lý bằng biến công cụ hoặc mô hình mở rộng. Sự kiện lặp lại hoặc cạnh tranh: Chọn Competing Risks hoặc Recurrent Event để xử lý sự kiện phức tạp. Ứng dụng: Kinh tế: Phân tích thời gian đến phá sản công ty, dùng Cox model để xem tác động quy mô và lợi nhuận. Quản trị kinh doanh: Phân tích thời gian khách hàng rời bỏ dịch vụ, dùng Kaplan-Meier và AFT model để so sánh chiến dịch giữ chân khách. Du lịch: Phân tích thời gian khách quay lại điểm đến, dùng Recurrent Event model để xem tác động chi phí và trải nghiệm. Sức khỏe/Y tế: Phân tích thời gian sống sót sau điều trị ung thư, dùng Competing Risks model để xem xét tử vong do ung thư hoặc nguyên nhân khác.",
    "subsections": []
  }
]

