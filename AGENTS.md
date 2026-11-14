# Agent notes

## AI ledger and playbook (all AI work, every repo)

Before you match or start a task, read the active orchestration lessons that apply to you:
the `active` entries of `reports/orch_loop/lessons.json` in deuxpardeux/dpd-tools that match your bot, task kind, tool and model
Follow them.

Every AI-built PR body ends with two lines (the CI check warns when they are missing):

    AI-Tool: <cursor|grok-bot|claude-code|claude-routine|codex|human|github-automation>
    AI-Model: <the model that did the work, e.g. composer-2.5, grok-4.7, claude-opus-5-5, or none>

Commits made by an AI tool carry the same two lines as trailers. Use the real model; write `unknown` rather than guess.

Every API-key AI call goes through the LiteLLM gateway (`https://dpd-litellm.fly.dev/v1` with your bot key), never straight to a provider. `AI ledger checks` warns on bypasses. Subscription apps (ChatGPT, Claude, Grok Bot, Cursor, Perplexity, Higgsfield, ElevenLabs) are never wired into code with a login.

A job that runs a model outside the gateway records one ledger row with `tools/ai_ledger/events.py record` from deuxpardeux/dpd-tools (on the box: `python3 /workspace/workflows/tools/ai_ledger.py record`) (tool, model, effort, tokens if known, task kind, outcome, failure reason). No prompts, answers or keys in the row.
