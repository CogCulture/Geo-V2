import os
from typing import List, Dict, Any
from mistralai import Mistral

from dotenv import load_dotenv
load_dotenv()

MISTRAL_API_KEY = os.environ.get("MISTRAL_API_KEY")
mistral_client = Mistral(api_key=MISTRAL_API_KEY)

def extract_keywords(brand_name: str, research_data: Dict[str, Any], 
                    product_name: str = None, industry: str = None, num_keywords: int = 35) -> List[str]:  # ✅ ADDED industry param
    """
    Extract 30-40 SEO-friendly keywords using Mistral LLM
    
    Args:
        brand_name: The brand name
        research_data: Deep research data from Tavily
        product_name: Optional product name/description
        industry: Optional industry context
        num_keywords: Number of keywords to extract (default: 35)
    
    Returns:
        List of SEO-friendly keywords
    """
    
    # Build context from research data
    context = f"Brand: {brand_name}\n"
    
    if product_name:
        context += f"Product: {product_name}\n"
    
    # ✅ ADDED: Include industry if provided
    if industry:
        context += f"Industry: {industry}\n"
    
    if research_data.get('brand_category'):
        context += f"Category: {research_data['brand_category']}\n"
    
    if research_data.get('market_reputation'):
        context += f"Market Position: {research_data['market_reputation'][:300]}\n"
    
    if research_data.get('product_insights'):
        context += f"Product Details: {research_data['product_insights'][:300]}\n"
    
    if research_data.get('pricing_structure'):
        context += f"Pricing: {research_data['pricing_structure'][:200]}\n"
    
    if research_data.get('competitors'):
        context += f"Competitors: {', '.join(research_data['competitors'][:5])}\n"
    
    if research_data.get('trends'):
        context += f"Industry Trends: {research_data['trends'][:300]}\n"
    
    # ✅ ENHANCED: Mention industry in the prompt
    industry_mention = f" in the {industry} industry" if industry else ""
    
    # Create prompt for Mistral
    prompt = f"""Based on the following brand and product information{industry_mention}, extract {num_keywords} SEO-friendly keywords that are highly relevant for organic search visibility analysis.

{context}

Requirements for keywords:
1. Mix of broad industry terms and specific product/brand related terms
2. Include category-level keywords (e.g., "health supplements", "organic nutrition")
3. Include problem-solution keywords (e.g., "best supplements for wellness", "top nutrition brands")
4. Include comparison keywords (e.g., "supplement comparison", "nutrition alternatives")
5. Include informational keywords (e.g., "how to choose supplements", "supplement benefits")
6. Prioritize keywords that real users would search for when looking for products/brands in this category
7. Keywords should be 1-4 words each
8. Do NOT include the brand name in the keywords (we're testing organic visibility)

Provide exactly {num_keywords} keywords, one per line, without numbering or bullet points. Just the keywords."""

    try:
        # Call Mistral API using compatible chat method
        response = mistral_client.chat.complete(
            model="mistral-small-latest",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=1000
        )
                
        # Extract keywords from response
        keywords_text = response.choices[0].message.content
        keywords = [line.strip() for line in keywords_text.split('\n') if line.strip()]
        
        # Clean up keywords (remove numbering if present)
        cleaned_keywords = []
        for keyword in keywords:
            # Remove leading numbers, dots, dashes, etc.
            cleaned = keyword.lstrip('0123456789.-) ').strip()
            if cleaned:
                cleaned_keywords.append(cleaned)
        
        # Ensure we have the requested number of keywords
        if len(cleaned_keywords) < num_keywords:
            # Add generic fallback keywords if needed
            cleaned_keywords.extend(get_fallback_keywords(brand_name, research_data, industry, num_keywords - len(cleaned_keywords)))  # ✅ Pass industry
        
        return cleaned_keywords[:num_keywords]
    
    except Exception as e:
        print(f"Error extracting keywords with Mistral: {str(e)}")
        # Return fallback keywords
        return get_fallback_keywords(brand_name, research_data, industry, num_keywords)


def get_fallback_keywords(brand_name: str, research_data: Dict[str, Any], industry: str = None, count: int = 35) -> List[str]: 
    """Generate fallback keywords if API fails"""
    fallback_keywords = []
    if industry:
        fallback_keywords.extend([
            f"best {industry} brands",
            f"top {industry} companies",
            f"leading {industry} products",
            f"{industry} market leaders",
            f"trusted {industry} brands"
        ])    
    # Extract category-based keywords
    category = research_data.get('brand_category', '')
    if category:
        category_words = category.lower().split()[:3]
        fallback_keywords.extend([
            f"best {' '.join(category_words)}",
            f"top {' '.join(category_words)}",
            f"{' '.join(category_words)} brands",
            f"{' '.join(category_words)} reviews",
            f"leading {' '.join(category_words)}"
        ])
    
    # Generic industry keywords
    fallback_keywords.extend([
        "market leaders",
        "industry comparison",
        "product reviews",
        "best alternatives",
        "top brands",
        "customer reviews",
        "quality products",
        "trusted brands",
        "popular choices",
        "recommended products"
    ])
    
    return fallback_keywords[:count]


def group_keywords_by_intent(keywords: List[str]) -> Dict[str, List[str]]:
    """Group keywords by search intent (informational, commercial, transactional)"""
    grouped = {
        'informational': [],
        'commercial': [],
        'transactional': [],
        'navigational': []
    }
    
    for keyword in keywords:
        keyword_lower = keyword.lower()
        
        # Informational intent
        if any(word in keyword_lower for word in ['how to', 'what is', 'benefits', 'guide', 'tips', 'why']):
            grouped['informational'].append(keyword)
        
        # Transactional intent
        elif any(word in keyword_lower for word in ['buy', 'purchase', 'order', 'price', 'deal', 'discount']):
            grouped['transactional'].append(keyword)
        
        # Commercial intent
        elif any(word in keyword_lower for word in ['best', 'top', 'review', 'comparison', 'vs', 'alternative']):
            grouped['commercial'].append(keyword)
        
        # Navigational intent
        elif any(word in keyword_lower for word in ['brand', 'company', 'official', 'website']):
            grouped['navigational'].append(keyword)
        
        # Default to commercial
        else:
            grouped['commercial'].append(keyword)
    
    return grouped