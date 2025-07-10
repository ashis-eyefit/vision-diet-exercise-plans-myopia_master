from pydantic import BaseModel,Field
from typing import Optional, List, Dict, Any

## personal data schema
class UserPersonalDataCreate(BaseModel):
    child_name: str
    child_age: int
    school_name: str | None = None
    eye_power: str | None = None

## onboarding data schema
class UserOnboardingAnswerBase(BaseModel):
    user_id: str # required filed
    outdoor_hours_per_day: Optional[str] = Field(None, max_length=50)
    screen_hours_per_day: Optional[str] = Field(None, max_length=50)
    follows_20_20_20_rule: Optional[str] = Field(None, max_length=50)
    holds_screen_too_close: Optional[str] = Field(None, max_length=10)
    parent_has_myopia: Optional[str] = Field(None, max_length=10)
    has_headaches_or_distance_vision_issues: Optional[str] = Field(None, max_length=10)
    lighting_quality: Optional[str] = None
    had_eye_checkup_before: Optional[str] = Field(None, max_length=10)
    myopia_worsened_last_year: Optional[str] = Field(None, max_length=10)
    axial_length_measured: Optional[str] = Field(None, max_length=10)

## eye health questionnaires data schema
class IntakeForm(BaseModel):
    symptoms: List[str]
    sleepHours: float
    bedTime: str
    usualDietType: str
    dietQuality: str
    hydrationFrequency: str
    screenBrightness: str
    diagnosedConditions: List[str]
    currentMedications: Optional[str]
    parentsDiagnosedConditions: List[str]

## feedback schema
class FeedbackSchema(BaseModel):
    symptom_improvement: str
    exercise_frequency: str
    hydration_consistency: str
    screen_breaks: str
    next_focus_area: str
    new_symptoms_observed: Optional[str] = None

#### llm output for pre and post feedback
class MealItem(BaseModel):
    food: List[str]
    portion_size: str
    benefit: str
    calorie_information: str
    nutrients: Dict[str, str]
    image_prompt: str

class Meals(BaseModel):
    breakfast: MealItem
    lunch: MealItem
    snack: MealItem
    dinner: MealItem

class DayPlanOutput(BaseModel):
    user_id:str
    exercises: List[Dict[str, Any]]
    meals: Meals
    hydration_tip: str
    child_message: str
    parent_nudge: str




### Daily user activity log (activity done or not)
class DailyUserActivityLog(BaseModel):
    # Optional boolean fields
    exercise_1_done: Optional[bool] = False
    exercise_2_done: Optional[bool] = False
    exercise_3_done: Optional[bool] = False
    breakfast_done: Optional[bool] = False
    lunch_done: Optional[bool] = False
    snack_done: Optional[bool] = False
    dinner_done: Optional[bool] = False
    hydration_followed: Optional[bool] = False