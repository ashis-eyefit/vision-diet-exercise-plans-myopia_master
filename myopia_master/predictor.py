# Load json files
import json
import os
from myopia_master.data_extractor import parse_myopia_data

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
            
            ## biometric factors depens on demogrphies [age and ethnicity]
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
                #print("------------------------------------------", detail_scores)

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
        "divider":"========================================== FACTOR WISE DETAILED SCORE ====================================================",
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
    #print(input_data)
    result = predict_myopia_risk(
        input_data=input_data,
        threshold_map=threshold_map,
        scoring_weights=scoring_weights,
        demographic_schema=demographic_schema
    )
    
    return result, ethnicity, input_data

#print(myopia_wrapper())

####### Store the data into the db ####################
import mysql.connector
from mysql.connector import Error
import json

def store_myopia_data(user_id:str, input_data: dict, prediction_data: dict, ai_insight_data: dict, db):
    try:
    
        cursor = db.cursor(dictionary = True)

        # === 1. Insert into myopia_input_data ===
        insert_input_query = """
        INSERT INTO myopia_input_data (
            user_id, age, ethnicity, axial_length_right, axial_length_left,
            spherical_eq_right, spherical_eq_left, keratometry_right, keratometry_left,
            cylinder_right, cylinder_left, al_percentile_right, al_percentile_left,
            parental_history_myopia, daily_outdoor_time_hours, screen_time_hours_per_day,
            average_sleep_hours, hydration_level, diet_quality, room_lighting,
            common_symptoms, created_at
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
        """

        common_symptoms_json = json.dumps(input_data.get("common_symptoms", []))

        input_values = (
            user_id, input_data["age"], input_data["ethnicity"],
            input_data.get("axial_length_right"), input_data.get("axial_length_left"),
            input_data.get("spherical_eq_right"), input_data.get("spherical_eq_left"),
            input_data.get("keratometry_right"), input_data.get("keratometry_left"),
            input_data.get("cylinder_right"), input_data.get("cylinder_left"),
            input_data.get("al_percentile_right"), input_data.get("al_percentile_left"),
            input_data.get("parental_history_myopia"),
            input_data.get("daily_outdoor_time_hours"),
            input_data.get("screen_time_hours_per_day"),
            input_data.get("average_sleep_hours"),
            input_data.get("hydration_level"), input_data.get("diet_quality"),
            input_data.get("room_lighting"), common_symptoms_json
        )

        cursor.execute(insert_input_query, input_values)
        input_id = cursor.lastrowid

        # === 2. Insert into myopia_predictions ===
        insert_prediction_query = """
        INSERT INTO myopia_predictions (
            input_id, user_id, age_group, left_eye_score, right_eye_score, shared_score,
            total_score, overall_risk_level, eye_risk_levels, factor_wise_scores, created_at
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
        """

        prediction_values = (
            input_id,
            user_id,
            prediction_data.get("age_group"),
            prediction_data.get("left_eye_score"),
            prediction_data.get("right_eye_score"),
            prediction_data.get("shared_score"),
            prediction_data.get("total_score"),
            prediction_data.get("overall_risk_level"),
            json.dumps(prediction_data.get("eye_risk_levels", {})),
            json.dumps(prediction_data.get("details", {}))
        )

        cursor.execute(insert_prediction_query, prediction_values)

        # === 3. Insert into myopia_ai_insights ===
        insert_insight_query = """
        INSERT INTO myopia_ai_insights (
            input_id, user_id, summary, axial_length_left, axial_length_right, spherical_eq_left, spherical_eq_right,
            keratometry_left, keratometry_right, cylinder_left, cylinder_right, al_percentile_left, al_percentile_right,
            hydration_level, diet_quality, screen_time_hours_per_day, daily_outdoor_time_hours,
            average_sleep_hours, parental_history_myopia, room_lighting, common_symptoms, created_at
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
        """

        insight_values = (
            input_id,
            user_id,
            json.dumps(ai_insight_data.get("summary")),
            json.dumps(ai_insight_data.get("axial_length_left")),
            json.dumps(ai_insight_data.get("axial_length_right")),
            json.dumps(ai_insight_data.get("spherical_eq_left")),
            json.dumps(ai_insight_data.get("spherical_eq_right")),
            json.dumps(ai_insight_data.get("keratometry_left")),
            json.dumps(ai_insight_data.get("keratometry_right")),
            json.dumps(ai_insight_data.get("cylinder_left")),
            json.dumps(ai_insight_data.get("cylinder_right")),
            json.dumps(ai_insight_data.get("al_percentile_left")),
            json.dumps(ai_insight_data.get("al_percentile_right")),
            json.dumps(ai_insight_data.get("hydration_level")),
            json.dumps(ai_insight_data.get("diet_quality")),
            json.dumps(ai_insight_data.get("screen_time_hours_per_day")),
            json.dumps(ai_insight_data.get("daily_outdoor_time_hours")),
            json.dumps(ai_insight_data.get("average_sleep_hours")),
            json.dumps(ai_insight_data.get("parental_history_myopia")),
            json.dumps(ai_insight_data.get("room_lighting")),
            json.dumps(ai_insight_data.get("common_symptoms"))
        )

        cursor.execute(insert_insight_query, insight_values)

        db.commit()
        #print("✅ Myopia input, prediction, and insight data stored successfully.")

    except Error as e:
        if db:
            db.rollback()
        print("❌ Error:", str(e))

    finally:
        if cursor:
            cursor.close()

############ Generate output ###################

import openai
from typing import Dict
import os
import json
import asyncio
from myopia_master.sqldb import get_db
from dotenv import load_dotenv

load_dotenv()

client = openai.OpenAI(api_key = os.getenv("OPENAI_API"))

pdf_path = r"C:\Users\DELL\Desktop\R1_Project\Vision_Exercise_Project\data\raw\Myopia-Report-sample.pdf"


def generate_predictions_and__ai_insights(pdf_path, user_id) -> Dict[str, str]:
  try:
    db = get_db()
    cursor = db.cursor(dictionary=True)
    result, ethnicity, input_data = myopia_wrapper(pdf_path=pdf_path, user_id=user_id, cursor=cursor)
    
    system_prompt = """
      You are a senior pediatric ophthalmologist and vision care expert. You generate medically accurate, conservative, and actionable insights from structured risk data used in a commercial child myopia management platform.

      This platform is used by real families and doctors. Never provide misleading, speculative, or unverified information. Never recommend medications, surgery, or medical devices unless explicitly mentioned in the input.

      Use only best practices in pediatric optometry and public health. All insights must be realistic, age-appropriate, and safe.

      Instructions:
      You will receive an input with a child profile and vision risk details. Each risk factor includes both:
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
    
    risk_score_details = result["details"]
    user_prompt = f"""
          child profile: 
            - age: {result["age"]}
            - ethnicity: {ethnicity}
    
          vision_risk_details:
            - axial_length_left: 
              score: {risk_score_details['axial_length_left']['score']}
              risk_level: {risk_score_details['axial_length_left']['risk_level']}
            
            - axial_length_right: 
              score: {risk_score_details['axial_length_right']['score']}
              risk_level: {risk_score_details['axial_length_right']['risk_level']}
            
            - spherical_eq_left: 
              score : {risk_score_details['spherical_eq_left']['score']}
              risk_level: {risk_score_details['spherical_eq_left']['risk_level']}
              
            - spherical_eq_right: 
              score: {risk_score_details['spherical_eq_right']['score']}
              risk_level: {risk_score_details['spherical_eq_right']['risk_level']}
        
            - keratometry_left: 
              score: {risk_score_details['keratometry_left']['score']}
              risk_level: {risk_score_details['keratometry_left']['risk_level']}
            
            - keratometry_right":
              score: {risk_score_details['keratometry_right']['score']}
              risk_level: {risk_score_details['keratometry_right']['risk_level']}
        
            - cylinder_left": 
              score: {risk_score_details['cylinder_left']['score']}
              risk_level: {risk_score_details['cylinder_left']['risk_level']}
            
            - cylinder_right: 
              score:{risk_score_details['cylinder_right']['score']}"
              risk_level: {risk_score_details['cylinder_right']['risk_level']}
            
            - al_percentile_left: 
              score: {risk_score_details['al_percentile_left']['score']}
              risk_level: {risk_score_details['al_percentile_left']['risk_level']}
            
            - al_percentile_right: 
              score: {risk_score_details['al_percentile_right']['score']}
              risk_level: {risk_score_details['al_percentile_right']['risk_level']}


            - daily_outdoor_time_hours:
              score: {risk_score_details['daily_outdoor_time_hours']['score']}
              "risk_level": {risk_score_details['daily_outdoor_time_hours']['risk_level']}
            
            - screen_time_hours_per_day: 
              score: {risk_score_details['screen_time_hours_per_day']['score']}
              risk_level: {risk_score_details['screen_time_hours_per_day']['risk_level']}
            
            - average_sleep_hours: 
              score: {risk_score_details['average_sleep_hours']['score']}
              risk_level: {risk_score_details['average_sleep_hours']['risk_level']}
            
            - room_lighting:
              score: {risk_score_details['room_lighting']['score']}
              risk_level: {risk_score_details['room_lighting']['risk_level']}
            
            - hydration_level: 
              score: {risk_score_details["hydration_level"]['score']}
              risk_level: {risk_score_details['hydration_level']['risk_level']}
        
            - diet_quality: 
              score: {risk_score_details['diet_quality']['score']}
              risk_level: {risk_score_details['diet_quality']['risk_level']}
            
            - common_symptoms: 
              score: {risk_score_details['common_symptoms']['score']}
              risk_level: {risk_score_details['common_symptoms']['risk_level']}
        
            - parental_history_myopia: 
              score: {risk_score_details['parental_history_myopia']['score']}
              risk_level: {risk_score_details['parental_history_myopia']['risk_level']}
            
        Finally, include an overall summary of the report
        """

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        temperature=0.7,
        max_tokens=4500,
    )
    content = response.choices[0].message.content

    if not content:
      raise ValueError("OpenAI response content is empty!")

    # Clean triple-backtick blocks, if present
    if content.startswith("```json"):
      content = content.strip("```json").strip("```").strip()
    elif content.startswith("```"):
      content = content.strip("```").strip()

      # debuging print
    #print("🔎 Cleaned Content:\n", content)

    parsed_content = json.loads(content)
    final_result = {
        #"Predictions": result,
        #"AI-Insights": parsed_content,
        "message": "myopia data generated and stored successfully"
        }
    ### store the data when this function triggered###
    store_myopia_data(user_id= user_id, input_data=input_data, prediction_data= result, ai_insight_data=parsed_content, db = db)
    db.close()
    return final_result
  except json.JSONDecodeError as e:
    raise ValueError(f"Failed to parse JSON. Raw content:\n{content}\n\nError: {e}")




#### debugging part


#sample_pdf = r"C:\Users\DELL\Desktop\R1_Project\Vision_Exercise_Project\data\raw\MM019.pdf"

#print(generate_predictions_and__ai_insights(pdf_path=sample_pdf, user_id="Ganesh_Sri12"))