import os

db_manager_file = r"c:\Users\Cog\Downloads\GEO-V2\GEO(Server-Test)\GEO-backend\services\database_manager.py"
db_dir = r"c:\Users\Cog\Downloads\GEO-V2\GEO(Server-Test)\GEO-backend\db"

with open(db_manager_file, "r", encoding="utf-8") as f:
    lines = f.readlines()

os.makedirs(db_dir, exist_ok=True)
with open(os.path.join(db_dir, "__init__.py"), "w", encoding="utf-8") as f:
    f.write("")

# Common imports to add at the top of everything
common_imports = lines[0:15]  # The first 15 lines contain imports
supabase_client_lines = lines[15:26] 

def write_module(filename, line_ranges):
    # line_ranges is a list of tuples (start_line_1_index, end_line_1_index_inclusive)
    content = []
    content.extend(common_imports)
    content.append("from db.client import supabase\n\n")
    
    for start, end in line_ranges:
        content.extend(lines[start-1:end])
    
    filepath = os.path.join(db_dir, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        f.writelines(content)
    print(f"Created {filename}")

# db/client.py
with open(os.path.join(db_dir, "client.py"), "w", encoding="utf-8") as f:
    f.writelines(common_imports)
    f.writelines(supabase_client_lines)
    f.write("\n")
    f.writelines(lines[64:223])  # init_database
    f.write("\n")
    f.writelines(lines[1617:1621])  # Call init_database()
print("Created client.py")

# db/sessions.py
write_module("sessions.py", [
    (27, 63),       # session state/metadata
    (225, 232),     # create_session_id/create_prompt_id
    (234, 267),     # save_session
    (1359, 1365),   # get_user_sessions
    (1367, 1441),   # duplicate_...
    (426, 435),     # get_all_sessions
    (965, 974),     # get_recent_sessions
    (770, 777),     # get_all_unique_brands
    (779, 788),     # get_recent_sessions_by_brand
    (1598, 1617),   # replace_session_competitors, clear_session_metrics
])

# db/results.py
write_module("results.py", [
    (269, 313),   # save_llm_response, save_scoring_result
    (315, 330),   # save_competitors
    (332, 349),   # save_share_of_voice
    (351, 383),   # save_brand_score_summary
    (385, 424),   # get_session_results
    (437, 513),   # get_brand_visibility_history
    (515, 548),   # get_llm_aggregate_scores
    (550, 585),   # get/save prompts
    (587, 768),   # get_session_results_aggregated
    (790, 799),   # get_saved_prompts_for_analysis
    (801, 894),   # get_visibility_history_for_same_prompts
    (896, 963),   # get_product_specific_visibility_history
])

# db/cohorts.py
write_module("cohorts.py", [
    (976, 1209),  # save_cohorts to get_selected_prompts
])

# db/users.py
write_module("users.py", [
    (1210, 1252), # signup_user to get_user_by_id
])

# db/payments.py
write_module("payments.py", [
    (1255, 1356), # activate_user_subscription to get_subscription_status
])

# db/projects.py
write_module("projects.py", [
    (1442, 1580), # project management to monitored entities
    (1581, 1597), # project dashboard metrics
])

# db/citations.py
write_module("citations.py", [
    (1622, 1832), # detailed citation analytics to previous sov data
])

# Rewrite database_manager.py
new_db_manager = []
new_db_manager.append('"""\nThis file is now a central exporter for all db modules.\nIt exists to maintain backwards compatibility for existing imports.\n"""\n')
new_db_manager.append('from db.client import *\n')
new_db_manager.append('from db.sessions import *\n')
new_db_manager.append('from db.results import *\n')
new_db_manager.append('from db.cohorts import *\n')
new_db_manager.append('from db.users import *\n')
new_db_manager.append('from db.payments import *\n')
new_db_manager.append('from db.projects import *\n')
new_db_manager.append('from db.citations import *\n')

with open(db_manager_file, "w", encoding="utf-8") as f:
    f.writelines(new_db_manager)

print("Updated database_manager.py")
