# Linear Regression Fundamentals

<details>
<summary><strong>The image shows the total variance (SST) of two models, each split into an explained and an unexplained part. What does the split represent, and which model has the higher R²?</strong></summary>

Each bar shows **SST = explained (SSR) + unexplained (SSE) variance**. Model A has the higher R² because its explained share dominates, and R² is the explained fraction of total variance: **R² = SSR / SST**.

🔗 WebLink: [Wikipedia's article on the explained sum of squares](https://en.wikipedia.org/wiki/Explained_sum_of_squares)
</details>

<details>
<summary><strong>What does RMSE tell you?</strong></summary>

RMSE describes the typical size of the prediction error, expressed in the same units as the target variable:

**RMSE = √[(1/n) Σ(yᵢ − ŷᵢ)²]**

Because errors are squared, RMSE penalizes large errors more strongly. Lower is better.

🔗 WebLink: [Wikipedia's article on root mean square deviation](https://en.wikipedia.org/wiki/Root_mean_square_deviation)
</details>

<details>
<summary><strong>How do you read an R² value (including the edge cases)?</strong></summary>

- **R² = 1:** the model explains all variance (suspicious: check for leakage)
- **R² = 0.75:** 75% of the target variance is explained
- **R² = 0:** no better than always predicting the mean
- **R² < 0:** the model is worse than the mean baseline; this is possible on test data

🔗 WebLink: [Wikipedia's article on the coefficient of determination](https://en.wikipedia.org/wiki/Coefficient_of_determination)
</details>

<details>
<summary><strong>What does Ordinary Least Squares (OLS) do?</strong></summary>

OLS finds the regression coefficients by minimizing the sum of squared residuals:

**min Σ(yᵢ − ŷᵢ)²**

🔗 WebLink: [Wikipedia's overview of ordinary least squares](https://en.wikipedia.org/wiki/Ordinary_least_squares)
</details>

<details>
<summary><strong>In the matrix form y = Xb + e, what is each symbol, and why does X carry a column of ones?</strong></summary>

- **y:** the target vector containing *n* observations
- **X:** the design matrix, with *n* rows and one column per feature
- **b:** the coefficient vector b₀, b₁, ..., bₘ
- **e:** the residual/error vector

The leading column of ones multiplies b₀, allowing the intercept to be fitted through the same matrix operation as every slope. Without it, the regression is forced through the origin.

🔗 WebLink: [Wikipedia's article on the design matrix](https://en.wikipedia.org/wiki/Design_matrix)
</details>

<details>
<summary><strong>Why does OLS square the residuals instead of using absolute values?</strong></summary>

Squaring keeps the cost function smooth and differentiable everywhere, enables an exact closed-form solution, makes every term positive, and penalizes large errors more heavily. Absolute loss has a non-differentiable corner at zero.

🔗 WebLink: [Wikipedia's article on least absolute deviations](https://en.wikipedia.org/wiki/Least_absolute_deviations)
</details>

<details>
<summary><strong>Which point does every OLS regression line pass through?</strong></summary>

For simple OLS regression with an intercept, the line passes through the point of means **(x̄, ȳ)**. Since **b₀ = ȳ − b₁x̄**, inserting **x = x̄** gives exactly **ŷ = ȳ**.

🔗 WebLink: [Wikipedia's derivation of simple linear regression](https://en.wikipedia.org/wiki/Simple_linear_regression)
</details>

<details>
<summary><strong>What is the SST = SSR + SSE decomposition, and what's the notation trap to watch for?</strong></summary>

**SST = SSRₑₓₚₗₐᵢₙₑd + SSEᵣₑₛᵢdᵤₐₗ:** total variance equals explained variance plus unexplained variance.

The notation trap is that **SSR** is used ambiguously: sometimes it means the explained regression sum of squares and sometimes the residual/error sum of squares. Always check the source's convention.

🔗 WebLink: [Wikipedia's article on the partitioning of sums of squares](https://en.wikipedia.org/wiki/Partition_of_sums_of_squares)
</details>

<details>
<summary><strong>What is the simplest possible baseline model for predicting y, and why does it matter?</strong></summary>

The simplest baseline predicts the mean **ȳ** for every input *x*. R² is measured against exactly this baseline: **R² = 0** means the model is no better than the mean, while **R² < 0** means it is worse.

🔗 WebLink: [Wikipedia's article on the coefficient of determination](https://en.wikipedia.org/wiki/Coefficient_of_determination)
</details>

<details>
<summary><strong>How do SSR, RMSE, and R² move relative to each other?</strong></summary>

When SSR means the sum of squared residuals, they are three views of the same fit:

**SSR ↓ ⇒ RMSE ↓ ⇒ R² ↑**

The opposite is also true. For the same dataset, minimizing residual SSR also minimizes RMSE and maximizes R².

🔗 WebLink: [Wikipedia's article on root mean square deviation](https://en.wikipedia.org/wiki/Root_mean_square_deviation)
</details>

<details>
<summary><strong>Why can you not just add up the raw residuals to judge how good a line is?</strong></summary>

Overestimates and underestimates have opposite signs and cancel each other out, so even a wildly inaccurate line can have a residual sum near zero. Squaring each residual removes the sign, allowing errors to accumulate.

🔗 WebLink: [Wikipedia's article on the least squares method](https://en.wikipedia.org/wiki/Least_squares)
</details>

<details>
<summary><strong>The image shows deviations measured from two baselines: a flat one in Panel A, a sloped (fitted) one in Panel B. Which panel's variance does R² treat as "unexplained"?</strong></summary>

**Panel B.** Deviations from the fitted regression line are the residuals and therefore the unexplained variance. Panel A's deviations from the flat mean line are the total variance:

**R² = 1 − (Panel B variance / Panel A variance)**

🔗 WebLink: [Wikipedia's article on total sum of squares](https://en.wikipedia.org/wiki/Total_sum_of_squares)
</details>

<details>
<summary><strong>What two properties do OLS residuals always have?</strong></summary>

For OLS with an intercept:

- **Σeᵢ = 0:** the residuals sum to zero
- **Σ(xᵢ − x̄)eᵢ = 0:** the residuals are orthogonal/uncorrelated with the feature

The second property makes the decomposition **SST = SSE + SSR** hold exactly.

🔗 WebLink: [Wikipedia's article on errors and residuals in statistics](https://en.wikipedia.org/wiki/Errors_and_residuals_in_statistics)
</details>

<details>
<summary><strong>What is Adjusted R², and why use it?</strong></summary>

Adjusted R² penalizes unnecessary predictors:

**Adjusted R² = 1 − (1 − R²)(n − 1)/(n − p − 1)**

Ordinary R² never decreases when a feature is added. Adjusted R² increases only when the new feature improves the model enough to justify the added complexity, making it useful for comparing models with different numbers of predictors.

🔗 WebLink: [Wikipedia's section on adjusted R²](https://en.wikipedia.org/wiki/Coefficient_of_determination#Adjusted_R2)
</details>

<details>
<summary><strong>What is a Residual (in regression)?</strong></summary>

A residual is the difference between an observed value and the model's prediction:

**eᵢ = yᵢ − ŷᵢ**

A positive residual means the model underestimated the actual value; a negative residual means it overestimated it. Geometrically, it is the vertical distance between a data point and the fitted line.

🔗 WebLink: [Wikipedia's article on errors and residuals in statistics](https://en.wikipedia.org/wiki/Errors_and_residuals_in_statistics)
</details>

<details>
<summary><strong>The image shows two loss curves against the residual e: Curve A is a smooth bowl, Curve B is a sharp V. Which is the squared loss, and why does OLS use it?</strong></summary>

**Curve A**, the smooth parabola **e²**, is squared loss. It is differentiable everywhere, enables a closed-form OLS solution, and penalizes large errors disproportionately. Curve B is absolute loss **|e|**, with a non-differentiable corner at zero.

🔗 WebLink: [Wikipedia's article on loss functions](https://en.wikipedia.org/wiki/Loss_function)
</details>

<details>
<summary><strong>MAE vs. RMSE: when does which matter?</strong></summary>

- **MAE = (1/n) Σ|yᵢ − ŷᵢ|:** treats errors proportionally, is easy to interpret, and is more robust to outliers. Use it when errors have approximately equal importance.
- **RMSE = √[(1/n) Σ(yᵢ − ŷᵢ)²]:** penalizes large errors more strongly and is more sensitive to outliers. Use it when large mistakes are especially costly.

Both are expressed in the same units as the target.

🔗 WebLink: [Wikipedia's article on regression metrics](https://en.wikipedia.org/wiki/Regression_validation)
</details>

<details>
<summary><strong>In multiple regression, what does a single feature's coefficient represent?</strong></summary>

A coefficient bⱼ represents the expected change in predicted *y* when xⱼ increases by one unit, **holding all other included features constant** (*ceteris paribus*). It is a partial association within the model, not necessarily a causal effect or the feature's effect in isolation.

🔗 WebLink: [Wikipedia's section on multiple linear regression](https://en.wikipedia.org/wiki/Linear_regression#Introduction_to_multiple_linear_regression)
</details>

<details>
<summary><strong>What is the difference between y = b₀ + b₁x + e and ŷ = b₀ + b₁x?</strong></summary>

**y = b₀ + b₁x + e** describes the observed value as the systematic linear component plus unexplained error. **ŷ = b₀ + b₁x** is the model's predicted/fitted value and does not include the unknown error. Their difference is the residual: **e = y − ŷ**.

🔗 WebLink: [Wikipedia's article on simple linear regression](https://en.wikipedia.org/wiki/Simple_linear_regression)
</details>

<details>
<summary><strong>What is a proxy feature? Give an example.</strong></summary>

A proxy feature correlates with the target not because it causes it, but because both share a hidden common cause. For example, "fire trucks dispatched" predicts "fire damage" because both are driven by fire severity—not because fire trucks cause the damage.

🔗 WebLink: [Wikipedia's article on confounding](https://en.wikipedia.org/wiki/Confounding)
</details>

<details>
<summary><strong>The image tracks two model-quality metrics as features are added one by one: Metric A keeps rising and plateaus; Metric B peaks at 6 features (circled), then falls. Which is plain R² and which is adjusted R²?</strong></summary>

**Metric A is plain R²:** it increases or stays unchanged as predictors are added. **Metric B is adjusted R²:** it penalizes unnecessary features and can therefore fall. Its peak at six features suggests the best balance between explanatory power and model complexity.

🔗 WebLink: [Wikipedia's section on adjusted R²](https://en.wikipedia.org/wiki/Coefficient_of_determination#Adjusted_R2)
</details>

<details>
<summary><strong>How do you compute a residual for one data point (recipe)?</strong></summary>

1. Insert the feature value into the regression equation: **ŷᵢ = b₀ + b₁xᵢ**.
2. Subtract the prediction from the actual value: **eᵢ = yᵢ − ŷᵢ**.

For example, if **yᵢ = 20** and **ŷᵢ = 17**, then **eᵢ = 3**, meaning the model underestimated the value by three units.

🔗 WebLink: [Wikipedia's article on errors and residuals](https://en.wikipedia.org/wiki/Errors_and_residuals_in_statistics)
</details>

<details>
<summary><strong>What is the Normal Equation?</strong></summary>

The Normal Equation provides an exact, closed-form solution for the OLS coefficients:

**b̂ = (XᵀX)⁻¹Xᵀy**

It requires no learning rate or iterations, but can be slow for many features. If **XᵀX** is not invertible, use a pseudoinverse or numerical solver.

🔗 WebLink: [Wikipedia's section on the Normal Equations](https://en.wikipedia.org/wiki/Linear_least_squares#Derivation_of_the_normal_equations)
</details>

<details>
<summary><strong>How are R² and the Pearson correlation coefficient r related?</strong></summary>

For simple linear regression with one feature and an intercept:

**R² = r²**

For example, **r = 0.9** gives **R² = 0.81**, so the model explains 81% of the variance. The correlation coefficient *r* ranges from −1 to 1 and carries direction, while R² does not.

🔗 WebLink: [Wikipedia's article on the Pearson correlation coefficient](https://en.wikipedia.org/wiki/Pearson_correlation_coefficient)
</details>

<details>
<summary><strong>What are the two different jobs you can use a linear regression for?</strong></summary>

1. **Prediction:** estimate a continuous target value for new observations.
2. **Inference/explanation:** estimate and interpret how features are associated with the target.

A regression coefficient describes an association and does not automatically prove causality.

🔗 WebLink: [Wikipedia's article on linear regression](https://en.wikipedia.org/wiki/Linear_regression)
</details>

<details>
<summary><strong>What exactly is the least squares criterion?</strong></summary>

Choose b₀ and b₁ to minimize the sum of squared residuals:

**J(b₀,b₁) = Σeᵢ² = Σ[yᵢ − (b₀ + b₁xᵢ)]²**

Comparing this one cost value across candidate lines determines which line fits better; OLS chooses the line with the smallest value.

🔗 WebLink: [Wikipedia's article on the least squares method](https://en.wikipedia.org/wiki/Least_squares)
</details>

<details>
<summary><strong>Multiple vs. multivariate regression: what is the difference?</strong></summary>

- **Multiple regression:** predicts one target variable using two or more input features.
- **Multivariate regression:** predicts multiple target variables simultaneously.

Memory aid: **multiple = multiple predictors; multivariate = multiple targets**.

🔗 WebLink: [Wikipedia's article on multivariate regression](https://en.wikipedia.org/wiki/Multivariate_regression)
</details>

<details>
<summary><strong>What is extrapolation, and why is it dangerous?</strong></summary>

Extrapolation means predicting for feature values outside the range observed in the training data. It is dangerous because the learned relationship may not continue outside that range: the trend could flatten, curve, reverse, or follow different conditions, while a linear model simply extends the same line.

🔗 WebLink: [Wikipedia's article on extrapolation](https://en.wikipedia.org/wiki/Extrapolation)
</details>
