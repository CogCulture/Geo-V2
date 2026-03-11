import os
import sys
from dotenv import load_dotenv

# Add parent directory to path to import services
sys.path.append(os.path.join(os.getcwd(), 'services'))

load_dotenv()

from database_manager import get_brand_citation_repository, get_all_sessions

def verify():
    print("Starting Citation Repository Verification...")
    
    # 1. Get all sessions to find a brand with multiple sessions
    sessions = get_all_sessions()
    brand_counts = {}
    for s in sessions:
        brand = s['brand_name']
        brand_counts[brand] = brand_counts.get(brand, 0) + 1
    
    multi_session_brands = [b for b, count in brand_counts.items() if count > 1]
    
    if not multi_session_brands:
        print("BRAND INFO: No brands with multiple sessions found. Testing with latest brand.")
        if not sessions:
            print("ERROR: No sessions found at all. Cannot verify.")
            return
        test_brand = sessions[0]['brand_name']
    else:
        test_brand = multi_session_brands[0]
        print(f"SUCCESS: Found candidate brand for cross-session testing: '{test_brand}' ({brand_counts[test_brand]} sessions)")

    # 2. Get user_id (needed for the repository call)
    # We'll take it from one of the sessions for this brand
    sessions_for_brand = [s for s in sessions if s['brand_name'] == test_brand]
    test_session_id = sessions_for_brand[0]['session_id']
    
    from database_manager import supabase
    session_data = supabase.table('analysis_sessions').select('user_id').eq('session_id', test_session_id).execute()
    if not session_data.data:
        print("ERROR: Could not retrieve user_id for session.")
        return
    user_id = session_data.data[0]['user_id']
    
    # 3. Call the new repository function
    print(f"INFO: Aggregating citations for brand: '{test_brand}'...")
    results = get_brand_citation_repository(test_brand, user_id)
    
    citations = results.get('citations', [])
    total_count = results.get('total_citations', 0)
    
    print(f"SUCCESS: Result: Found {len(citations)} unique domains with a total of {total_count} citations.")
    
    if len(citations) > 0:
        print("\nTop 5 Citation Domains:")
        for i, cit in enumerate(citations[:5]):
            print(f"{i+1}. {cit['domain']}: {cit['count']} citations ({cit['percentage']}%)")
            # print(f"   URLs: {len(cit['urls'])}")
    else:
        print("INFO: No citations found for this brand yet.")

    print("\nVerification complete.")

if __name__ == "__main__":
    verify()
