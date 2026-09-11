# ADR-003: Custom State Machine for Agent Loop

## Status
Accepted

## Context
In Sprint 3, SAFIRE must transition from a straight-line pipeline to an iterative agent loop capable of using tools (including a Python sandbox). The Master PRD §15 requires strict enforcement of execution boundaries:
- `MAX_AGENT_STEPS`
- `MAX_TOOL_CALLS`
- `MAX_RETRIES`
- `MAX_ESCALATIONS`
- `MAX_EXECUTION_TIME`
- `MAX_CONTEXT_GROWTH`

We must choose an architecture for the agent loop. The primary candidates are:
1. **LangGraph**: A popular framework for orchestrating cyclic agent graphs.
2. **Custom Async State Machine**: A tailor-made Python loop that maps directly to our canonical `TaskState` enum.

## Decision
We have decided to implement a **Custom Async State Machine** for the agent loop rather than adopting LangGraph.

## Rationale
1. **Sovereignty & Control**: SAFIRE requires extreme predictability. Enforcing strict bounds (`MAX_AGENT_STEPS`, `MAX_EXECUTION_TIME`) is much simpler and more transparent in a custom loop where we have full control over the execution context and memory. Intercepting and hard-stopping a framework like LangGraph introduces unnecessary complexity.
2. **Alignment with TaskState**: We already have a tightly defined `TaskState` enum (`INTAKE -> CLASSIFY -> PLAN -> RETRIEVE -> OBSERVE -> VERIFY -> APPROVE -> DELIVER`). Writing a state machine that explicitly implements transitions between these exact states ensures code reflects the domain perfectly.
3. **Reduced Dependency Overhead**: LangGraph introduces significant mental overhead and dependency weight. A custom async state machine is lightweight and easily auditable, which aligns perfectly with the Sovereignty OS ethos.
4. **Tool Calling Integration**: We already have an established adapter pattern that normalizes `TOOL_CALLING` capabilities from the gateway. We can easily consume the `ToolCallResult` from the adapter within our custom loop.

## Consequences
- **Positive**: Complete control over execution limits; highly observable; no framework magic; direct alignment with domain language (`TaskState`).
- **Negative**: We must build and maintain the context growth logic, history tracking, and transition mechanics ourselves (which are otherwise provided by LangGraph).
