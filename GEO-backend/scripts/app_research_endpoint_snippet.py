
@app.post("/api/analysis/research")
async def conduct_research_endpoint(request: ResearchRequest, user_id: str = Depends(get_current_user)):
    """Conduct deep research to find competitors and industry info"""
    try:
        from services.deep_research import conduct_deep_research
        
        logger.info(f"🔍 Starting deep research for {request.brand_name}...")
        
        # Run deep research (synchronously for now as per user request flow)
        results = conduct_deep_research(
            brand_name=request.brand_name,
            website_url=request.website_url
        )
        
        return {
            "status": "success", 
            "data": results
        }
    except Exception as e:
        logger.error(f"Error in deep research endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
