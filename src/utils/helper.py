from datetime import date
import json
import openai
import os
from src.models.schema import DayPlanOutput
from typing import Union


### Generating unique session_id for the feedback ######
def generate_session_id(user_id: str, feedback_number: int = 0) -> str:
    #today = date.today().strftime('%d_%m_%Y')
        return f"{user_id}_FN{feedback_number}"
   

###### Retrieve data for LLM input prompt ############
def get_llm_input(user_id: str, cursor) -> dict:

    try:   
        # Get personal data (non-PII fields only)
        cursor.execute("""
            SELECT child_age, eye_power
            FROM user_personal_data
            WHERE user_id = %s
        """, (user_id,))
        personal_data = cursor.fetchone()
        #print("debug user profile",personal_data)

        if not personal_data:
            #print("debug user profile","no personal_data")
            raise ValueError("User personal data not found")

        # Get onboarding data (non-PII fields only)
        cursor.execute("""
            SELECT outdoor_hours_per_day, screen_hours_per_day, follows_20_20_20_rule,
                    holds_screen_too_close, parent_has_myopia, has_headaches_or_distance_vision_issues,
                    lighting_quality, had_eye_checkup_before, myopia_worsened_last_year, axial_length_measured
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
                    bedtime, usual_diet_type, diet_quality, hydration_frequency,
                    screen_brightness, diagnosed_conditions, current_medications, parents_diagnosed_conditions
            FROM intake_questionnaire
            WHERE user_id = %s
        """, (user_id,))
        intake_data = cursor.fetchone()
        #print("debug intake data",intake_data)
    
        if not intake_data:
            #print("debug intake data","no intake_data")
            raise ValueError("No intake eye health answers available")

        
        feedback_data = {}
        feedback_number = 0

        cursor.execute("""
            SELECT feedback_number
            FROM feedback
            WHERE user_id = %s
            ORDER BY created_at DESC
            LIMIT 1
        """, (user_id,))
        result = cursor.fetchone()

        if result and result["feedback_number"] is not None:
            feedback_number = result["feedback_number"]

        if feedback_number > 0:
            cursor.execute("""
                SELECT symptom_improvement, exercise_frequency, hydration_consistency,
                    screen_breaks, next_focus_area, new_symptoms_observed
                FROM feedback
                WHERE user_id = %s
                ORDER BY created_at DESC
                LIMIT 1
            """, (user_id,))
            feedback_data = cursor.fetchone() or {}

                

        # Construct profile data for LLM
        llm_input_profile_data = {
            # registration
            "age": personal_data["child_age"],
            "Existing_power": personal_data["eye_power"],
            # Onboarding
            "outdoor_hours_per_day": onboarding_data["outdoor_hours_per_day"],
            "screen_hours_per_day": onboarding_data["screen_hours_per_day"],
            "follows_20_20_20_rule": onboarding_data["follows_20_20_20_rule"],
            "holds_screen_too_close": onboarding_data["holds_screen_too_close"],
            "parent_has_myopia": onboarding_data["parent_has_myopia"],
            "has_headaches_or_distance_vision_issues": onboarding_data["has_headaches_or_distance_vision_issues"],
            "lighting_quality": onboarding_data["lighting_quality"],
            "had_eye_checkup_before": onboarding_data["had_eye_checkup_before"],
            "myopia_worsened_last_year": onboarding_data["myopia_worsened_last_year"],
            "axial_length_measured": onboarding_data["axial_length_measured"],
            # Intake
            "symptoms": [s.strip() for s in intake_data["symptoms"].split(",") if s],
            "sleep_hours": intake_data["sleep_hours"],
            "bedtime": intake_data["bedtime"],
            "usual_diet_type": intake_data["usual_diet_type"],
            "diet_quality": intake_data["diet_quality"],
            "hydration_frequency": intake_data["hydration_frequency"],
            "screen_brightness": intake_data["screen_brightness"],
            "diagnosed_conditions": [s.strip() for s in intake_data["diagnosed_conditions"].split(",") if s],
            "current_medications": intake_data["current_medications"],
            "parents_diagnosed_conditions": [s.strip() for s in intake_data["parents_diagnosed_conditions"].split(",") if s]
        }

        # Leave feedback block ready for later expansion
        llm_input_feedback_data = {
            "symptom_improvement": feedback_data.get("symptom_improvement", ""),
            "exercise_frequency": feedback_data.get("exercise_frequency", ""),
            "hydration_consistency": feedback_data.get("hydration_consistency", ""),
            "screen_breaks": feedback_data.get("screen_breaks", ""),
            "next_focus_area": feedback_data.get("next_focus_area", ""),
            "new_symptoms_observed": feedback_data.get("new_symptoms_observed", "")
        }

        #print("\\\\\\\\\\\\\\\\\\\\\\\\\\", llm_input_profile_data)

        return llm_input_profile_data, llm_input_feedback_data, feedback_number # or combine with feedback later
    except Exception as e:
        raise RuntimeError(f"Error in get_llm_input(): {str(e)}")




##### Parsing the data from pre-feedback llm output data through api_all #######

### openai client for LLM("gpt-4o") access through api call
client = openai.OpenAI(api_key = os.getenv("OPENAI_API_KEY"))


def get_data_llm_output(user_id:str, cursor)->json:
    pre_feedback_llm_input, post_feedback_llm_input, feedback_number = get_llm_input(user_id, cursor)
        #print("🔍 Getting LLM input for user_id:", user_id)
        #print(pre_feedback_llm_input)
    system_prompt_pre = """
          You are a paediatric eye care vision expert with extensive experience in suggesting vision activities (exercises and games) and diet to children. Your task is to generate a structured JSON-based daily vision care plan for children aged 4-15. Use the given profile to generate Day 1 only of a 14-day plan.

        PLAN OBJECTIVE:
        Design a safe, fun, playful, short, and engaging plan to:
        - Reduce symptoms and cure diagnosed conditions
        - Include easy methods (e.g., games, break timers, parental support)
        - Improve hydration and nutrition (e.g., reusable superhero bottles, sticker charts)
        - Build healthy habits related to digital screen use, food, and rest
        - Keep the user's usual diet type in mind while recommending food for specific diet
        - Be imaginative, child-friendly, and varied
        - Activities should feel like games or missions
        - Avoid repeating the same food, exercise or game more than twice in 14 days
        - Keep total daily time short (7-10 mins max)
        - Assume light parental support is available
        

        DAILY OUTPUT STRUCTURE:
        Each day should include the following:

        1. **Vision Activities (2 exercises and 1 game per day)**:
        - `name`
        - `duration`: Between 40 to 50 seconds only for exercise and 2 minutres only for game
        - `simple explanation`
        - `specific benefit` (e.g., improve focus, relax muscle)
        - `video_filename` (choose from the mapping below if profile matches)


        🎥 VIDEO FILENAME MAPPING:
        Use the JSON mapping of activity names and filenames to suggest only exact activity names and filenames when the benefit or symptom matches. 
        Suggest activities ending with exercise as exercises, and those ending with game as games.
        Use only the matching video_filename from the json. Omit the field if no match applies without invention.
        {
            "Eye-Hand Coordination Game": "eye_hand_coordination_game.mp4",
            "Focus Training Ball Bouncing Game": "focus_training_game.mp4",
            "Mirror Blink Race Exercise": "mirror_blink_game.mp4",
            "Eye Strain Relief Massage Exercise": "eye_strain_relief.mp4",
            "Palming Relaxation Exercise": "palming_relaxation.mp4",
            "Near-Far Focus Switch Exercise": "near_far_focus.mp4",
            "Astigmatism Tracking Movement Exercise": "tracking_movement_exercise.mp4",
            "Sunlight Play Task Game": "sunlight_play_task.mp4",
            "Smooth Tracking Exercise": "smooth_tracking_exercise.mp4",
            "Eye Muscle 8-Pattern Exercise": "eight_pattern_exercise.mp4",
            "Saccadic Movement Training Exercise": "saccade_training_game.mp4",
            "Peripheral Awareness Exercise": "peripheral_awareness_game.mp4",
            "Focus Switch Objects Exercise": "focus_switch_objects.mp4",
            "Myopia Control Walk Game": "myopia_control_walk.mp4",
            "Clockwise Eye Roll Exercise": "clockwise_eye_roll.mp4",
            "Anti-Clockwise Eye Roll Exercise": "anticlockwise_eye_roll.mp4",
            "Zoom Focus Exercise": "zoom_focus_exercise.mp4",
            "Pencil Pushup Focus Exercise": "pencil_pushup_exercise.mp4",
            "Blinking with Breathing Exercise": "blinking_breathing_relaxation.mp4",
            "Diagonal Eye Tracking Exercise": "diagonal_tracking_exercise.mp4",
            "Thumb Near-Far Focus Exercise": "thumb_focus_shift.mp4",
            "Eye Stretch Up and Down Exercise": "eye_stretch_up_down.mp4",
            "Spoon Tracking Challenge Exercise": "spoon_tracking_game.mp4",
            "Color Contrast Explorer Exercise": "color_contrast_explorer.mp4",
            "Eye Shoulder Tag Exercise": "shoulder_tap_eyes.mp4",
            "Fan Blade Zoom Focus Exercise": "fan_blade_focus.mp4",
            "Mirror Eye Movement Mimic Exercise": "mirror_eye_mimic.mp4",
            "Vertical Line Chase Exercise": "vertical_chase_game.mp4", 
            "Snack Time Color Hunt Game": "color_snack_focus.mp4",
            "Shape Recognition Blink Task Exercise": "shape_blink_game.mp4",
            "Shadow Chase Peripheral Exercise": "shadow_chase_peripheral.mp4",
            "Spiral Spin Exercise": "spiral_spin.mp4",
            "Fruit Toss Distance Drill Exercise": "fruit_toss_focus.mp4",
            "Water Bottle Tracking Exercise": "water_bottle_track.mp4",
            "Late Afternoon Skyline Horizon Distant Tree Blink Game": "late_afternoon_skyline_blink_relax.mp4",
            "Toy Hunt Peripheral Exercise": "toy_peripheral_spotting.mp4",
            "Rainbow Rope Eye Guide Exercise": "rainbow_rope_jumps.mp4",
            "Color Hunt in Room Game": "room_color_scan.mp4",
            "Glow Dot Grid Jump Exercise": "glow_dot_grid_saccade.mp4", 
            "Bouncing Letter Focus Game Exercise": "letter_focus_bounce.mp4",
            "Star Figure Tracking Exercise": "star_pattern_tracking.mp4",
            "Foot Tap Direction Game": "foot_tap_eye_lead.mp4",
            "Color Toss Sorting Game": "color_toss_sorting.mp4",
            "Pillow Maze Obstacle Game": "pillow_maze_navigation.mp4",
            "Box Peek & Recall Game": "box_peek_memory.mp4",
            "Soap Bubble Pop Walk Game": "bubble_pop_chase.mp4",
            "Shadow Shape Tracing Game":"shadow_trace_game.mp4",
            "Toy Toss and Spot Game": "toy_toss_spot_game.mp4",
            "Animal Track and Freeze Game": "animal_track_freeze.mp4"
        }


        2. **Meal Recommendations (4 meals)**:
        Each meal includes:
        - `food`: List of 1-2 Indian food items supporting eye health based on user's usual diet type
        - `portion_size`: Use clear child-friendly measures like grams (g), ml, or count (e.g., “150 ml smoothie” or “1 medium carrot”)
        - `benefit`: Specific to **eye health** (e.g., "Helps retina stay strong", "Filters harmful blue light")
        - `nutrients`: List 1-2 key nutrients per portion using only familiar units like milligrams (mg) or micrograms (µg). Never use International Units (IU). Always add a short emoji-based explanation (e.g., "Vitamin A": "300 µg - 👁️ Supports retina health").
            Example: `{ "Vitamin A": "300 µg - 👁️ Supports retina health", "Lutein": "2 mg - 🌿 Filters harmful blue light" }`
        - `image_prompt`: Realistic food prompt in Indian style (e.g., “A colorful plate with palak paneer and roti, child-friendly kitchen setting, bright lighting”)

        Meals:
        - breakfast
        - lunch
        - snack
        - dinner

        Make sure diet section includes:
          - Portion sizes (in grams, ml, or count-based like “1 small banana”)
          - Familiar nutrients (in mg or µg) with emoji explanations
          - Calorie information for each portion
          - Simple language (no technical or medical terms)
            
          :: Also make sure all benefit explanations (for exercises, meals, etc.) use very simple, clear language. No complex terms or medical jargon — make it easy for less literate parents to understand.

        3. **Hydration Tip or Reminder**:
        - Suggest **realistic**, fun ideas that don’t require daily new bottles
        - Examples:
          - “Add lemon slices to your water for a fun twist!”
          - “Stick a cartoon sticker on your bottle and take 5 sips every hour”
          - “Use a tracker sticker on your bottle to tick off sips!”

        4. **Motivational Message for the Child**:
        - Encouraging, playful one-liner (e.g., “Your eyes are superheroes — let's train them like champions!”)

        5. **Supportive Nudge for the Parent**:
        - Helpful parenting tip for the day (e.g., “Try doing 20-20-20 breaks together during screen time”)

        FORMAT:
        Return a full structured JSON plan.

        EXAMPLE SNIPPET:
        [
        {
        "day": 1,
        "exercises": [
          {
            "name": "Focus Training Game",
            "duration": "45 seconds",
            "explanation": "Follow the bouncing ball with your eyes only, no head movement!",
            "benefit": "Improves focus and eye muscle control",
            "video_filename": "focus_training_game.mp4"
          }
        ],
        "meals": {
          "breakfast": {
            "food": ["Spinach paratha", "Papaya slices"],
            "portion_size: Always provide child-friendly measures using grams (g) or milliliters (ml) or count-based units (like “1 medium guava”, “5 almonds”). For items like rice, paneer, dal, etc., include the gram equivalent (e.g., “½ cup cooked brown rice (≈100g)”, “1 bowl dal (≈150g)”).",
            "benefit": "Strengthens vision by nourishing the retina",
            "calorie_information":"This 
            "nutrients": {
              "Vitamin A": "950 IU - 👁️ Supports retina health",
              "Lutein": "2.5 mg - 🌿 Filters blue light"
            },
            "calorie_information": "Spinach paratha (≈100g) ≈ 200 kcal, Papaya slices (≈75g) ≈ 30 kcal — Total ≈ 230 kcal",
            "image_prompt": "A spinach paratha with papaya slices on a bright, child-friendly Indian-style breakfast plate"
          },
          ...
        },
        "hydration_tip": "Infuse your water with lemon and mint — superhero potion for your eyes!",
        "child_message": "Blink blink like a bunny! Your eyes will thank you!",
        "parent_nudge": "Remind your child to blink often during screen time to avoid dry eyes"
        },
        {"day":2,
        ...
        ...
        }
        ]


        IMPORTANT: Return only valid JSON, without any explanations, commentary, or markdown formatting (e.g., no triple backticks).
        """

    user_prompt_pre= f"""
        Generate Day 1 only of a structured 14-day vision care plan for a child based on the following profile:

        PROFILE:
        - Age: {pre_feedback_llm_input["age"]}
        - Existing eye power: {pre_feedback_llm_input["Existing_power"]}
        - Gets outdoor time: {pre_feedback_llm_input["outdoor_hours_per_day"]}
        - Daily screen time: {pre_feedback_llm_input["screen_hours_per_day"]}
        - 20-20-20 rule followed: {pre_feedback_llm_input["follows_20_20_20_rule"]}
        - Holds screen too close: {pre_feedback_llm_input["holds_screen_too_close"]}
        - Parent has myopia: {pre_feedback_llm_input["parent_has_myopia"]}  
        - Child feels headache or difficulty seeing distant objects: {pre_feedback_llm_input["has_headaches_or_distance_vision_issues"]}
        - Light quality while studying and using screen: {pre_feedback_llm_input["lighting_quality"]} 
        - Last eye checkup: {pre_feedback_llm_input["had_eye_checkup_before"]}
        - Myopia worsened last year: {pre_feedback_llm_input["myopia_worsened_last_year"]}
        - Axial length measured: {pre_feedback_llm_input["axial_length_measured"]}
        - Eye symptoms: {pre_feedback_llm_input["symptoms"]}
        - Sleep duration: {pre_feedback_llm_input["sleep_hours"]}
        - Usual bedtime: {pre_feedback_llm_input["bedtime"]}
        - Usual diet type: {pre_feedback_llm_input["usual_diet_type"]}
        - Diet quality: {pre_feedback_llm_input["diet_quality"]}
        - Hydration: {pre_feedback_llm_input["hydration_frequency"]}
        - Screen brightness: {pre_feedback_llm_input["screen_brightness"]}
        - Child's diagnosed conditions: {pre_feedback_llm_input["diagnosed_conditions"]}
        - Current child's medications: {pre_feedback_llm_input["current_medications"]}
        - Parents diagnosed with: {pre_feedback_llm_input["parents_diagnosed_conditions"]}         
        """
    
    system_prompt_post = """
          You are a paediatric eye care vision expert with extensive experience in suggesting vision activities (exercises and games) and diet to children. Your task is to generate a structured JSON-based daily vision care plan for children aged 4-15. Use the given child's profile and consider the parent's last 2 days feedback to generate a 2-days plan.

        PLAN OBJECTIVE:
        Design a safe, fun, playful, short, and engaging plan to:
        - Reduce symptoms and cure diagnosed conditions
        - Include easy methods (e.g., games, break timers, parental support)
        - Improve hydration and nutrition (e.g., reusable superhero bottles, sticker charts)
        - Build healthy habits related to digital screen use, food, and rest
        - Keep the user's usual diet type in mind while recommending food for specific diet
        - Be imaginative, child-friendly, and varied
        - Activities should feel like games or missions
        - Avoid repeating the same food, exercise or game more than twice in 14 days
        - Keep total daily time short (7-10 mins max)
        - Assume light parental support is available
        

        DAILY OUTPUT STRUCTURE:
        Each day should include the following:

        1. **Vision Activities (2 exercises and 1 game per day)**:
        - `name`
        - `duration`: Between 40 to 50 seconds only for exercise and 2 minutres only for game
        - `simple explanation`
        - `specific benefit` (e.g., improve focus, relax muscle)
        - `video_filename` (choose from the mapping below if profile matches)


        🎥 VIDEO FILENAME MAPPING:
        Use the JSON mapping of activity names and filenames to suggest only exact activity names and filenames when the benefit or symptom matches. 
        Suggest activities ending with exercise as exercises, and those ending with game as games.
        Use only the matching video_filename from the json. Omit the field if no match applies without invention.
        {
            "Eye-Hand Coordination Game": "eye_hand_coordination_game.mp4",
            "Focus Training Ball Bouncing Game": "focus_training_game.mp4",
            "Mirror Blink Race Exercise": "mirror_blink_game.mp4",
            "Eye Strain Relief Massage Exercise": "eye_strain_relief.mp4",
            "Palming Relaxation Exercise": "palming_relaxation.mp4",
            "Near-Far Focus Switch Exercise": "near_far_focus.mp4",
            "Astigmatism Tracking Movement Exercise": "tracking_movement_exercise.mp4",
            "Sunlight Play Task Game": "sunlight_play_task.mp4",
            "Smooth Tracking Exercise": "smooth_tracking_exercise.mp4",
            "Eye Muscle 8-Pattern Exercise": "eight_pattern_exercise.mp4",
            "Saccadic Movement Training Exercise": "saccade_training_game.mp4",
            "Peripheral Awareness Exercise": "peripheral_awareness_game.mp4",
            "Focus Switch Objects Exercise": "focus_switch_objects.mp4",
            "Myopia Control Walk Game": "myopia_control_walk.mp4",
            "Clockwise Eye Roll Exercise": "clockwise_eye_roll.mp4",
            "Anti-Clockwise Eye Roll Exercise": "anticlockwise_eye_roll.mp4",
            "Zoom Focus Exercise": "zoom_focus_exercise.mp4",
            "Pencil Pushup Focus Exercise": "pencil_pushup_exercise.mp4",
            "Blinking with Breathing Exercise": "blinking_breathing_relaxation.mp4",
            "Diagonal Eye Tracking Exercise": "diagonal_tracking_exercise.mp4",
            "Thumb Near-Far Focus Exercise": "thumb_focus_shift.mp4",
            "Eye Stretch Up and Down Exercise": "eye_stretch_up_down.mp4",
            "Spoon Tracking Challenge Exercise": "spoon_tracking_game.mp4",
            "Color Contrast Explorer Exercise": "color_contrast_explorer.mp4",
            "Eye Shoulder Tag Exercise": "shoulder_tap_eyes.mp4",
            "Fan Blade Zoom Focus Exercise": "fan_blade_focus.mp4",
            "Mirror Eye Movement Mimic Exercise": "mirror_eye_mimic.mp4",
            "Vertical Line Chase Exercise": "vertical_chase_game.mp4", 
            "Snack Time Color Hunt Game": "color_snack_focus.mp4",
            "Shape Recognition Blink Task Exercise": "shape_blink_game.mp4",
            "Shadow Chase Peripheral Exercise": "shadow_chase_peripheral.mp4",
            "Spiral Spin Exercise": "spiral_spin.mp4",
            "Fruit Toss Distance Drill Exercise": "fruit_toss_focus.mp4",
            "Water Bottle Tracking Exercise": "water_bottle_track.mp4",
            "Late Afternoon Skyline Horizon Distant Tree Blink Game": "late_afternoon_skyline_blink_relax.mp4",
            "Toy Hunt Peripheral Exercise": "toy_peripheral_spotting.mp4",
            "Rainbow Rope Eye Guide Exercise": "rainbow_rope_jumps.mp4",
            "Color Hunt in Room Game": "room_color_scan.mp4",
            "Glow Dot Grid Jump Exercise": "glow_dot_grid_saccade.mp4", 
            "Bouncing Letter Focus Game Exercise": "letter_focus_bounce.mp4",
            "Star Figure Tracking Exercise": "star_pattern_tracking.mp4",
            "Foot Tap Direction Game": "foot_tap_eye_lead.mp4",
            "Color Toss Sorting Game": "color_toss_sorting.mp4",
            "Pillow Maze Obstacle Game": "pillow_maze_navigation.mp4",
            "Box Peek & Recall Game": "box_peek_memory.mp4",
            "Soap Bubble Pop Walk Game": "bubble_pop_chase.mp4",
            "Shadow Shape Tracing Game":"shadow_trace_game.mp4",
            "Toy Toss and Spot Game": "toy_toss_spot_game.mp4",
            "Animal Track and Freeze Game": "animal_track_freeze.mp4"
        }


        2. **Meal Recommendations (4 meals)**:
        Each meal includes:
        - `food`: List of 1-2 Indian food items supporting eye health based on user's usual diet type
        - `portion_size`: Use clear child-friendly measures like grams (g), ml, or count (e.g., “150 ml smoothie” or “1 medium carrot”)
        - `benefit`: Specific to **eye health** (e.g., "Helps retina stay strong", "Filters harmful blue light")
        - `nutrients`: List 1-2 key nutrients per portion using only familiar units like milligrams (mg) or micrograms (µg). Never use International Units (IU). Always add a short emoji-based explanation (e.g., "Vitamin A": "300 µg - 👁️ Supports retina health").
            Example: `{ "Vitamin A": "300 µg - 👁️ Supports retina health", "Lutein": "2 mg - 🌿 Filters harmful blue light" }`
        - `image_prompt`: Realistic food prompt in Indian style (e.g., “A colorful plate with palak paneer and roti, child-friendly kitchen setting, bright lighting”)

        Meals:
        - breakfast
        - lunch
        - snack
        - dinner

        Make sure diet section includes:
          - Portion sizes (in grams, ml, or count-based like “1 small banana”)
          - Familiar nutrients (in mg or µg) with emoji explanations
          - Calorie information for each portion
          - Simple language (no technical or medical terms)
            
          :: Also make sure all benefit explanations (for exercises, meals, etc.) use very simple, clear language. No complex terms or medical jargon — make it easy for less literate parents to understand.

        3. **Hydration Tip or Reminder**:
        - Suggest **realistic**, fun ideas that don’t require daily new bottles
        - Examples:
          - “Add lemon slices to your water for a fun twist!”
          - “Stick a cartoon sticker on your bottle and take 5 sips every hour”
          - “Use a tracker sticker on your bottle to tick off sips!”

        4. **Motivational Message for the Child**:
        - Encouraging, playful one-liner (e.g., “Your eyes are superheroes — let's train them like champions!”)

        5. **Supportive Nudge for the Parent**:
        - Helpful parenting tip for the day (e.g., “Try doing 20-20-20 breaks together during screen time”)

        FORMAT:
        Return a full structured JSON plan.

        EXAMPLE SNIPPET:
        [
        {
        "day": 1,
        "exercises": [
          {
            "name": "Focus Training Game",
            "duration": "45 seconds",
            "explanation": "Follow the bouncing ball with your eyes only, no head movement!",
            "benefit": "Improves focus and eye muscle control",
            "video_filename": "focus_training_game.mp4"
          }
        ],
        "meals": {
          "breakfast": {
            "food": ["Spinach paratha", "Papaya slices"],
            "portion_size: Always provide child-friendly measures using grams (g) or milliliters (ml) or count-based units (like “1 medium guava”, “5 almonds”). For items like rice, paneer, dal, etc., include the gram equivalent (e.g., “½ cup cooked brown rice (≈100g)”, “1 bowl dal (≈150g)”).",
            "benefit": "Strengthens vision by nourishing the retina",
            "calorie_information":"This 
            "nutrients": {
              "Vitamin A": "950 IU - 👁️ Supports retina health",
              "Lutein": "2.5 mg - 🌿 Filters blue light"
            },
            "calorie_information": "Spinach paratha (≈100g) ≈ 200 kcal, Papaya slices (≈75g) ≈ 30 kcal — Total ≈ 230 kcal",
            "image_prompt": "A spinach paratha with papaya slices on a bright, child-friendly Indian-style breakfast plate"
          },
          ...
        },
        "hydration_tip": "Infuse your water with lemon and mint — superhero potion for your eyes!",
        "child_message": "Blink blink like a bunny! Your eyes will thank you!",
        "parent_nudge": "Remind your child to blink often during screen time to avoid dry eyes"
        },
        {"day":2,
        ...
        ...
        }
        ]

        IMPORTANT: Return only valid JSON, without any explanations, commentary, or markdown formatting (e.g., no triple backticks).
        """
    if feedback_number>0:
        user_prompt_post = f"""
            Generate 2 days vision care plan for a child based on the following profile and parent's feedback for last 14 days:

            PROFILE:
            - Age: {pre_feedback_llm_input["age"]}
            - Existing eye power: {pre_feedback_llm_input["Existing_power"]}
            - Gets outdoor time: {pre_feedback_llm_input["outdoor_hours_per_day"]}
            - Daily screen time: {pre_feedback_llm_input["screen_hours_per_day"]}
            - 20-20-20 rule followed: {pre_feedback_llm_input["follows_20_20_20_rule"]}
            - Holds screen too close: {pre_feedback_llm_input["holds_screen_too_close"]}
            - Parent has myopia: {pre_feedback_llm_input["parent_has_myopia"]}  
            - Child feels headache or difficulty seeing distant objects: {pre_feedback_llm_input["has_headaches_or_distance_vision_issues"]}
            - Light quality while studying and using screen: {pre_feedback_llm_input["lighting_quality"]} 
            - Last eye checkup: {pre_feedback_llm_input["had_eye_checkup_before"]}
            - Myopia worsened last year: {pre_feedback_llm_input["myopia_worsened_last_year"]}
            - Axial length measured: {pre_feedback_llm_input["axial_length_measured"]}
            - Eye symptoms: {pre_feedback_llm_input["symptoms"]}
            - Sleep duration: {pre_feedback_llm_input["sleep_hours"]}
            - Usual bedtime: {pre_feedback_llm_input["bedtime"]}
            - Usual diet type: {pre_feedback_llm_input["usual_diet_type"]}
            - Diet quality: {pre_feedback_llm_input["diet_quality"]}
            - Hydration: {pre_feedback_llm_input["hydration_frequency"]}
            - Screen brightness: {pre_feedback_llm_input["screen_brightness"]}
            - Child's diagnosed conditions: {pre_feedback_llm_input["diagnosed_conditions"]}
            - Current child's medications: {pre_feedback_llm_input["current_medications"]}
            - Parents diagnosed with: {pre_feedback_llm_input["parents_diagnosed_conditions"]}


            PARENT FEEDBACK FROM LAST 14 DAYS:
            - Improvement of child’s eye-related symptoms: {post_feedback_llm_input["symptom_improvement"]}
            - Consistency of vision exercises: {post_feedback_llm_input["exercise_frequency"]}
            - Hydration consistency (daily 6-8 glasses): {post_feedback_llm_input["hydration_consistency"]}
            - Screen break behaviour: {post_feedback_llm_input["screen_breaks"]}
            - Area for more focus in next plan: {post_feedback_llm_input[ "next_focus_area"]}
            - New symptoms or diagnosed conditions (if any): {post_feedback_llm_input["new_symptoms_observed"]}
            """
    
        #print(user_prompt)

    
    if feedback_number>0:
        response_post = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt_post},
                {"role": "user", "content": user_prompt_post}
            ],
            temperature=0.7,
            max_tokens=7000,
        )
        content_post = response_post.choices[0].message.content

        if not content_post:
            raise ValueError("OpenAI response content is empty!")

        # Clean triple-backtick blocks, if present
        if content_post.startswith("```json"):
            content_post = content_post.strip("```json").strip("```").strip()
        elif content_post.startswith("```"):
            content_post = content_post.strip("```").strip()

        # debuging print
        #print("🔎 Cleaned Content:\n", content)

        parsed_content_post = json.loads(content_post)
        return parsed_content_post, feedback_number
    else:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt_pre},
                {"role": "user", "content": user_prompt_pre}
            ],
            temperature=0.7,
            max_tokens=7000,
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
        return parsed_content, feedback_number


###### Storing the daywise LLM output data in mysql db using post request ##########
def store_day_plan(user_id: str, cursor, db,  data: Union[DayPlanOutput, None] = None) -> Union[dict, None]:
    try:
        # 1. Retrieve JSON data from wherever LLM output was stored
        result, feedback_number = get_data_llm_output(user_id, cursor)

        print(result)
        session_id = generate_session_id(user_id=user_id, feedback_number=feedback_number)
        # Ensure the session_id exists in the feedback table if feedback_number == 0
        if feedback_number == 0:
            check_query = """
                SELECT session_id FROM feedback
                WHERE session_id = %s
            """
            cursor.execute(check_query, (session_id,))
            existing_feedback = cursor.fetchone()

            if not existing_feedback:
                # Insert dummy feedback row with feedback_number = 0
                insert_dummy_feedback = """
                    INSERT INTO feedback (session_id, user_id, feedback_number)
                    VALUES (%s, %s, %s)
                """
                cursor.execute(insert_dummy_feedback, (session_id, user_id, 0))


        for day_plan in result:
            if "user_id" not in day_plan:
                day_plan["user_id"] = user_id
                
            if "vision_activities" in day_plan and "exercises" not in day_plan:
                day_plan["exercises"] = day_plan.pop("vision_activities")


            plan_data = DayPlanOutput(**day_plan)

            insert_query = """
            INSERT INTO generated_daywise_plans (
                user_id,
                session_id,
                day_number,
                exercises,
                meals,
                hydration_tip,
                child_message,
                parent_nudge
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """

            cursor.execute(insert_query, (
                plan_data.user_id,
                session_id,
                day_plan["day"],
                json.dumps(plan_data.exercises),
                json.dumps(plan_data.meals.model_dump()),
                plan_data.hydration_tip,
                plan_data.child_message,
                plan_data.parent_nudge
            ))

        db.commit()
        db.close()


            
        #print(json.dumps(plan_data.meals, indent=2))

        return {
            "status": "success",
            "message": f"Your [{plan_data.user_id}] 14 days plan has been generated successfully! kindly, follow the plan and give a feedback after 14 days for the next 14 days plan",
            "output":f"Your plan is {result}"
        }

    except Exception as e:
        return {"status": "error", "message": str(e), "output":"No output due to server error"}
    


###Get the last feedback for a specific user
def get_latest_feedback_number(user_id: str, cursor):
    try:
        # Make sure previous results are cleared
        cursor.fetchall()  # if anything pending from earlier
    except:
        pass  # optional, skip if nothing to clear

    try:
        cursor.execute("""
            SELECT feedback_number
            FROM feedback
            WHERE user_id = %s
            ORDER BY feedback_number DESC
            LIMIT 1
        """, (user_id,))
        result = cursor.fetchone()
        return result[0] if result else 0
    except Exception as e:
        raise RuntimeError(f"Error fetching feedback number: {e}")


#### show the generated plans from data base without regenerating again

