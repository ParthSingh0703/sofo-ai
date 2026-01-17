"""
Image-based photo labeling and analysis using vision AI.
Handles room/portion identification and image descriptions.
"""
import os
import re
import base64
import json
from typing import Dict, Optional, Literal
from pathlib import Path


# Valid room/portion labels
VALID_ROOM_LABELS = [
    "front_exterior", "back_exterior", "side_exterior", "backyard",
    "living_room", "kitchen", "bedroom", "bathroom", "dining_room",
    "master_bedroom", "primary_bedroom", "guest_bedroom",
    "master_bathroom", "primary_bathroom", "guest_bathroom",
    "patio", "deck", "garage", "basement", "attic",
    "community", "amenities", "floor_plan", "map", "other"
]

PHOTO_TYPES = ["interior", "exterior", "floor_plan", "map", "other"]


def extract_label_from_filename(filename: str) -> Optional[str]:
    """
    Extract room/portion label from filename if clearly present.
    
    Args:
        filename: Original filename (e.g., "kitchen.jpg", "front_exterior_1.png")
        
    Returns:
        Room label if found, None if ambiguous
    """
    if not filename:
        return None
    
    filename_lower = filename.lower()
    
    # Remove extension
    name_without_ext = Path(filename).stem.lower()
    
    # Check for exact matches or clear patterns
    for label in VALID_ROOM_LABELS:
        # Check if label appears in filename
        if label in name_without_ext:
            return label
    
    # Check for common variations
    label_mappings = {
        "front": "front_exterior",
        "back": "back_exterior",
        "side": "side_exterior",
        "yard": "backyard",
        "living": "living_room",
        "dining": "dining_room",
        "master": "master_bedroom",
        "primary": "primary_bedroom",
        "guest": "guest_bedroom",
        "bath": "bathroom",
        "bed": "bedroom",
    }
    
    for keyword, label in label_mappings.items():
        if keyword in name_without_ext:
            return label
    
    return None


def analyze_image_with_vision(
    image_path: str,
    filename: Optional[str] = None
) -> Dict[str, any]:
    """
    Analyze image using vision AI to determine room/portion and generate description.
    
    Args:
        image_path: Path to image file
        filename: Original filename (for label extraction precedence)
        
    Returns:
        Dictionary with:
        - room_label: Detected room/portion
        - photo_type: interior | exterior | floor_plan | map | other
        - description: Image description (1-2 sentences)
        - is_primary_candidate: Whether this could be the primary front exterior image
    """
    # Check filename first (precedence rule)
    filename_label = extract_label_from_filename(filename) if filename else None
    
    # If filename has clear label, use it and skip vision for labeling
    if filename_label:
        # Still use vision for description
        vision_result = _call_vision_for_description(image_path)
        photo_type = _determine_photo_type(filename_label)
        
        return {
            "room_label": filename_label,
            "photo_type": photo_type,
            "description": vision_result.get("description", ""),
            "is_primary_candidate": filename_label == "front_exterior"
        }
    
    # Filename is ambiguous, use vision for both labeling and description
    vision_result = _call_vision_for_analysis(image_path)
    
    room_label = vision_result.get("room_label", "other")
    photo_type = vision_result.get("photo_type", "other")
    
    return {
        "room_label": room_label,
        "photo_type": photo_type,
        "description": vision_result.get("description", ""),
        "is_primary_candidate": room_label == "front_exterior" and photo_type == "exterior"
    }


def _call_vision_for_analysis(image_path: str) -> Dict[str, any]:
    """
    Call Gemini API to analyze image for room/portion identification and description.
    Uses Gemini 2.5 Flash for image vision-based labeling and description generation.
    """
    vision_api_key = os.getenv("GEMINI_API_KEY") or os.getenv("VISION_API_KEY")
    # Use Gemini 2.5 Flash for image analysis
    vision_model = os.getenv("IMAGE_VISION_MODEL", "gemini-2.5-flash")
    
    if not vision_api_key:
        # Fallback: return defaults
        return {
            "room_label": "other",
            "photo_type": "other",
            "description": ""
        }
    
    try:
        import google.genai as genai
        from PIL import Image
        import base64
        import io
        
        # Create Gemini client
        client = genai.Client(api_key=vision_api_key)
        
        # Use Gemini 2.5 Flash for image analysis
        model_name = vision_model if vision_model else "gemini-2.5-flash"
        
        # Read and open image
        image = Image.open(image_path)
        
        # Convert PIL Image to base64
        img_buffer = io.BytesIO()
        image.save(img_buffer, format='PNG')
        img_base64 = base64.b64encode(img_buffer.getvalue()).decode('utf-8')
        
        prompt = """You are an expert real estate copywriter and top-tier listing agent. Your goal is to analyze property images and generate engaging, professional marketing copy for a listing website (like Zillow or Redfin).

Task:

1. Identify: Analyze the uploaded image to determine which room or area of the property is shown. Choose ONE from:
   - front_exterior, back_exterior, side_exterior, backyard
   - living_room, kitchen, bedroom, bathroom, dining_room
   - master_bedroom, primary_bedroom, guest_bedroom
   - master_bathroom, primary_bathroom, guest_bathroom
   - patio, deck, garage, basement, attic
   - community, amenities, floor_plan, map, other

2. Photo type: interior | exterior | floor_plan | map | other

3. Analyze Features: Detect key selling points such as flooring type (e.g., LVP, hardwood, tile), natural lighting, fixtures (ceiling fans, chandeliers), wall condition (fresh paint), and architectural details (open concept, high ceilings).

4. Write: Draft a "punchy" photo caption (2-3 sentences max).

Style Guidelines:

Tone: Inviting, professional, and enthusiastic.

Vocabulary: Use high-value adjectives (e.g., "pristine," "sun-drenched," "serene," "low-maintenance", etc).

Language: Neutral and MLS-safe language. No assumptions about materials, upgrades, or condition unless clearly visible. No marketing exaggeration. No Fair Housing language.

Focus: Highlight the best features visible in the image. If the room is empty, emphasize the "potential".

Constraint: Do not describe clutter or bad angles. Focus only on the positive assets.

Return JSON:
{
  "room_label": "string",
  "photo_type": "string",
  "description": "string"
}"""
        
        # Call Gemini with image and prompt
        response = client.models.generate_content(
            model=model_name,
            contents=[
                {"role": "user", "parts": [
                    {"text": prompt},
                    {"inline_data": {"mime_type": "image/png", "data": img_base64}}
                ]}
            ]
        )
        
        response_text = response.text
        
        # Parse JSON from response
        json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
        if json_match:
            return json.loads(json_match.group())
        else:
            return {
                "room_label": "other",
                "photo_type": "other",
                "description": ""
            }
    
    except ImportError:
        print("google-genai library not installed. Install with: pip install google-genai")
        return {
            "room_label": "other",
            "photo_type": "other",
            "description": ""
        }
    except (ConnectionError, OSError) as e:
        error_msg = str(e)
        if "getaddrinfo failed" in error_msg or "11001" in error_msg:
            print(f"Gemini vision analysis failed: Network connection error - Cannot reach Gemini API. Check your internet connection and DNS settings.")
        else:
            print(f"Gemini vision analysis failed: Network error - {error_msg}")
    except Exception as e:
        error_msg = str(e)
        if "getaddrinfo failed" in error_msg or "11001" in error_msg:
            print(f"Gemini vision analysis failed: Network connection error - Cannot reach Gemini API. Check your internet connection.")
        else:
            print(f"Gemini vision analysis failed: {error_msg}")
        return {
            "room_label": "other",
            "photo_type": "other",
            "description": ""
        }
    
    # # OpenAI Vision implementation (commented for testing with Groq)
    # try:
    #     from openai import OpenAI
    #     client = OpenAI(api_key=vision_api_key)
    #     
    #     # Read and encode image
    #     with open(image_path, "rb") as img_file:
    #         image_bytes = img_file.read()
    #         image_base64 = base64.b64encode(image_bytes).decode('utf-8')
    #     
    #     prompt = """Analyze this real estate property image and provide:
    #
    # 1. Room/portion identification: Choose ONE from:
    #    - front_exterior, back_exterior, side_exterior, backyard
    #    - living_room, kitchen, bedroom, bathroom, dining_room
    #    - master_bedroom, primary_bedroom, guest_bedroom
    #    - master_bathroom, primary_bathroom, guest_bathroom
    #    - patio, deck, garage, basement, attic
    #    - community, amenities, floor_plan, map, other
    #
    # 2. Photo type: interior | exterior | floor_plan | map | other
    #
    # 3. Brief description (1-2 sentences): Describe ONLY what is clearly visible.
    #    - Neutral, MLS-safe language
    #    - No assumptions about materials, upgrades, or condition
    #    - No marketing exaggeration
    #
    # Return JSON:
    # {
    #   "room_label": "string",
    #   "photo_type": "string",
    #   "description": "string"
    # }"""
    #     
    #     response = client.chat.completions.create(
    #         model=vision_model,
    #         messages=[
    #             {
    #                 "role": "user",
    #                 "content": [
    #                     {"type": "text", "text": prompt},
    #                     {
    #                         "type": "image_url",
    #                         "image_url": {
    #                             "url": f"data:image/png;base64,{image_base64}"
    #                         }
    #                     }
    #                 ]
    #             }
    #         ],
    #         max_tokens=500,
    #         temperature=0.3
    #     )
    #     
    #     response_text = response.choices[0].message.content
    #     
    #     # Parse JSON from response
    #     json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
    #     if json_match:
    #         return json.loads(json_match.group())
    #     else:
    #         return {
    #             "room_label": "other",
    #             "photo_type": "other",
    #             "description": ""
    #         }
    # 
    # except Exception as e:
    #     print(f"Vision analysis failed: {str(e)}")
    #     return {
    #         "room_label": "other",
    #         "photo_type": "other",
    #         "description": ""
    #     }


def _call_vision_for_description(image_path: str) -> Dict[str, str]:
    """
    Call Gemini API only for description generation (when label is known from filename).
    Uses Gemini 2.5 Flash for image vision-based description generation.
    """
    vision_api_key = os.getenv("GEMINI_API_KEY") or os.getenv("VISION_API_KEY")
    # Use Gemini 2.5 Flash for image descriptions
    vision_model = os.getenv("IMAGE_VISION_MODEL", "gemini-2.5-flash")
    
    if not vision_api_key:
        return {"description": ""}
    
    try:
        import google.genai as genai
        from PIL import Image
        import base64
        import io
        
        # Create Gemini client
        client = genai.Client(api_key=vision_api_key)
        
        # Use Gemini 2.5 Flash for image descriptions
        model_name = vision_model if vision_model else "gemini-2.5-flash"
        
        # Read and open image
        image = Image.open(image_path)
        
        # Convert PIL Image to base64
        img_buffer = io.BytesIO()
        image.save(img_buffer, format='PNG')
        img_base64 = base64.b64encode(img_buffer.getvalue()).decode('utf-8')
        
        prompt = """You are an expert real estate copywriter and top-tier listing agent. Your goal is to analyze property images and generate engaging, professional marketing copy for a listing website (like Zillow or Redfin).

Task:

1. Identify: Analyze the uploaded image to determine which room or area of the property is shown (e.g., Living Room, Primary Bedroom, Kitchen, Exterior Facade, Bathroom).

2. Analyze Features: Detect key selling points such as flooring type (e.g., LVP, hardwood, tile), natural lighting, fixtures (ceiling fans, chandeliers), wall condition (fresh paint), and architectural details (open concept, high ceilings).

3. Write: Draft a "punchy" photo caption (2-3 sentences max).

Style Guidelines:

Tone: Inviting, professional, and enthusiastic.

Vocabulary: Use high-value adjectives (e.g., "pristine," "sun-drenched," "serene," "low-maintenance").

Language: Neutral and MLS-safe language. No assumptions about materials, upgrades, or condition unless clearly visible. No marketing exaggeration. No Fair Housing language.

Focus: Highlight the best features visible in the image. If the room is empty, emphasize the "potential".

Constraint: Do not describe clutter or bad angles. Focus only on the positive assets.

Return JSON:
{
  "description": "string"
}"""
        
        # Call Gemini with image and prompt
        response = client.models.generate_content(
            model=model_name,
            contents=[
                {"role": "user", "parts": [
                    {"text": prompt},
                    {"inline_data": {"mime_type": "image/png", "data": img_base64}}
                ]}
            ]
        )
        
        response_text = response.text
        json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
        if json_match:
            return json.loads(json_match.group())
        else:
            return {"description": ""}
    
    except ImportError:
        print("google-genai library not installed. Install with: pip install google-genai")
        return {"description": ""}
    except (ConnectionError, OSError) as e:
        error_msg = str(e)
        if "getaddrinfo failed" in error_msg or "11001" in error_msg:
            print(f"Gemini vision description failed: Network connection error - Cannot reach Gemini API. Check your internet connection and DNS settings.")
        else:
            print(f"Gemini vision description failed: Network error - {error_msg}")
        return {"description": ""}
    except Exception as e:
        error_msg = str(e)
        if "getaddrinfo failed" in error_msg or "11001" in error_msg:
            print(f"Gemini vision description failed: Network connection error - Cannot reach Gemini API. Check your internet connection.")
        else:
            print(f"Gemini vision description failed: {error_msg}")
        return {"description": ""}
    
    # # OpenAI Vision implementation (commented for testing with Groq)
    # try:
    #     from openai import OpenAI
    #     client = OpenAI(api_key=vision_api_key)
    #     
    #     with open(image_path, "rb") as img_file:
    #         image_bytes = img_file.read()
    #         image_base64 = base64.b64encode(image_bytes).decode('utf-8')
    #     
    #     prompt = """Describe this real estate property image in 1-2 sentences.
    #
    # Rules:
    # - Describe ONLY what is clearly visible
    # - Neutral, MLS-safe language
    # - No assumptions about materials, upgrades, or condition
    # - No marketing exaggeration
    # - No Fair Housing language
    #
    # Return JSON:
    # {
    #   "description": "string"
    # }"""
    #     
    #     response = client.chat.completions.create(
    #         model=vision_model,
    #         messages=[
    #             {
    #                 "role": "user",
    #                 "content": [
    #                     {"type": "text", "text": prompt},
    #                     {
    #                         "type": "image_url",
    #                         "image_url": {
    #                             "url": f"data:image/png;base64,{image_base64}"
    #                         }
    #                     }
    #                 ]
    #             }
    #         ],
    #         max_tokens=200,
    #         temperature=0.3
    #     )
    #     
    #     response_text = response.choices[0].message.content
    #     json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
    #     if json_match:
    #         return json.loads(json_match.group())
    #     else:
    #         return {"description": ""}
    # 
    # except Exception as e:
    #     print(f"Vision description failed: {str(e)}")
    #     return {"description": ""}


def _determine_photo_type(room_label: str) -> Literal["interior", "exterior", "floor_plan", "map", "other"]:
    """
    Determine photo type from room label.
    """
    exterior_labels = ["front_exterior", "back_exterior", "side_exterior", "backyard", "patio", "deck", "garage"]
    interior_labels = ["living_room", "kitchen", "bedroom", "bathroom", "dining_room", 
                      "master_bedroom", "primary_bedroom", "guest_bedroom",
                      "master_bathroom", "primary_bathroom", "guest_bathroom",
                      "basement", "attic"]
    
    if room_label in exterior_labels:
        return "exterior"
    elif room_label in interior_labels:
        return "interior"
    elif room_label == "floor_plan":
        return "floor_plan"
    elif room_label == "map":
        return "map"
    else:
        return "other"
