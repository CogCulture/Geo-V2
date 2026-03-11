from typing import List, Dict, Any
import statistics
from dotenv import load_dotenv
load_dotenv()

def calculate_share_of_voice(brand_results: List[Dict[str, Any]], competitors: List[str], brand_aliases: List[str] = None) -> Dict[str, Any]:
    """
    Perform Share of Voice Analysis comparing brand against competitors.
    
    Logic:
    1. Calculate Raw Visibility % for Main Brand (Mentions / Total Prompts * 100).
    2. Calculate Raw Visibility % for each Competitor.
    3. Sum all Visibility percentages to get Total Market Visibility.
    4. Share of Voice = (Brand Visibility / Total Market Visibility) * 100.
    """
    
    # 1. Analyze Main Brand
    brand_name = brand_results[0]['brand_name'] if brand_results else "Unknown"
    brand_metrics = aggregate_brand_metrics(brand_results, brand_name, brand_aliases)
    
    # ✅ FIX: Recalculate Main Brand Average Position dynamically against ALL current competitors
    # This prevents stale position data for the main brand when new competitors are added
    if brand_results and competitors:
        from .scoring_engine import calculate_relative_rank
        
        recalculated_ranks = []
        full_competitor_list = [c for c in competitors if c != brand_name]
        
        for result in brand_results:
            # Only if brand was mentioned originally (score > 0)
            if result['scores']['mention_score'] > 0:
                response_text = result['response']
                # Calculate rank against updated competitor list
                new_rank = calculate_relative_rank(response_text, brand_name, full_competitor_list)
                
                # IMPORTANT: If it's an alias match (where brand name isn't found), rank will be 0.
                # calculate_relative_rank returns 0 if main name not found.
                # However, if it was counted as a mention via Alias, we should probably keep it 0 or exclude it?
                # Per user request: "just want to use allias for brand mentioning ... not anywhere else"
                # So if rank is 0, it contributes nothing to average position (filtered out). This is correct.
                
                if new_rank > 0:
                    recalculated_ranks.append(new_rank)

        # Update brand_metrics with new average if we have valid ranks
        if recalculated_ranks:
            brand_metrics['average_positioning'] = round(statistics.mean(recalculated_ranks), 2)
        # Note: If no valid ranks (e.g. all alias matches), average_positioning stays what aggregate_brand_metrics returned (likely 0) or 0.
    
    # Create list of all brand names for relative ranking context
    all_brand_names = [brand_name] + competitors
    
    # Initialize list with Main Brand
    all_brands = [brand_metrics]
    
    # 2. Analyze Competitors
    for competitor in competitors:
        if competitor == brand_name:
            continue
            
        # Pass all_brand_names so we can rank this competitor against others
        competitor_metrics = analyze_competitor_from_responses(
            brand_results, 
            competitor, 
            all_brand_names
        )
        all_brands.append(competitor_metrics)
    
    # 3. Calculate Total Visibility Mass (e.g., 60 + 70 + 40 = 170)
    # We use 'raw_visibility' which holds the exact mention rate (0-100)
    total_visibility_mass = sum(b['raw_visibility'] for b in all_brands)
    
    # 4. Normalize to get Share of Voice (e.g., 60 / 170)
    if total_visibility_mass > 0:
        for brand in all_brands:
            # Calculate Share
            brand['share_percentage'] = round((brand['raw_visibility'] / total_visibility_mass) * 100, 2)
            
            # OVERWRITE normalized_visibility with the SHARE percentage for storage/display
            # This ensures the final output represents the Share of Voice (Market Share)
            brand['normalized_visibility'] = brand['share_percentage']
    else:
        for brand in all_brands:
            brand['share_percentage'] = 0.0
            brand['normalized_visibility'] = 0.0
    
    # Rank brands by their Share of Voice (now stored in normalized_visibility)
    ranked_brands = sorted(all_brands, key=lambda x: x['normalized_visibility'], reverse=True)
    
    # Add rank information
    for rank, brand in enumerate(ranked_brands, 1):
        brand['rank'] = rank
    
    return {
        'ranked_brands': ranked_brands,
        'total_brands_analyzed': len(ranked_brands),
        'main_brand': brand_name,
        'main_brand_rank': next((b['rank'] for b in ranked_brands if b['brand_name'] == brand_name), 0)
    }

def aggregate_brand_metrics(results: List[Dict[str, Any]], brand_name: str, brand_aliases: List[str] = None) -> Dict[str, Any]:
    """
    Aggregate metrics for the Main Brand.
    """
    if not results:
        return _empty_metrics(brand_name)
    
    total_prompts = len(results)
    
    # Count Mentions
    # Logic: 
    # 1. Existing score > 0 (Main brand logic)
    # 2. OR match any alias (if score was 0)
    
    mentions_count = 0
    if not brand_aliases:
        mentions = [r for r in results if r['scores']['mention_score'] > 0]
        mentions_count = len(mentions)
    else:
        import re
        alias_patterns = [re.compile(re.escape(alias.strip()), re.IGNORECASE) for alias in brand_aliases if alias and alias.strip()]
        
        for result in results:
            # Check existing score first
            if result['scores']['mention_score'] > 0:
                mentions_count += 1
                continue
                
            # Check aliases if main brand not found
            response_text = result['response']
            found_alias = False
            for pattern in alias_patterns:
                if pattern.search(response_text):
                    found_alias = True
                    break
            
            if found_alias:
                mentions_count += 1
                
    total_mentions = mentions_count
    
    # Calculate Raw Visibility (Mention Rate)
    # Example: 6 mentions / 10 prompts = 60.0
    raw_visibility = (total_mentions / total_prompts * 100) if total_prompts > 0 else 0.0
    
    # Average Positioning
    positioning_scores = [r['scores']['average_positioning'] for r in results if r['scores']['average_positioning'] > 0]
    avg_position = statistics.mean(positioning_scores) if positioning_scores else 0
    
    # Weighted Score (Average of individual weighted scores)
    weighted_scores = [r['scores']['weighted_score'] for r in results]
    avg_weighted = statistics.mean(weighted_scores) if weighted_scores else 0
    
    return {
        'brand_name': brand_name,
        'raw_visibility': raw_visibility,          # e.g., 60.0
        'normalized_visibility': raw_visibility,   # Placeholder, will be overwritten by Share calculation
        'average_positioning': round(avg_position, 2),
        'weighted_score': round(avg_weighted, 2),
        'total_mentions': total_mentions,
        'total_prompts': total_prompts,
        'mention_rate': round(raw_visibility, 2)
    }

def analyze_competitor_from_responses(brand_results: List[Dict[str, Any]], competitor_name: str, all_brand_names: List[str] = None) -> Dict[str, Any]:
    """
    Analyze competitor mentions using the same responses.
    """
    import re
    # ✅ Fix: Import correct functions from updated scoring_engine
    from .scoring_engine import (
        calculate_mention_score, 
        calculate_relative_rank,   # Use new relative rank logic
        calculate_richness_score, 
        calculate_keyword_score,
        calculate_weighted_score
    )
    
    competitor_scores = []
    
    for result in brand_results:
        response_text = result['response']
        
        # 1. Calculate Mention (0 or 1)
        mention = calculate_mention_score(response_text, competitor_name)
        
        # 2. Calculate Rank (Positioning)
        # We rank this competitor against all other brands in the list
        if mention > 0 and all_brand_names:
            other_brands = [b for b in all_brand_names if b != competitor_name]
            relative_rank = calculate_relative_rank(response_text, competitor_name, other_brands)
        else:
            relative_rank = 0
            
        # 3. Calculate Position Score (for Weighted Score calculation)
        if relative_rank > 0:
            position_score = max(0, 35 - (relative_rank * 5))
        else:
            position_score = 0
            
        # 4. Other Scores
        richness = calculate_richness_score(response_text, competitor_name)
        keyword = calculate_keyword_score(response_text, competitor_name)
        
        # Calculate Weighted Score
        weighted = calculate_weighted_score(mention, position_score, richness, keyword)
        
        competitor_scores.append({
            'mention_score': mention,
            'average_positioning': relative_rank,
            'weighted_score': weighted
        })
    
    if not competitor_scores:
        return _empty_metrics(competitor_name)

    total_prompts = len(competitor_scores)
    
    # Count Mentions
    mentions = [s for s in competitor_scores if s['mention_score'] > 0]
    total_mentions = len(mentions)
    
    # Calculate Raw Visibility (Mention Rate)
    # Example: 7 mentions / 10 prompts = 70.0
    raw_visibility = (total_mentions / total_prompts * 100) if total_prompts > 0 else 0.0
    
    # Average Positioning
    positioning_scores = [s['average_positioning'] for s in competitor_scores if s['average_positioning'] > 0]
    avg_position = statistics.mean(positioning_scores) if positioning_scores else 0
    
    # Average Weighted Score
    weighted_scores = [s['weighted_score'] for s in competitor_scores]
    avg_weighted = statistics.mean(weighted_scores) if weighted_scores else 0
    
    return {
        'brand_name': competitor_name,
        'raw_visibility': raw_visibility,          # e.g., 70.0
        'normalized_visibility': raw_visibility,   # Placeholder
        'average_positioning': round(avg_position, 2),
        'weighted_score': round(avg_weighted, 2),
        'total_mentions': total_mentions,
        'total_prompts': total_prompts,
        'mention_rate': round(raw_visibility, 2)
    }

def _empty_metrics(brand_name: str) -> Dict[str, Any]:
    return {
        'brand_name': brand_name,
        'raw_visibility': 0.0,
        'normalized_visibility': 0.0,
        'average_positioning': 0,
        'weighted_score': 0,
        'total_mentions': 0,
        'total_prompts': 0,
        'mention_rate': 0
    }


def calculate_llm_specific_metrics(results: List[Dict[str, Any]], llm_name: str) -> Dict[str, Any]:
    """
    Calculate metrics for a specific LLM
    
    Args:
        results: All scoring results
        llm_name: Name of the LLM to analyze
    
    Returns:
        dict: LLM-specific metrics
    """
    
    llm_results = [r for r in results if r.get('llm_name') == llm_name]
    
    if not llm_results:
        return {
            'llm_name': llm_name,
            'total_prompts': 0,
            'avg_normalized_visibility': 0,
            'avg_positioning': 0,
            'avg_weighted_score': 0,
            'mention_rate': 0
        }
    
    mentions = [r for r in llm_results if r['scores']['mention_score'] > 0]
    positioning_scores = [r['scores']['average_positioning'] for r in llm_results if r['scores']['average_positioning'] > 0]
    
    return {
        'llm_name': llm_name,
        'total_prompts': len(llm_results),
        'avg_normalized_visibility': round(statistics.mean([r['scores']['normalized_visibility'] for r in llm_results]), 2),
        'avg_positioning': round(statistics.mean(positioning_scores), 2) if positioning_scores else 0,
        'avg_weighted_score': round(statistics.mean([r['scores']['weighted_score'] for r in llm_results]), 2),
        'mention_rate': round((len(mentions) / len(llm_results)) * 100, 2)
    }

def generate_sov_insights(sov_data: Dict[str, Any]) -> List[str]:
    """
    Generate actionable insights from Share of Voice analysis
    
    Args:
        sov_data: Share of Voice analysis results
    
    Returns:
        list: List of insight strings
    """
    
    insights = []
    ranked_brands = sov_data['ranked_brands']
    main_brand = sov_data['main_brand']
    main_brand_rank = sov_data['main_brand_rank']
    
    # Overall position insight
    if main_brand_rank == 1:
        insights.append(f"🏆 {main_brand} leads in share of voice across all analyzed competitors")
    elif main_brand_rank <= 3:
        insights.append(f"📈 {main_brand} ranks #{main_brand_rank} in share of voice - strong visibility position")
    else:
        insights.append(f"📊 {main_brand} ranks #{main_brand_rank} in share of voice - opportunity for improvement")
    
    # Find main brand data
    main_brand_data = next((b for b in ranked_brands if b['brand_name'] == main_brand), None)
    
    if main_brand_data:
        # Mention rate insight
        if main_brand_data['mention_rate'] > 70:
            insights.append(f"✅ Excellent organic visibility with {main_brand_data['mention_rate']:.1f}% mention rate")
        elif main_brand_data['mention_rate'] > 40:
            insights.append(f"⚠️ Moderate organic visibility with {main_brand_data['mention_rate']:.1f}% mention rate")
        else:
            insights.append(f"🔴 Low organic visibility with {main_brand_data['mention_rate']:.1f}% mention rate - needs SEO/content improvement")
        
        # Positioning insight
        if main_brand_data['average_positioning'] > 0:
            if main_brand_data['average_positioning'] <= 3:
                insights.append(f"🎯 Strong positioning - typically appears in top 3 positions (avg: {main_brand_data['average_positioning']:.1f})")
            else:
                insights.append(f"📍 Average positioning at position {main_brand_data['average_positioning']:.1f} - room for improvement")
    
    # Competitive gap insight
    if len(ranked_brands) > 1:
        top_brand = ranked_brands[0]
        if main_brand_rank > 1:
            gap = top_brand['weighted_score'] - main_brand_data['weighted_score']
            insights.append(f"🎯 Close gap with {top_brand['brand_name']} (leader) - difference of {gap:.1f} points")
    
    return insights