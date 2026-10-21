# Virtual Office conversation modes: CEO, direct departments, Reception

This supplement clarifies the required chat interaction model for VazaoSovereignTrader.

## CEO chat is the default

The CEO is the owner's primary and most frequently used conversation. It is the default chat opened by the office. The owner can ask general questions, request system-wide status, set priorities, or delegate work. The CEO may answer directly or coordinate one or more departments and consolidate their results.

## Direct department conversations

The owner must be able to click any department in the office/navigation and open a distinct conversation with that department. The user can address a specialist directly without first going through Reception or the CEO. Keep the conversation thread and task history scoped to the selected department, while allowing authorized access to the shared Runtime learning memory and relevant internal coordination.

Direct access is a communication choice, not an authorization escalation. Each department remains limited to its capability scope; all execution and risk decisions stay under the authoritative Runtime and existing server-side guards.

## Reception is optional

Reception is a separate, optional entry point for routine requests or when the owner is unsure which department is appropriate. It classifies, clarifies, routes, tracks and returns a result. It must not become a mandatory hop for the CEO chat or direct department conversations.

## Required UI behavior

- Default landing conversation: CEO.
- Department click: opens the selected department's own chat and preserves its conversation identity.
- Reception click: opens the optional routing conversation.
- Make the active interlocutor visible at all times.
- Show task ownership, progress, evidence/freshness and final results in the originating conversation.
- Switching rooms must not create another Runtime or lose the authoritative task state.
- CEO, Reception and department chats must use authenticated APIs and explicit scopes.
- The visual character is only a representation of the real interlocutor/task state; it is not the source of truth.

## Acceptance tests

1. Initial office launch opens CEO chat.
2. A CEO request can be answered directly or delegated.
3. Clicking Research opens a direct Research conversation.
4. Clicking Exchange Comparison opens a direct Exchange Comparison conversation.
5. Direct department requests do not pass through Reception unless the user explicitly asks for routing.
6. Reception can route an ordinary request to a department and return the result to the Reception thread.
7. Conversation history and task correlation remain distinct and correct across CEO, department and Reception chats.
8. Direct chat cannot bypass permissions, risk gates or explicit human authorization.
9. Runtime continues when any conversation panel, department room or entire office is closed or disconnected.

This is a target contract; it does not claim that these UI flows are already implemented.
