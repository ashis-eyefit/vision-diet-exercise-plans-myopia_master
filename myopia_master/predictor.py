# Load json files
import json
import os
from data_extractor import parse_myopia_data

base_dir = os.path.dirname(__file__)

with open(os.path.join(base_dir, "data", "demographic_schema.json")) as f:
    demographic_schema = json.load(f)

with open(os.path.join(base_dir, "data", "risk_factors_v2.json")) as f:
    threshold_map = json.load(f)

with open(os.path.join(base_dir, "data", "wt_score_mapping.json")) as f:
    scoring_weights = json.load(f)


def predict_myopia_risk(input_data, threshold_map, scoring_weights, demographic_schema):
    from collections import defaultdict

    age = input_data.get("age")
    ethnicity = input_data.get("ethnicity", "other").lower()


    def get_age_group(age):
        for group_key, group_def in demographic_schema["age_groups"].items():
            if group_def["range"][0] <= round(age) <= group_def["range"][1]:
                return group_key
        return None

    age_group = get_age_group(age)

    left_eye_score = 0.0
    right_eye_score = 0.0
    shared_score = 0.0
    detail_scores = defaultdict(dict)
    


    left_factor = []
    right_factor = []
    common_factor_age_dependent = ["daily_outdoor_time_hours", "average_sleep_hours", "screen_time_hours_per_day"]
    common_factor_age_independent = ["hydration_level", "diet_quality", "room_lighting", "common_symptoms", "parental_history_myopia"]

    for factor, details  in scoring_weights.items():
        weight = details["weightage"]
        score_levels_dict = details["score"]
        value = input_data.get(factor)

        is_left = factor.endswith("_left")
        is_right = factor.endswith("_right")

        if is_left:
            left_factor.append(factor)
        elif is_right:
            right_factor.append(factor)
        else:
            pass

        # score for left eye
        if factor in left_factor and value:
            
            ## biometric factors depens on demogrphies [age, gender and ethnicity]
            if factor in ["axial_length_left","keratometry_left"]:
                if threshold_map[factor][age_group][ethnicity] is not None:
                    value_map_dict_all_demoraphies = threshold_map[factor][age_group][ethnicity]
                    #print(json.dumps(threshold_map[factor][age_group][gender][ethnicity], indent=2))

                    if value >= value_map_dict_all_demoraphies["high"]:
                        factor_score_left, level = score_levels_dict["high"], "high"
                    elif value >= value_map_dict_all_demoraphies["moderate"] and value < value_map_dict_all_demoraphies["high"]:
                        factor_score_left, level = score_levels_dict["moderate"], "moderate"
                    elif value < value_map_dict_all_demoraphies["moderate"] and value >= value_map_dict_all_demoraphies["low"]: 
                        factor_score_left, level = score_levels_dict["low"], "low"
                else:
                    factor_score_left, level = 0 , "safe / factor is not defined"
                detail_scores[factor]["risk_level"] = level
            
            elif factor == "spherical_eq_left":
                if threshold_map[factor][age_group][ethnicity]:
                    value_map_dict_all_demoraphies = threshold_map[factor][age_group][ethnicity]
                    if abs(value) >= abs(value_map_dict_all_demoraphies["high"]):
                        factor_score_left, level = score_levels_dict["high"], "high"
                    elif abs(value) >= abs(value_map_dict_all_demoraphies["moderate"]) and abs(value) < abs(value_map_dict_all_demoraphies["high"]):
                        factor_score_left, level = score_levels_dict["moderate"], "moderate"
                    elif abs(value) < abs(value_map_dict_all_demoraphies["moderate"]) and abs(value) >= abs(value_map_dict_all_demoraphies["low"]): 
                        factor_score_left , level = score_levels_dict["low"], "low"
                else:
                    factor_score_left, level = 0, "safe / factor is not defined"
                detail_scores[factor]["risk_level"] = level

            
            ## biometric factors depends on only age
            elif factor == "cylinder_left":
                if threshold_map[factor]["thresholds"]:
                    value_map_dict_age = threshold_map[factor]["thresholds"]
                    #print(json.dumps(threshold_map[factor][age_group], indent=2))
                    if value >= value_map_dict_age["high"]:
                        factor_score_left, level = score_levels_dict["high"], "high"
                    elif value >= value_map_dict_age["moderate"] and value < value_map_dict_age["high"]:
                        factor_score_left, level = score_levels_dict["moderate"], "moderate"
                    elif value < value_map_dict_age["moderate"] and value >= value_map_dict_age["low"]: 
                        factor_score_left, level = score_levels_dict["low"], "low"
                else:
                    factor_score_left, level = 0, "safe / factor is not defined"
                detail_scores[factor]["risk_level"] = level
            

            ## demographies independent biometric factors
            elif factor == "al_percentile_left":
                if threshold_map[factor]["thresholds"]:
                    value_map_dict_demography_independent = threshold_map[factor]["thresholds"]
                    if value >= value_map_dict_demography_independent["high"]:
                        factor_score_left, level = score_levels_dict["high"], "high"
                    elif value >= value_map_dict_demography_independent["moderate"] and value < value_map_dict_demography_independent["high"]:
                        factor_score_left, level = score_levels_dict["elevated"], "elevated"
                    elif value >= value_map_dict_demography_independent["low"] and value < value_map_dict_demography_independent["moderate"]:
                        factor_score_left, level = score_levels_dict["moderate"], "moderate"
                    elif value < value_map_dict_demography_independent["low"]: 
                        factor_score_left, level = score_levels_dict["low"], "low"
                else:
                    factor_score_left, level = 0, "safe / factor is not defined"
                detail_scores[factor]["risk_level"] = level
        
            left_eye_score = left_eye_score + weight * factor_score_left
            detail_scores[factor]["score"] = weight * factor_score_left
        
        ### Right eye score
        elif factor in right_factor and value:
            
            ## biometric factors depens on demogrphies [age, gender and ethnicity]
            if factor in ["axial_length_right", "keratometry_right"]:
                if threshold_map[factor][age_group][ethnicity]:
                    value_map_dict_all_demoraphies = threshold_map[factor][age_group][ethnicity]
                    
                    if value >= value_map_dict_all_demoraphies["high"]:
                        factor_score_right, level = score_levels_dict["high"], "high"
                    elif value >= value_map_dict_all_demoraphies["moderate"] and value < value_map_dict_all_demoraphies["high"]:
                        factor_score_right, level = score_levels_dict["moderate"], "moderate"
                    elif value < value_map_dict_all_demoraphies["moderate"] and value >= value_map_dict_all_demoraphies["low"]: 
                        factor_score_right, level = score_levels_dict["low"],"low"
                else:
                    factor_score_right, level = 0, "safe / factor is not defined"
                detail_scores[factor]["risk_level"] = level
            
            elif factor == "spherical_eq_right":
                if threshold_map[factor][age_group][ethnicity]:
                    value_map_dict_all_demoraphies = threshold_map[factor][age_group][ethnicity]
                    if abs(value) >= abs(value_map_dict_all_demoraphies["high"]):
                        factor_score_right, level = score_levels_dict["high"], "high"
                    elif abs(value) >= abs(value_map_dict_all_demoraphies["moderate"]) and abs(value) < abs(value_map_dict_all_demoraphies["high"]):
                        factor_score_right , level= score_levels_dict["moderate"], "moderate"
                    elif abs(value) < abs(value_map_dict_all_demoraphies["moderate"]) and abs(value) >= abs(value_map_dict_all_demoraphies["low"]): 
                        factor_score_right, level = score_levels_dict["low"], "low"
                else:
                    factor_score_right, level = 0, "safe / factor is not defined"
                detail_scores[factor]["risk_level"] = level
            
            ## biometric factors depends on only age
            elif factor == "cylinder_right":
                if threshold_map[factor]["thresholds"]:
                    value_map_dict_age = threshold_map[factor]["thresholds"]
                    if value >= value_map_dict_age["high"]:
                        factor_score_right, level = score_levels_dict["high"], "high"
                    elif value >= value_map_dict_age["moderate"] and value < value_map_dict_age["high"]:
                        factor_score_right, level = score_levels_dict["moderate"], "moderate"
                    elif value < value_map_dict_age["moderate"] and value >= value_map_dict_age["low"]: 
                        factor_score_right, level = score_levels_dict["low"], "low"
                else:
                    factor_score_right, level = 0, "safe / factor is not defined"
                detail_scores[factor]["risk_level"] = level


            ## demographies independent biometric factors
            elif factor == "al_percentile_right":
                if threshold_map[factor]["thresholds"]:
                    value_map_dict_demography_independent = threshold_map[factor]["thresholds"]
                    if value >= value_map_dict_demography_independent["high"]:
                        factor_score_right, level = score_levels_dict["high"], "high"
                    elif value >= value_map_dict_demography_independent["moderate"] and value < value_map_dict_demography_independent["high"]:
                        factor_score_right, level = score_levels_dict["elevated"], "elevated"
                    elif value >= value_map_dict_demography_independent["low"] and value < value_map_dict_demography_independent["moderate"]:
                        factor_score_right, level = score_levels_dict["moderate"], "moderate"
                    elif value < value_map_dict_demography_independent["low"]: 
                        factor_score_right, level = score_levels_dict["low"], "low"
                else:
                    factor_score_right, level = 0, "safe / factor is not defined"
                detail_scores[factor]["risk_level"] = level

            right_eye_score = right_eye_score + weight * factor_score_right
            detail_scores[factor]["score"] = weight * factor_score_right


        ## shared score for both right and left eyes   
        elif factor in common_factor_age_dependent or factor in common_factor_age_independent:
            ## non-biometric factors depend on age
            if factor == "average_sleep_hours":
                if threshold_map[factor][age_group]["thresholds"]:
                    value_map_dict_age = threshold_map[factor][age_group]["thresholds"]
                    if value >= value_map_dict_age["low"]:
                        factor_score_shared, level = score_levels_dict["low"], "low"
                    elif value >= value_map_dict_age["moderate"] and value < value_map_dict_age["low"]:
                        factor_score_shared, level = score_levels_dict["moderate"], "moderate"
                    elif value < value_map_dict_age["moderate"]:
                        factor_score_shared, level = score_levels_dict["high"], "high"
                    else:
                        factor_score_shared, level = 0 , "safe / factor is not defined"
                else:
                    factor_score_shared, level = 0, "safe / factor is not defined"
                detail_scores[factor]["risk_level"] = level
                detail_scores[factor]["score"] = weight * factor_score_shared

            elif factor in ["screen_time_hours_per_day", "daily_outdoor_time_hours"]:
                if threshold_map[factor][age_group]["thresholds"]:
                    value_map_dict_age = threshold_map[factor][age_group]["thresholds"]
                    if value == value_map_dict_age["high"]:
                        factor_score_shared, level = score_levels_dict["high"], "high"
                    elif value == value_map_dict_age["low"]: 
                        factor_score_shared, level = score_levels_dict["low"], "low"
                    else:
                        factor_score_shared, level = 0 , "safe / factor is not defined"
                else:
                    factor_score_shared, level = 0 , "safe / factor is not defined"
                detail_scores[factor]["risk_level"] = level
                detail_scores[factor]["score"] = weight * factor_score_shared
            

            ## non-biometric factors independent of demography
            elif factor in common_factor_age_independent:
                if threshold_map[factor]["rules"]:
                    value_map_dict_non_bio_independent_demography = threshold_map[factor]["rules"]
                    if factor in ["hydration_level", "diet_quality"]:
                        if value in threshold_map[factor]["rules"]["poor"]:
                            factor_score_shared = score_levels_dict["poor"]
                            level = "high"
                        elif value in threshold_map[factor]["rules"]["moderate"]:
                            factor_score_shared = score_levels_dict["moderate"]
                            level = "moderate"
                        elif value in threshold_map[factor]["rules"]["good"]:
                            factor_score_shared = score_levels_dict["good"]
                            level = "low"
                       
                        detail_scores[factor]["risk_level"] = level

                    elif factor == "room_lighting":
                        if value == "Well-lit environment":
                            factor_score_shared, level = 0, "low"
                        elif value == "Dim lightning or screens in the dark":
                            factor_score_shared, level = 2.5, "high"
                        else:
                            factor_score_shared, level = 0, "safe / factor is not defined"
                    
                        detail_scores[factor]["risk_level"] = level

                    elif factor == "common_symptoms":
                        if value:
                            symptom_count = len(value)
                            if symptom_count > 0 and symptom_count <= 1:
                                factor_score_shared, level = 0.5, "low"
                            elif symptom_count > 1 and symptom_count<=2:
                                factor_score_shared, level = 1.5, "moderate"
                            elif symptom_count > 2:
                                factor_score_shared, level = 2.5, "high"
                            else:
                                factor_score_shared, level = 0, "safe / factor is not defined"
                    
                            detail_scores[factor]["risk_level"] = level

                    elif factor == "parental_history_myopia":
                        if value == "Yes":
                            factor_score_shared, level = 2.5, "high"
                        elif value == "No":
                            factor_score_shared, level = 1, "low"
                  
                        else:
                            factor_score_shared, level = 0, "safe / no parent's history is defined"
                        detail_scores[factor]["risk_level"] = level
                else:
                    factor_score_shared, level = 0, "safe / no parent's history is defined"
                detail_scores[factor]["risk_level"] = level
                

                shared_score = shared_score + weight * factor_score_shared
                #print(f"{factor}:{factor_score_shared}")
                detail_scores[factor]["score"] = weight * factor_score_shared
                


    ## overall risk band prediction including both eyes  max score  = 71
    def overall_risk_band(score):
        if score >= 62:
            return "High"
        elif score >= 35 and score <62:
            return "Moderate"
        else:
          return "Low"
    ## eyewise risk band prediction for each eye separately   max score = 45.5
    def eye_wise_risk_band(score):
        if score >= 38:
            return "High"
        elif score<38 and score >= 22:
            return "Moderate"
        else:
            return "Low"

    

    return {
        "age": age_group,
        "left_eye_score": f"{round(left_eye_score, 2)} / 27",
        "right_eye_score": f"{round(right_eye_score, 2)} / 27",
        "shared_score": f"{round(shared_score, 2)} / 29.5",
        "total_score": f"{round(left_eye_score + right_eye_score + shared_score, 2)} / 83.5",
        "overall_risk_level": overall_risk_band(left_eye_score + right_eye_score + shared_score),
        "eye_risk_levels": {
            "left": eye_wise_risk_band(left_eye_score + shared_score),
            "right": eye_wise_risk_band(right_eye_score + shared_score),
        },
        #"divider":"========================================== FACTOR WISE DETAILED SCORE ====================================================",
        "details": detail_scores
    }



def get_shared_data_input(user_id: str, cursor) -> dict:

    try:   
        
        # Get onboarding data (non-PII fields only)
        cursor.execute("""
            SELECT outdoor_hours_per_day, screen_hours_per_day, parent_has_myopia,
                    lighting_quality
            FROM user_onboarding_answers
            WHERE user_id = %s
        """, (user_id,))
        onboarding_data = cursor.fetchone()
        #print("debug onboarding data", onboarding_data)
        
        if not onboarding_data:
            #print("debug onboarding data", "no onboarding_data")
            raise ValueError("No onboarding data available")

        # Get intake data (non-PII fields only)
        cursor.execute("""
            SELECT  symptoms, sleep_hours,
                    diet_quality, hydration_frequency
            FROM intake_questionnaire
            WHERE user_id = %s
        """, (user_id,))
        intake_data = cursor.fetchone()
        #print("debug intake data",intake_data)
    
        if not intake_data:
            #print("debug intake data","no intake_data")
            raise ValueError("No intake eye health answers available")
                

        # Construct profile data for LLM
        myopia_pred_input_profile_data = {
            # Onboarding
            "outdoor_hours_per_day": onboarding_data["outdoor_hours_per_day"],
            "screen_hours_per_day": onboarding_data["screen_hours_per_day"],
            "parent_has_myopia": onboarding_data["parent_has_myopia"],
            "lighting_quality": onboarding_data["lighting_quality"],

            # Intake
            "symptoms": [s.strip() for s in intake_data["symptoms"].split(",") if s],
            "sleep_hours": intake_data["sleep_hours"],
            "diet_quality": intake_data["diet_quality"],
            "hydration_frequency": intake_data["hydration_frequency"],
           }


        return myopia_pred_input_profile_data
    except Exception as e:
        raise RuntimeError(f"Error in get_llm_input(): {str(e)}")

def myopia_wrapper(user_id, pdf_path, cursor):
    result_dict = parse_myopia_data(pdf_path)

    shared_data = get_shared_data_input(user_id, cursor)

    if result_dict["ethnicity"] in ["asian", "caucasian", "african", "hispanic"]:
        ethnicity = result_dict["ethnicity"]
    else:
        ethnicity = "other"

    input_data = {
    "ethnicity": ethnicity,
    "age": result_dict["age"] or 12,

    "axial_length_right":result_dict["axial_length_right"], ###
    "axial_length_left": result_dict["axial_length_left"], ####
    "spherical_eq_right": result_dict["spherical_eq_right"], ####
    "spherical_eq_left": result_dict["spherical_eq_left"], ####
    "keratometry_right": result_dict["keratometry_right"], ###
    "keratometry_left": result_dict["keratometry_left"], ####
    "cylinder_right": result_dict["cylinder_right"], ###
    "cylinder_left": result_dict["cylinder_left"], ###
    "al_percentile_right": result_dict["al_percentile_right"], ###
    "al_percentile_left": result_dict["al_percentile_left"], ###

    "parental_history_myopia": shared_data["parent_has_myopia"],#####
    "daily_outdoor_time_hours":shared_data["outdoor_hours_per_day"],####
    "screen_time_hours_per_day": shared_data["screen_hours_per_day"], #####
    "average_sleep_hours": shared_data["sleep_hours"], #####
    "hydration_level": shared_data["hydration_frequency"], ####
    
    "diet_quality": shared_data["diet_quality"], ####
    "room_lighting": shared_data["lighting_quality"], ####
    "common_symptoms": shared_data[ "symptoms"] #####
    }
    print(input_data)
    result = predict_myopia_risk(
        input_data=input_data,
        threshold_map=threshold_map,
        scoring_weights=scoring_weights,
        demographic_schema=demographic_schema
    )
    

    return result

#print(myopia_wrapper())

def system_prompt():
    return """
        You are a senior pediatric ophthalmologist and vision care expert. You generate medically accurate, conservative, and actionable insights from structured risk data used in a commercial child myopia management platform.

        This platform is used by real families and doctors. Never provide misleading, speculative, or unverified information. Never recommend medications, surgery, or medical devices unless explicitly mentioned in the input.

        Use only best practices in pediatric optometry and public health. All insights must be realistic, age-appropriate, and safe.

        Instructions:
        You will receive structured JSON input with a child profile and vision risk details. Each factor includes both:
        - a numeric score (representing severity or magnitude)
        - a categorical risk_level ("low", "moderate", or "high")
            Use `risk_level` to determine whether to write full or brief insights.
            Use `score` to adjust the tone of explanation: a high score within a risk band may warrant stronger recommendations
        - Input includes child demographics and vision risk levels for multiple biometric and lifestyle factors.
        - Each factor has a `risk_level` of either `low`, `moderate`, or `high`.

        Guidelines:
        1. For **high** and **moderate** risks:
        - Explain the **likely cause** of the risk level.
        - Describe **future consequences** if left unmanaged.
        - Suggest **safe, evidence-based interventions**: lifestyle, behavior, screen hygiene, diet, or eye exercises.
        - Provide a **realistic timeline** for improvement (e.g., 6–12 months).

        2. For **low** risk factors:
        - Briefly note the cause of low risk.
        - Suggest **light preventive advice** to avoid worsening over time.

        3. Do not hallucinate scores, create fictional treatments, or exaggerate outcomes.
        4. Write in **supportive, professional, parent-friendly language**.
        5. Format insights clearly: 1 paragraph per factor. Include a short summary at the end if requested.
        6. Output format requirement:
            Return the insights strictly as a valid JSON object. Each key should be a factor name. Each value must be an object with the following keys:
            - "risk_level": one of ["low", "moderate", "high"]
            - "cause": string (explain why this risk is present)
            - "future_consequences": string (what may happen if unmanaged)
            - "recommendations": string (safe lifestyle/behavior changes)
            - "timeline": string (realistic expected time for improvement)

            Include a separate key `"summary"` with a short plain-language and point wise (with number) summary for parents.
            Do not return any extra commentary, markdown, or explanation — only valid JSON.

        Speak conservatively and factually — this is for a medical product.
        """


    
''''
def user_prompt(user_id, pdf_path, cursor):
    response = myopia_wrapper(user_id, pdf_path, cursor)
    details = response["details"]
    return f"""
    {
      "child_profile": {
        "age": 10,
        "ethnicity": "caucasian"
      },
      "vision_risk_details": {
        "axial_length_left": {
          "score": 6.0,
          "risk_level": "high"
        },
        "axial_length_right": {
          "score": 1.0,
          "risk_level": "low"
        },
        "spherical_eq_left": {
          "score": 4.5,
          "risk_level": "high"
        },
        "spherical_eq_right": {
          "score": 4.5,
          "risk_level": "high"
        },
        "keratometry_left": {
          "score": 3.0,
          "risk_level": "high"
        },
        "keratometry_right": {
          "score": 1.5,
          "risk_level": "moderate"
        },
        "cylinder_left": {
          "score": 1.5,
          "risk_level": "moderate"
        },
        "cylinder_right": {
          "score": 0.5,
          "risk_level": "low"
        },
        "al_percentile_left": {
          "score": 6.0,
          "risk_level": "high"
        },
        "al_percentile_right": {
          "score": 6.0,
          "risk_level": "high"
        },
        "daily_outdoor_time_hours": {
          "score": 4.0,
          "risk_level": "high"
        },
        "screen_time_hours_per_day": {
          "score": 3.0,
          "risk_level": "high"
        },
        "average_sleep_hours": {
          "score": 2.0,
          "risk_level": "high"
        },
        "room_lighting": {
          "score": 0.5,
          "risk_level": "high"
        },
        "hydration_level": {
          "score": 1.0,
          "risk_level": "moderate"
        },
        "diet_quality": {
          "score": 1.0,
          "risk_level": "high"
        },
        "common_symptoms": {
          "score": 0.75,
          "risk_level": "low"
        },
        "parental_history_myopia": {
          "score": 2.0,
          "risk_level": "moderate"
        }
      },
      "include_summary": true
    }

    """
    '''



#### debugging part
def final_myopia_wrapper():
    pdf_path = r"C:\Users\DELL\Desktop\R1_Project\Vision_Exercise_Project\data\raw\Myopia-Report-sample.pdf"

    from sqldb import get_db

    db = get_db()
    cursor = db.cursor(dictionary=True)
    print((myopia_wrapper(pdf_path=pdf_path, user_id="Ganesh_Sri12", cursor=cursor)["details"]))

    return (myopia_wrapper(pdf_path=pdf_path, user_id="Ganesh_Sri12", cursor=cursor)["details"])