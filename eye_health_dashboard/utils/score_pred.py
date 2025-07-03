def predict_fatigue_score(feedback_data, intake_data, daily_logs):
    score = 0
    
    # Mapping enums to numeric scores (normalized 0–100)
    exercise_map = {
        "📅 Daily": 100,
        "📆 3-4 times a week": 70,
        "🗓️ 1-2 times a week": 40,
        "🚫 Not at all": 0
    }
    hydration_map = {
        "👍 Yes": 100,
        "😌 Sometimes": 60,
        "👎 No": 20,
        "❓ Not sure": 50
    }
    screen_break_map = {
        "✅ Yes, regularly": 100,
        "🔁 Occasionally": 70,
        "😕 Rarely": 40,
        "🚫 No": 0
    }
    symptom_improve_map = {
        "✅ Yes, significantly": 100,
        "🙂 Yes, slightly": 70,
        "😐 No change": 50,
        "⚠️ Got worse": 20,
        "❓ Not sure": 40
    }
    new_symptom_penalty = {
        "❌ None": 0,
        "👓 Myopia (Near-sightedness)": -20,
        "💻😫 Digital Eye Strain / Screen-Related Fatigue / headaches after reading or screen time": -30,
        "✍️ Other (Please write the new observed symptoms):": -20,
        # All others treated as moderate impact
    }

    # 🧘 Exercise
    score += exercise_map.get(feedback_data["exercise_frequency"], 50) * 0.20

    # 💧 Hydration
    score += hydration_map.get(feedback_data["hydration_consistency"], 50) * 0.10

    # 🖥️ Screen breaks
    score += screen_break_map.get(feedback_data["screen_breaks"], 50) * 0.10

    # 😴 Lifestyle strain index (from intake / daily logs)
    lifestyle_factors = 0

    if intake_data["screen_hours_per_day"] > 4:
        lifestyle_factors -= 10
    if intake_data["sleep_hours"] < 7:
        lifestyle_factors -= 10
    if intake_data["lighting_quality"] == "Poor":
        lifestyle_factors -= 10
    if intake_data["holds_screen_too_close"]:
        lifestyle_factors -= 10

    lifestyle_score = 100 + lifestyle_factors
    lifestyle_score = max(0, min(lifestyle_score, 100))
    score += lifestyle_score * 0.20

    # 👁️ Symptom improvement
    score += symptom_improve_map.get(feedback_data["symptom_improvement"], 50) * 0.20

    # ❗ New symptoms
    observed = feedback_data["new_symptoms_observed"]
    penalty = 0
    if observed in new_symptom_penalty:
        penalty = new_symptom_penalty[observed]
    elif observed != "❌ None":
        penalty = -10  # Default for other valid symptoms
    new_symptom_score = max(0, 100 + penalty)
    score += new_symptom_score * 0.10

    # 🎯 Plan Follow-through (hydration, meals logged, etc.)
    # Here assumed from logs vs plan adherence %
    follow_through_adherence = daily_logs.get("adherence_percentage", 70)
    score += follow_through_adherence * 0.10

    # Final normalization
    return round(score, 2)
