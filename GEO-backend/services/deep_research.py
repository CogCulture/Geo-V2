import os
import re
from typing import Dict, Any, List, Optional
from tavily import TavilyClient
from anthropic import Anthropic
from mistralai import Mistral

from dotenv import load_dotenv
load_dotenv()

TAVILY_API_KEY = os.environ.get("TAVILY_API_KEY")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")
MISTRAL_API_KEY = os.environ.get("MISTRAL_API_KEY")

tavily_client = TavilyClient(api_key=TAVILY_API_KEY)
anthropic_client = Anthropic(api_key=ANTHROPIC_API_KEY) if ANTHROPIC_API_KEY else None
mistral_client = Mistral(api_key=MISTRAL_API_KEY) if MISTRAL_API_KEY else None

def conduct_deep_research(brand_name: str, product_name: Optional[str] = None, 
                         website_url: Optional[str] = None, 
                         industry: Optional[str] = None,
                         custom_competitors: Optional[List[str]] = None) -> Dict[str, Any]:  # ✅ ADDED
    """
    Conduct extensive web-based deep research using Tavily API
    
    ✅ NEW: If custom_competitors is provided, skip automatic competitor research
    
    Returns comprehensive brand information including:
    - Brand category and type
    - Market reputation and online presence
    - Product-specific insights (if provided)
    - Pricing structure (B2C/D2C brands)
    - Top 5 competitors (custom or automatically extracted)
    - Current trends and technologies
    """
    
    research_results = {
        'brand_category': '',
        'brand_type': '',
        'competitors': [],
        'industry': industry or '',
        'raw_data': []
    }
    
    # ✅ If custom competitors provided, use them directly and skip research
    if custom_competitors and len(custom_competitors) > 0:
        research_results['competitors'] = custom_competitors
        print(f"✅ Using {len(custom_competitors)} custom competitors: {custom_competitors}")
        skip_competitor_research = True
    else:
        skip_competitor_research = False
    
    # Research query 1: Brand overview and category
    query_1 = f" What is {brand_name} ?"
    if product_name:
        query_1 += f" {product_name}"
    if industry:
        query_1 += f" {industry}"
    if website_url:
        query_1 += f" {website_url}"
    
    try:
        response_1 = tavily_client.search(
            query=query_1,
            search_depth="advanced",
            max_results=3,
            include_answer=True
        )
        research_results['raw_data'].append({
            'query': query_1,
            'results': response_1.get('results', []),
            'answer': response_1.get('answer', '')
        })
        
        if response_1.get('answer'):
            research_results['brand_category'] = response_1['answer']
            
            # ✅ Infer short industry if not provided
            if not industry:
                 inferred_industry = extract_industry_with_llm(brand_name, response_1['answer'])
                 if inferred_industry:
                     research_results['industry'] = inferred_industry
                     industry = inferred_industry # Update local var for subsequent use
                     print(f"✅ Inferred Industry: {industry}")
    except Exception as e:
        print(f"Error in brand overview research: {str(e)}")
    
    # Research query 5: Competitor Research (SKIP if custom competitors provided)
    if not skip_competitor_research:
        competitors_data = []
        competitor_queries = [
            f"What are the top 5 competitors of {brand_name} in India ?"
        ]
        
        for query in competitor_queries:
            try:
                response = tavily_client.search(
                    query=query.strip(),
                    search_depth="advanced",
                    max_results=3,
                    include_answer=True
                )
                competitors_data.append({
                    'query': query,
                    'answer': response.get('answer', '')
                })
                research_results['raw_data'].append({
                    'query': query,
                    'results': response.get('results', []),
                    'answer': response.get('answer', '')
                })
            except Exception as e:
                print(f"Error in competitor research: {str(e)}")
        
        research_results['competitors'] = extract_competitors_with_llm(
            brand_name, 
            competitors_data,
            research_results['brand_category'],
            industry
        )
    return research_results

def extract_competitors_with_llm(brand_name: str, competitors_data: List[Dict], 
                                 brand_category: str, 
                                 industry: Optional[str] = None) -> List[str]:  # ✅ ADDED industry param
    """
    Extract genuine competitors using Claude LLM for accurate identification
    """
    
    if not anthropic_client:
        print("Warning: Anthropic API not available, using fallback extraction")
        return extract_competitors_fallback(competitors_data, brand_name)
    
    # Compile all research text
    research_text = ""
    for data in competitors_data:
        if data.get('answer'):
            research_text += f"\n{data['answer']}\n"
        for result in data.get('results', [])[:3]:
            research_text += f"\n{result.get('content', '')[:500]}\n"
    
    # Limit text length to avoid token limits
    research_text = research_text[:4000]
    
    if not research_text.strip():
        print("Warning: No research text available for competitor extraction")
        return []
    
    # ✅ ENHANCED: Include industry in prompt
    industry_context = f"\nIndustry: {industry}" if industry else ""
    
    # Create LLM prompt for competitor extraction
    prompt = f"""Based on the following market research about "{brand_name}", extract competitor brand names.

Brand Category: {brand_category}{industry_context}

Research Data:
{research_text}

CRITICAL REQUIREMENTS:
1. Extract ONLY real company/brand names that are direct competitors of {brand_name}
2. DO NOT include: {brand_name} itself, generic terms, product categories, or descriptive phrases
3. Return ONLY actual competitor brand names (proper nouns)
4. Prioritize brands in the same industry/category as {brand_name}
5. Focus on answer from research data.

Format your response as a simple list, one competitor per line, with NO numbering or bullet points:
Competitor Name 1
Competitor Name 2
Competitor Name 3
etc."""

    try:
        try:
            response = anthropic_client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=500,
                temperature=0.3,
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            )
            response_text = response.content[0].text
            print(f"✅ Claude extracted competitors for {brand_name}")
            
        except Exception as anthropic_error:
            print(f"⚠️ Claude API failed: {str(anthropic_error)}")
            print(f"🔄 Attempting fallback to Mistral...")
            
            if not mistral_client:
                print("Mistral API key not found. Using fallback")
                return extract_competitors_fallback(competitors_data, brand_name)
            
            try:
                mistral_response = mistral_client.chat.complete(
                    model="mistral-small-latest",
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=500,
                    temperature=0.3
                )
                response_text = mistral_response.choices[0].message.content
                print(f"✅ Mistral extracted competitors for {brand_name} (fallback)")
                
            except Exception as mistral_error:
                print(f"❌ Both Claude and Mistral failed")
                print(f"   Claude: {str(anthropic_error)}")
                print(f"   Mistral: {str(mistral_error)}")
                return extract_competitors_fallback(competitors_data, brand_name)
        
        # Extract competitor names from response
        competitors = []
        lines = response_text.strip().split('\n')
        
        for line in lines:
            # Clean the line
            line = line.strip()
            # Remove numbering if present
            line = re.sub(r'^\d+[\.\)]\s*', '', line)
            line = re.sub(r'^[-*•]\s*', '', line)
            
            # Validate it's a proper brand name
            if (line and 
                len(line) > 2 and 
                len(line) < 50 and
                brand_name.lower() not in line.lower() and
                not is_generic_term(line)):
                
                competitors.append(line)
        
        # Limit to 5 competitors
        competitors = competitors[:5]
        
        if len(competitors) > 0:
            print(f"✅ Extracted {len(competitors)} genuine competitors using LLM")
            return competitors
        else:
            print("Warning: LLM returned no valid competitors, using fallback")
            return extract_competitors_fallback(competitors_data, brand_name)
    
    except Exception as e:
            print(f"Error in LLM competitor extraction: {str(e)}")
            return extract_competitors_fallback(competitors_data, brand_name)


def is_generic_term(term: str) -> bool:
    """Check if a term is generic rather than a brand name"""
    generic_terms = [
        'other', 'refinery', 'petroleum', 'energy', 'company', 'companies',
        'brand', 'brands', 'manufacturer', 'supplier', 'provider', 'corporation',
        'industry', 'market', 'sector', 'alternative', 'competitor', 'similar',
        'various', 'many', 'several', 'numerous', 'etc', 'and more'
    ]
    
    term_lower = term.lower()
    
    # Check if it's a generic term
    if any(generic in term_lower for generic in generic_terms):
        return True
    
    # Check if it's too short or contains suspicious patterns
    if len(term) <= 2 or term.endswith("'s"):
        return True
    
    return False


def extract_competitors_fallback(competitors_data: List[Dict], exclude_brand: str) -> List[str]:
    """
    Fallback competitor extraction using heuristics
    """
    competitors = set()
    
    # Compile all text
    all_text = ""
    for data in competitors_data:
        if data.get('answer'):
            all_text += " " + data['answer']
        for result in data.get('results', [])[:3]:
            all_text += " " + result.get('content', '')[:300]
    
    # Look for capitalized phrases (potential brand names)
    # Match patterns like "Apple Inc", "Tesla Motors", "Amazon"
    brand_pattern = r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\b'
    matches = re.findall(brand_pattern, all_text)
    
    for match in matches:
        # Filter out generic terms and the main brand
        if (len(match) > 2 and 
            len(match) < 50 and
            exclude_brand.lower() not in match.lower() and
            not is_generic_term(match) and
            match not in ['The', 'This', 'That', 'These', 'Those', 'India', 'China', 'USA']):
            
            competitors.add(match)
    
    # Convert to list and limit to 5
    competitors_list = list(competitors)[:5]
    
    if len(competitors_list) > 0:
        print(f"✓ Extracted {len(competitors_list)} competitors using fallback method")
    else:
        print("⚠ Warning: Could not extract any competitors from research data")
    
    return competitors_list


def get_research_summary(research_data: Dict[str, Any]) -> str:
    """Generate a concise summary of research findings"""
    summary_parts = []
    
    if research_data.get('brand_category'):
        summary_parts.append(f"**Category:** {research_data['brand_category'][:200]}")
    
    if research_data.get('market_reputation'):
        summary_parts.append(f"**Reputation:** {research_data['market_reputation'][:200]}")
    
    if research_data.get('competitors'):
        summary_parts.append(f"**Top Competitors:** {', '.join(research_data['competitors'][:5])}")
    else:
        summary_parts.append("**Top Competitors:** None identified (research in progress)")
    
    if research_data.get('pricing_structure'):
        summary_parts.append(f"**Pricing:** {research_data['pricing_structure'][:200]}")
    
    if research_data.get('trends'):
        summary_parts.append(f"**Industry Trends:** {research_data['trends'][:200]}")
    
    return "\n\n".join(summary_parts)

def extract_industry_with_llm(brand_name: str, context_text: str) -> Optional[str]:
    """Extract a short, concise industry name from text"""
    if not context_text:
        return None
        
    prompt = f"""Based on this description of "{brand_name}", identify the specific industry it belongs to.
Description: {context_text[:1000]}

Return ONLY the Industry Name (max 3-4 words). Examples: "SaaS", "E-commerce Footwear", "Fintech", "Automotive".
Do not write "The industry is...". Just the name."""

    try:
        # Prefer Mistral for this simple task to save Claude tokens, or Claude if Mistral missing
        client = mistral_client if mistral_client else anthropic_client
        if not client:
            return None
            
        if client == mistral_client:
             response = client.chat.complete(
                model="mistral-small-latest",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=20,
                temperature=0.1
            )
             return response.choices[0].message.content.strip()
        else:
             response = client.messages.create(
                model="claude-sonnet-4-20250514", # Using available model string
                max_tokens=20,
                temperature=0.1,
                messages=[{"role": "user", "content": prompt}]
            )
             return response.content[0].text.strip()
             
    except Exception as e:
        print(f"Error inferring industry: {str(e)}")
        return None