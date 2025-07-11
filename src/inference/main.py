from fastapi import FastAPI, Depends, HTTPException
from src.data.client_data import get_db
from src.models.schema import FeedbackSchema, UserOnboardingAnswerBase, UserPersonalDataCreate, IntakeForm, DailyUserActivityLog
from src.utils.helper import generate_session_id, get_data_llm_output, store_day_plan, get_llm_input, get_latest_feedback_number
import os
import json
from dotenv import load_dotenv
from tests.fatigue_score import calculate_fatiue_score
#from myopia_master.predictor import myopia_wrapper
from contextlib import asynccontextmanager
from scheduler import start_scheduler
from notifications import send_feedback_reminders
from notifications.send_feedback_reminders import get_db_connection
from typing import Dict,List
from notifications.send_feedback_reminders import update_feedback_queue_from_feedback


load_dotenv()

#-----------------------------------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler = start_scheduler()  # starts APScheduler with daily job
    yield
    scheduler.shutdown()

app = FastAPI(lifespan=lifespan)
#------------------------------------------------------------------------------------------------------

########### storing CLIENT side data in the database ##########################

#---------------------------------------------------------------------------------------------for user_id and db
## peronal data store through post request
@app.post("/user-personal-data")
def create_user_personal_data(data: UserPersonalDataCreate, db=Depends(get_db)):
    try:
        cursor = db.cursor()
    
        # Generate a short, readable user_id
        school = [i for i in data.school_name]
        b = [i for i in school]
        c = ""
        for j in b[0:3]:
            c = c+j

        user_id = f"{data.child_name}_{c}{data.child_age}"

        query = """
            INSERT INTO user_personal_data (user_id, child_name, child_age, school_name, eye_power)
            VALUES (%s, %s, %s, %s, %s)
        """
        cursor.execute(query, (user_id, data.child_name, data.child_age, data.school_name, data.eye_power))
        db.commit()
        cursor.close()
        db.close()
        # show the user_id in ui for the further data entry using this as FK
        return {"user_id": user_id, "message": "User personal data saved successfully. user_id is required to proceed. Please enter the ID you received after profile creation."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
#-----------------------------------------------------------------------------------------------------------    
### onboarding data store by post request
#----------------------------------------------------------------------------------------------------check preformed db
@app.post("/user-onboarding-data")
async def create_user_personal_onboarding_data(data: UserOnboardingAnswerBase, db=Depends(get_db)):
    
    try:
        if data.user_id:
            cursor = db.cursor()
        

            query = """
                    INSERT INTO user_onboarding_answers (
                        user_id, outdoor_hours_per_day, screen_hours_per_day, follows_20_20_20_rule,
                        holds_screen_too_close, parent_has_myopia, has_headaches_or_distance_vision_issues,
                        lighting_quality, had_eye_checkup_before, myopia_worsened_last_year,
                        axial_length_measured
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """

            cursor.execute(query, (data.user_id, data.outdoor_hours_per_day, 
                                data.screen_hours_per_day, data.follows_20_20_20_rule, 
                                data.holds_screen_too_close, data.parent_has_myopia, 
                                data.has_headaches_or_distance_vision_issues, 
                                data.lighting_quality, data.had_eye_checkup_before,data.myopia_worsened_last_year,
                                data.axial_length_measured))
            db.commit()
            cursor.close()
            db.close()

            return {"message": "User onboarding data saved successfully"}
        else:
            return{"message":"  Kindly provide the correct user_id"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
#-------------------------------------------------------------------------------------------------------------------------------

## intake eye health questionnaries daata store in mysql db through post request
@app.post("/submit-intake/{user_id}")
async def submit_intake(user_id:str,  data: IntakeForm, db=Depends(get_db)):
    try:
        
        cursor = db.cursor()

        query = """
        INSERT INTO intake_questionnaire(
            user_id, symptoms, sleep_hours, bedtime, usual_diet_type, diet_quality, hydration_frequency, screen_brightness, 
            diagnosed_conditions, current_medications, parents_diagnosed_conditions
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """

        values = (
            user_id,
            ",".join(data.symptoms),
            data.sleepHours,
            data.bedTime,
            data.usualDietType,
            data.dietQuality,
            data.hydrationFrequency,
            data.screenBrightness,
            ",".join(data.diagnosedConditions),
            data.currentMedications,
            ",".join(data.parentsDiagnosedConditions)
        )

        cursor.execute(query, values)
        db.commit()
        feedback_number = 0
        session_id = generate_session_id(user_id, feedback_number)
        cursor = db.cursor()
        cursor.execute("""
            INSERT INTO feedback (
                user_id, session_id, feedback_number, symptom_improvement,
                exercise_frequency, hydration_consistency,
                screen_breaks, next_focus_area,
                new_symptoms_observed
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            user_id,
            session_id,
            feedback_number,
            None,
            None,
            None,
            None,
            None,
            None
        ))
        db.commit()
        cursor.close()
        cursor2 = db.cursor(dictionary = True)
        store_day_plan(user_id=user_id, db=db, cursor=cursor2)
        cursor2.close()
        update_feedback_queue_from_feedback()
        db.close()

        return {"message": " eye health answers data inserted and generated plan successfully"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


### storing user feedback data in mysql database throgh post request
@app.post("/submit-feedback/{user_id}")
async def submit_feedback(user_id:str, feedback: FeedbackSchema, db = Depends(get_db)):
    try:
        cursor1 = db.cursor()
        feedback_number = get_latest_feedback_number(user_id, cursor1)
        feedback_number = feedback_number+1
        session_id = generate_session_id(user_id, feedback_number)
        cursor = db.cursor()
        cursor.execute("""
            INSERT INTO feedback (
                user_id, session_id, feedback_number, symptom_improvement,
                exercise_frequency, hydration_consistency,
                screen_breaks, next_focus_area,
                new_symptoms_observed
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            user_id,
            session_id,
            feedback_number,
            feedback.symptom_improvement,
            feedback.exercise_frequency,
            feedback.hydration_consistency,
            feedback.screen_breaks,
            feedback.next_focus_area,
            feedback.new_symptoms_observed
        ))
        db.commit()
        cursor.close()
        cursor2 = db.cursor(dictionary = True)
        store_day_plan(user_id=user_id, db=db, cursor=cursor2)
        update_feedback_queue_from_feedback()
        db.close()

        return {"message": "Feedback submitted and generated plan successfully"}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    


## Get user personal data to check user with their personal data in ui for internal use only
@app.get("/user-personal-data")
def get_all_users(db=Depends(get_db)):
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM user_personal_data")
    result = cursor.fetchall()
    cursor.close()
    db.close()
    return result



"""########### Retrieving CLIENT side data from the database and showing in ui for internal use only to check the llm input ##################

@app.get("/get-llm-input/{user_id}")
def get_llm_input_data(user_id: str, db = Depends(get_db)):
    try:
        cursor = db.cursor(dictionary = True)
        pre_feedback_llm_input, post_feedback_llm_input, feedback_number = get_llm_input(user_id, cursor)
        print("Output result:", pre_feedback_llm_input)

        return {"pre_feedback_llm_input":pre_feedback_llm_input, "post_feedback_llm_input":post_feedback_llm_input}

    except Exception as e:
        print("Output result:", str(e))

        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()
        db.close()

"""


####### LLM OUTPUT PLAN TO SHOW IN UI ################

 #### show the plan button. once plan is generated disable the generate button and enable show button
@app.get("/get-latest-plan/{user_id}")
def get_latest_14_day_plan(user_id: str, db=Depends(get_db)):
    try:
        cursor = db.cursor(dictionary=True)

        # Step 1: Check if any plan exists for user
        cursor.execute("""
            SELECT session_id 
            FROM generated_daywise_plans
            WHERE user_id = %s
            ORDER BY session_id DESC 
            LIMIT 1
        """, (user_id,))
        session = cursor.fetchone()
        if not session:
            return {
                "status": "no_plan",
                "message": f"No plan found for user {user_id}. Kindly generate your plan."
            }

        session_id = session["session_id"]

        # Step 2: Fetch all 14 day plans
        cursor.execute("""
            SELECT 
                day_number,
                exercises,
                meals,
                hydration_tip,
                child_message,
                parent_nudge
            FROM generated_daywise_plans
            WHERE user_id = %s AND session_id = %s
            ORDER BY day_number ASC
        """, (user_id, session_id))

        rows = cursor.fetchall()
        if not rows:
            return {
                "status": "no_plan",
                "message": f"No plan stored yet for session {session_id}. Kindly generate your plan."
            }

        # Step 3: Format response
        plan = []
        for row in rows:
            plan.append({
                "day_number": row["day_number"],
                "exercises": json.loads(row["exercises"]),
                "meals": json.loads(row["meals"]),
                "hydration_tip": row["hydration_tip"],
                "child_message": row["child_message"],
                "parent_nudge": row["parent_nudge"]
            })

        return {
            "status": "success",
            "user_id": user_id,
            "session_id": session_id,
            "plan": plan
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch plan: {str(e)}")

    finally:
        if cursor: cursor.close()
        if db: db.close()

###### Success message to the user and automatically storing the daywise LLM output data confirmation in mysql db by the help of heper file ##########

@app.get("/load-llm-output-success-message/{user_id}") ### generate the plan button
def confirmation_store_data_n_db(user_id: str, db=Depends(get_db)):
    try:
        cursor = db.cursor(dictionary = True)
        result = store_day_plan(user_id=user_id, db=db, cursor=cursor)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    




"""#-----------------------------------------------------------------------------------------------------------------
#### fatiue score calculation
@app.get("/fatigue-score-prediction/{user_id}")
def predict_fatigue_score(user_id: str, db = Depends(get_db)):
    try:
        score = calculate_fatiue_score(user_id, db)
        return {f"fatigue score for {user_id} is" : f" {score} / 100 "}
    except Exception as e:
        raise HTTPException(status_code = 500, detail= str(e))
    
#----------------------------------------------------------------------------------------------------------------------"""

"""#---------------------------------------------------------------------------------------------------    
#### notification send ###############
@app.get("/test-feedback-reminder")
def test_feedback_reminder_endpoint(db=Depends(get_db_connection)):
    try:
        send_feedback_reminders.send_feedback_reminder_if_due()
        return {"status": "Reminder check executed"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))"""



"""@app.get("/run-feedback-job")
async def run_manual_job():
    try:
        from scheduler import start_scheduler
        start_scheduler()
        return {"status": "Manual job run executed"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))"""


#---------------------------------------------------------------------------------------------------------------

#### # POST endpoint to Load and track the user daily activity logs whether each acitivity done or not

@app.post("/log-user-daily-activity/{user_id}/{session_id}/{day}")
async def log_activity(user_id:str, session_id: str, day:int, activity: DailyUserActivityLog, db=Depends(get_db)):
    try:
        cursor = db.cursor(dictionary=True)  # use dictionary to access by column names

        # Step 1: Check if entry exists
        check_sql = """
        SELECT * FROM daily_activity_log
        WHERE user_id = %s AND session_id = %s AND day = %s
        """
        cursor.execute(check_sql, (user_id, session_id, day))
        existing = cursor.fetchone()

        if existing:
            # Step 2: Merge existing True values with new ones
            merged = {
                'exercise_1_done': activity.exercise_1_done or existing['exercise_1_done'],
                'exercise_2_done': activity.exercise_2_done or existing['exercise_2_done'],
                'exercise_3_done': activity.exercise_3_done or existing['exercise_3_done'],
                'breakfast_done': activity.breakfast_done or existing['breakfast_done'],
                'lunch_done': activity.lunch_done or existing['lunch_done'],
                'snack_done': activity.snack_done or existing['snack_done'],
                'dinner_done': activity.dinner_done or existing['dinner_done'],
                'hydration_followed': activity.hydration_followed or existing['hydration_followed']
            }

            update_sql = """
            UPDATE daily_activity_log
            SET exercise_1_done = %s,
                exercise_2_done = %s,
                exercise_3_done = %s,
                breakfast_done = %s,
                lunch_done = %s,
                snack_done = %s,
                dinner_done = %s,
                hydration_followed = %s,
                updated_at = NOW()
            WHERE id = %s
            """
            cursor.execute(update_sql, (
                merged['exercise_1_done'],
                merged['exercise_2_done'],
                merged['exercise_3_done'],
                merged['breakfast_done'],
                merged['lunch_done'],
                merged['snack_done'],
                merged['dinner_done'],
                merged['hydration_followed'],
                existing['id']
            ))
        else:
            # Insert new row if doesn't exist
            insert_sql = """
            INSERT INTO daily_activity_log (
                user_id, session_id, day,
                exercise_1_done, exercise_2_done, exercise_3_done,
                breakfast_done, lunch_done, snack_done, dinner_done,
                hydration_followed
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            cursor.execute(insert_sql, (
                user_id,
                session_id,
                day,
                activity.exercise_1_done,
                activity.exercise_2_done,
                activity.exercise_3_done,
                activity.breakfast_done,
                activity.lunch_done,
                activity.snack_done,
                activity.dinner_done,
                activity.hydration_followed
            ))

        db.commit()
        return {"status": "success", "message": "Activity log updated"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        if cursor:
            cursor.close()
        if db:
            db.close()


#### show the generated plans from data base without regenerating again. the get end point for this part

@app.get("/get-latest-plan/{user_id}", response_model=List[Dict])
def get_latest_saved_plan(user_id: str, db=Depends(get_db)):
    try:
        cursor = db.cursor(dictionary=True)

        # Step 1: Get the session_id with highest feedback number
        session_query = """
        SELECT session_id
        FROM generated_daywise_plans
        WHERE user_id = %s
        ORDER BY CAST(SUBSTRING_INDEX(session_id, 'FN', -1) AS UNSIGNED) DESC
        LIMIT 1
        """
        cursor.execute(session_query, (user_id,))
        session_row = cursor.fetchone()

        if not session_row:
            raise HTTPException(status_code=404, detail="No plan found for this user.")

        latest_session_id = session_row["session_id"]

        # Step 2: Fetch all plan days for that session_id
        plan_query = """
        SELECT day_number, exercises, meals, hydration_tip, child_message, parent_nudge
        FROM generated_daywise_plans
        WHERE user_id = %s AND session_id = %s
        ORDER BY day_number ASC
        """
        cursor.execute(plan_query, (user_id, latest_session_id))
        plan_rows = cursor.fetchall()

        if not plan_rows:
            raise HTTPException(status_code=404, detail="No plan data found for this session.")

        # Parse JSON fields
        for row in plan_rows:
            row["exercises"] = json.loads(row["exercises"])
            row["meals"] = json.loads(row["meals"])

        return plan_rows

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()

#### Store the myopia report result through post call into the db###

from myopia_master.predictor import generate_predictions_and__ai_insights


@app.post("/myopia-report-generate-and-store/{user_id}")
def generate_myopia_report_local(user_id: str , db=Depends(get_db)):
    try:
        # Temporary hardcoded PDF path for testing
        sample_pdf_path = r"C:\Users\DELL\Desktop\R1_Project\Vision_Exercise_Project\data\raw\MM019.pdf"
        result = generate_predictions_and__ai_insights(
            pdf_path=sample_pdf_path,
            user_id=user_id
        )

        return {
            "message": f"✅{result}"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

############ Myopia master result pulled from db through api ##########

@app.get("/myopia-result/{user_id}")
def get_clean_myopia_output(user_id: str, db=Depends(get_db)):
    try:
        cursor = db.cursor(dictionary=True)

        # 1. Get latest input record to find input_id
        cursor.execute("""
            SELECT input_id FROM myopia_input_data 
            WHERE user_id = %s 
            ORDER BY created_at DESC 
            LIMIT 1
        """, (user_id,))
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="No input record found")

        input_id = row["input_id"]

        # 2. Get prediction (cleaned)
        cursor.execute("""
            SELECT left_eye_score, right_eye_score, shared_score, total_score, 
                   overall_risk_level, eye_risk_levels, factor_wise_scores, created_at
            FROM myopia_predictions 
            WHERE input_id = %s
        """, (input_id,))
        prediction = cursor.fetchone()
        if prediction:
            # Convert stringified JSON fields
            prediction["eye_risk_levels"] = json.loads(prediction["eye_risk_levels"])
            prediction["factor_wise_scores"] = json.loads(prediction["factor_wise_scores"])

        # 3. Get AI insights (excluding ids and user_id)
        cursor.execute("""
            SELECT summary, axial_length_left, axial_length_right, spherical_eq_left, spherical_eq_right,
                   keratometry_left, keratometry_right, cylinder_left, cylinder_right,
                   al_percentile_left, al_percentile_right, hydration_level, diet_quality,
                   screen_time_hours_per_day, daily_outdoor_time_hours, average_sleep_hours,
                   parental_history_myopia, room_lighting, common_symptoms, created_at
            FROM myopia_ai_insights 
            WHERE input_id = %s
        """, (input_id,))
        insights = cursor.fetchone()
        if insights:
            # Convert all JSON columns back to dict
            for key in insights:
                if key != "created_at":
                    insights[key] = json.loads(insights[key])

        return {
            "prediction_summary": prediction,
            "ai_insights": insights
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"MySQL error: {str(e)}")
    finally:
        if cursor:
            cursor.close()
        if db:
            db.close()


################## Image generation part ##############
import os
import json
import hashlib
from fastapi import FastAPI, Depends
from fastapi.staticfiles import StaticFiles
from diffusers import StableDiffusionPipeline
import torch
from src.utils.s3_utils import upload_image_to_s3, generate_s3_url, file_exists_in_s3

# Mount local image folder (for development mode)
app.mount("/outputs/generated_example_images", StaticFiles(directory="outputs/generated_example_images"), name="outputs")

# Load diffusion model
dtype = torch.float16 if torch.cuda.is_available() else torch.float32
print("🚀 Starting model load...")
pipe = StableDiffusionPipeline.from_pretrained(
    "runwayml/stable-diffusion-v1-5", torch_dtype=dtype
)
pipe.to("cuda" if torch.cuda.is_available() else "cpu")
print("✅ Model loaded.")


# Utility to hash prompt into filename
def hash_prompt(prompt: str) -> str:
    if not isinstance(prompt, str):
        raise ValueError(f"Expected prompt as string, got {type(prompt)}")
    return hashlib.sha256(prompt.encode("utf-8")).hexdigest()[:16]


@app.get("/generate-meal-images/{user_id}")
def generate_all_meal_images(user_id: str, db=Depends(get_db)):
    cursor = db.cursor(dictionary=True)
    try:
        # Get latest session_id
        cursor.execute("""
            SELECT session_id FROM generated_daywise_plans
            WHERE user_id = %s
            ORDER BY session_id DESC LIMIT 1
        """, (user_id,))
        session = cursor.fetchone()
        if not session:
            return {"status": "error", "message": "No plan found for user"}

        session_id = session["session_id"]

        # Get all 14 daywise plans
        cursor.execute("""
            SELECT day_number, meals FROM generated_daywise_plans
            WHERE user_id = %s AND session_id = %s
        """, (user_id, session_id))
        plans = cursor.fetchall()

        if not plans:
            return {"status": "error", "message": "No daywise plans found"}

        all_files = []

        for plan in plans:
            day = plan["day_number"]
            meals = plan["meals"]

            if isinstance(meals, str):
                meals = json.loads(meals)

            for meal_name in ["breakfast", "lunch", "snack", "dinner"]:
                meal = meals.get(meal_name)
                if not isinstance(meal, dict):
                    print(f"⚠️ Skipping {meal_name} - Day {day}: Invalid structure")
                    continue

                prompt = meal.get("image_prompt")
                if not isinstance(prompt, str) or not prompt.strip():
                    print(f"⚠️ Skipping {meal_name} - Day {day}: Invalid prompt -> {prompt}")
                    continue

                print(f"Processing image for {meal_name} - Day {day} with prompt: {prompt[:60]}...")

                # Generate filename from prompt
                file_hash = hash_prompt(prompt)
                filename = f"{meal_name}_{file_hash}.png"

                # ---------------------
                # S3 Bucket Version
                # ---------------------
                s3_key = f"{user_id}/{session_id}/day{day}/{filename}"

                if not file_exists_in_s3(s3_key):
                    print(f"Generating image: {s3_key}")
                    image = pipe(prompt, num_inference_steps=20).images[0]

                    temp_dir = "temp_images"
                    os.makedirs(temp_dir, exist_ok=True)
                    temp_path = os.path.join(temp_dir, filename)
                    image.save(temp_path)

                    upload_image_to_s3(temp_path, s3_key)
                    os.remove(temp_path)

                image_url = generate_s3_url(s3_key)

                # --------------------------
                # Local Folder (Optional)
                # --------------------------
                """
                local_dir = f"outputs/generated_example_images/{user_id}/{session_id}/day{day}"
                os.makedirs(local_dir, exist_ok=True)
                local_path = os.path.join(local_dir, filename)

                if not os.path.exists(local_path):
                    print(f" Generating local image: {local_path}")
                    image = pipe(prompt, num_inference_steps=20).images[0]
                    image.save(local_path)

                relative_path = local_path.replace("outputs/", "")
                image_url = f"/outputs/{relative_path}"
                """

                all_files.append({
                    "day": day,
                    "meal": meal_name,
                    "filename": filename,
                    "url": image_url
                })

        return {
            "status": "success",
            "message": f"Images generated for {user_id}, session {session_id}",
            "images": all_files
        }

    except Exception as e:
        return {"status": "error", "message": str(e)}

    finally:
        if cursor: cursor.close()
        if db: db.close()


