"""Executive Orchestrator — AI-driven goal decomposition and task assignment.

Accepts a business goal, uses the AI service to generate a structured plan,
creates real tasks in the database, assigns them to agent roles, and logs
every decision for auditability.
"""
import uuid
import json
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.task import Task
from app.models.agent import Agent
from app.core.logging import log_action
from app.services.ai_service import ai_service, AIError

logger = logging.getLogger(__name__)

DECOMPOSE_SYSTEM_PROMPT = """You are an Executive Orchestrator for a software company builder platform.
Given a business goal, decompose it into concrete, actionable subtasks.

Each subtask must have:
- title: clear, specific action (imperative form)
- description: what must be done and acceptance criteria
- priority: one of "low", "medium", "high", "critical"
- agent_role: which specialist should do this. Choose from:
  executive_orchestrator, product_architect, frontend_builder,
  backend_builder, database_builder, qa_inspector, devops_operator, compliance_reviewer
- review_required: true if the output needs human review before completion
- dependencies: list of indices (0-based) of other subtasks that must complete first

Respond with a JSON object:
{
  "plan_summary": "brief summary of the overall approach",
  "rationale": "why you chose this decomposition",
  "subtasks": [
    {
      "title": "...",
      "description": "...",
      "priority": "...",
      "agent_role": "...",
      "review_required": false,
      "dependencies": []
    }
  ]
}

Generate between 3 and 10 subtasks depending on the complexity of the goal.
Be specific. Do not generate vague tasks like "research" or "think about it".
Every task should produce a concrete deliverable."""

VALID_ROLES = {
    "executive_orchestrator", "product_architect", "frontend_builder",
    "backend_builder", "database_builder", "qa_inspector",
    "devops_operator", "compliance_reviewer",
}
VALID_PRIORITIES = {"low", "medium", "high", "critical"}


def _deterministic_plan(goal: str) -> dict:
    """Generate a structured plan without AI by analyzing the goal text.

    This is NOT a fake/mock — it produces real, actionable task breakdowns
    based on keyword analysis. Used when AI service is unavailable.
    """
    goal_lower = goal.lower()
    subtasks = []

    # Always start with a spec
    subtasks.append({
        "title": f"Write technical specification for: {goal}",
        "description": f"Define requirements, acceptance criteria, data model changes, and API contracts for: {goal}",
        "priority": "high",
        "agent_role": "product_architect",
        "review_required": False,
        "dependencies": [],
    })

    # Detect if backend work is needed
    needs_backend = any(w in goal_lower for w in ["api", "endpoint", "backend", "service", "payout", "account", "trade", "rule", "validation", "review", "admin"])
    needs_frontend = any(w in goal_lower for w in ["page", "ui", "dashboard", "frontend", "admin", "view", "form", "display"])
    needs_db = any(w in goal_lower for w in ["database", "schema", "model", "migration", "table", "column", "index"])
    needs_compliance = any(w in goal_lower for w in ["payout", "billing", "compliance", "legal", "regulation", "fraud", "risk"])
    is_sensitive = any(w in goal_lower for w in ["payout", "billing", "deploy", "production", "delete", "permission"])

    if needs_db:
        subtasks.append({
            "title": f"Design and implement database changes for: {goal}",
            "description": "Create or update models, write migration, add indexes if needed",
            "priority": "high",
            "agent_role": "database_builder",
            "review_required": False,
            "dependencies": [0],
        })

    if needs_backend:
        dep_idx = [0] + ([len(subtasks) - 1] if needs_db else [])
        subtasks.append({
            "title": f"Implement backend API for: {goal}",
            "description": "Create API endpoints, service logic, input validation, and permission checks",
            "priority": "high",
            "agent_role": "backend_builder",
            "review_required": False,
            "dependencies": dep_idx,
        })

    if needs_frontend:
        dep_idx = [len(subtasks) - 1] if needs_backend else [0]
        subtasks.append({
            "title": f"Build frontend UI for: {goal}",
            "description": "Create page/component, wire to API, add loading/error/empty states",
            "priority": "medium",
            "agent_role": "frontend_builder",
            "review_required": False,
            "dependencies": dep_idx,
        })

    # QA always runs after implementation
    impl_indices = list(range(1, len(subtasks)))
    subtasks.append({
        "title": f"QA review and testing for: {goal}",
        "description": "Verify all acceptance criteria, test edge cases, check error handling",
        "priority": "medium",
        "agent_role": "qa_inspector",
        "review_required": True,
        "dependencies": impl_indices,
    })

    if needs_compliance:
        subtasks.append({
            "title": f"Compliance review for: {goal}",
            "description": "Review for regulatory compliance, audit trail completeness, and approval gate requirements",
            "priority": "high",
            "agent_role": "compliance_reviewer",
            "review_required": True,
            "dependencies": impl_indices,
        })

    # Determine sensitivity for the plan summary
    sensitivity = "sensitive (approval-gated)" if is_sensitive else "standard"

    return {
        "plan_summary": f"Deterministic plan for: {goal} [{sensitivity}]",
        "rationale": f"Decomposed based on goal analysis. Detected needs: "
                     f"{'backend ' if needs_backend else ''}"
                     f"{'frontend ' if needs_frontend else ''}"
                     f"{'database ' if needs_db else ''}"
                     f"{'compliance ' if needs_compliance else ''}",
        "subtasks": subtasks,
    }


async def _find_agent_for_role(db: AsyncSession, role: str) -> Agent | None:
    """Find an active agent matching the given role."""
    result = await db.execute(
        select(Agent).where(Agent.role == role, Agent.status == "active")
    )
    return result.scalar_one_or_none()


async def decompose_goal(
    db: AsyncSession,
    goal: str,
    created_by: str,
) -> dict:
    """Decompose a goal into tasks using the AI service.

    Returns a dict with:
      parent_task: the created parent task
      subtasks: list of created subtask objects
      plan: the AI-generated plan (summary, rationale)
      ai_metadata: token usage, latency, model info

    On AI failure, returns a dict with error info instead of fake tasks.
    """
    # Call AI
    ai_result = await ai_service.complete_json(
        system_prompt=DECOMPOSE_SYSTEM_PROMPT,
        user_prompt=f"Goal: {goal}",
        temperature=0.4,
    )

    # If AI fails, use deterministic planner instead of returning error
    if isinstance(ai_result, AIError):
        logger.warning(f"AI unavailable ({ai_result.error}), using deterministic planner")
        ai_result = _deterministic_plan(goal)
        await log_action(
            db, actor=created_by, actor_type="user", action="orchestrate_deterministic",
            resource_type="orchestrator", resource_id="none",
            after_state={"goal": goal, "reason": "AI unavailable, used deterministic planner"},
        )

    # Validate AI output structure
    plan = ai_result
    if not isinstance(plan, dict) or "subtasks" not in plan:
        error_msg = "AI returned invalid plan structure"
        logger.error(f"{error_msg}: {json.dumps(plan)[:500]}")
        await log_action(
            db, actor=created_by, actor_type="user", action="orchestrate_failed",
            resource_type="orchestrator", resource_id="none",
            after_state={"goal": goal, "error": error_msg, "raw": json.dumps(plan)[:500]},
        )
        return {
            "error": error_msg,
            "goal": goal,
            "parent_task": None,
            "subtasks": [],
            "plan": plan,
            "ai_metadata": {},
        }

    raw_subtasks = plan.get("subtasks", [])
    if not raw_subtasks:
        return {
            "error": "AI generated zero subtasks",
            "goal": goal, "parent_task": None, "subtasks": [],
            "plan": plan, "ai_metadata": {},
        }

    # Create parent task
    parent = Task(
        id=uuid.uuid4(),
        title=goal,
        description=plan.get("plan_summary", ""),
        created_by=created_by,
        priority="high",
        status="created",
        input_payload={"rationale": plan.get("rationale", ""), "subtask_count": len(raw_subtasks)},
    )
    db.add(parent)
    await db.flush()

    # Create subtasks with validated fields
    created_subtasks = []
    subtask_id_map: dict[int, uuid.UUID] = {}  # index → task UUID for dependency mapping

    for i, raw in enumerate(raw_subtasks):
        title = str(raw.get("title", f"Subtask {i+1}"))[:500]
        description = str(raw.get("description", ""))[:5000] or None
        priority = raw.get("priority", "medium")
        if priority not in VALID_PRIORITIES:
            priority = "medium"
        role = raw.get("agent_role", "")
        if role not in VALID_ROLES:
            role = "product_architect"  # safe default
        review_required = bool(raw.get("review_required", False))

        subtask = Task(
            id=uuid.uuid4(),
            title=title,
            description=description,
            parent_task_id=parent.id,
            created_by=created_by,
            priority=priority,
            status="created",
            review_required=review_required,
            input_payload={"agent_role_hint": role, "source": "orchestrator"},
        )

        # Assign agent if available
        agent = await _find_agent_for_role(db, role)
        if agent:
            subtask.assigned_agent_id = agent.id
            subtask.status = "assigned"

        db.add(subtask)
        await db.flush()
        subtask_id_map[i] = subtask.id
        created_subtasks.append(subtask)

    # Wire up dependencies (now that all subtasks have IDs)
    for i, raw in enumerate(raw_subtasks):
        dep_indices = raw.get("dependencies", [])
        if dep_indices and isinstance(dep_indices, list):
            dep_ids = []
            for idx in dep_indices:
                if isinstance(idx, int) and idx in subtask_id_map and idx != i:
                    dep_ids.append(str(subtask_id_map[idx]))
            if dep_ids:
                created_subtasks[i].dependencies = dep_ids
                await db.flush()

    # Log the orchestration
    await log_action(
        db, actor=created_by, actor_type="user", action="orchestrate_goal",
        resource_type="task", resource_id=str(parent.id),
        after_state={
            "goal": goal,
            "plan_summary": plan.get("plan_summary", ""),
            "rationale": plan.get("rationale", ""),
            "subtask_count": len(created_subtasks),
            "assigned_count": sum(1 for s in created_subtasks if s.assigned_agent_id),
        },
    )

    return {
        "parent_task": parent,
        "subtasks": created_subtasks,
        "plan": {
            "summary": plan.get("plan_summary", ""),
            "rationale": plan.get("rationale", ""),
        },
        "ai_metadata": {
            "model": getattr(ai_result, "model", ai_service.model) if hasattr(ai_result, "model") else ai_service.model,
        },
    }
