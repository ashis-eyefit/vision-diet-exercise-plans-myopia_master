from diffusers import StableDiffusionPipeline
import torch
import os

def main():
    try:
        print("Starting image generation...")

        # Create output folder
        image_folder = os.path.join("test", "images")
        os.makedirs(image_folder, exist_ok=True)

        # Load model with float32 for CPU
        print(" Loading model (this can take a few minutes)...")
        pipe = StableDiffusionPipeline.from_pretrained(
            "runwayml/stable-diffusion-v1-5",
            torch_dtype=torch.float32
        ).to("cpu")

        # Prompt
        prompt = "A stack of blueberry pancakes with a side of yogurt, served on a colorful child-friendly plate"

        # Reduce steps for speed
        print("Generating image (this may take 2-5 minutes)...")
        image = pipe(prompt, num_inference_steps=20).images[0]

        # Save
        image_path = os.path.join(image_folder, "breakfast_day1.png")
        image.save(image_path)
        print(f"Image saved to: {image_path}")

    except Exception as e:
        print("Error occurred:", e)

if __name__ == "__main__":
    main()
