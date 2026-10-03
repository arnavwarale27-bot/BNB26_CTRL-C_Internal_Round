# BNB26_CTRL-C_Internal_Round
this repo is for international hackathon where swap is lead and i am software head less see 
# Black Box — A Flight Recorder for AI Agents

## Overview

**Black Box** is an observability and debugging system for multi-step AI agents.

Modern AI agents perform multiple steps such as planning, searching, retrieving context, calling APIs/tools, validating results, and generating a final answer. When the final output is wrong, developers often know only that the agent failed—not which intermediate step caused the failure.

Black Box is being built to answer that question.

It records the complete execution trace, analyzes the trace to localize the most suspicious/failure-causing step, provides evidence for the diagnosis, and allows developers to replay the agent from a saved checkpoint.

---

## Core Workflow

```text
AI Agent
   ↓
Execution Recorder
   ↓
Execution Trace
   ↓
Failure Analysis Model
   ↓
Failure Localization
   ↓
Evidence / Diagnosis
   ↓
Checkpoint Replay
   ↓
Alternative Execution
   ↓
Trace Comparison
```

The goal is to move from:

> "The agent failed."

to:

> "This specific step most likely caused the failure, here is the evidence, and here is what happened when we replayed it with a correction."

---

## What We Are Building

### 1. Agent Execution Recorder

The recorder captures important information from every agent step.

Example:

```text
Step 1 → Planning
Step 2 → Search
Step 3 → Context Retrieval
Step 4 → API / Tool Call
Step 5 → Validation
Step 6 → Final Answer
```

A trace can contain:

- Step type
- Input
- Output
- Tool/API used
- Execution time
- Errors
- Retry information
- Model/token information
- Previous and next step relationships

---

### 2. Failure Localization Model

Instead of only detecting that an agent failed, Black Box attempts to determine **where the failure originated**.

We plan to train our own model using historical agent execution traces.

Potential signals include:

- Tool/API errors
- Unusual inputs or outputs
- Latency changes
- Retry patterns
- Semantic differences
- Downstream failures
- Historical failure patterns
- Step type and execution context

The model will help rank execution steps by their likelihood of being responsible for the failure.

> The exact model architecture, dataset, labels, and evaluation method will be finalized after mentor validation.

---

### 3. Evidence-Based Diagnosis

Black Box should not simply say:

```text
Step 4 is the problem.
```

It should explain **why**.

Example:

```text
Suspected Step:
Step 4 — Weather API Call

Evidence:
• API parameter does not match the expected format.
• Similar input appeared in previous failed executions.
• The next validation step failed immediately afterward.
```

This makes the system a debugging tool rather than just a monitoring dashboard.

---

### 4. Checkpoint Replay

Important execution points are saved as checkpoints.

If Step 4 is identified as suspicious, the developer can restore the state immediately before that step and replay the execution.

```text
Checkpoint
    ↓
Step 4
    ↓
Replay
```

This avoids restarting the entire agent from the beginning.

---

### 5. Alternative Execution

Developers can modify the suspicious step and replay it.

Example:

### Original

```text
unit = "Celcius"
→ API failure
→ Validation failure
→ Agent fails
```

### Alternative

```text
unit = "Celsius"
→ API succeeds
→ Validation succeeds
→ Agent succeeds
```

The system then compares both executions.

---

### 6. Trace Comparison

Example:

```text
Original Run              Alternative Run
─────────────             ────────────────
Plan       ✓              Plan       ✓
Search     ✓              Search     ✓
Context    ✓              Context    ✓
Tool Call  ✕              Tool Call  ✓
Validate   ✕              Validate   ✓
Answer     ✕              Answer     ✓
```

This provides evidence about whether changing the suspected step changed the outcome.

---

# MVP

The first prototype will use a small deterministic agent workflow:

```text
User Request
     ↓
Agent Planning
     ↓
Search
     ↓
Context Retrieval
     ↓
API Call
     ↓
Validation
     ↓
Final Answer
```

A controlled API parameter error will intentionally create a failure.

The MVP should:

1. Record the complete execution.
2. Detect the failed execution.
3. Analyze the execution steps.
4. Identify the suspicious step.
5. Display supporting evidence.
6. Save a checkpoint.
7. Replay the execution.
8. Allow the parameter to be corrected.
9. Run the alternative execution.
10. Compare the original and alternative traces.

---

# System Architecture

```text
                    ┌─────────────────┐
                    │    AI Agent     │
                    └────────┬────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │    Recorder     │
                    └────────┬────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │ Execution Trace │
                    │    / SQLite     │
                    └────────┬────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │ Failure Analysis│
                    │      Model      │
                    └────────┬────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │ Diagnosis +     │
                    │ Evidence        │
                    └────────┬────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │ Checkpoint      │
                    │ Replay          │
                    └────────┬────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │ Alternative Run │
                    └────────┬────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │ Trace Comparison│
                    └─────────────────┘
```

---

# Technology Direction

## Frontend

Initial frontend:

- HTML
- CSS
- Vanilla JavaScript

The UI will be a single long-scrolling technical interface containing:

1. Product introduction
2. Run Agent
3. Execution Trace
4. Diagnosis
5. Checkpoint Replay
6. Original vs Alternative execution

Design principles:

- Minimal
- Technical
- Human-designed
- Responsive
- No unnecessary visual effects

We intentionally avoid:

- Excessive gradients
- Glassmorphism
- Neon effects
- Decorative blobs
- Fake metrics
- Generic AI dashboard styling
- Unnecessary animations

## Backend

Planned backend:

- Python
- FastAPI
- SQLite for the MVP

The backend will handle:

- Agent execution
- Trace recording
- Trace storage
- Model inference
- Diagnosis
- Checkpoint management
- Replay
- Alternative execution
- Trace comparison

## Machine Learning

The ML component is the main research component of Black Box.

Potential features include:

```text
Latency
Error presence
Tool failure
Retry count
Input/output characteristics
Semantic similarity
Token usage
Step type
Previous execution behavior
Downstream failure
Historical failure frequency
```

The system should distinguish between:

- **Anomaly detection** — does this step look unusual?
- **Failure-step localization** — which step most likely caused the failure?
- **Root-cause classification** — what type of failure occurred?

The main objective is **failure-step localization**, supported by anomaly signals and execution evidence.

---

# Evaluation

The model will eventually be evaluated using executions with known failure points.

Possible metrics:

- Top-1 failure localization accuracy
- Top-3 failure localization accuracy
- Precision
- Recall
- False-positive rate

Only metrics obtained from actual experiments will be reported.

---

# Development Phases

## Phase 1 — Frontend Prototype

Build:

```text
Run Agent
   ↓
Execution Trace
   ↓
Diagnosis
   ↓
Replay
   ↓
Comparison
```

## Phase 2 — Real Agent Backend

Connect the frontend to a Python/FastAPI backend and run a real agent.

## Phase 3 — Trace Database

Store real executions in SQLite.

## Phase 4 — ML Model

Create a dataset of successful and failed executions and train the failure-localization model.

## Phase 5 — Replay Engine

Implement checkpoint restoration and alternative execution.

## Phase 6 — Evaluation

Test the model against known failure cases and measure localization performance.

## Phase 7 — Generalization

Experiment with different agent workflows and failure types.

---

# Final Product Goal

Black Box should become a debugging layer around an AI agent.

Instead of manually inspecting large amounts of logs, developers should be able to answer:

```text
WHAT HAPPENED?
      ↓
WHERE DID IT FAIL?
      ↓
WHY DO WE THINK IT FAILED THERE?
      ↓
CAN WE REPLAY IT?
      ↓
WHAT HAPPENS IF WE CHANGE THAT STEP?
```

The final system combines:

**Observability + Machine Learning + Explainability + Checkpoint Replay**

into one workflow for debugging AI agents.

---

# Current MVP Goal

> **Build one working AI-agent workflow that can fail, record its complete execution trace, identify the suspicious step, explain the evidence, replay from a checkpoint, and demonstrate that an alternative execution can succeed.**

Once this works reliably, the system can be expanded into a more general-purpose flight recorder for AI agents.

---

## Short Description

> **Black Box is a flight recorder for AI agents. It records multi-step agent executions, uses a trained model to localize likely failure points, explains the evidence, and lets developers replay and compare alternative executions.**

## Status

**Stage:** MVP / Prototype

**Current priorities:**

1. Working frontend
2. Deterministic agent simulation
3. Execution trace
4. Failure diagnosis
5. Checkpoint replay
6. Real agent integration
7. Own failure-localization model
8. Evaluation
