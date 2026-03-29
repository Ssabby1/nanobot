# Fitness Agent Overview

## What This Project Is

This fitness module is a vertical agent workflow built on top of `nanobot`.
Instead of treating the assistant as an open-ended chatbot, it constrains user requests into a structured execution loop:

1. Understand the user's intent
2. Route it into a supported fitness action
3. Collect missing fields through multi-turn follow-up
4. Execute deterministic business logic
5. Persist state for future turns

The result is a practical domain agent for:

- profile creation and updates
- weekly plan generation
- daily feedback logging
- adjustment suggestion generation

## Why It Is Interesting

### Rule-first, LLM-fallback routing

The system does not let the model directly execute arbitrary logic.
It first tries a local rule router. If the request is more ambiguous or more conversational, it falls back to an LLM router that still returns structured outputs instead of free-form decisions.

### Multi-turn slot filling

If the user does not provide enough information in one message, the agent stores pending state and continues the same task in later turns. The follow-up copy also adapts across turns, so the second and third prompts feel like continuation instead of restart.

### Deterministic execution layer

Both rule routing and LLM routing eventually call the same `FitnessService`, which keeps the execution path deterministic and easier to test.

### Built-in evaluation

The repository includes deterministic evaluation cases and a CLI command:

```bash
nanobot fitness eval
```

This generates a structured JSON report under:

```text
<workspace>/fitness_eval_reports/<timestamp>/fitness_eval_report.json
```

## Demo Commands

### Full natural-language profile creation

```bash
nanobot agent -m "我叫彭于晏，男，23岁，176cm，体重140斤，目标减脂，训练老手，已经锻炼五年了，每周练4次，每次60分钟，健身房训练，每天自己在家做饭吃"
```

### Multi-turn follow-up

```bash
nanobot agent -m "我叫sasa，男，23岁，176cm"
nanobot agent -m "体重140斤"
nanobot agent -m "目标减脂，练了五年，每周练4次，每次60分钟，健身房训练，自己做饭"
```

### Rest-day feedback

```bash
nanobot agent -m "我今天没练"
nanobot agent -m "有点累，饮食还行"
```

### Evaluation

```bash
nanobot fitness eval
```

## Technical Highlights

- CLI product surface with `nanobot agent -m` and `nanobot fitness ...`
- structured routing with action + arguments + missing fields
- recent-user reuse across turns
- pending route persistence
- deterministic evaluation suite for regression checking

## Suggested Resume Framing

Possible directions for resume bullets:

- Built a vertical fitness agent on top of a lightweight CLI agent framework, covering profile, planning, feedback, and adaptive suggestion flows.
- Designed a rule-first, LLM-fallback routing layer with structured actions and deterministic execution through a shared service layer.
- Implemented multi-turn slot filling, pending-state continuation, and built-in evaluation cases with JSON reporting for regression validation.
