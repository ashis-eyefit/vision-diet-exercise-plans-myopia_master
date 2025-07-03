import requests
import os

# Replace with your actual Hugging Face API token


API_URL = "https://api-inference.huggingface.co/ByteDance/AnimateDiff-Lightning"
headers = {
    "Authorization": f"Bearer {API_TOKEN}", # provide the api key
    "Content-Type": "application/json"
}

prompt = "Cartoon child plays a fun catch-the-ball game with parent in a garden, tracking and catching a bouncing colorful ball — showing exaggerated joyful eye tracking."

def query(prompt):
    response = requests.post(API_URL, headers=headers, json={"inputs": prompt})
    if response.status_code == 200:
        return response.content  # This is binary image data
    else:
        raise Exception(f"Request failed: {response.status_code} - {response.text}")

image_name = "video1.mp4"
image_path = os.path.join("src/data/static_video_folder/generated_video",image_name)

# Call the function and save the result
try:
    image_bytes = query(prompt)

    with open(image_path, "wb") as f:
        f.write(image_bytes)

    print("✅ Image saved to breakfast_day1.png")
except Exception as e:
    print("❌ Error:", e)
