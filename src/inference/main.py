from fastapi import FastAPI, Depends, HTTPException
from src.data.client_data import get_db
from src.models.schema import FeedbackSchema, UserOnboardingAnswerBase, UserPersonalDataCreate, IntakeForm, DailyUserActivityLog
from src.utils.helper import generate_session_id, get_data_llm_output, store_day_plan, get_llm_input
import os
import json
from dotenv import load_dotenv
from tests.fatigue_score import calculate_fatiue_score
from myopia_master.predictor import myopia_wrapper
from contextlib import asynccontextmanager
from scheduler import start_scheduler
from notifications import send_feedback_reminders
from notifications.send_feedback_reminders import get_db_connection
from typing import Dict,List


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

            await cursor.execute(query, (data.user_id, data.outdoor_hours_per_day, 
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
@app.post("/submit-intake")
async def submit_intake(data: IntakeForm, db=Depends(get_db)):
    try:
        if data.user_id:
            cursor = db.cursor()

            query = """
            INSERT INTO intake_questionnaire(
                user_id, symptoms, sleep_hours, bedtime, usual_diet_type, diet_quality, hydration_frequency, screen_brightness, 
                diagnosed_conditions, current_medications, parents_diagnosed_conditions
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """

            values = (
                data.user_id,
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

            await cursor.execute(query, values)
            db.commit()
            cursor.close()
            db.close()

            return {"message": " eye health answers data inserted successfully"}
        else:
            return{"message":"  Kindly provide the correct user_id that "}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


### storing user feedback data in mysql database throgh post request
@app.post("/submit-feedback")
async def submit_feedback(feedback: FeedbackSchema, db = Depends(get_db)):
    try:
        if feedback.user_id:
            session_id = generate_session_id(feedback.user_id, feedback.feedback_number)
            cursor = db.cursor()
            await cursor.execute("""
                INSERT INTO feedback (
                    user_id, session_id, feedback_number, symptom_improvement,
                    exercise_frequency, hydration_consistency,
                    screen_breaks, next_focus_area,
                    new_symptoms_observed
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                feedback.user_id,
                session_id,
                feedback.feedback_number,
                feedback.symptom_improvement,
                feedback.exercise_frequency,
                feedback.hydration_consistency,
                feedback.screen_breaks,
                feedback.next_focus_area,
                feedback.new_symptoms_observed
            ))
            db.commit()
            cursor.close()
            db.close()
            return {"message": "Feedback submitted successfully"}
        else:
            return{"message":"  Kindly provide the correct user_id that "}
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



########### Retrieving CLIENT side data from the database and showing in ui for internal use only to check the llm input ##################

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




"""####### LLM OUTPUT PLAN TO SHOW IN UI ################

@app.get("/output-plan-from-llm/{user_id}")
def llm_output(user_id: str, db = Depends(get_db)):

    try:
        cursor = db.cursor(dictionary = True)
        output, feedback_number = get_data_llm_output(user_id, cursor)
        print({"Plan": output, "feedback_number":feedback_number})
        return {"Plan": output, "feedback_number":feedback_number}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))"""
    


###### Success message to the user and automatically storing the daywise LLM output data confirmation in mysql db by the help of heper file ##########

@app.get("/load-llm-output-success-message/{user_id}")
def confirmation_store_data_n_db(user_id: str, db=Depends(get_db)):
    try:
        cursor = db.cursor(dictionary = True)
        result = store_day_plan(user_id=user_id, db=db, cursor=cursor)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

#-----------------------------------------------------------------------------------------------------------------
#### fatiue score calculation
@app.get("/fatigue-score-prediction/{user_id}")
def predict_fatigue_score(user_id: str, db = Depends(get_db)):
    try:
        score = calculate_fatiue_score(user_id, db)
        return {f"fatigue score for {user_id} is" : f" {score} / 100 "}
    except Exception as e:
        raise HTTPException(status_code = 500, detail= str(e))
    
#----------------------------------------------------------------------------------------------------------------------

#---------------------------------------------------------------------------------------------------    
#### notification send ###############
@app.get("/test-feedback-reminder")
def test_feedback_reminder_endpoint(db=Depends(get_db_connection)):
    try:
        send_feedback_reminders.send_feedback_reminder_if_due()
        return {"status": "Reminder check executed"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/run-feedback-job")
async def run_manual_job():
    try:
        from scheduler import start_scheduler
        start_scheduler()
        return {"status": "Manual job run executed"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

'''
##### datailed myopic score showing in ui ########
@app.get("/show-myopia-details")
async def show_myopia_details():
    try:
        result = myopia_wrapper()
        return {"result":result}
    except Exception as e:
        raise HTTPException(status_code=500, detail= str(e))
'''
#---------------------------------------------------------------------------------------------------------------

#### # POST endpoint to Load and track the user daily activity logs whether each acitivity done or not

@app.post("/log-user-daily-activity/")
async def log_activity(activity: DailyUserActivityLog, db=Depends(get_db)):
    try:
        cursor = db.cursor(dictionary=True)  # use dictionary to access by column names

        # Step 1: Check if entry exists
        check_sql = """
        SELECT * FROM daily_activity_log
        WHERE user_id = %s AND session_id = %s AND day = %s
        """
        await cursor.execute(check_sql, (activity.user_id, activity.session_id, activity.day))
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
            await cursor.execute(update_sql, (
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
            await cursor.execute(insert_sql, (
                activity.user_id,
                activity.session_id,
                activity.day,
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

##### Image generation dynamically ######

from diffusers import StableDiffusionPipeline
import torch, os, hashlib


# Load once globally
pipe = StableDiffusionPipeline.from_pretrained(
    "runwayml/stable-diffusion-v1-5",
    torch_dtype=torch.float32
)
pipe.to("cuda" if torch.cuda.is_available() else "cpu")  # Using CPU here for your local machine

# Hash helper
def hash_prompt(prompt):
    return hashlib.sha256(prompt.encode('utf-8')).hexdigest()[:16]


@app.get("/generate-one-day-images/{user_id}")
def generate_images_for_user(user_id: str, db=Depends(get_db)):

    cursor = db.cursor(dictionary=True)
    try:
            # Get latest session_id
        cursor.execute("""
            SELECT session_id FROM generated_daywise_plans
            WHERE user_id = %s
            ORDER BY session_id DESC LIMIT 1
        """, (user_id,))
        session_result = cursor.fetchone()
        if not session_result:
            return {"status": "error", "message": "No session found for user"}

        session_id = session_result["session_id"]

        # Get one day's plan (Day 1)
        cursor.execute("""
            SELECT day_number, meals FROM generated_daywise_plans
            WHERE user_id = %s AND session_id = %s AND day_number = 1
        """, (user_id, session_id))
        plan = cursor.fetchone()
        if not plan:
            return {"status": "error", "message": "Day 1 plan not found"}

        meals = plan["meals"]
        if isinstance(meals, str):
            import json
            meals = json.loads(meals)

        image_paths = []
        for meal_name in ["breakfast", "lunch", "snack", "dinner"]:
            meal = meals.get(meal_name)
            if not meal: continue

            prompt = meal.get("image_prompt")
            if not prompt: continue

            # Generate hash-based filename
            file_hash = hash_prompt(prompt)
            output_dir = f"images/{user_id}/day1"
            os.makedirs(output_dir, exist_ok=True)
            file_path = os.path.join(output_dir, f"{meal_name}_{file_hash}.png")

            if not os.path.exists(file_path):
                print(f"Generating image for {meal_name}...")
                image = pipe(prompt, num_inference_steps=20).images[0]
                image.save(file_path)
            else:
                print(f"Image for {meal_name} already exists.")

            image_paths.append(file_path)

        return {
            "status": "success",
            "message": f"Generated images for {user_id} - Day 1",
            "files": image_paths
        }

    except Exception as e:
        return {"status": "error", "message": str(e)}

    finally:
        cursor.close()
        if db:
            db.close()
        
