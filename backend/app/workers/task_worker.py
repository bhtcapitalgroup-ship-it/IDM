"""Background task worker — processes queued agent tasks via Redis.

Job lifecycle:
  QUEUED → RUNNING → COMPLETED | FAILED

Each job is a JSON payload in a Redis list. Worker pops from the list,
executes, and stores the result. Failures are logged and retried up to
the task's max_retries limit.

Run: python -m app.workers.task_worker
"""
import asyncio
import json
import uuid
import logging
import traceback
from datetime import datetime, timezone

import redis.asyncio as aioredis
from sqlalchemy import select

from app.config import get_settings
from app.database import async_session
from app.models.task import Task
from app.core.logging import log_action
from app.services.ai_service import ai_service, AIError

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

settings = get_settings()

QUEUE_KEY = "agentic:task_queue"
RESULTS_PREFIX = "agentic:task_result:"
WORKER_POLL_INTERVAL = 2  # seconds


async def enqueue_task(task_id: str, redis_client: aioredis.Redis | None = None):
    """Push a task ID onto the Redis queue for background processing."""
    client = redis_client or aioredis.from_url(settings.redis_url)
    try:
        payload = json.dumps({"task_id": task_id, "queued_at": datetime.now(timezone.utc).isoformat()})
        await client.lpush(QUEUE_KEY, payload)
        logger.info(f"Enqueued task {task_id}")
    finally:
        if not redis_client:
            await client.aclose()


async def get_task_result(task_id: str, redis_client: aioredis.Redis | None = None) -> dict | None:
    """Fetch the stored result for a completed/failed task."""
    client = redis_client or aioredis.from_url(settings.redis_url)
    try:
        raw = await client.get(f"{RESULTS_PREFIX}{task_id}")
        return json.loads(raw) if raw else None
    finally:
        if not redis_client:
            await client.aclose()


async def _execute_task(task: Task) -> dict:
    """Execute a single task. Returns output payload.

    Currently uses AI to generate a response based on the task description.
    This is the extension point where real agent execution would be plugged in.
    """
    prompt = f"""You are a {task.input_payload.get('agent_role_hint', 'specialist')} agent.
Complete this task and provide the deliverable.

Task: {task.title}
Description: {task.description or 'No additional details.'}

Respond with a JSON object containing:
- "status": "done"
- "deliverable": a brief summary of what was produced
- "details": any relevant output or notes
"""

    result = await ai_service.complete_json(
        system_prompt="You are a specialist agent completing an assigned task. Respond with valid JSON.",
        user_prompt=prompt,
    )

    if isinstance(result, AIError):
        return {"status": "error", "error": result.error}

    return result if isinstance(result, dict) else {"status": "done", "raw": str(result)}


async def _process_one(job_payload: str):
    """Process a single job from the queue."""
    try:
        job = json.loads(job_payload)
    except json.JSONDecodeError:
        logger.error(f"Invalid job payload: {job_payload[:200]}")
        return

    task_id = job.get("task_id")
    if not task_id:
        logger.error("Job missing task_id")
        return

    logger.info(f"Processing task {task_id}")

    async with async_session() as db:
        result = await db.execute(select(Task).where(Task.id == uuid.UUID(task_id)))
        task = result.scalar_one_or_none()

        if not task:
            logger.error(f"Task {task_id} not found in database")
            return

        if task.status not in ("assigned", "in_progress"):
            logger.warning(f"Task {task_id} in unexpected status '{task.status}', skipping")
            return

        # Move to in_progress
        task.status = "in_progress"
        await db.flush()
        await log_action(
            db, actor="worker", actor_type="system", action="task_started",
            resource_type="task", resource_id=task_id,
        )

        try:
            output = await _execute_task(task)

            if output.get("status") == "error":
                raise RuntimeError(output.get("error", "Unknown execution error"))

            task.output_payload = output
            task.status = "review" if task.review_required else "completed"
            await db.flush()

            await log_action(
                db, actor="worker", actor_type="system", action="task_completed",
                resource_type="task", resource_id=task_id,
                after_state={"status": task.status},
            )

            # Store result in Redis
            redis = aioredis.from_url(settings.redis_url)
            await redis.set(
                f"{RESULTS_PREFIX}{task_id}",
                json.dumps({"status": task.status, "output": output}),
                ex=86400,  # 24h TTL
            )
            await redis.aclose()

            logger.info(f"Task {task_id} completed → {task.status}")

        except Exception as e:
            task.retry_count += 1
            if task.retry_count >= task.max_retries:
                task.status = "failed"
                logger.error(f"Task {task_id} failed permanently after {task.retry_count} retries: {e}")
            else:
                task.status = "assigned"  # Back to queue
                logger.warning(f"Task {task_id} failed (retry {task.retry_count}/{task.max_retries}): {e}")
                # Re-enqueue for retry
                redis = aioredis.from_url(settings.redis_url)
                await enqueue_task(task_id, redis)
                await redis.aclose()

            task.output_payload = {"error": str(e), "traceback": traceback.format_exc()[-500:]}
            await db.flush()

            await log_action(
                db, actor="worker", actor_type="system",
                action="task_failed" if task.status == "failed" else "task_retry",
                resource_type="task", resource_id=task_id,
                after_state={"status": task.status, "retry_count": task.retry_count, "error": str(e)[:200]},
            )

        await db.commit()


async def run_worker():
    """Main worker loop — pops tasks from Redis and processes them."""
    logger.info(f"Worker starting, polling {QUEUE_KEY} every {WORKER_POLL_INTERVAL}s")
    redis = aioredis.from_url(settings.redis_url)

    try:
        while True:
            job = await redis.rpop(QUEUE_KEY)
            if job:
                await _process_one(job if isinstance(job, str) else job.decode("utf-8"))
            else:
                await asyncio.sleep(WORKER_POLL_INTERVAL)
    except asyncio.CancelledError:
        logger.info("Worker shutting down")
    finally:
        await redis.aclose()


if __name__ == "__main__":
    asyncio.run(run_worker())
