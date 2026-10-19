"""Async workflow orchestration engine with parallel DAG scheduling, retries, and persistence."""

import asyncio
import os
import random
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Set
from flowforge.actions.base import ActionContext, ActionRegistry, registry as default_registry
from flowforge.core.expression import ExpressionEvaluator
from flowforge.core.graph import WorkflowGraph
from flowforge.core.models import (
    RetryPolicy,
    StepDefinition,
    StepRun,
    StepStatus,
    WorkflowDefinition,
    WorkflowRun,
    WorkflowStatus,
)
from flowforge.engine.events import EngineEvent, EventBus, EventType
from flowforge.storage.base import BaseStorage
from flowforge.storage.memory import MemoryStorage
from flowforge.utils.logger import logger


class WorkflowEngine:
    """Async engine executing DAG workflows with concurrency control, retries, and state persistence."""

    def __init__(
        self,
        storage: Optional[BaseStorage] = None,
        action_registry: Optional[ActionRegistry] = None,
    ) -> None:
        self.storage = storage or MemoryStorage()
        self.registry = action_registry or default_registry
        self.evaluator = ExpressionEvaluator()
        self.event_bus = EventBus()

    async def execute(
        self,
        workflow: WorkflowDefinition,
        trigger_type: str = "manual",
        trigger_payload: Optional[Dict[str, Any]] = None,
        initial_context: Optional[Dict[str, Any]] = None,
    ) -> WorkflowRun:
        """Execute a workflow to completion asynchronously."""
        run_id = f"run_{uuid.uuid4().hex[:12]}"
        trigger_payload = trigger_payload or {}

        # 1. Initialize execution context
        merged_env = {**os.environ, **workflow.env}
        context: Dict[str, Any] = {
            "workflow": {
                "id": workflow.id,
                "name": workflow.name,
                "version": workflow.version,
            },
            "run_id": run_id,
            "env": merged_env,
            "trigger": {
                "type": trigger_type,
                "payload": trigger_payload,
            },
            "steps": {},
        }
        if initial_context:
            context.update(initial_context)

        # 2. Instantiate and persist WorkflowRun
        run = WorkflowRun(
            run_id=run_id,
            workflow_id=workflow.id,
            status=WorkflowStatus.RUNNING,
            trigger_type=trigger_type,
            trigger_payload=trigger_payload,
            context=context,
        )
        self.storage.create_run(run)

        await self.event_bus.emit(
            EngineEvent(
                event_type=EventType.WORKFLOW_STARTED,
                workflow_id=workflow.id,
                run_id=run_id,
                status=WorkflowStatus.RUNNING.value,
            )
        )

        # 3. Build graph and scheduler state
        graph = WorkflowGraph(workflow)
        step_definitions: Dict[str, StepDefinition] = {s.id: s for s in workflow.steps}

        pending_step_ids: Set[str] = set(step_definitions.keys())
        running_tasks: Dict[str, asyncio.Task] = {}
        completed_step_ids: Set[str] = set()
        failed_step_ids: Set[str] = set()
        skipped_step_ids: Set[str] = set()

        semaphore = asyncio.Semaphore(workflow.concurrency)

        start_time = time.perf_counter()

        async def _execute_single_step(step: StepDefinition) -> StepRun:
            """Execute a single step with retry policy and timeouts."""
            step_run = StepRun(step_id=step.id, run_id=run_id)
            step_run.mark_started()
            run.step_runs[step.id] = step_run
            self.storage.save_step_run(step_run)

            await self.event_bus.emit(
                EngineEvent(
                    event_type=EventType.STEP_STARTED,
                    workflow_id=workflow.id,
                    run_id=run_id,
                    step_id=step.id,
                    status=StepStatus.RUNNING.value,
                )
            )

            # Check condition expression
            if step.when:
                should_run = self.evaluator.evaluate_condition(step.when, context)
                if not should_run:
                    step_run.mark_skipped(f"Condition '{step.when}' evaluated to False")
                    self.storage.save_step_run(step_run)
                    await self.event_bus.emit(
                        EngineEvent(
                            event_type=EventType.STEP_SKIPPED,
                            workflow_id=workflow.id,
                            run_id=run_id,
                            step_id=step.id,
                            status=StepStatus.SKIPPED.value,
                        )
                    )
                    return step_run

            action_cls = self.registry.get(step.action)
            if not action_cls:
                step_run.mark_failed(f"Unregistered action type: '{step.action}'")
                self.storage.save_step_run(step_run)
                await self.event_bus.emit(
                    EngineEvent(
                        event_type=EventType.STEP_FAILED,
                        workflow_id=workflow.id,
                        run_id=run_id,
                        step_id=step.id,
                        status=StepStatus.FAILED.value,
                        error=step_run.error,
                    )
                )
                return step_run

            action_instance = action_cls()
            retry_policy = step.retry or RetryPolicy(max_attempts=1)
            max_attempts = retry_policy.max_attempts
            delay = retry_policy.initial_delay

            last_error: Optional[str] = None

            for attempt in range(1, max_attempts + 1):
                step_run.attempt = attempt

                try:
                    # Dynamically evaluate step parameters against current context
                    resolved_params = self.evaluator.evaluate(step.with_params, context)
                    step_run.input_data = resolved_params

                    act_ctx = ActionContext(
                        step_id=step.id,
                        run_id=run_id,
                        workflow_id=workflow.id,
                        context=context,
                    )

                    async with semaphore:
                        if step.timeout:
                            res = await asyncio.wait_for(
                                action_instance.execute(resolved_params, act_ctx),
                                timeout=step.timeout,
                            )
                        else:
                            res = await action_instance.execute(resolved_params, act_ctx)

                    step_run.logs.extend(res.logs)

                    if res.success:
                        step_run.mark_success(res.output)
                        self.storage.save_step_run(step_run)
                        await self.event_bus.emit(
                            EngineEvent(
                                event_type=EventType.STEP_COMPLETED,
                                workflow_id=workflow.id,
                                run_id=run_id,
                                step_id=step.id,
                                status=StepStatus.SUCCESS.value,
                                data={"output": res.output},
                            )
                        )
                        return step_run
                    else:
                        last_error = res.error or "Action returned failure"

                except asyncio.TimeoutError:
                    last_error = f"Step execution timed out after {step.timeout}s"
                    step_run.logs.append(last_error)
                except Exception as ex:
                    last_error = f"Unhandled exception: {str(ex)}"
                    step_run.logs.append(last_error)

                # Retry backoff if attempts remain
                if attempt < max_attempts:
                    jitter = random.uniform(0.1, 0.5) if retry_policy.jitter else 0.0
                    sleep_time = min(delay, retry_policy.max_delay) + jitter
                    step_run.logs.append(
                        f"Attempt {attempt}/{max_attempts} failed ({last_error}). Retrying in {sleep_time:.2f}s..."
                    )
                    await self.event_bus.emit(
                        EngineEvent(
                            event_type=EventType.STEP_RETRYING,
                            workflow_id=workflow.id,
                            run_id=run_id,
                            step_id=step.id,
                            data={"attempt": attempt, "next_delay": sleep_time},
                            error=last_error,
                        )
                    )
                    await asyncio.sleep(sleep_time)
                    delay *= retry_policy.backoff_multiplier

            # If all attempts exhausted
            step_run.mark_failed(last_error or "All retry attempts failed")
            self.storage.save_step_run(step_run)
            await self.event_bus.emit(
                EngineEvent(
                    event_type=EventType.STEP_FAILED,
                    workflow_id=workflow.id,
                    run_id=run_id,
                    step_id=step.id,
                    status=StepStatus.FAILED.value,
                    error=step_run.error,
                )
            )
            return step_run

        try:
            # 4. Main DAG scheduling loop
            while pending_step_ids or running_tasks:
                # Find steps ready to schedule
                ready_to_launch: Set[str] = set()
                steps_to_skip: Set[str] = set()

                for sid in list(pending_step_ids):
                    prereqs = graph.get_prerequisites(sid)
                    all_prereqs_finished = prereqs.issubset(
                        completed_step_ids | failed_step_ids | skipped_step_ids
                    )

                    if all_prereqs_finished:
                        # Check if any prerequisite failed
                        failed_prereqs = prereqs.intersection(failed_step_ids)
                        step_def = step_definitions[sid]

                        if failed_prereqs and not step_def.continue_on_error:
                            steps_to_skip.add(sid)
                        else:
                            ready_to_launch.add(sid)

                # Process skipped steps
                for sid in steps_to_skip:
                    pending_step_ids.remove(sid)
                    skipped_step_ids.add(sid)
                    sr = StepRun(step_id=sid, run_id=run_id)
                    sr.mark_skipped("Skipped due to upstream step failure")
                    run.step_runs[sid] = sr
                    self.storage.save_step_run(sr)
                    context["steps"][sid] = {
                        "status": StepStatus.SKIPPED.value,
                        "output": None,
                        "error": sr.error,
                    }
                    await self.event_bus.emit(
                        EngineEvent(
                            event_type=EventType.STEP_SKIPPED,
                            workflow_id=workflow.id,
                            run_id=run_id,
                            step_id=sid,
                            status=StepStatus.SKIPPED.value,
                        )
                    )

                # Launch ready steps
                for sid in ready_to_launch:
                    pending_step_ids.remove(sid)
                    task = asyncio.create_task(
                        _execute_single_step(step_definitions[sid]),
                        name=f"step_{sid}_{run_id}",
                    )
                    running_tasks[sid] = task

                if not running_tasks:
                    break

                # Await at least one step task to finish
                done, _ = await asyncio.wait(
                    running_tasks.values(), return_when=asyncio.FIRST_COMPLETED
                )

                # Collect completed tasks
                finished_step_ids = [
                    sid for sid, task in running_tasks.items() if task in done
                ]

                for sid in finished_step_ids:
                    task = running_tasks.pop(sid)
                    step_run: StepRun = await task
                    run.step_runs[sid] = step_run

                    # Update context with output
                    context["steps"][sid] = {
                        "status": step_run.status.value,
                        "output": step_run.output_data,
                        "error": step_run.error,
                    }

                    if step_run.status == StepStatus.SUCCESS:
                        completed_step_ids.add(sid)
                    elif step_run.status == StepStatus.SKIPPED:
                        skipped_step_ids.add(sid)
                    else:
                        failed_step_ids.add(sid)

            # 5. Determine overall workflow completion status
            total_duration_ms = (time.perf_counter() - start_time) * 1000.0
            run.duration_ms = round(total_duration_ms, 2)
            run.completed_at = datetime.now(timezone.utc)
            run.context = context

            if failed_step_ids:
                has_critical_failure = False
                for sid in failed_step_ids:
                    if not step_definitions[sid].continue_on_error:
                        has_critical_failure = True
                        break

                if has_critical_failure:
                    run.status = WorkflowStatus.FAILED
                    run.error = f"Steps failed: {sorted(list(failed_step_ids))}"
                else:
                    run.status = WorkflowStatus.PARTIALLY_FAILED
            else:
                run.status = WorkflowStatus.SUCCESS

            self.storage.update_run(run)

            await self.event_bus.emit(
                EngineEvent(
                    event_type=(
                        EventType.WORKFLOW_COMPLETED
                        if run.status in (WorkflowStatus.SUCCESS, WorkflowStatus.PARTIALLY_FAILED)
                        else EventType.WORKFLOW_FAILED
                    ),
                    workflow_id=workflow.id,
                    run_id=run_id,
                    status=run.status.value,
                    error=run.error,
                )
            )

            return run

        except Exception as e:
            logger.exception("Fatal workflow engine failure: %s", e)
            run.mark_failed(f"Engine exception: {str(e)}")
            self.storage.update_run(run)
            return run
