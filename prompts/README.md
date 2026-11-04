# Prompts and test records

This directory coordinates repeatable validation work across separate ChatGPT accounts and the Windows PC.

## Current master prompt
- `MASTER_PROMPT_WINDOWS_LOCAL_VALIDATION.md` — run only when the owner is at the PC and the Windows artifact for the specified commit is available.

## Test records
- `test-records/README.md` — rules for recording evidence.
- `test-records/RESULT_TEMPLATE.md` — copy this template for each local test session.

## Source of truth
1. Current PR and exact commit SHA.
2. GitHub Actions workflow results and artifacts for that exact SHA.
3. Timestamped local report under `test-records/`.
4. Follow-up analysis in the current VST development conversation.

Never infer success from a file existing, an installer opening, or an API returning HTTP 200. Mark each check PASS, FAIL, BLOCKED, or NOT RUN and attach evidence.
