def predict_myopia_risk(input_data, threshold_map, scoring_weights, demographic_schema):
    from collections import defaultdict

    age = input_data.get("age")
    gender = input_data.get("gender", "other").lower()
    ethnicity = input_data.get("ethnicity", "other").lower()

    def get_age_group(age):
        for group_key, group_def in demographic_schema["age_groups"].items():
            if group_def["range"][0] <= age <= group_def["range"][1]:
                return group_key
        return None

    age_group = get_age_group(age)

    RISK_DIRECTION = {
        "spherical_eq": "abs",
        "cylinder": "abs",
        "lens_power": "reverse",
        "axial_length": "normal",
        "al_cr_ratio": "normal",
        "keratometry": "normal",
        "al_percentile": "normal"
    }

    left_eye_score = 0.0
    right_eye_score = 0.0
    shared_score = 0.0
    detail_scores = defaultdict(dict)

    for factor, config in scoring_weights.items():
        weight = config["weightage"]
        score_levels = config["score"]
        value = input_data.get(factor)
        base = factor.replace("_left", "").replace("_right", "")

        is_left = factor.endswith("_left")
        is_right = factor.endswith("_right")

        # Skip if value not provided
        if value is None:
            continue

        direction = RISK_DIRECTION.get(base, "normal")

        def compare_direction(val, thresholds):
            if direction == "abs":
                val = abs(val)
            if direction == "reverse":  # lower is higher risk
                if val <= thresholds["high"]:
                    return "high"
                elif val <= thresholds["moderate"]:
                    return "moderate"
                else:
                    return "low"
            else:  # normal or abs
                if val >= thresholds["high"]:
                    return "high"
                elif val >= thresholds["moderate"]:
                    return "moderate"
                else:
                    return "low"

        # Extract thresholds from demographic-aware or age-only or rule-based
        try:
            factor_thresholds = threshold_map.get(factor, {})

            if "thresholds" in factor_thresholds.get(age_group, {}):
                # age-group only (non-gender/ethnicity)
                thresholds = factor_thresholds[age_group]["thresholds"]

            elif gender in factor_thresholds.get(age_group, {}):
                # age-group + gender + ethnicity based
                thresholds = factor_thresholds[age_group][gender][ethnicity]

            elif "rules" in factor_thresholds:
                # categorical factors
                level_index = factor_thresholds["rules"].get(value, 0)
                level = ["low", "moderate", "high"][level_index]
                score = score_levels[level] * weight
                shared_score += score
                detail_scores["shared"][factor] = {"value": value, "risk_level": level, "score": score}
                continue

            else:
                thresholds = None

            # Compare value with thresholds and compute score
            level = compare_direction(value, thresholds)
            score = score_levels[level] * weight

            if is_left:
                left_eye_score += score
                detail_scores["left"][factor] = {"value": value, "risk_level": level, "score": score}
            elif is_right:
                right_eye_score += score
                detail_scores["right"][factor] = {"value": value, "risk_level": level, "score": score}
            else:
                shared_score += score
                detail_scores["shared"][factor] = {"value": value, "risk_level": level, "score": score}

        except Exception as e:
            detail_scores["errors"][factor] = {"error": str(e)}
            continue

    total_score = left_eye_score + right_eye_score + shared_score

    def risk_band(score):
        if score >= 55:
            return "High"
        elif score >= 30:
            return "Moderate"
        else:
            return "Low"

    return {
        "left_eye_score": round(left_eye_score, 2),
        "right_eye_score": round(right_eye_score, 2),
        "shared_score": round(shared_score, 2),
        "total_score": round(total_score, 2),
        "overall_risk_level": risk_band(total_score),
        "eye_risk_levels": {
            "left": risk_band(left_eye_score),
            "right": risk_band(right_eye_score),
        },
        "details": detail_scores
    }


# Load json files
import json

with open("myopia_master/data/demographic_schema.json") as f:
    demographic_schema = json.load(f)

with open("myopia_master/data/wt_score_mapping.json") as f:
    scoring_weights = json.load(f)

with open("myopia_master/data/risk_factors.json") as f:
    threshold_map = json.load(f)


input_data = {
    "child_id": "CHILD1234",
    "name": "PP Ranjith",
    "gender": "male",
    "ethnicity": "caucasian",
    "age": 10,

    "axial_length_right": 24.84,
    "axial_length_left": 24.75,
    "spherical_eq_right": -5.83,
    "spherical_eq_left": -5.41,
    "keratometry_right": 43.80,
    "keratometry_left": 44.2,
    "cylinder_right": 1.145,
    "cylinder_left": None,
    "lens_power_right": None,
    "lens_power_left": None,
    "al_percentile_right": 95,
    "al_percentile_left": 94,

    "parental_history_myopia": "both_parents",
    "daily_outdoor_time_hours": 0.5,
    "screen_time_hours_per_day": 3.5,
    "average_sleep_hours": 7.5,
    "hydration_level": "moderate",
    "diet_quality": "poor",
    "room_lighting": "dim",
    "common_symptoms": "eye strain"  # choose one for now
}

result = predict_myopia_risk(
    input_data=input_data,
    threshold_map=threshold_map,
    scoring_weights=scoring_weights,
    demographic_schema=demographic_schema
)

#print(result)
