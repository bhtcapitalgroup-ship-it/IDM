"""Seed script to populate initial agents, tools, and admin user.

Run: cd backend && python -m app.seed
"""
import asyncio
import sys
import os
import uuid

# Ensure the backend directory is on the path when run directly
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import async_session
from app.models.agent import Agent
from app.models.tool import Tool
from app.models.user import User
from app.core.auth import hash_password
from sqlalchemy import select

DEFAULT_AGENTS = [
    {
        "name": "Executive Orchestrator",
        "role": "executive_orchestrator",
        "type": "manager",
        "description": "Top-level agent that decomposes goals into tasks, assigns specialist agents, and tracks overall progress.",
        "permissions": {"create_task": True, "assign_task": True, "read_all": True, "manage_workflow": True},
        "tools": ["task_planner", "agent_selector", "status_tracker"],
        "memory_scope": "global",
        "creation_source": "system",
    },
    {
        "name": "Product Architect",
        "role": "product_architect",
        "type": "specialist",
        "description": "Defines features, writes specs, reviews designs, and creates technical architecture documents.",
        "permissions": {"create_task": True, "read_specs": True, "write_specs": True},
        "tools": ["spec_writer", "schema_designer"],
        "memory_scope": "role",
        "creation_source": "system",
    },
    {
        "name": "Frontend Builder",
        "role": "frontend_builder",
        "type": "specialist",
        "description": "Implements UI components, pages, layouts, and frontend business logic.",
        "permissions": {"write_frontend": True, "read_specs": True},
        "tools": ["code_writer", "component_generator"],
        "memory_scope": "task",
        "creation_source": "system",
    },
    {
        "name": "Backend Builder",
        "role": "backend_builder",
        "type": "specialist",
        "description": "Implements APIs, services, business logic, and backend integrations.",
        "permissions": {"write_backend": True, "read_specs": True},
        "tools": ["code_writer", "api_generator"],
        "memory_scope": "task",
        "creation_source": "system",
    },
    {
        "name": "Database Builder",
        "role": "database_builder",
        "type": "specialist",
        "description": "Designs schemas, writes migrations, optimizes queries, and manages data models.",
        "permissions": {"write_db": True, "read_specs": True},
        "tools": ["migration_generator", "query_optimizer"],
        "memory_scope": "task",
        "creation_source": "system",
    },
    {
        "name": "QA Inspector",
        "role": "qa_inspector",
        "type": "specialist",
        "description": "Tests features, validates outputs, reports bugs, and ensures quality standards.",
        "permissions": {"read_all": True, "create_task": True},
        "tools": ["test_runner", "validator"],
        "memory_scope": "task",
        "creation_source": "system",
    },
    {
        "name": "DevOps Operator",
        "role": "devops_operator",
        "type": "specialist",
        "description": "Manages infrastructure, CI/CD pipelines, deployments, and monitoring.",
        "permissions": {"read_infra": True, "request_deploy": True},
        "tools": ["deploy_tool", "infra_manager"],
        "memory_scope": "role",
        "creation_source": "system",
    },
    {
        "name": "Compliance Reviewer",
        "role": "compliance_reviewer",
        "type": "specialist",
        "description": "Reviews legal text, compliance requirements, risk assessments, and regulatory adherence.",
        "permissions": {"read_all": True, "flag_issues": True},
        "tools": ["compliance_checker", "risk_assessor"],
        "memory_scope": "role",
        "creation_source": "system",
    },
]

DEFAULT_TOOLS = [
    {
        "name": "task_planner",
        "description": "Decomposes high-level goals into structured task hierarchies",
        "allowed_roles": ["executive_orchestrator"],
        "permission_level": "standard",
    },
    {
        "name": "agent_selector",
        "description": "Selects the best agent for a given task based on role and availability",
        "allowed_roles": ["executive_orchestrator"],
        "permission_level": "standard",
    },
    {
        "name": "status_tracker",
        "description": "Monitors and reports on task progress across all agents",
        "allowed_roles": ["executive_orchestrator"],
        "permission_level": "standard",
    },
    {
        "name": "code_writer",
        "description": "Generates code based on specifications and requirements",
        "allowed_roles": ["frontend_builder", "backend_builder"],
        "permission_level": "standard",
    },
    {
        "name": "spec_writer",
        "description": "Generates technical specifications and design documents",
        "allowed_roles": ["product_architect"],
        "permission_level": "standard",
    },
    {
        "name": "schema_designer",
        "description": "Designs database schemas and data models",
        "allowed_roles": ["product_architect", "database_builder"],
        "permission_level": "standard",
    },
    {
        "name": "component_generator",
        "description": "Generates UI components from design specifications",
        "allowed_roles": ["frontend_builder"],
        "permission_level": "standard",
    },
    {
        "name": "api_generator",
        "description": "Generates API endpoints and service scaffolding",
        "allowed_roles": ["backend_builder"],
        "permission_level": "standard",
    },
    {
        "name": "migration_generator",
        "description": "Generates database migration scripts",
        "allowed_roles": ["database_builder"],
        "permission_level": "standard",
    },
    {
        "name": "query_optimizer",
        "description": "Analyzes and optimizes database queries",
        "allowed_roles": ["database_builder"],
        "permission_level": "standard",
    },
    {
        "name": "test_runner",
        "description": "Runs test suites and reports results",
        "allowed_roles": ["qa_inspector"],
        "permission_level": "standard",
    },
    {
        "name": "validator",
        "description": "Validates outputs against specifications and quality criteria",
        "allowed_roles": ["qa_inspector"],
        "permission_level": "standard",
    },
    {
        "name": "deploy_tool",
        "description": "Executes deployment pipelines to target environments",
        "allowed_roles": ["devops_operator"],
        "permission_level": "elevated",
        "requires_approval": True,
    },
    {
        "name": "infra_manager",
        "description": "Manages cloud infrastructure and configuration",
        "allowed_roles": ["devops_operator"],
        "permission_level": "elevated",
        "requires_approval": True,
    },
    {
        "name": "compliance_checker",
        "description": "Validates content against compliance rules and regulations",
        "allowed_roles": ["compliance_reviewer"],
        "permission_level": "standard",
    },
    {
        "name": "risk_assessor",
        "description": "Assesses risk levels for proposed changes and actions",
        "allowed_roles": ["compliance_reviewer"],
        "permission_level": "standard",
    },
]


async def seed():
    try:
        async with async_session() as session:
            # Seed admin user
            result = await session.execute(select(User).where(User.email == "admin@agentic.dev"))
            if not result.scalar_one_or_none():
                session.add(User(
                    id=uuid.uuid4(),
                    email="admin@agentic.dev",
                    hashed_password=hash_password("admin123"),
                    full_name="System Admin",
                    role="admin",
                ))
                print("[+] Created admin user: admin@agentic.dev / admin123")
            else:
                print("[=] Admin user already exists")

            # Seed agents
            created_agents = 0
            for agent_data in DEFAULT_AGENTS:
                result = await session.execute(select(Agent).where(Agent.role == agent_data["role"]))
                if not result.scalar_one_or_none():
                    session.add(Agent(id=uuid.uuid4(), **agent_data))
                    created_agents += 1
                    print(f"[+] Created agent: {agent_data['name']}")
            if created_agents == 0:
                print(f"[=] All {len(DEFAULT_AGENTS)} agents already exist")

            # Seed tools
            created_tools = 0
            for tool_data in DEFAULT_TOOLS:
                result = await session.execute(select(Tool).where(Tool.name == tool_data["name"]))
                if not result.scalar_one_or_none():
                    session.add(Tool(id=uuid.uuid4(), **tool_data))
                    created_tools += 1
                    print(f"[+] Created tool: {tool_data['name']}")
            if created_tools == 0:
                print(f"[=] All {len(DEFAULT_TOOLS)} tools already exist")

            await session.commit()
            print(f"\nSeed complete: {created_agents} agents, {created_tools} tools")

    except Exception as e:
        print(f"\n[!] Seed failed: {e}")
        print("    Make sure PostgreSQL is running and the database exists.")
        print("    Run: docker compose up -d && ./scripts/migrate.sh")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(seed())
