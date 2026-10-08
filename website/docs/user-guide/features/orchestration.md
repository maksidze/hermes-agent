---
title: Multi-model orchestration
sidebar_label: Model orchestration
---

# Multi-model orchestration

Orchestration is an optional fork feature. The main Hermes agent continues to answer
simple questions, plan work and aggregate results. Its `orchestrate_task` tool can
delegate a task to a configured execution profile, verify the result, repair it on
the same profile, and follow a bounded LangGraph workflow.
When orchestration is enabled, every user message starts this workflow. When it is
disabled, the chat model handles the message normally.

## Graph workflows

The engine uses the optional `orchestration` dependency extra. Provision it through
Hermes PM: `python -c "from pm import sync_venv; sync_venv(['orchestration'], explicit=True)"`.
The development launcher in this fork uses the prepared `graph-env` on drive D.

**Settings → Orchestration → Routes** contains a React Flow canvas. Drag nodes to
move them, scroll to zoom, drag the background to pan, and drag between ports to
connect groups. Double-click empty canvas to add a group. Select a group to name it,
describe its purpose, choose several model profiles in execution order, or make it
the entry point. Undo/redo affects the draft; Save persists it for subsequent runs.

Each group tries its enabled, available models in order. Permission/refusal and
ambiguous external effects stop execution. Otherwise the group's output selects
one connection: **Verified**, **Check failed**, **Unavailable**, or **Evidence
missing**. A disconnected Verified output completes the task; other disconnected
outputs stop it. A successful connection continues to another group with the existing
workspace and evidence. It does not run models in parallel. Each output has at most
one destination. With adaptive entry, groups may be independent: the architect
can select groups connected to its planning output. Select a model, add a group,
then drag from the planning output to the group's input. Delete a planning edge
to remove that direct choice. Saved graphs store these connections in `entry_nodes`;
older graphs without that field retain their previous all-groups choice.
Use one model per group to offer alternative executors, not an ordered pool.
With a fixed start, all groups must be reachable from the entry. Cycles are permitted
but consume shared run budgets, with an additional 128-transition ceiling.

There is no fixed number of strength levels: up to 64 groups and 32 profiles per
group are supported. Connections can go in either direction. The selected graph group takes
precedence over legacy `fast/balanced/deep` hints. Existing list routes are displayed
as connected groups and migrate to graph configuration when edited. Existing profile
IDs and provider credentials remain valid. Profiles have an optional description of
suitable tasks and limitations, included in the architect's configuration catalog.

The canvas also shows the real shared **Planning** role, connected to worker groups.
Select the architect in this node. With **Architect chooses the starting group** enabled
(the default), the architect selects a configured group for each task and supplies a
reason. Complex work can start at a capable group directly; routine work should start
economically. Unknown group IDs stop the plan before workers launch. Disabling this
option forces the configured entry. An explicitly fixed worker still takes precedence.
The subsequent worker transitions continue to follow the saved graph.

Every worker displays the configured reviewer. Review controls below the canvas edit
the same shared settings as General/Verification. Hermes first checks recorded test
evidence, schema and execution errors. A definite failure returns immediately. In
`risk_based` mode the reviewer is called only for inconclusive checks; `always` calls
it after any non-failed check, and `off` skips model review. The reviewer sees evidence
and task requirements, without tools. Category-specific role overrides remain available.

LangGraph controls execution transitions; Hermes owns model calls, tools, cancellation,
privacy, evidence, worktrees and applying verified changes. The chat retains node and
transition events. Worktree journals retain the graph snapshot and tool evidence.
This is not automatic crash recovery: saved journals do not resume a process, and a
LangGraph transition does not roll back filesystem or external side effects.

## Automatic setup

After creating profiles and a route, open **General → Use recommended setup**, then
**Save**. This selects an enabled `deep` architect, a `balanced` reviewer, automatic
planning, isolated Git worktrees, and a budget of at least 16 attempts,
80 model calls and 20 minutes. The switch applies to the next user message, including
in an existing conversation, without rebuilding its cached prompt or tool schemas.
You can change every role in the same form; profile IDs and routes are preserved.

There are only two run states: **On** and **Off**. There is no wording classifier,
development-only trigger or preview mode. Legacy `mode` and `automation.mode` config
values remain readable for compatibility but no longer select run behavior;
`enabled` is authoritative. Internal background skill reviews and orchestration
children do not recursively start a new plan.

When at least one execution profile exists, Desktop shows **Orchestration: On/Off**
beside the model and reasoning selectors below the composer. Its menu selects the
worker route and architect profile. The control reads/writes the owning Hermes
profile's settings, including in a secondary chat pane; changes affect subsequent
messages in chats using that Hermes profile. If there are profiles but no route,
enabling creates a route ordered from Fast to Deep. Without an explicit architect,
the last enabled profile of the selected route supplies it.

The architect can inspect files through inherited read-only file tools. It returns
an architecture, ordered subtasks, dependencies, starting levels and acceptance
checks. Invalid/cyclic plans stop before workers launch.
An omitted `depends_on` is treated as an empty list. Explicit malformed dependencies,
unknown task IDs and cycles still stop the plan; errors name the offending field
without dumping the validation schema.
Subtasks run sequentially; each receives prior results and the same working copy. Failed subtasks stop dependent
work. Planning, execution, repairs and review share one operation budget.
Current-turn attachments also reach the architect and every worker, including repairs
and specialist transfers. Images retain vision routing; structured audio, file and
video content parts retain their original format. Already-expanded file context
(text previews or binary-file paths) is carried into the isolated workspace without
being re-resolved there. The selected provider must support the supplied media format;
forwarding an attachment does not add media support to a model.
Explicit `orchestrate_task` calls accept `images` and `attachments` (typed message
content objects); automatic orchestration takes them from the admitted user turn.
Desktop regenerate, restore and text edits replay the gateway-resolvable attachment
references, including images and file-backed audio/video/documents, rather than
local preview URLs. Attachment-only turns can also be replayed.

The architect marks visual deliverables with `visual_check` and lists expected
workspace-relative output files in `artifacts`. These checks are independent of
the connected application: missing output files or a missing fresh candidate image
after the final edit cannot pass. A semantic reviewer receives both the source
references and candidate images; passing code checks does not skip this comparison.
External applications have their own working directories. Workers must use explicit
absolute output paths beneath the assigned workspace, not an application's cwd.
The turn then ends with the controller's report. The main model cannot silently
continue outside this budget after a blocked plan or refusal.

Planning defaults to one complete deliverable per worker. A small website is not
split into separate HTML, CSS, JavaScript and testing agents. Multi-step plans must
explicitly justify independent deliverables; different specialist routes also retain
separate tasks. Each worker implements and checks its result in the same session.
Reviewers check concrete requirements without requiring features assigned to later
tasks or treating a disabled automatic verification service as a failed test.

`budget.max_calls_per_attempt` (default 12, also available in Desktop settings)
bounds physical model requests within one attempt, including auxiliary requests.
Architects use at most four requests and reviewers at most two, within that ceiling.
Before exceeding either the attempt allowance or the total model-call budget,
Hermes asks whether to continue for another `max_calls_per_attempt` requests.
Approval resumes the same worker with its existing conversation and files; it
does not restart the task or switch models. Counters remain cumulative. Declining,
closing, or timing out the question stops execution and retains the work. Without
an interactive callback it stops rather than silently granting more calls.
Time spent waiting for this answer does not consume the orchestration deadline.
MCP image results are available as collapsed previews in chat, including in the
orchestration timeline. Expand a preview to load it through the existing local or
profile-scoped remote media reader. Cached image references survive chat reloads.
Existing restrictions on uncertain external side effects still block unsafe retries.
This is a ceiling, not a target or a promise that every provider finishes within it.

Desktop keeps a dedicated orchestration timeline in the main conversation: the plan,
selected profiles/models, public tool actions, repairs, transfers, checks and final
status. It remains in chat history after completion and reopening, including when
large tool evidence is saved separately. It does not expose private model reasoning.
The card shows up to 500 recent entries; the full activity journal is retained under
the owning Hermes home's `orchestration/progress/` directory. Failed work stays in its
worktree and is not automatically applied to the original project.

The orchestration wall-clock budget supervises the whole plan. The ordinary tool-call
timeout does not cut it short while leaving children running. Budget exhaustion is
reported with the actual limit and retained artifacts, rather than a generic missing
orchestration result. Existing conversations from before this change do not gain a
retroactive live timeline.

**Fixed worker** explicitly selects one profile independently of its fast/balanced/deep
label. This can be a small local or specialized model. It disables worker escalation
and leaves architect/reviewer selection independent. Policy/permission refusals stop
for inspection; they are not treated as insufficient model capacity or automatically
retried on another provider. Ordinary capability failures can still escalate through
the selected route when no fixed worker is selected.

## Specialists: task type independently of model size

Open **Specializations → Add four category templates**. The templates cover
`reverse_engineering` (decompilation and reverse engineering), `roleplay` (fictional
dialogue), `sensitive_analysis` (sensitive-topic analysis), and `local_private`
(local model execution). They start disabled. Select an existing route, edit the
description of when to choose it, optionally assign an architect and reviewer,
enable the category, then save. You can also create custom categories.
Templates do not install models or establish that a model is "uncensored".
An architect-invented category such as `frontend` is ignored with a timeline notice;
the task keeps its original route and any original privacy restrictions. Explicit
user selections, configured disabled categories and reserved local categories still
require their configured route: they are never silently downgraded to cloud execution.
Choose the actual provider/model in **Profiles**, then include it in the category's
route. One small specialist can be the entire route; a specialist reviewer can be
assigned separately from the general reviewer.

With automatic planning enabled, the architect sees the enabled category descriptions
and can assign `specialization` and `specialization_reason` to individual plan tasks.
This applies to dialogue and analysis too. Explicitly starting with
`@roleplay Write a scene between two characters` selects that category *before*
planning. Orchestration itself must be enabled. The four built-in
prefixes stop if their category is missing or disabled rather than silently ignoring
the selection. Custom prefixes become recognized when their category is configured.

A worker can request a specialist by returning only:

```text
ORCHESTRATION_SPECIALIST: {"category":"roleplay","reason":"This task needs sustained character dialogue"}
```

This is a transfer request, not a completed result. Hermes records the request and
reason, retains the attempt and working copy, and starts at the destination route's
lowest available tier. Deep can therefore transfer to Fast without consuming a
capacity escalation. Further failures can escalate *within that specialist route*.
Repeated categories stop a transfer cycle; `routing.max_specialist_switches` defaults
to 2 per subtask. The existing attempt/call/deadline budgets remain shared.
Unknown/disabled categories, uncertain external effects, and policy/permission refusals
stop the task instead of initiating a transfer. A refusal alone never selects a
different provider. A fixed worker outside the selected category's route is a
configuration conflict, not silently overridden.

MCP discovery's profile-scoped `readOnlyHint` distinguishes reads from writes;
discovery itself is not a side effect. Successfully completed MCP writes are
recorded as confirmed execution and can be handed off after a verification failure,
without replaying the same tool/arguments. Failed, timed-out or abandoned writes
remain uncertain and block automatic retries. Confirmation of execution is not
confirmation that the deliverable is correct.

An explicit category applies its `isolate_workspace` choice when starting a fresh
operation. The dialogue and analysis templates turn Git isolation off so they can
run without a repository. A plan or transfer already in progress keeps its workspace;
per-subtask selection does not discard existing changes. The architect and reviewer
overrides apply to their respective roles (a task selected after planning cannot
retroactively change the architect).

### Local categories and private input

`local_only: true` requires loopback model endpoints for the orchestrated architect,
workers, reviewer and auxiliary LLM calls. If role overrides are omitted, the last
enabled profile in the category's route supplies the architect and reviewer. Use a
route containing local profiles; a cloud role is blocked before its completion call.
Subsequent specialist transfers cannot relax an operation's existing cloud ban.

Select `@local_private` **before** submitting confidential input. A category discovered
after cloud-enabled planning/execution stops with `local_selection_required` and asks
for a new local task: switching models cannot undo prior disclosure. This conservative
rule applies whenever the previous operation allowed cloud calls, even if its last
worker happened to be local.

This setting governs the orchestration's model calls. For the entire conversation to
remain local, also configure the main Hermes model and auxiliary services (including
titles/memory/preprocessing) locally before sending input. Existing terminal, browser
and service tool permissions still govern network actions; a local model endpoint is
not a network sandbox or a guarantee that a local proxy never forwards traffic.

## Attempt history and recovery

**Keep attempts in a separate Git worktree** requires a local Git project with an
initial commit. Dirty tracked files and ordinary untracked files are copied into the
worktree; the original index and user changes are preserved. Dependency directories
and ignored files are not copied. Dependencies may therefore need installing inside
the worktree. Isolation is a working-directory contract, not an OS security sandbox.
Orchestration also blocks its file-writing tools outside that worktree, including
multi-file patches; shell commands still require the existing tool permissions.

Before each worker attempt, Hermes takes a checkpoint. Afterwards it stores a patch,
public tool evidence and the verification verdict. The next model inspects and repairs
the retained state. There is no unconditional reset that discards the previous attempt.
Existing checkpoint/rollback tools can be used for a reviewed, selective restoration.
Do not restore while a cancelled writer is still settling: its journal can remain
`running` until inspected, and the workspace is blocked from new orchestration writers.

The active Hermes home's `orchestration/runs/<id>/` holds `plan.json`, `run.json`,
`attempt-*.patch` and `result.patch`. Worktrees remain under the project's `.worktrees/`.
These files survive restart; automatic process resumption is not implemented. Checkpoint
exclusions and size limits still apply (including secrets, dependencies and large build
outputs); these are source checkpoints, not a full machine backup. External actions,
such as sending a message or changing a service, cannot be undone by a Git rollback.

With **Apply the completed result**, Hermes applies the cumulative patch only after
every subtask succeeds and the source checkpoint still matches the initial state.
A concurrent source change or patch conflict blocks application and retains artifacts
for review. Failed plans leave the original source unchanged.

## Configure profiles

In Desktop, open **Settings → Orchestration**. Use **Applies to** to select the
Hermes profile that owns these settings. Configure the provider and its credentials
in the existing model/provider settings first. Orchestration stores provider IDs
and model IDs; it never stores API keys or endpoint URLs.

1. Under **Profiles**, add execution profiles, using the existing provider/model
   catalog. Add a description of suitable tasks; optionally set reasoning effort and capabilities.
2. Under **Routes**, connect groups and select an entry point. Models in a group are ordered alternatives;
   output connections control transitions. Create the default `general` workflow and optional specialist workflows.
3. Select a verifier under **Verification** for tasks without executable checks or
   an output schema. A verifier receives the result and public evidence, with no tools.
4. Save, then use **Test profile** to make a small completion and, when tools are
   enabled/automatic, a harmless tool call. This probe can incur provider charges.
5. Enable orchestration and start a **new conversation** to load the tool schema.

Edits use the existing `/api/config` endpoint and profile-scoped `config.yaml`.
Deleting a referenced profile or route is rejected. Remove its category/route/architect/verifier/fixed-worker references
first. Saving never swaps the current conversation's model or tool schemas.

Here is an example. Replace the illustrative provider/model IDs with configured,
available IDs from your catalog before enabling it:

```yaml
orchestration:
  enabled: false
  automation:
    planner_profile: codex_deep
    max_tasks: 6
  workspace:
    enabled: true
    apply_on_success: true
  routing:
    strategy: agent
    default_route: general
    default_level: fast
    allow_direct_deep: true
  profiles:
    local_fast:
      enabled: true
      provider: custom:local
      model: your-local-model
      level: fast
      reasoning_effort: low
      max_parallel: 1
    cloud_balanced:
      enabled: true
      provider: openrouter
      model: your-provider/model
      level: balanced
    codex_deep:
      enabled: true
      provider: openai-codex
      model: your-codex-model
      level: deep
      reasoning_effort: high
  routes:
    general: [local_fast, cloud_balanced, codex_deep]
    coding: [local_fast, cloud_balanced, codex_deep]
  verification:
    deterministic: true
    semantic: risk_based
    verifier_profile: cloud_balanced
    uncertain_action: escalate
    main_agent_stop_gate: false
  escalation:
    enabled: true
    same_profile_repairs: 1
    max_escalations: 2
  budget:
    max_attempts: 16
    max_escalations: 2
    max_model_calls: 80
    max_parallel_tasks: 4
    timeout_seconds: 1200
  privacy:
    cloud_allowed: true
```

## Routing and verification

The tool accepts `goal`, `context`, an optional configured `route`, a logical
`level` (`auto`, `fast`, `balanced`, `deep`), `output_schema`, `images`, and
`background`, and `specialization` with a brief `specialization_reason`.
`plan: true` requests foreground architecture and dependent execution
for one goal. A `tasks` array can provide independent requests instead of one
goal. The model cannot supply a provider, endpoint or credential.

```json
{"goal":"Fix the reconnect unit test", "route":"coding", "level":"fast"}
```

`agent` routing uses the main agent's requested route/level. For legacy list routes only, `auto` routes small
deterministic rules recognize coding, research, image and complex architecture
tasks. Direct deep routing can be disabled. Profiles with incompatible explicit
capabilities are excluded. Workers retain the displayed route order within each capability class. Legacy
`priority` values remain readable but no longer override the explicit route order. An unavailable profile is skipped without consuming an
intellectual escalation. Orchestration children disable inherited provider fallback
chains so the controller remains responsible for selecting their execution profiles.

Deterministic checks reject malformed/schema-invalid answers, explicit requests
for escalation, repeated failures, repeated tool results, truncation, and failed
Hermes verification evidence. `risk_based` semantic review runs when deterministic
evidence is inconclusive; `always` also reviews deterministic passes. A missing or
invalid verifier result is **uncertain**, never an implicit pass. JSON-schema
validation requires the existing optional `jsonschema` dependency and fails closed
when it is unavailable. A schema pass establishes the output contract, not the
truth of arbitrary claims; use semantic verification when that distinction matters.

`uncertain_action` chooses accept, repair or escalate. Repairs and escalations
have hard limits. When only one attempt remains and a stronger profile is next,
it is reserved for escalation rather than another same-profile repair.
The optional main-agent stop gate requests delegation only after
confirmed failed file-verification evidence, at most once per turn.

## Scope, cost and safety

- An absent/disabled section removes the orchestration tool from new session schemas.
  Enabling during an existing conversation starts a backend-owned plan on the next
  user message even if that session has no orchestration tool. Existing tool schemas
  and past messages stay unchanged; turning off stops new plans.
- Each task (or entire automatic plan) shares one ledger across execution, repairs, semantic review and
  auxiliary LLM requests. `max_model_calls` counts Hermes provider attempts,
  including Hermes retries; transport/SDK-internal retries are not separate ledger
  entries. Nested delegation is disabled for orchestration children in this MVP.
- Batches execute serially. Writers sharing a directory serialize even across
  concurrent tool calls. Profile `max_parallel` limits also apply across separate
  workspaces. Existing delegation depth, one-shot spawn allowance, concurrency,
  approvals remain in effect. Orchestration's workspace setting additionally requires
  isolation rather than silently falling back to the original source directory.
- Repairs/escalations reuse the task's existing worktree and receive changed files,
  public tool results, checks and remaining budget. Hidden reasoning is excluded.
- Unknown service actions and opaque shell/code execution are treated as uncertain
  external effects. A failed task that may have changed an external system returns
  `blocked` for inspection instead of automatically repeating the action. Common
  standalone verification commands can be retried. This conservative check is not
  an external transaction log.
- `cloud_allowed: false` requires loopback model endpoints for execution, review
  and auxiliary LLM calls. This controls model routing, not general tool network
  access; existing tool permissions still govern browser/terminal/service tools.
- Cancellation is cooperative. A timed-out writer keeps its workspace blocked
  until its actual worker settles. Threads and diagnostic history do not survive
  process exit.

## Diagnostics and implementation

**Diagnostics** shows mode, profile readiness and recent structured events, including
route/profile choices, verification, repairs, escalation and consumed budgets.
Local readiness probes `/models`; cloud readiness establishes provider resolution
only. **Test profile** verifies actual completion/tool behavior. Readiness uses a
short cache and failure cooldown. Logs use `hermes.orchestration` and contain
metadata rather than task text, authorization headers or reasoning.

Implementation lives in `agent/orchestration/` and new Desktop settings components.
It uses the existing provider resolver, `AIAgent`, public subagent lifecycle,
delegation workspaces, permissions and background completion queue. Small optional
integration points account for main/auxiliary requests and preserve cancellation
and workspace ownership.

Classifier strategies, adaptive cost/latency routing, benchmarks and automatic
resumption of interrupted plans are deferred. This implementation
rejects unsupported classifier strategies instead of silently ignoring them.

### Compact model settings

The Profiles page shows one collapsed row per configured model and its disabled status.
New, incomplete profiles open for editing. Expand a row to change the provider, model
or description; IDs, reasoning effort, parallelism and capability overrides are under
Advanced settings. Collapsing a row preserves edits. There is no required strength
selector. Architect and reviewer profiles remain separate choices under General.
