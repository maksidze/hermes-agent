"""Service-gated multi-model orchestration. Absent from disabled session schemas."""

from tools.registry import no_cache_check_fn, registry


@no_cache_check_fn
def check_requirements():
    from agent.orchestration.config import enabled
    return enabled()


def handle(args, **kwargs):
    from agent.orchestration.tool import handle as run
    return run(args, **kwargs)


_TASK = {
    "type": "object", "required": ["goal"], "additionalProperties": False,
    "properties": {
        "goal": {"type": "string", "description": "Self-contained goal and acceptance criteria."},
        "context": {"type": "string", "description": "Constraints, relevant files and verified facts."},
        "route": {"type": "string", "description": "Configured route, e.g. general, coding, research or vision."},
        "level": {"type": "string", "enum": ["auto", "fast", "balanced", "deep"]},
        "specialization": {"type": "string", "description": "Configured expertise category, independent of model capacity."},
        "specialization_reason": {"type": "string", "description": "Concrete reason this task needs the selected specialization."},
        "output_schema": {"type": "object", "description": "JSON Schema for the final result."},
        "images": {"type": "array", "items": {"type": "string"}, "maxItems": 8},
        "attachments": {"type": "array", "items": {"type": "object", "required": ["type"],
                        "properties": {"type": {"type": "string"}}, "additionalProperties": True},
                        "description": "Admitted message content parts (text, image, audio, file or video), preserved for every worker."},
    },
}

registry.register(
    name="orchestrate_task", toolset="orchestration",
    schema={
        "name": "orchestrate_task",
        "description": "Use configured execution profiles for work needing another model. Do simple work inline. "
                       "Choose the minimum sufficient level; select deep directly for complex architecture or analysis. "
                       "Results are checked and may be repaired or escalated within configured budgets. "
                       "Use one goal or tasks with independent goals. Background returns through the normal completion queue. "
                       "Do not retry external side effects without checking their state.",
        "parameters": {"type": "object", "additionalProperties": False, "properties": {
            **_TASK["properties"], "tasks": {"type": "array", "items": _TASK},
            "background": {"type": "boolean"},
            "plan": {"type": "boolean", "description": "Plan with the architect, then execute and verify dependent subtasks."},
        }},
    }, handler=handle, check_fn=check_requirements,
)
