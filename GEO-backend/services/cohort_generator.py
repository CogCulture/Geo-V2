import os
import json
import logging
import re
from anthropic import Anthropic
from mistralai import Mistral
from dotenv import load_dotenv
from typing import Dict, List, Optional, Any

load_dotenv()

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")
anthropic = Anthropic(api_key=ANTHROPIC_API_KEY)
DEFAULT_MODEL_STR = "claude-sonnet-4-20250514"

MISTRAL_API_KEY = os.environ.get("MISTRAL_API_KEY")
mistral_client = Mistral(api_key=MISTRAL_API_KEY) if MISTRAL_API_KEY else None


logger = logging.getLogger(__name__)

def extract_json_from_response(text: str) -> List[Dict]:
    """Extract JSON array from Claude response safely"""
    
    # 1. Clean Markdown code blocks
    text = re.sub(r'```json\s*', '', text)
    text = re.sub(r'```\s*', '', text)
    text = text.strip()

    # 2. Try to find the array pattern directly
    json_match = re.search(r'\[\s*\{.*\}\s*\]', text, re.DOTALL)
    
    potential_json = json_match.group(0) if json_match else text

    try:
        return json.loads(potential_json)
    except json.JSONDecodeError:
        # 3. Fallback: Try bracket extraction if strictly JSON failed
        try:
            start = text.find('[')
            end = text.rfind(']') + 1
            if start != -1 and end != 0:
                return json.loads(text[start:end])
        except:
            pass
        return [] 

def generate_cohorts(
    brand_name: str,
    research_context: Dict,
    keywords: List[str],
    industry: Optional[str] = None,
    num_cohorts: int = 5,
    product_name: Optional[str] = None,
    extracted_content: Optional[dict] = None
) -> List[Dict[str, Any]]:
    """
    Generate thematic cohorts (topics) for prompt organization.
    Similar to Peec AI's topic grouping system.
    
    Returns:
        List of cohort dictionaries with structure:
        {
            'name': 'Cohort Name',
            'description': 'What this cohort covers',
            'prompt_count': 5  # How many prompts to generate for this cohort
        }
    """
    if not ANTHROPIC_API_KEY:
        raise ValueError("Anthropic API key not found")
    
    try:
        # Extract context
        industry_text = research_context
        competitors = research_context.get('competitors', [])[:5]
        competitors_str = ", ".join(competitors) if competitors else "market competitors"
        keywords_str = ", ".join(keywords[:40]) if keywords else ""
        custom_keywords_highlight = ""
        if keywords:
            custom_keywords_highlight = f"\n🎯 Priority Keywords: {', '.join(keywords[:5])}"

        extracted_content_str = ""
        if extracted_content:
            extracted_content_str = f"\nEXTRACTED WEBSITE CONTENT:\nMeta Description: {extracted_content.get('meta_description', '')}\nMeta Tags: {json.dumps(extracted_content.get('meta_tags', {}), indent=2)}\nOrganization Schema: {json.dumps(extracted_content.get('organization_schema', []), indent=2)}\n"

        # Build cohort generation prompt
        prompt = f"""You are a senior Generative Engine Optimization (GEO) strategist.

BRAND CONTEXT:
Brand: {brand_name}
Industry: {extracted_content_str}

TASK: Your task is to infer the MOST IMPORTANT stakeholder cohorts that historically generated the highest Google search demand around a brand, and who are now most likely to search for the same information using AI assistants (ChatGPT, Gemini, Claude) in 2026.

COHORT INFERENCE PRINCIPLES
------------------------------------
1. Each cohort must represent a DISTINCT group of real users who:
   - Share similar roles, intent patterns, and decision contexts
   - Historically contributed to high-volume Google searches
   - Will now ask similar questions to LLMs instead of search engines

2. Cohorts MUST be aligned with downstream prompt generation logic:
   - Cohorts should clearly map to one or more business models:
     B2C, B2B, B2B2C, B2G, D2C
   - Cohorts should naturally trigger specific prompt-writing styles:
     consumer, professional, distributor, or government-oriented

3. Use ALL of the following dimensions to infer cohorts:
   - Role (consumer, buyer, evaluator, implementer, partner, procurement)
   - Intent dominance (informational, investigational, comparative, commercial, transactional)
   - Funnel stage bias (awareness, consideration, decision, post-purchase)
   - Industry context (B2C vs B2B, high vs low consideration)
   - Competitive pressure (brands commonly compared at scale)
------------------------------------
PRIORITIZATION RULES
------------------------------------
- Generate FEWER cohorts (high-impact only)
- Each cohort must correspond to LARGE, REPEATED search demand clusters
- Prefer cohorts that:
  - Trigger “best / top / which is better” type searches
  - Lead to brand comparisons
  - Influence purchase or vendor shortlisting
- Avoid niche, edge-case, or low-volume user types
------------------------------------
COHORT NAMING RULES
------------------------------------
- Name must be 3–6 words
- Name should implicitly signal:
  - User type
  - Intent bias
  - Business context
------------------------------------
COHORT DESCRIPTION RULES
------------------------------------
Each description must:
- Be exactly ONE sentence
- Clearly explain:
  - WHO these users are
  - WHAT they search for
  - WHY their searches have high volume
- Hint at:
  - Category relevance (B2C/B2B/B2B2C/B2G/D2C)
  - Dominant intent types

OUTPUT FORMAT:
Return a JSON array with exactly {num_cohorts} cohort objects. Each object must have:
"name": Specific cohort name (3-6 words, descriptive of the persona/context)
"description": One detailed sentence explaining WHO these people are and WHAT they search for
"prompt_count": Integer (5) - always use 3 prompts per cohort

Example structure:
[
  {{
    "name": "Specific cohort name (3–6 words)",
    "description": "One detailed sentence explaining who these people are and what they search for",
    "prompt_count": 5
  }},
  ...
]

------------------------------------
IMPORTANT CONSTRAINTS
------------------------------------
- Do NOT generate prompts
- Do NOT mention brand name in cohort names or descriptions
- Do NOT include explanations outside JSON
- Do NOT invent user types unsupported by keywords or context
- Ensure cohorts are compatible with Indian search behaviour and business context
- Cohorts must naturally map to the prompt styles defined for B2C, B2B, B2B2C, or B2G

Return ONLY the JSON array, no other text."""

        # Call Claude
        try:
            response = anthropic.messages.create(
                model=DEFAULT_MODEL_STR,
                max_tokens=1500,
                temperature=0.7,
                messages=[{"role": "user", "content": prompt}]
            )

            
            response_text = response.content[0].text.strip()
            logger.info(f"✅ Claude generated cohorts for {brand_name}")
            
        except Exception as anthropic_error:
            logger.warning(f"⚠️ Claude API failed: {str(anthropic_error)}")
            logger.info(f"🔄 Attempting fallback to Mistral...")
            
            if not mistral_client:
                logger.error("Mistral API key not found. Please set MISTRAL_API_KEY environment variable.")
                return get_fallback_cohorts(industry_text, num_cohorts)
            
            try:
                mistral_response = mistral_client.chat.complete(
                    model="mistral-small-latest",
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=1500,
                    temperature=0.5
                )
                response_text = mistral_response.choices[0].message.content.strip()
                logger.info(f"✅ Mistral generated cohorts for {brand_name} (fallback)")
                
            except Exception as mistral_error:
                logger.error(f"❌ Both Claude and Mistral failed")
                logger.error(f"   Claude: {str(anthropic_error)}")
                logger.error(f"   Mistral: {str(mistral_error)}")
                return get_fallback_cohorts(industry_text, num_cohorts)
        
        # Extract JSON from response
        cohorts = extract_json_from_response(response_text)
        
        if not cohorts or len(cohorts) == 0:
            logger.warning("No cohorts extracted, using fallback")
            return get_fallback_cohorts(industry_text, num_cohorts)
        
        # Validate structure
        validated_cohorts = []
        for cohort in cohorts[:num_cohorts]:
            if isinstance(cohort, dict) and 'name' in cohort and 'description' in cohort:
                validated_cohorts.append({
                    'name': str(cohort['name']),
                    'description': str(cohort.get('description', '')),
                    'prompt_count': int(cohort.get('prompt_count', 3))
                })
        
        logger.info(f"✅ Generated {len(validated_cohorts)} cohorts for {brand_name}")
        for c in validated_cohorts:
            logger.info(f"  📁 {c['name']}: {c['prompt_count']} prompts")
        
        return validated_cohorts
        
    except Exception as e:
        logger.error(f"Error generating cohorts: {str(e)}")
        return get_fallback_cohorts(industry or 'product', num_cohorts)


def extract_json_from_response(text: str) -> List[Dict]:
    """Extract JSON array from Claude response"""
    import re
    
    # Try to find JSON array
    json_match = re.search(r'\[[\s\S]*\]', text)
    if json_match:
        try:
            return json.loads(json_match.group(0))
        except json.JSONDecodeError:
            pass
    
    # Try parsing entire response
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return []


def get_fallback_cohorts(industry: str, num_cohorts: int = 5) -> List[Dict]:
    """Fallback cohorts if LLM generation fails"""
    fallback = [
        {
            'name': f'Top {industry.title()} Brands',
            'description': f'Users searching for leading brands and rankings in {industry}',
            'prompt_count': 4
        },
        {
            'name': 'Product Comparison',
            'description': f'Users comparing different {industry} options and alternatives',
            'prompt_count': 3
        },
        {
            'name': 'Reviews & Reputation',
            'description': f'Users researching reviews and brand reputation in {industry}',
            'prompt_count': 3
        },
        {
            'name': 'Buying Guide',
            'description': f'Users seeking advice on how to choose {industry} products',
            'prompt_count': 3
        },
        {
            'name': 'Industry Trends',
            'description': f'Users interested in latest trends and innovations in {industry}',
            'prompt_count': 2
        }
    ]
    
    return fallback[:num_cohorts]
