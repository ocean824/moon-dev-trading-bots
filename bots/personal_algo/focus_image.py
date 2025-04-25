from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse, FileResponse
from pydantic import BaseModel
from openai import OpenAI
import os
import base64
from dotenv import load_dotenv
from typing import List
import json
from datetime import datetime

# Load environment variables
load_dotenv()

# Initialize FastAPI app
app = FastAPI(title="Moon Dev Focus Generator 🌙")

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv('OPENAI_KEY'))

# Constants for the system prompt
SYSTEM_PROMPT = """You are a highly motivational AI assistant helping Moon Dev achieve their goals.
Based on their input about what they want to achieve and do each day, create:
1. An inspiring quote (1 sentence) that resonates with their goals
2. Six specific, actionable todos that will help them achieve these goals
Format the response as JSON with fields: 'quote' and 'todos' (array of 6 strings)"""

IMAGE_PROMPT_TEMPLATE = """Create a minimalist, professional rectangular banner image (like a credit card shape). The image should be motivational and incorporate the following goal: {goal}. 
Use a clean, modern aesthetic with a dark background and elegant typography. Make it look premium and inspiring."""

class GoalInput(BaseModel):
    goals: str

def generate_focus_content(goals: str) -> dict:
    try:
        print(f"🌙 Moon Dev Focus Generator - Processing goals...")
        response = client.chat.completions.create(
            model="gpt-4-1106-preview",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": goals}
            ],
            response_format={ "type": "json_object" }
        )
        print(f"✨ Moon Dev Focus Generator - Content generated successfully!")
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        print(f"❌ Moon Dev Error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

def generate_focus_image(goal: str) -> bytes:
    try:
        print(f"🎨 Moon Dev Image Generator - Creating visualization...")
        image_prompt = IMAGE_PROMPT_TEMPLATE.format(goal=goal)
        
        result = client.images.generate(
            model="gpt-image-1",
            prompt=image_prompt
        )
        
        image_base64 = result.data[0].b64_json
        image_bytes = base64.b64decode(image_base64)
        
        print(f"🖼️ Moon Dev Image Generator - Image created successfully!")
        return image_bytes
    except Exception as e:
        print(f"❌ Moon Dev Error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/generate-focus")
async def generate_focus(goal_input: GoalInput):
    print(f"🚀 Moon Dev API - Received new focus generation request")
    
    # Generate the motivational content
    content = generate_focus_content(goal_input.goals)
    
    # Generate the image
    image_bytes = generate_focus_image(goal_input.goals)
    
    # Save the image with a timestamp to make it unique
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    image_filename = f"focus_image_{timestamp}.png"
    
    with open(image_filename, "wb") as f:
        f.write(image_bytes)
    
    response_data = {
        "quote": content["quote"],
        "todos": content["todos"],
        "image_path": image_filename,
        "timestamp": datetime.now().isoformat()
    }
    
    print(f"✅ Moon Dev API - Request completed successfully!")
    return JSONResponse(content=response_data)

if __name__ == "__main__":
    import uvicorn
    print("🌙 Moon Dev Focus Generator - Starting server...")
    uvicorn.run(app, host="0.0.0.0", port=8000)
