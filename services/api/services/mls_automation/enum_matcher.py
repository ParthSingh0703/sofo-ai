"""
Enum matching utilities for MLS automation.
Uses AI to semantically match canonical values to MLS enum options.
"""
import os
import json
from typing import Optional, List, Tuple, Dict, Any

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")


def match_enum_with_ai(
    canonical_value: str,
    mls_options: List[str],
    field_name: Optional[str] = None
) -> Tuple[Optional[str], float]:
    """
    Use AI to find the best matching MLS enum option for a canonical value.
    
    Args:
        canonical_value: The value from canonical JSON
        mls_options: List of available MLS enum options
        field_name: Optional field name for context
        
    Returns:
        Tuple of (matched_option, confidence) or (None, 0.0) if no match
    """
    if not GEMINI_API_KEY:
        return None, 0.0
    
    if not canonical_value or not mls_options:
        return None, 0.0
    
    try:
        import google.genai as genai
        
        client = genai.Client(api_key=GEMINI_API_KEY)
        
        # Build prompt
        field_context = f" for field '{field_name}'" if field_name else ""
        prompt = f"""You are matching a canonical listing value to an MLS enum option{field_context}.

Canonical value: "{canonical_value}"

Available MLS options:
{json.dumps(mls_options, indent=2)}

Task:
1. Find the best matching MLS option for the canonical value
2. Consider synonyms, abbreviations, and variations
3. Return ONLY the exact option text from the list above (case-sensitive)
4. If no good match exists, return "NO_MATCH"

Return format (JSON):
{{
    "matched_option": "exact option text from list" or "NO_MATCH",
    "confidence": 0.0-1.0,
    "reasoning": "brief explanation"
}}"""
        
        response = client.models.generate_content(
            model="gemini-2.0-flash-exp",
            contents=[{"role": "user", "parts": [{"text": prompt}]}]
        )
        response_text = response.text.strip() if hasattr(response, 'text') else str(response).strip()
        
        # Parse JSON response
        # Sometimes Gemini wraps in markdown code blocks
        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0].strip()
        elif "```" in response_text:
            response_text = response_text.split("```")[1].split("```")[0].strip()
        
        result = json.loads(response_text)
        
        matched_option = result.get("matched_option")
        confidence = float(result.get("confidence", 0.0))
        
        # Validate that matched_option is in the original list
        if matched_option and matched_option != "NO_MATCH":
            # Try exact match first
            if matched_option in mls_options:
                return matched_option, confidence
            
            # Try case-insensitive match
            matched_lower = matched_option.lower()
            for option in mls_options:
                if option.lower() == matched_lower:
                    return option, confidence
            
            # Try partial match
            for option in mls_options:
                if matched_lower in option.lower() or option.lower() in matched_lower:
                    return option, confidence * 0.8  # Lower confidence for partial match
        
        return None, 0.0
        
    except Exception as e:
        print(f"Error in AI enum matching: {str(e)}")
        return None, 0.0


def batch_match_enums(
    mappings: Dict[str, Tuple[str, List[str]]],
    field_names: Optional[Dict[str, str]] = None
) -> Dict[str, Tuple[Optional[str], float]]:
    """
    Batch match multiple enum values using AI.
    
    Args:
        mappings: Dict mapping field_name -> (canonical_value, mls_options)
        field_names: Optional mapping of field_name -> display_name for context
        
    Returns:
        Dict mapping field_name -> (matched_option, confidence)
    """
    if not GEMINI_API_KEY:
        return {name: (None, 0.0) for name in mappings.keys()}
    
    if not mappings:
        return {}
    
    try:
        import google.genai as genai
        
        client = genai.Client(api_key=GEMINI_API_KEY)
        
        # Build batch prompt
        items = []
        for field_name, (canonical_value, mls_options) in mappings.items():
            display_name = field_names.get(field_name, field_name) if field_names else field_name
            items.append({
                "field": field_name,
                "display_name": display_name,
                "canonical_value": canonical_value,
                "mls_options": mls_options
            })
        
        prompt = f"""You are matching canonical listing values to MLS enum options for multiple fields.

Items to match:
{json.dumps(items, indent=2)}

For each item:
1. Find the best matching MLS option for the canonical value
2. Consider synonyms, abbreviations, and variations
3. Return ONLY the exact option text from the list (case-sensitive)
4. If no good match exists, return "NO_MATCH"

Return format (JSON array):
[
    {{
        "field": "field_name",
        "matched_option": "exact option text" or "NO_MATCH",
        "confidence": 0.0-1.0,
        "reasoning": "brief explanation"
    }},
    ...
]"""
        
        response = client.models.generate_content(
            model="gemini-2.0-flash-exp",
            contents=[{"role": "user", "parts": [{"text": prompt}]}]
        )
        response_text = response.text.strip() if hasattr(response, 'text') else str(response).strip()
        
        # Parse JSON response
        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0].strip()
        elif "```" in response_text:
            response_text = response_text.split("```")[1].split("```")[0].strip()
        
        results = json.loads(response_text)
        
        # Build result dictionary
        matched_results = {}
        for result in results:
            field_name = result.get("field")
            matched_option = result.get("matched_option")
            confidence = float(result.get("confidence", 0.0))
            
            if field_name in mappings:
                canonical_value, mls_options = mappings[field_name]
                
                # Validate matched_option
                if matched_option and matched_option != "NO_MATCH":
                    # Try exact match
                    if matched_option in mls_options:
                        matched_results[field_name] = (matched_option, confidence)
                        continue
                    
                    # Try case-insensitive match
                    matched_lower = matched_option.lower()
                    for option in mls_options:
                        if option.lower() == matched_lower:
                            matched_results[field_name] = (option, confidence)
                            break
                    else:
                        matched_results[field_name] = (None, 0.0)
                else:
                    matched_results[field_name] = (None, 0.0)
        
        # Fill in any missing fields
        for field_name in mappings:
            if field_name not in matched_results:
                matched_results[field_name] = (None, 0.0)
        
        return matched_results
        
    except Exception as e:
        print(f"Error in batch AI enum matching: {str(e)}")
        return {name: (None, 0.0) for name in mappings.keys()}
