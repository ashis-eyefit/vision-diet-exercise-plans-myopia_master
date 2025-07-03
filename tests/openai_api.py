import openai
from typing import Dict
import os
import json
import asyncio
#from src.utils.helper import get_llm_input
#from tests.sqldb import get_db
#from dotenv import load_dotenv

#load_dotenv()

client = openai.OpenAI(api_key = os.getenv("OPENAI_API"))


async def generate_day1_plan() -> Dict[str, str]:
  try:
    #db = get_db()
    #user_id = input("Give the uiser_id here: ")
    #pre_feedback_llm_input, post_feedback_llm_input = get_llm_input(user_id, db)
    system_prompt = """
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
    user_prompt = """
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
    return {"day_1_content": parsed_content}
  except json.JSONDecodeError as e:
    raise ValueError(f"Failed to parse JSON. Raw content:\n{content}\n\nError: {e}")

  
if __name__ == "__main__":
  result = asyncio.run(generate_day1_plan())
  print(json.dumps(result, indent=2, ensure_ascii=False))