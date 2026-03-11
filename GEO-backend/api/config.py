PLAN_LIMITS = {
    "free": {"max_projects": 1, "max_prompts_per_project": 2}, # Default for unpaid users
    "lite plan": {"max_projects": 2, "max_prompts_per_project": 5},
    "growth plan": {"max_projects": 4, "max_prompts_per_project": 10},
    "custom plan": {"max_projects": 8, "max_prompts_per_project": 10},
    "pro plan": {"max_projects": 8, "max_prompts_per_project": 10}, # Alias for legacy
    "enterprise": {"max_projects": 100, "max_prompts_per_project": 100}
}
