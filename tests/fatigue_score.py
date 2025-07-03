from src.utils.helper import get_llm_input

### defining and mapping the fatigue score based on feedback
def define_fatigue_score(feedback: dict) -> int:
    score = 0

    # Symptom improvement scoring
    symptom_improvement_score = {
        "✅ Yes, significantly": 0,
        "🙂 Yes, slightly": 5,
        "😐 No change": 10,
        "⚠️ Got worse": 25,
        "❓ Not sure": 10
    }
    score += symptom_improvement_score.get(feedback.get("symptom_improvement"), 10)

    # Vision exercise frequency scoring
    exercise_frequency_score = {
        "📅 Daily": 0,
        "📆 3-4 times a week": 5,
        "🗓️ 1-2 times a week": 15,
        "🚫 Not at all": 25
    }
    score += exercise_frequency_score.get(feedback.get("exercise_frequency"), 10)

    # Hydration consistency scoring
    hydration_score = {
        "👍 Yes": 0,
        "😌 Sometimes": 10,
        "👎 No": 20,
        "❓ Not sure": 10
    }
    score += hydration_score.get(feedback.get("hydration_consistency"), 10)

    # Screen break adherence scoring
    screen_breaks_score = {
        "✅ Yes, regularly": 0,
        "🔁 Occasionally": 5,
        "😕 Rarely": 15,
        "🚫 No": 20
    }
    score += screen_breaks_score.get(feedback.get("screen_breaks"), 10)
    # next focus area with light weight
    next_focus_score_map = {
        "🧘 More vision exercises/outdoor activities": 5,
        "🥗 Better diet/meal planning": 5,
        "💧 Improving hydration": 2,
        "⏸️ Taking screen breaks": 3,
        "🌙 Better sleep habits": 4,
        "🎉 Keeping child motivated": 1
    }
    score += next_focus_score_map.get(feedback.get("next_focus_area"), 0)


    # New symptoms scoring
    new_symptom_score_map = {
        "❌ None": 0,
        "👁️👁️⚡ Frequent blinking": 5,
        "👁️💧 Watery eyes": 5,
        "💻😫 Digital Eye Strain / Screen-Related Fatigue / headaches after reading or screen time": 10,
        "🤧 Allergic Conjunctivitis (Eye allergy/redness/itching/frequent eye rubbing)": 10,
        "👓 Myopia (Near-sightedness)": 15,
        "🔭 Hyperopia (Far-sightedness)": 15,
        "📐 Astigmatism (Blurred/distorted vision)": 20,
        "👀 Strabismus (Crossed eyes)": 25,
        "😴 Amblyopia (Lazy eye)": 25,
        "😕 Ptosis (Drooping eyelid)": 25,
        "🌈❌ Colour Vision Deficiency (Trouble seeing certain colors)": 25,
        "🔁 Nystagmus (Involuntary eye movement)": 30,
        "👶☁️ Congenital Cataract (Clouded lens at birth)": 30,
        "👶💧 Congenital Glaucoma (High eye pressure at birth)": 30,
        "👶🩺 Retinopathy of Prematurity (ROP)(Retinal issues in premature babies)": 30,
        "✍️ Other (Please write the new observed symptoms):": 15
    }
    score += new_symptom_score_map.get(feedback.get("new_symptoms_observed"), 10)

    result  = min(score, 100)

    return result # Cap score at 100


### prediction of the fatiue score for a specific user
def calculate_fatiue_score(user_id: str, db)-> float:
    profile_data, feedback_data = get_llm_input(user_id=user_id, db=db)
    fatigue_score = define_fatigue_score(feedback_data)
    return fatigue_score
