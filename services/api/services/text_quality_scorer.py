"""
Text quality scoring for determining extraction method suitability.
"""
import re
import math
from typing import Dict


# MLS-relevant keywords for quality scoring
MLS_KEYWORDS = [
    "listing", "property", "address", "price", "bedroom", "bathroom",
    "square feet", "sqft", "acre", "lot size", "year built", "garage",
    "fireplace", "kitchen", "bathroom", "bedroom", "living room",
    "dining room", "master", "bedrooms", "bathrooms", "property type",
    "mls", "listing agent", "broker", "real estate", "subdivision",
    "city", "state", "zip code", "county", "school", "elementary",
    "middle school", "high school", "tax", "assessed value",
    "association fee", "hoa", "utilities", "heating", "cooling",
    "construction", "roof", "foundation", "flooring", "features"
]


def calculate_text_length_score(text: str) -> float:
    """
    Score based on text length.
    Longer text generally indicates better extraction quality.
    
    Returns:
        Score between 0.0 and 1.0
    """
    if not text:
        return 0.0
    
    char_count = len(text)
    word_count = len(text.split())
    
    # Normalize: Good quality text typically has 500+ words or 3000+ chars
    word_score = min(word_count / 500.0, 1.0)
    char_score = min(char_count / 3000.0, 1.0)
    
    # Average of both metrics
    return (word_score + char_score) / 2.0


def calculate_entropy_score(text: str) -> float:
    """
    Calculate Shannon entropy to detect meaningful text vs random characters.
    Higher entropy indicates more meaningful text.
    
    Returns:
        Score between 0.0 and 1.0
    """
    if not text:
        return 0.0
    
    # Filter to alphanumeric characters for entropy calculation
    clean_text = re.sub(r'[^a-zA-Z0-9]', '', text.lower())
    
    if len(clean_text) < 2:
        return 0.0
    
    # Calculate character frequency
    char_counts = {}
    for char in clean_text:
        char_counts[char] = char_counts.get(char, 0) + 1
    
    # Calculate Shannon entropy
    entropy = 0.0
    text_length = len(clean_text)
    
    for count in char_counts.values():
        probability = count / text_length
        if probability > 0:
            entropy -= probability * math.log2(probability)
    
    # Normalize: Maximum entropy for English is ~4.7 bits per character
    # Good quality text typically has entropy > 3.5
    normalized_entropy = min(entropy / 4.7, 1.0)
    
    # Threshold: score 0 if entropy < 2.0 (likely garbage)
    if entropy < 2.0:
        return 0.0
    
    return normalized_entropy


def calculate_keyword_score(text: str) -> float:
    """
    Score based on presence of MLS-relevant keywords.
    
    Returns:
        Score between 0.0 and 1.0
    """
    if not text:
        return 0.0
    
    text_lower = text.lower()
    found_keywords = []
    
    for keyword in MLS_KEYWORDS:
        if keyword.lower() in text_lower:
            found_keywords.append(keyword)
    
    # Score based on percentage of keywords found
    # Finding 10+ relevant keywords indicates good MLS document
    keyword_score = min(len(found_keywords) / 10.0, 1.0)
    
    return keyword_score


def calculate_text_quality_score(text: str) -> float:
    """
    Calculate overall text quality score.
    Combines length, entropy, and keyword presence metrics.
    
    Args:
        text: The extracted text to score
        
    Returns:
        Overall quality score between 0.0 and 1.0
        
    Quality thresholds:
        - < 0.3: Poor quality, should use vision extraction
        - 0.3 - 0.5: Marginal, may need vision extraction
        - > 0.5: Good quality, can use native text extraction
    """
    if not text or not text.strip():
        return 0.0
    
    length_score = calculate_text_length_score(text)
    entropy_score = calculate_entropy_score(text)
    keyword_score = calculate_keyword_score(text)
    
    # Weighted average
    # Entropy is most important (detects garbage), then keywords, then length
    overall_score = (
        entropy_score * 0.4 +
        keyword_score * 0.35 +
        length_score * 0.25
    )
    
    return round(overall_score, 3)


def get_text_quality_details(text: str) -> Dict[str, float]:
    """
    Get detailed breakdown of text quality metrics.
    
    Returns:
        Dictionary with individual scores
    """
    return {
        "overall_score": calculate_text_quality_score(text),
        "length_score": calculate_text_length_score(text),
        "entropy_score": calculate_entropy_score(text),
        "keyword_score": calculate_keyword_score(text),
        "word_count": len(text.split()) if text else 0,
        "char_count": len(text) if text else 0,
    }
