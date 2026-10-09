def validate_rating(value, risk_model, rating_name):
    """
    Validate that a likelihood or impact rating is within
    the range defined by the risk model.
    """

    minimum = risk_model["scale"]["minimum"]
    maximum = risk_model["scale"]["maximum"]

    if not isinstance(value, int):
        raise ValueError(
            f"{rating_name} must be a whole number."
        )

    if value < minimum or value > maximum:
        raise ValueError(
            f"{rating_name} must be between "
            f"{minimum} and {maximum}."
        )


def calculate_risk(likelihood, impact, risk_model):
    """
    Calculate the numerical risk score.

    Risk Score = Likelihood x Impact
    """

    validate_rating(
        likelihood,
        risk_model,
        "Likelihood"
    )

    validate_rating(
        impact,
        risk_model,
        "Impact"
    )

    return likelihood * impact


def classify_risk(score, risk_model):
    """
    Convert a numerical risk score into a severity level
    using the severity bands from risk-model.json.
    """

    for band in risk_model["severityBands"]:

        minimum = band["minimum"]
        maximum = band["maximum"]

        if minimum <= score <= maximum:
            return band["label"]

    raise ValueError(
        f"Risk score {score} does not match "
        "any configured severity band."
    )


def get_rating_label(value, levels):
    """
    Return the descriptive label for a likelihood
    or impact value.
    """

    for level in levels:

        if level["value"] == value:
            return level["label"]

    return "Unknown"


def assess_risk(likelihood, impact, risk_model):
    """
    Perform a complete risk assessment and return
    the result as a dictionary.
    """

    score = calculate_risk(
        likelihood,
        impact,
        risk_model
    )

    severity = classify_risk(
        score,
        risk_model
    )

    likelihood_label = get_rating_label(
        likelihood,
        risk_model["likelihoodLevels"]
    )

    impact_label = get_rating_label(
        impact,
        risk_model["impactLevels"]
    )

    return {
        "likelihood": likelihood,
        "likelihoodLabel": likelihood_label,
        "impact": impact,
        "impactLabel": impact_label,
        "riskScore": score,
        "severity": severity
    }