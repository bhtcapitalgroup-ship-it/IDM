from fastapi import HTTPException, status

# Human user roles and their permissions
ROLE_PERMISSIONS = {
    "admin": ["*"],
    "operator": [
        "read_agents", "create_agents", "update_agents", "delete_agents",
        "read_tasks", "create_tasks", "update_tasks",
        "read_approvals", "create_approvals",
        "read_prompts", "create_prompts", "update_prompts",
        "read_tools", "create_tools", "update_tools",
    ],
    "reviewer": [
        "read_agents", "read_tasks",
        "read_approvals", "review_approvals",
        "read_prompts", "read_tools",
    ],
    "viewer": ["read_agents", "read_tasks", "read_approvals", "read_prompts", "read_tools"],
}

# Agent role permissions (what agents are allowed to do)
AGENT_ROLE_PERMISSIONS = {
    "executive_orchestrator": ["create_task", "assign_task", "read_all", "manage_workflow"],
    "product_architect": ["create_task", "read_specs", "write_specs"],
    "frontend_builder": ["write_frontend", "read_specs"],
    "backend_builder": ["write_backend", "read_specs"],
    "database_builder": ["write_db", "read_specs"],
    "qa_inspector": ["read_all", "create_task", "run_tests"],
    "devops_operator": ["read_infra", "request_deploy"],
    "compliance_reviewer": ["read_all", "flag_issues"],
}

APPROVAL_REQUIRED_ACTIONS = [
    "production_deployment",
    "billing_change",
    "payout_change",
    "legal_text_change",
    "destructive_action",
    "permission_escalation",
    "agent_creation_elevated",
]


def check_permission(user_role: str, required_permission: str):
    perms = ROLE_PERMISSIONS.get(user_role, [])
    if "*" not in perms and required_permission not in perms:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Role '{user_role}' lacks permission '{required_permission}'",
        )


def check_agent_permission(agent_role: str, required_permission: str) -> bool:
    perms = AGENT_ROLE_PERMISSIONS.get(agent_role, [])
    return "read_all" in perms or required_permission in perms


def requires_approval(action_type: str) -> bool:
    return action_type in APPROVAL_REQUIRED_ACTIONS
