import re
from typing import Dict, List, Any

from dotenv import load_dotenv
load_dotenv()

def calculate_scores(responses, brand_name, keywords=None, competitors=None):
    """
    Calculate visibility scores for each response
    
    Updated: Uses relative ranking logic (Brand vs Competitors order)
    """
    
    scored_results = []
    
    for response_data in responses:
        if response_data.get('error'):
            # Skip error responses
            continue
        
        prompt = response_data['prompt']
        response_text = response_data['response']
        prompt_index = response_data.get('prompt_index', 0)
        llm_name = response_data.get('llm_name', 'Claude')
        
        # 1. Calculate Mention Score (0 or 1)
        mention_score = calculate_mention_score(response_text, brand_name)
        
        # 2. Calculate Relative Rank (The new logic: 1st, 2nd, 3rd...)
        # If brand is mentioned, find its rank among competitors. If not, rank is 0.
        if mention_score > 0:
            relative_rank = calculate_relative_rank(response_text, brand_name, competitors)
        else:
            relative_rank = 0
            
        # 3. Calculate Position Score (0-30 points based on rank)
        # Rank 1 = 30, Rank 2 = 25, Rank 3 = 20, etc. (Decay by 5)
        if relative_rank > 0:
            position_score = max(0, 35 - (relative_rank * 5))
        else:
            position_score = 0
            
        # 4. Calculate existing metrics (Preserving your original logic)
        richness_score = calculate_richness_score(response_text, brand_name)
        keyword_score = calculate_keyword_score(response_text, brand_name, keywords)
        
        # Visibility is 100% if mentioned, 0% if not
        normalized_visibility = 100.0 if mention_score > 0 else 0.0
        
        # 5. Analysis Metadata (Preserving existing structure, updating position)
        analysis = analyze_brand_context(response_text, brand_name)
        analysis['position'] = relative_rank  # Override with new rank
        
        # Weighted score calculation
        weighted_score = calculate_weighted_score(mention_score, position_score, richness_score, keyword_score)
        
        scored_result = {
            'prompt': prompt,
            'response': response_text,
            'brand_name': brand_name,
            'llm_name': llm_name,
            'scores': {
                'mention_score': mention_score,         # Now 0 or 1
                'position_score': position_score,       # Derived from Relative Rank
                'richness_score': richness_score,
                'keyword_score': keyword_score,
                'total_score': min(100, weighted_score), # Using weighted as total roughly
                'normalized_visibility': normalized_visibility,
                'average_positioning': relative_rank,   # THIS is the metric you wanted (1, 2, 3...)
                'weighted_score': weighted_score,
                'brand_mention_score': mention_score
            },
            'analysis': analysis,
            'prompt_index': prompt_index,
            'visibility_score': normalized_visibility
        }
        
        scored_results.append(scored_result)
    
    return scored_results

def calculate_relative_rank(response_text, brand_name, competitors):
    """
    Calculate rank based on order of first appearance in the text,
    only among the TRACKED set (brand + competitors).

    Rank is capped at the size of the tracked set so it is always
    a meaningful 1-to-N value (e.g. 1-5 when monitoring 4 competitors).
    """
    if not brand_name:
        return 0

    text_lower = response_text.lower()
    brand_lower = brand_name.lower()

    # Find first occurrence of main brand
    brand_index = text_lower.find(brand_lower)
    if brand_index == -1:
        return 0

    # Build a deduplicated competitor list (case-insensitive)
    seen = {brand_lower}
    unique_competitors = []
    if competitors:
        for comp in competitors:
            if not comp:
                continue
            comp_lower = comp.lower()
            if comp_lower not in seen:
                seen.add(comp_lower)
                unique_competitors.append(comp)

    # Build tracked entities: (first_occurrence_index, name)
    found_entities = [(brand_index, brand_name)]
    for comp in unique_competitors:
        idx = text_lower.find(comp.lower())
        if idx != -1:
            found_entities.append((idx, comp))

    # Sort by first appearance order in response
    found_entities.sort(key=lambda x: x[0])

    # Find the rank of the main brand (1-based)
    for rank, (_, name) in enumerate(found_entities, 1):
        if name.lower() == brand_lower:
            # Cap: rank cannot exceed total tracked entities found
            return min(rank, len(found_entities))

    return 0


def calculate_normalized_visibility(mention_score, position_score):
    """
    ✅ DEPRECATED: Kept for backward compatibility only
    
    NEW LOGIC: Visibility is purely mention-based
    - Brand mentioned = 100%
    - Brand not mentioned = 0%
    """
    return 100.0 if mention_score > 0 else 0.0


def calculate_weighted_score(mention_score, position_score, richness_score, keyword_score):
    """
    Calculate weighted score with emphasis on position and mentions
    Formula: (mention * 0.3) + (position * 0.4) + (richness * 0.2) + (keyword * 0.1)
    """
    weighted = (mention_score * 0.3) + (position_score * 0.4) + (richness_score * 0.2) + (keyword_score * 0.1)
    return round(weighted, 2)


def calculate_mention_score(response_text, brand_name):
    """
    Calculate mention score (20 points max)
    
    Args:
        response_text (str): The response text
        brand_name (str): The brand name to look for
    
    Returns:
        int: Mention score (0 or 20)
    """
    
    # Case-insensitive search for brand name
    pattern = re.compile(re.escape(brand_name), re.IGNORECASE)
    
    if pattern.search(response_text):
        return 1
    else:
        return 0


def calculate_position_score(response_text, brand_name):
    """
    Calculate position score (30 points max)
    
    Args:
        response_text (str): The response text
        brand_name (str): The brand name to look for
    
    Returns:
        float: Position score (0-30)
    """
    
    # First check if brand is mentioned
    if not re.search(re.escape(brand_name), response_text, re.IGNORECASE):
        return 0
    
    # Find the position of the brand in any list
    position_info = find_brand_position(response_text, brand_name)
    
    if position_info['position'] == -1:
        return 0  # Brand mentioned but not in a list
    
    position = position_info['position']
    total_items = position_info['total_items']
    
    if total_items <= 1:
        return 30  # Only item in list gets full score
    
    # Calculate normalized position score
    # Position Score = 1 - ((N - 1) / (T - 1)) * 30
    # where N is position (1-based) and T is total items
    position_score = (1 - ((position - 1) / (total_items - 1))) * 30
    
    return round(position_score, 1)


def calculate_richness_score(response_text, brand_name):
    """
    Calculate description richness score (30 points max)
    
    Args:
        response_text (str): The response text
        brand_name (str): The brand name to look for
    
    Returns:
        int: Richness score (0-30)
    """
    
    # Find brand mentions and their context
    brand_contexts = extract_brand_context(response_text, brand_name)
    
    if not brand_contexts:
        return 0
    
    # Analyze the richness of the description
    total_words = 0
    has_benefits = False
    has_details = False
    
    for context in brand_contexts:
        words = len(context.split())
        total_words += words
        
        # Check for benefit-related keywords
        benefit_keywords = ['benefit', 'advantage', 'helps', 'improves', 'provides', 'offers', 'features', 'known for']
        if any(keyword in context.lower() for keyword in benefit_keywords):
            has_benefits = True
        
        # Check for detailed information
        detail_keywords = ['product', 'ingredient', 'certified', 'organic', 'natural', 'formula', 'supplement', 'vitamin']
        if any(keyword in context.lower() for keyword in detail_keywords):
            has_details = True
    
    # Score based on description richness
    if total_words <= 10:
        base_score = 5  # Short, one-line mention
    elif total_words <= 30:
        base_score = 15  # Medium description
    else:
        base_score = 25  # Rich description
    
    # Bonus points for benefits and details
    if has_benefits:
        base_score += 3
    if has_details:
        base_score += 2
    
    return min(30, base_score)


def calculate_keyword_score(response_text, brand_name, keywords=None):
    """
    Calculate keyword strength score (20 points max)
    
    Args:
        response_text (str): The response text
        brand_name (str): The brand name to look for
        keywords (list): Optional list of SEO keywords
    
    Returns:
        int: Keyword score (0-20)
    """
    
    # Find brand mentions and their context
    brand_contexts = extract_brand_context(response_text, brand_name)
    
    if not brand_contexts:
        return 0
    
    # Strong keywords that indicate positive positioning
    strong_keywords = [
        'top', 'leading', 'best', 'premium', 'excellent', 'outstanding',
        'certified', 'innovative', 'award-winning', 'trusted', 'reputable',
        'popular', 'renowned', 'established', 'quality', 'superior',
        'recommended', 'preferred', 'favorite', 'market leader', 'industry leader',
        'first', 'pioneer', 'cutting-edge', 'advanced', 'professional',
        'authentic', 'genuine', 'pure', 'natural', 'organic'
    ]
    
    # Add SEO keywords if provided
    if keywords:
        # Extract individual words from keywords
        for keyword in keywords[:15]:  # Limit to top 15
            words = keyword.lower().split()
            strong_keywords.extend(words)
    
    score = 0
    found_keywords = set()
    
    for context in brand_contexts:
        context_lower = context.lower()
        for keyword in strong_keywords:
            if keyword in context_lower and keyword not in found_keywords:
                found_keywords.add(keyword)
                # Different keywords have different weights
                if keyword in ['top', 'leading', 'best', 'market leader', 'industry leader']:
                    score += 5
                elif keyword in ['premium', 'excellent', 'outstanding', 'award-winning']:
                    score += 4
                elif keyword in ['certified', 'innovative', 'trusted', 'reputable']:
                    score += 3
                else:
                    score += 2
    
    return min(20, score)


def find_brand_position(response_text, brand_name):
    """
    Find the position of the brand in any list structure
    
    Args:
        response_text (str): The response text
        brand_name (str): The brand name to look for
    
    Returns:
        dict: Position information
    """
    
    lines = response_text.split('\n')
    position = -1
    total_items = 0
    
    # Look for numbered lists
    numbered_items = []
    for i, line in enumerate(lines):
        if re.match(r'^\d+\.', line.strip()):
            numbered_items.append((i, line))
    
    if numbered_items:
        total_items = len(numbered_items)
        for i, (line_num, line) in enumerate(numbered_items):
            if re.search(re.escape(brand_name), line, re.IGNORECASE):
                position = i + 1
                break
    
    # If no numbered list, look for bullet points
    if position == -1:
        bullet_items = []
        for i, line in enumerate(lines):
            if re.match(r'^[-•*]\s', line.strip()):
                bullet_items.append((i, line))
        
        if bullet_items:
            total_items = len(bullet_items)
            for i, (line_num, line) in enumerate(bullet_items):
                if re.search(re.escape(brand_name), line, re.IGNORECASE):
                    position = i + 1
                    break
    
    # If still no position, look for ordinal indicators
    if position == -1:
        ordinal_pattern = r'\b(first|second|third|fourth|fifth|sixth|seventh|eighth|ninth|tenth)\b'
        ordinal_matches = re.finditer(ordinal_pattern, response_text, re.IGNORECASE)
        
        ordinal_map = {
            'first': 1, 'second': 2, 'third': 3, 'fourth': 4, 'fifth': 5,
            'sixth': 6, 'seventh': 7, 'eighth': 8, 'ninth': 9, 'tenth': 10
        }
        
        for match in ordinal_matches:
            sentence = get_sentence_containing_position(response_text, match.start())
            if re.search(re.escape(brand_name), sentence, re.IGNORECASE):
                position = ordinal_map[match.group().lower()]
                total_items = max(total_items, position)
                break
    
    return {
        'position': position,
        'total_items': total_items
    }


def extract_brand_context(response_text, brand_name):
    """
    Extract sentences or contexts where the brand is mentioned
    
    Args:
        response_text (str): The response text
        brand_name (str): The brand name to look for
    
    Returns:
        list: List of contexts mentioning the brand
    """
    
    sentences = re.split(r'[.!?]+', response_text)
    brand_contexts = []
    
    for sentence in sentences:
        if re.search(re.escape(brand_name), sentence, re.IGNORECASE):
            brand_contexts.append(sentence.strip())
    
    return brand_contexts


def get_sentence_containing_position(text, position):
    """
    Get the sentence containing a specific character position
    
    Args:
        text (str): The text to search
        position (int): Character position
    
    Returns:
        str: The sentence containing the position
    """
    
    sentences = re.split(r'[.!?]+', text)
    current_pos = 0
    
    for sentence in sentences:
        if current_pos <= position <= current_pos + len(sentence):
            return sentence.strip()
        current_pos += len(sentence) + 1
    
    return ""


def analyze_brand_context(response_text, brand_name):
    """
    Provide detailed analysis of how the brand is presented
    
    Args:
        response_text (str): The response text
        brand_name (str): The brand name to analyze
    
    Returns:
        dict: Detailed analysis
    """
    
    contexts = extract_brand_context(response_text, brand_name)
    position_info = find_brand_position(response_text, brand_name)
    
    analysis = {
        'is_mentioned': len(contexts) > 0,
        'mention_count': len(contexts),
        'contexts': contexts,
        'position': position_info['position'],
        'total_items_in_list': position_info['total_items'],
        'is_in_list': position_info['position'] > 0,
        'sentiment': analyze_sentiment(contexts),
        'key_attributes': extract_key_attributes(contexts, brand_name)
    }
    
    return analysis


def analyze_sentiment(contexts):
    """
    Analyze the sentiment of brand mentions
    
    Args:
        contexts (list): List of contexts mentioning the brand
    
    Returns:
        str: Sentiment analysis result
    """
    
    if not contexts:
        return "neutral"
    
    positive_words = ['good', 'great', 'excellent', 'best', 'top', 'leading', 'quality', 'trusted', 'premium', 'innovative']
    negative_words = ['bad', 'poor', 'worst', 'low', 'cheap', 'unreliable', 'questionable']
    
    positive_count = 0
    negative_count = 0
    
    for context in contexts:
        context_lower = context.lower()
        for word in positive_words:
            if word in context_lower:
                positive_count += 1
        for word in negative_words:
            if word in context_lower:
                negative_count += 1
    
    if positive_count > negative_count:
        return "positive"
    elif negative_count > positive_count:
        return "negative"
    else:
        return "neutral"


def extract_key_attributes(contexts, brand_name):
    """
    Extract key attributes mentioned about the brand
    
    Args:
        contexts (list): List of contexts mentioning the brand
        brand_name (str): The brand name
    
    Returns:
        list: List of key attributes
    """
    
    attributes = []
    
    attribute_patterns = [
        r'(organic|natural|pure|clean|premium|quality|certified|trusted|innovative|award-winning|established|reputable)',
        r'(supplements?|nutrition|vitamins?|minerals?|herbs?|botanicals?|probiotics?|protein)',
        r'(manufacturing|products?|ingredients?|formula|blend|range|line)'
    ]
    
    for context in contexts:
        for pattern in attribute_patterns:
            matches = re.findall(pattern, context, re.IGNORECASE)
            for match in matches:
                if match.lower() not in [attr.lower() for attr in attributes]:
                    attributes.append(match)
    
    return attributes[:5]  # Return top 5 attributes


def aggregate_results(scored_results):
    """
    Aggregate results using the specific Average Positioning logic:
    Sum(Ranks) / Count(Prompts where Brand Appeared)
    """
    
    if not scored_results:
        return {
            'total_prompts': 0, 'total_mentions': 0, 'mention_rate': 0,
            'avg_position': 0, 'avg_visibility_score': 0, 
            'score_distribution': {}, 'top_performing_prompts': [], 'position_distribution': {}
        }
    
    total_prompts = len(scored_results)
    
    # Filter for prompts where brand was actually mentioned (Rank > 0)
    mentioned_results = [r for r in scored_results if r['scores']['mention_score'] > 0]
    total_mentions = len(mentioned_results)
    
    mention_rate = (total_mentions / total_prompts) * 100 if total_prompts > 0 else 0
    
    # Calculate Average Position
    # Logic: (1 + 2 + 3) / 3 = 2
    # We only sum the ranks where the brand appeared
    if mentioned_results:
        # Extract ranks (average_positioning holds the raw rank now)
        ranks = [r['scores']['average_positioning'] for r in mentioned_results if r['scores']['average_positioning'] > 0]
        
        if ranks:
            avg_position = sum(ranks) / len(ranks)
        else:
            avg_position = 0
    else:
        avg_position = 0
    
    # Helper for top prompts
    top_prompts = sorted(scored_results, key=lambda x: x['scores']['weighted_score'], reverse=True)[:3]
    
    return {
        'total_prompts': total_prompts,
        'total_mentions': total_mentions,
        'mention_rate': round(mention_rate, 2),
        'avg_position': round(avg_position, 2), # This is the (1+2+3)/3 result
        'avg_visibility_score': round(mention_rate, 2),
        'score_distribution': {}, 
        'top_performing_prompts': [{'prompt': p['prompt'], 'score': p['scores']['weighted_score']} for p in top_prompts],
        'position_distribution': {} 
    }