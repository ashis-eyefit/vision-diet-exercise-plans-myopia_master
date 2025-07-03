import os
from diffusers import StableDiffusionPipeline
import torch
from difflib import get_close_matches

# Load the model once
pipe = StableDiffusionPipeline.from_pretrained(
    "runwayml/stable-diffusion-v1-5",
    torch_dtype=torch.float32
)
pipe.to("cuda" if torch.cuda.is_available() else "cpu")

# Prompt cache (ideally should be persisted in a DB or JSON)
prompt_to_filename = {}

def normalize_prompt(prompt: str):
    return prompt.lower().replace("≈", "").replace("~", "").replace("gram", "").replace("ml", "").strip()

def is_prompt_similar(prompt, cache, threshold=0.92):
    normalized_prompt = normalize_prompt(prompt)
    matches = get_close_matches(normalized_prompt, list(cache.keys()), n=1, cutoff=threshold)
    return matches[0] if matches else None

def generate_image_if_needed(prompt: str, save_path: str):
    if os.path.exists(save_path):
        print(f"Image already exists: {save_path}")
        return

    similar_prompt = is_prompt_similar(prompt, prompt_to_filename)
    if similar_prompt:
        print(f"Prompt similar to previous, skipping generation: {similar_prompt}")
        return

    print(f"🎨 Generating image for prompt: {prompt}")
    image = pipe(prompt, num_inference_steps=20).images[0]
    image.save(save_path)
    prompt_to_filename[prompt] = save_path
    print(f" Image saved: {save_path}")
