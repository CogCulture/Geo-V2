import os
import time
import json
import logging
from anthropic import Anthropic
from mistralai import Mistral
from dotenv import load_dotenv
from typing import Dict, List, Optional, Any


load_dotenv()

# The newest Anthropic model is "claude-sonnet-4-20250514"
# If the user doesn't specify a model, always prefer using "claude-sonnet-4-20250514" as it is the latest model.
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")
anthropic = Anthropic(api_key=ANTHROPIC_API_KEY)

MISTRAL_API_KEY = os.environ.get("MISTRAL_API_KEY")
mistral_client = Mistral(api_key=MISTRAL_API_KEY) if MISTRAL_API_KEY else None

DEFAULT_MODEL_STR = "claude-sonnet-4-20250514"
logger = logging.getLogger(__name__)

def generate_prompts(brand_name, num_prompts=5, research_context=None, keywords=None, industry=None):
    """
    Generate relevant prompts for brand analysis using enhanced strategist approach.
    
    Integrates GeoAImode's context-enriched strategy with better competitor analysis
    and industry-specific queries.
    
    Args:
        brand_name (str): The brand name to analyze
        num_prompts (int): Number of prompts to generate (default: 10, max: 15)
        research_context (dict): Optional deep research data containing:
            - brand_category, competitors, trends, etc.
        keywords (list): Optional list of SEO keywords
        industry (str): Optional industry context (e.g., "health supplements", "smartphone")
    
    Returns:
        list: List of generated organic search prompts
    """
    
    if not ANTHROPIC_API_KEY:
        raise ValueError("Anthropic API key not found. Please set ANTHROPIC_API_KEY environment variable.")
    
    try:
        # Normalize num_prompts to maximum 25
        num_prompts = min(int(num_prompts), 25)
        
        # Build enhanced context similar to GeoAImode
        context_data = build_enriched_context(brand_name, research_context, keywords, industry)
        
        # Build strategist meta prompt with context
        meta_prompt = build_strategist_meta_prompt(brand_name, num_prompts, context_data, industry)
        
        logger.info(f"🧠 Generating {num_prompts} prompts for brand: {brand_name}")
        logger.info(f"   Industry: {context_data.get('industry', 'auto-detected')}")
        logger.info(f"   Competitors: {len(context_data.get('competitors', []))} identified")
        
        # Call Claude with enhanced prompt
        messages = [
            {
                "role": "user",
                "content": meta_prompt
            }
        ]
        
        try:
            response = anthropic.messages.create(
            model=DEFAULT_MODEL_STR,
            max_tokens=1000,
            temperature=0.7,
            system=get_strategist_system_prompt(),
            messages=messages
            )
        
            
            response_text = response.content[0].text
            logger.info(f"✅ Claude generated response: {len(response_text)} chars")
            
        except Exception as anthropic_error:
            logger.warning(f"⚠️ Claude API failed: {str(anthropic_error)}")
            logger.info(f"🔄 Attempting fallback to Mistral...")
            
            if not mistral_client:
                raise ValueError("Mistral API key not found. Please set MISTRAL_API_KEY environment variable.")
            
            try:
                mistral_response = mistral_client.chat.complete(
                    model="mistral-small-latest",
                    messages=[{"role": "user", "content": meta_prompt}],
                    max_tokens=1000,
                    temperature=0.5
                )
                response_text = mistral_response.choices[0].message.content
                logger.info(f"✅ Mistral generated response: {len(response_text)} chars (fallback)")
                
            except Exception as mistral_error:
                logger.error(f"❌ Both Claude and Mistral failed")
                logger.error(f"   Claude: {str(anthropic_error)}")
                logger.error(f"   Mistral: {str(mistral_error)}")
                logger.warning(f"⚠️ Falling back to heuristic prompts")
                return get_fallback_prompts(brand_name, keywords, industry, num_prompts)
        
        # Extract numbered prompts from response
        prompts = extract_numbered_prompts(response_text)
        
        if not prompts:
            logger.warning("⚠️ Could not extract prompts from Claude response, using fallback")
            return get_fallback_prompts(brand_name, keywords, industry, num_prompts)
        
        # Validate and deduplicate prompts
        validated = validate_and_dedupe_prompts(prompts)
        
        # Ensure we return exactly num_prompts
        final_prompts = validated[:num_prompts]
        
        logger.info(f"✅ Generated {len(final_prompts)} validated prompts")
        for i, p in enumerate(final_prompts, 1):
            logger.debug(f"   {i}. {p[:60]}...")
        
        return final_prompts
        
    except Exception as e:
        logger.error(f"❌ Error generating prompts: {str(e)}")
        logger.warning(f"⚠️ Falling back to heuristic prompts")
        return get_fallback_prompts(brand_name, keywords, industry, num_prompts)


def generate_prompts_by_cohort(
    brand_name: str,
    cohort: Dict,
    research_context: Dict,
    keywords: List[str],
    industry: Optional[str] = None,
    product_name: Optional[str] = None
) -> List[str]:
    """
    Generate prompts for a specific cohort.
    
    Args:
        brand_name: The brand name
        cohort: Dict with 'name', 'description', 'prompt_count'
        research_context: Deep research data
        keywords: SEO keywords
        industry: Industry context
    
    Returns:
        List of prompts for this cohort
    """
    if not ANTHROPIC_API_KEY:
        raise ValueError("Anthropic API key not found")
    
    try:
        num_prompts = cohort.get('prompt_count', 5)
        cohort_name = cohort.get('name', 'General')
        cohort_description = cohort.get('description', '')
        
        # Build context
        context_data = build_enriched_context(brand_name, research_context, keywords, industry)
        
        industry_text = context_data.get('industry', industry or 'market')
        competitors = context_data.get('competitors', [])
        competitors_str = ", ".join(competitors[:5]) if competitors else "market competitors"
        keywords_str = ", ".join(keywords[:40]) if keywords else ""
        keyword_guidance = ""
        if keywords and len(keywords) > 0:
            priority_keywords = keywords[:5]
            keyword_guidance = f"\n\n🎯 PRIORITY KEYWORDS TO INCORPORATE:\n{', '.join(priority_keywords)}\n\nWhen generating prompts, naturally weave these priority keywords into relevant queries where they make contextual sense. These represent specific aspects the user wants to explore."
        # Build cohort-specific prompt
        prompt = f"""You are a Generative Engine Optimization (GEO) specialist with deep expertise in understanding how Indian users query AI platforms like ChatGPT, Perplexity, Google AI Overview, and Claude. Your task is to generate realistic, high-volume prompts that Indian users are most likely to type when searching about a brand.

BRAND CONTEXT (for understanding only - DO NOT mention brand name in prompts):
Brand: {brand_name}
Product: {product_name}
Key Competitors: {competitors_str}
Category Keywords: {keywords_str}
current_date: 2026

COHORT FOCUS:
Name: {cohort_name}
Description: {cohort_description}

CRITICAL INSTRUCTION — ABSOLUTE UNIQUENESS REQUIREMENT:
This means:
**NEVER MENTION {brand_name} in any prompt.
If you generate prompts for B2C, B2B, B2B2C, B2G, and D2C, a prompt used in B2C cannot appear in B2B with minor word changes
Similar query structures with only the category context swapped are NOT allowed
Each prompt must ask a fundamentally different question or address a distinctly different user need
Violation of this rule invalidates the entire output.

Task: I want you to generate {num_prompts} strictly cohort specific prompt by going through the steps if have mentioned below. Assume that a real human inside {cohort_name} category with the nature - {cohort_description}. would search the most about the {brand_name}.

Step 1: Category Detection
Based on, identify which business model categories the brand operates in:
B2C (Business to Consumer) — Selling directly to individual consumers
B2B (Business to Business) — Selling to other businesses
B2B2C (Business to Business to Consumer) — Selling through business intermediaries who serve consumers
B2G (Business to Government) — Selling to government entities/PSUs
D2C (Direct to Consumer) — Brand-owned channels selling directly, bypassing retail
If the brand operates in multiple categories, list all applicable categories.

Step 2: Temporal Relevance Check
Before generating prompts, determine the temporal context based on {{current_date}}:
Identify Current Month & Year — Extract month and year from {{current_date}}
Determine Seasonal/Festive Context — Map the current month to relevant Indian context:
Month
Seasonal Context - Potential Festive/Event Context
January - Winter (North India), Pleasant (South), New Year, Republic Day, Budget Season
February - Late Winter, Valentine's Day
March - Spring, Financial Year End, Holi, CBSE/Board Exams, FY Closing
April - Summer Begins, New Financial Year, Ugadi, Baisakhi
May - Peak Summer, Summer Vacations, IPL
June - Pre-Monsoon, Extreme Heat, Summer Sales
July - Monsoon, Monsoon Sales
August - Monsoon, Independence Day, Raksha Bandhan, Janmashtami
September - Monsoon End, Ganesh Chaturthi, Onam
October - Autumn, Pleasant, Navratri, Durga Puja, Dussehra, Pre-Diwali
November - Early Winter, Diwali, Festive Sales, Wedding Season Begins
December - Winter, Christmas, Year End, Wedding Season

Apply Temporal Relevance — Where appropriate, incorporate:
Current year in prompts
Seasonal context if relevant to the industry
Festive context if applicable
Financial year context for B2B/B2G

Temporal Relevance Rules:
Use seasonal context only if genuinely relevant to the product/service
Do not force temporal references where they feel unnatural
Avoid outdated references (past years, past events)

Step 3: Keyword Diversity & Distribution
Before generating prompts, analyse {keywords_str} for {cohort_name} specific diversity 

Keyword Distribution Rules:
do not repeat keywords again and again. I want uniqueness and variety so that my user can choose from multiple options. 
Maintain natural language flow — keywords should fit seamlessly into the query structure

Keyword Integration Quality Check:
Read each prompt aloud — if the keyword feels forced or awkward, rephrase
Keywords should appear where a real user would naturally place them

Step 4: Generate 5 Prompts Per Category
For each detected category, generate exactly 5 prompts that:
Match Indian User Writing Style with Proper Structure:
Use natural, conversational Indian English
Ensure each prompt is grammatically correct and well-structured
Maintain the authentic way Indians phrase queries (direct, practical, value-focused)
Include phrases like "best," "top," "which is better - where relevant.
Balance grammatical correctness with natural Indian query patterns — avoid overly formal or academic phrasing
Cover High-Volume Search Intents (select based on what makes logical sense for the category and keywords):
Informational — Learning about the brand/product/service
Navigational — Finding specific brand information
Investigational — Researching before making a decision
Comparative — Comparing with competitors from {competitors_str}
Commercial — Evaluating purchase options
Transactional — Ready to buy/enquire

Align with Intent Stages most relevant to the category:
Awareness (what is, who is, tell me about)
Consideration (which is better, compare, vs, alternatives)
Decision (best, top, should I buy, is it worth)
Post-purchase (how to use, setup, support, service)

Incorporate Variables Naturally:
Use {brand_name} as the user would type it
Include comparisons using {competitors_str} where comparative intent applies
Weave in relevant terms from {keywords_str} naturally — never force keywords

Step 5: Category-Specific Writing Style
For B2C / D2C prompts:
Write as an everyday Indian consumer would type
Include budget considerations, regional relevance, family/home context
Use casual, direct language

For B2B prompts:
Write as procurement managers, supply chain heads, or technical evaluators would type
Include business context: bulk pricing, vendor evaluation, compliance, certifications, ROI
Use professional but practical language

For B2B2C prompts:
Write as channel partners, distributors, or retailers would type
Include margin, dealership, franchise, distribution context

For B2G prompts:
Write as government procurement officers or PSU evaluators would type
Include tender, GeM registration, compliance, empanelment context
Use formal, specification-driven language

Important Guidelines:
No prompt should be repeated — fully or partially
No prompt should be a minor rephrasing of another prompt
No two prompts should have the same semantic meaning, even if worded differently
Test: If two prompts would return similar results from an AI, they are duplicates — one must be replaced
Test: If swapping brand context between two prompts makes them identical, they are duplicates — one must be replaced

Prompt Structure & Grammar:
Every prompt must be grammatically correct and properly structured as a complete, coherent query
Maintain natural Indian English phrasing — do not over-formalise or make it sound like textbook English
The prompt should read smoothly and make immediate sense to anyone reading it
Avoid sentence fragments, awkward phrasing, or jumbled word order

Uniqueness Requirements (Within Category):
Each of the prompt within a category must be semantically unique
No two prompts should ask the same question in slightly different words
Vary the intent type, journey stage, keyword focus, and query structure across prompts
Use the uniqueness check: If two prompts would yield the same search results, one must be changed

General Rules:
Do not generate generic prompts — every prompt must feel like a real query an Indian user would type into an AI assistant
Do not include negative sentiment queries
Keep prompts concise — match how users actually type (not how they speak). Most LLM queries are 5-15 words

Pre-Output Validation Checklist:
Before finalising, verify each prompt against:
Check
Requirement
☐ Within-Cohort Uniqueness
Is this prompt different from the other prompts in the same category?
☐ Grammar
Is the prompt grammatically correct and well-structured?
☐ Natural Flow
Does it sound like a real Indian user query, not marketing copy?
☐ Temporal
Are year/season/festival references current and relevant?
☐ Keyword Fit
Are keywords integrated naturally without forcing?
☐ Keyword Diversity
Are different keywords used across the 10 prompts?
☐ Sense Check
Does the prompt make logical sense and would a real user type this?
☐ Conciseness
Is it 5-15 words (max 20)?

OUTPUT FORMAT:
Return exactly {num_prompts} prompts numbered from 1 to {num_prompts}.
Format: 1. [prompt], 2. [prompt], etc.

Begin immediately with the numbered list:"""
        messages = [{"role": "user", "content": prompt}]

        try:
            response =  anthropic.messages.create(
                model=DEFAULT_MODEL_STR,
                max_tokens=800,
                temperature=0.5,
                #system=get_strategist_system_prompt(),
                messages=messages
            )
        
        except Exception as anthropic_error:
            logger.warning(f"⚠️ Claude API failed: {str(anthropic_error)}")
            logger.info(f"🔄 Attempting fallback to Mistral for cohort '{cohort_name}'...")
            
            if not mistral_client:
                logger.error("Mistral API key not found. Please set MISTRAL_API_KEY environment variable.")
                return get_cohort_fallback_prompts(cohort_name, industry_text, num_prompts)
            
            try:
                mistral_response = mistral_client.chat.complete(
                    model="mistral-small-latest",
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=800,
                    temperature=0.5
                )
                response_text = mistral_response.choices[0].message.content
                logger.info(f"✅ Mistral generated response for cohort '{cohort_name}' (fallback)")
                
                # Extract prompts
                prompts = extract_numbered_prompts(response_text)
                
                if not prompts:
                    logger.warning(f"Could not extract prompts for cohort '{cohort_name}', using fallback")
                    return get_cohort_fallback_prompts(cohort_name, industry_text, num_prompts)
                
                # Validate and return
                validated = validate_and_dedupe_prompts(prompts)
                final_prompts = validated[:num_prompts]
                
                logger.info(f"✅ Generated {len(final_prompts)} prompts for cohort '{cohort_name}' (Mistral fallback)")
                
                return final_prompts
                
            except Exception as mistral_error:
                logger.error(f"❌ Both Claude and Mistral failed for cohort '{cohort_name}'")
                logger.error(f"   Claude: {str(anthropic_error)}")
                logger.error(f"   Mistral: {str(mistral_error)}")
                return get_cohort_fallback_prompts(cohort_name, industry_text, num_prompts)
        
        parts = []
        for block in response.content:
            if getattr(block, "type", None) == "text":
                parts.append(block.text)
            elif isinstance(block, dict) and block.get("type") == "text":
                parts.append(block.get("text", ""))

        response_text = "\n".join(parts).strip()
        
        # Extract prompts
        prompts = extract_numbered_prompts(response_text)
        
        if not prompts:
            logger.warning(f"Could not extract prompts for cohort '{cohort_name}', using fallback")
            return get_cohort_fallback_prompts(cohort_name, industry_text, num_prompts)
        
        # Validate and return
        validated = validate_and_dedupe_prompts(prompts)
        final_prompts = validated[:num_prompts]
        
        logger.info(f"✅ Generated {len(final_prompts)} prompts for cohort '{cohort_name}'")
        
        return final_prompts
        
    except Exception as e:
        logger.error(f"Error generating prompts for cohort: {str(e)}")
        return get_cohort_fallback_prompts(
            cohort.get('name', 'General'),
            industry or 'product',
            cohort.get('prompt_count', 3)
        )


def get_cohort_fallback_prompts(cohort_name: str, industry: str, num_prompts: int) -> List[str]:
    """Fallback prompts for a specific cohort"""
    fallback_templates = {
        'brand comparison': [
            f"top 10 {industry} brands in India",
            f"best {industry} companies 2025",
            f"leading {industry} providers comparison",
            f"most trusted {industry} brands"
        ],
        'product comparison': [
            f"compare {industry} products",
            f"{industry} alternatives comparison",
            f"which {industry} is better",
            f"{industry} options India"
        ],
        'reviews': [
            f"{industry} reviews 2025",
            f"best rated {industry}",
            f"{industry} customer feedback",
            f"genuine {industry} reviews"
        ],
        'buying guide': [
            f"how to choose {industry}",
            f"what to look for in {industry}",
            f"{industry} buying guide India",
            f"factors to consider when buying {industry}"
        ],
        'trends': [
            f"{industry} trends 2025",
            f"future of {industry}",
            f"latest {industry} innovations",
            f"{industry} industry insights"
        ]
    }
    
    # Match cohort name to template category
    cohort_lower = cohort_name.lower()
    for key in fallback_templates:
        if key in cohort_lower:
            return fallback_templates[key][:num_prompts]
    
    # Default fallback
    return [
        f"best {industry} options",
        f"top {industry} brands",
        f"{industry} reviews"
    ][:num_prompts]


def build_enriched_context(brand_name, research_context=None, keywords=None, industry=None):
    """
    Build enriched context data from research, keywords, and industry.
    Similar to enrich_brand_context in GeoAImode.py
    """
    context = {
        "industry": industry or "unknown",
        "business_type": "B2B/B2C",
        "primary_products": [],
        "target_audience": "users",
        "competitors": [],
        "unique_value_proposition": "quality products/services",
        "category_keywords": []
    }
    
    # Extract from research_context if available
    if research_context and isinstance(research_context, dict):
        context["industry"] = research_context.get("brand_category", industry or "unknown")
        context["competitors"] = research_context.get("competitors", [])[:5]
        context["primary_products"] = research_context.get("products", [])[:3]
        context["target_audience"] = research_context.get("target_audience", "users")
        context["unique_value_proposition"] = research_context.get("unique_value", "quality")
    
    # Add keywords as category keywords
    if keywords and isinstance(keywords, list):
        context["category_keywords"] = keywords[:10]
    
    return context


def build_strategist_meta_prompt(brand_name, num_prompts, context_data, industry=None):
    """
    Build enhanced meta prompt inspired by GeoAImode's build_enhanced_strategist_prompt
    with category-specific queries and competitor analysis.
    """
    
    industry_text = context_data.get("industry", industry or "the market")
    competitors = context_data.get("competitors", [])
    keywords = context_data.get("category_keywords", [])
    target_audience = context_data.get("target_audience", "users")
    
    competitors_str = ", ".join(competitors[:3]) if competitors else "market competitors"
    keywords_str = ", ".join(keywords[:5]) if keywords else "industry terms"
    
    prompt = f"""You are a senior brand and marketing strategist specializing in visibility improvement through AI search engines.

BRAND CONTEXT (for understanding only - DO NOT mention brand name in prompts):
- Brand: {brand_name}
- Industry: {industry_text}
- Target Audience: {target_audience}
- Key Competitors: {competitors_str}
- Category Keywords: {keywords_str}

TASK: Generate exactly {num_prompts} highly specific, organic search prompts that real users in India would type when looking for products/services in the {industry_text} industry.

CRITICAL RULES:
1. **NEVER mention "{brand_name}" in any prompt** - all prompts must be organic and natural
2. Each prompt should sound like a real user search query from 2025
3. Keep prompts focused on India market
4. Use natural language (not brand-focused)

PROMPT CATEGORIES TO INCLUDE:

1. **Visibility & Ranking Prompts** (3-4 prompts):
   - "top 10 {industry_text} brands in India"
   - "best {industry_text} companies 2025"
   - "leading {industry_text} providers"

2. **Comparison Prompts** (2-3 prompts):
   - Compare {competitors_str}
   - "{competitors} vs which is better"
   - Difference between options

3. **Feature & Specification Prompts** (2-3 prompts):
   - "how much does [product] cost in India"
   - "features of [product type]"
   - Technical details queries

4. **Problem-Solving Prompts** (2-3 prompts):
   - "how to choose [product] for [use case]"
   - "what to look for when buying [product]"
   - User pain-point solutions

5. **Reviews & Reputation Prompts** (2-3 prompts):
   - "[product type] reviews 2025"
   - "is [product] worth it"
   - "genuine vs fake [product]"

OUTPUT FORMAT:
Return exactly {num_prompts} prompts numbered from 1 to {num_prompts}.
Format: `1. [prompt]`, `2. [prompt]`, etc.
Each prompt must be a single natural-sounding question.

Begin immediately with the numbered list of {num_prompts} prompts:
"""
    
    return prompt


def get_strategist_system_prompt():
    """
    System prompt for Claude acting as a strategist
    """
    return """You are an expert SEO/GEO strategist and market analyst. Your task is to generate organic search prompts that real users would naturally type when searching for products or services. 

Key responsibilities:
- Generate prompts that reflect actual user search behavior in 2025
- Never mention specific brand names in the prompts
- Focus on industry-relevant, problem-solution oriented queries
- Consider geographic context (India)
- Create prompts that would naturally surface brand visibility
- Ensure diversity across different search intents (comparison, reviews, features, etc.)

Return only the numbered list of prompts with no additional commentary."""


def extract_numbered_prompts(text):
    """
    Extract numbered prompts from Claude response.
    Similar to extract_numbered_lines in GeoAImode.py
    """
    import re
    
    prompts = []
    
    # Split by newlines
    lines = text.split('\n')
    
    for line in lines:
        line = line.strip()
        
        if not line:
            continue
        
        # Match patterns like "1. ", "1) ", "1: ", etc.
        match = re.match(r'^(\d+)[.\)\:\-\s]+\s*(.+)$', line)
        
        if match:
            prompt_text = match.group(2).strip()
            # Remove quotes if present
            prompt_text = prompt_text.strip('"\'')
            
            if prompt_text and len(prompt_text) > 5:
                prompts.append(prompt_text)
    
    return prompts


def validate_and_dedupe_prompts(prompts):
    """
    Validate and deduplicate prompts.
    """
    validated = []
    seen = set()
    
    for prompt in prompts:
        if not isinstance(prompt, str):
            continue
        
        prompt = prompt.strip()
        
        # Skip if too short
        if len(prompt) < 5:
            continue
        
        # Skip if empty or duplicate
        norm = prompt.lower().strip()
        if norm in seen:
            continue
        
        seen.add(norm)
        validated.append(prompt)
    
    return validated


def get_fallback_prompts(brand_name, keywords=None, industry=None, num_prompts=10):
    """
    Generate fallback organic prompts if Claude generation fails.
    Based on get_fallback_prompts from prompt_generator.py with enhancements.
    """
    
    industry = industry or "product/service"
    
    # Industry-based fallback prompts
    industry_prompts = [
        f"top 10 most trusted {industry} brands",
        f"best {industry} companies",
        f"leading {industry} products",
        f"most popular {industry} brands",
        f"top rated {industry} companies",
        f"best {industry} brands in India",
        f"leading {industry} companies globally",
        f"most trusted {industry} manufacturers",
        f"top {industry} brands 2025",
        f"best {industry} companies for quality",
        f"how to choose {industry}",
        f"what to look for in {industry}",
        f"{industry} reviews 2025",
        f"is {industry} worth it",
        f"genuine vs fake {industry}",
    ]
    
    # If keywords available, enhance with keyword-based prompts
    if keywords and isinstance(keywords, list):
        keyword_prompts = []
        for keyword in keywords[:5]:
            keyword_prompts.extend([
                f"best {keyword}",
                f"top {keyword} brands",
                f"{keyword} reviews",
                f"how to choose {keyword}",
                f"{keyword} vs alternatives"
            ])
        # Combine and deduplicate
        all_prompts = industry_prompts + keyword_prompts
    else:
        all_prompts = industry_prompts
    
    # Deduplicate and return
    validated = validate_and_dedupe_prompts(all_prompts)
    return validated[:num_prompts]


def validate_prompts(prompts):
    """
    Validate that the generated prompts are suitable for analysis.
    """
    return validate_and_dedupe_prompts(prompts)


def extract_prompts_from_text(text):
    """
    Extract prompts from text when JSON parsing fails.
    Alias for _extract_numbered_prompts for backward compatibility.
    """
    return extract_numbered_prompts(text)



"""
You are a Generative Engine Optimization (GEO) specialist with deep expertise in understanding how Indian users query AI platforms like ChatGPT, Perplexity, Google AI Overview, and Claude. Your task is to generate realistic, high-volume prompts that Indian users are most likely to type when searching about a brand.

BRAND CONTEXT (for understanding only - DO NOT mention brand name in prompts):
Brand: {brand_name}
Industry: {industry_text}
Product: {product_name}
Key Competitors: {competitors_str}
Category Keywords: {keywords_str}{keyword_guidance}

COHORT FOCUS:
Name: {cohort_name}
Description: {cohort_description}

CRITICAL INSTRUCTION — ABSOLUTE UNIQUENESS REQUIREMENT:
This means:
If you generate prompts for B2C, B2B, B2B2C, B2G, and D2C, a prompt used in B2C cannot appear in B2B with minor word changes
Similar query structures with only the category context swapped are NOT allowed
Each prompt must ask a fundamentally different question or address a distinctly different user need
Violation of this rule invalidates the entire output.

Task: I want you to generate {num_prompts} strictly cohort specific prompt by going through the steps if have mentioned below. Assume that a real human inside {cohort_name} category with the nature - {cohort_description}. would search the most about the {brand_name}.

Step 1: Category Detection
Based on {industry_text}, identify which business model categories the brand operates in:
B2C (Business to Consumer) — Selling directly to individual consumers
B2B (Business to Business) — Selling to other businesses
B2B2C (Business to Business to Consumer) — Selling through business intermediaries who serve consumers
B2G (Business to Government) — Selling to government entities/PSUs
D2C (Direct to Consumer) — Brand-owned channels selling directly, bypassing retail
If the brand operates in multiple categories, list all applicable categories.

Step 2: Temporal Relevance Check
Before generating prompts, determine the temporal context based on {{current_date}}:
Identify Current Month & Year — Extract month and year from {{current_date}}
Determine Seasonal/Festive Context — Map the current month to relevant Indian context:
Month
Seasonal Context - Potential Festive/Event Context
January - Winter (North India), Pleasant (South), New Year, Republic Day, Budget Season
February - Late Winter, Valentine's Day
March - Spring, Financial Year End, Holi, CBSE/Board Exams, FY Closing
April - Summer Begins, New Financial Year, Ugadi, Baisakhi
May - Peak Summer, Summer Vacations, IPL
June - Pre-Monsoon, Extreme Heat, Summer Sales
July - Monsoon, Monsoon Sales
August - Monsoon, Independence Day, Raksha Bandhan, Janmashtami
September - Monsoon End, Ganesh Chaturthi, Onam
October - Autumn, Pleasant, Navratri, Durga Puja, Dussehra, Pre-Diwali
November - Early Winter, Diwali, Festive Sales, Wedding Season Begins
December - Winter, Christmas, Year End, Wedding Season

Apply Temporal Relevance — Where appropriate, incorporate:
Current year in prompts
Seasonal context if relevant to the industry
Festive context if applicable
Financial year context for B2B/B2G
Temporal Relevance Rules:
Include current year in at least 2-3 prompts where it adds value
Use seasonal context only if genuinely relevant to the product/service
Do not force temporal references where they feel unnatural
Avoid outdated references (past years, past events)

Step 3: Keyword Diversity & Distribution
Before generating prompts, analyse {keywords_str} for diversity:
Categorise Keywords — Group keywords from {keywords_str} into:
Product/Service Keywords — Specific offerings
Feature Keywords — Attributes and benefits
Use Case Keywords — Applications
Brand/USP Keywords — Unique identifiers
Category Keywords — Industry/segment terms

Keyword Distribution Rules:
Use keywords from ALL relevant categories across the 10 prompts
Do not repeat the same keyword more than twice across prompts
Prioritise high-ranking/primary keywords but ensure secondary keywords are also represented
Each prompt should feature different keyword combinations
Maintain natural language flow — keywords should fit seamlessly into the query structure
Keyword Integration Quality Check:
Read each prompt aloud — if the keyword feels forced or awkward, rephrase
Keywords should appear where a real user would naturally place them
Avoid keyword stuffing — maximum 2-3 keywords per prompt
If a keyword cannot be integrated naturally, skip it for that prompt

Step 4: Cross-Cohort Uniqueness Planning
Before generating prompts, create a mental map to ensure zero repetition across categories:
Assign Distinct Themes Per Category:
Each category should explore different aspects of the brand/product
B2C focuses on: personal use, home context, value, lifestyle, family needs
B2B focuses on: business efficiency, compliance, bulk operations, vendor evaluation
B2B2C focuses on: partnership, margins, dealership, distribution network
B2G focuses on: tenders, government compliance, PSU requirements, empanelment
D2C focuses on: direct purchase, official channels, authenticity, exclusive offerings
Assign Distinct Query Structures Per Category:
Vary the sentence structure and question format across categories
If B2C uses "best [product] for [use case]" — B2B should NOT use the same structure
If B2C uses "vs" comparison — other categories should use different comparison formats or skip comparisons
Assign Distinct Keywords Per Category:
Divide {keywords_str} across categories where possible
If a keyword is used in B2C, prefer different keywords for B2B
Only repeat keywords across categories if absolutely necessary and with completely different query contexts
Cross-Cohort Uniqueness Verification:
After drafting all prompts, review the complete list across all categories
Flag any prompt that is similar to another prompt in ANY category
Replace flagged prompts with completely new queries

Step 5: Generate 5 Prompts Per Category
For each detected category, generate exactly 5 prompts that:
Match Indian User Writing Style with Proper Structure:
Use natural, conversational Indian English
Ensure each prompt is grammatically correct and well-structured
Maintain the authentic way Indians phrase queries (direct, practical, value-focused)
Include phrases like "best," "top," "which is better," "for Indian [context]," "under [budget]," "in India," "for [city/region]" where relevant
Balance grammatical correctness with natural Indian query patterns — avoid overly formal or academic phrasing
Cover High-Volume Search Intents (select based on what makes logical sense for the category and keywords):
Informational — Learning about the brand/product/service
Navigational — Finding specific brand information
Investigational — Researching before making a decision
Comparative — Comparing with competitors from {competitors_str}
Commercial — Evaluating purchase options
Transactional — Ready to buy/enquire
Align with Intent Stages most relevant to the category:
Awareness (what is, who is, tell me about)
Consideration (which is better, compare, vs, alternatives)
Decision (best, top, should I buy, is it worth)
Post-purchase (how to use, setup, support, service)
Incorporate Variables Naturally:
Use {brand_name} as the user would type it
Reference industry context from {industry_text}
Include comparisons using {competitors_str} where comparative intent applies
Weave in relevant terms from {keywords_str} naturally — never force keywords
Add temporal context from {{current_date}} where it enhances relevance

Step 6: Category-Specific Writing Style
For B2C / D2C prompts:
Write as an everyday Indian consumer would type
Include budget considerations, regional relevance, family/home context
Use casual, direct language

For B2B prompts:
Write as procurement managers, supply chain heads, or technical evaluators would type
Include business context: bulk pricing, vendor evaluation, compliance, certifications, ROI
Use professional but practical language

For B2B2C prompts:
Write as channel partners, distributors, or retailers would type
Include margin, dealership, franchise, distribution context

For B2G prompts:
Write as government procurement officers or PSU evaluators would type
Include tender, GeM registration, compliance, empanelment context
Use formal, specification-driven language

Important Guidelines:
MANDATORY — Absolute Uniqueness Across All Cohorts:
THIS IS NON-NEGOTIABLE: Every prompt in the entire output must be 100% unique
No prompt should repeat — fully or partially — in any other category
No prompt should be a minor rephrasing of another prompt from any category
No two prompts should have the same semantic meaning, even if worded differently
If the brand operates in 5 categories, all prompts must be distinct
Test: If two prompts would return similar results from an AI, they are duplicates — one must be replaced
Test: If swapping brand context between two prompts makes them identical, they are duplicates — one must be replaced
Prompt Structure & Grammar:
Every prompt must be grammatically correct and properly structured as a complete, coherent query
Maintain natural Indian English phrasing — do not over-formalise or make it sound like textbook English
The prompt should read smoothly and make immediate sense to anyone reading it
Avoid sentence fragments, awkward phrasing, or jumbled word order
Uniqueness Requirements (Within Category):
Each of the prompt within a category must be semantically unique
No two prompts should ask the same question in slightly different words
Vary the intent type, journey stage, keyword focus, and query structure across prompts
Use the uniqueness check: If two prompts would yield the same search results, one must be changed
Uniqueness Requirements (Across Categories):
If generating for multiple categories, ensure cross-category uniqueness
Do NOT repeat the same prompt logic across B2C, B2B, B2G, B2B2C, D2C
Do NOT use the same query template with only category-specific words swapped
Each category should explore genuinely different user needs and query patterns

Temporal Relevance:
Include current year (extracted from {{current_date}}) in prompts where it adds genuine value
Reference current season or upcoming festivals only if relevant to the product/industry
Keyword Diversity & Natural Integration:
Use diverse keywords from {keywords_str} across all prompts — do not over-rely on 1-2 keywords
Each prompt should feature a different keyword combination where possible
Keywords must be integrated naturally — they should feel like a normal part of the query
If a keyword cannot fit naturally, do not force it — skip and use in another prompt
Read the prompt aloud: if the keyword sounds awkward or inserted, rephrase the entire prompt
Prioritise making sense over including keywords — a natural prompt without a keyword is better than an awkward prompt with a keyword
General Rules:
Do not generate generic prompts — every prompt must feel like a real query an Indian user would type into an AI assistant
Do not force all intent types into every category — only use intents that logically apply and would have high search volume
Do not include negative sentiment queries
Prioritise prompts by estimated search volume — most commonly searched query styles should appear first
Keep prompts concise — match how users actually type (not how they speak). Most LLM queries are 5-15 words
Use competitors from {competitors_str} only in comparative prompts — maximum 2-3 comparative prompts per category

Pre-Output Validation Checklist:
Before finalising, verify each prompt against:
Check
Requirement
☐ Within-Cohort Uniqueness
Is this prompt different from the other prompts in the same category?
☐ Grammar
Is the prompt grammatically correct and well-structured?
☐ Natural Flow
Does it sound like a real Indian user query, not marketing copy?
☐ Temporal
Are year/season/festival references current and relevant?
☐ Keyword Fit
Are keywords integrated naturally without forcing?
☐ Keyword Diversity
Are different keywords used across the 10 prompts?
☐ Sense Check
Does the prompt make logical sense and would a real user type this?
☐ Conciseness
Is it 5-15 words (max 20)?

OUTPUT FORMAT:
Return exactly {num_prompts} prompts numbered from 1 to {num_prompts}.
Format: 1. [prompt], 2. [prompt], etc.

Begin immediately with the numbered list:"""
""