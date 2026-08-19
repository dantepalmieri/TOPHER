# shared handoff/termination convention appended to every team agent's prompt, so
# the wording never drifts out of sync across five hand-copies (same reasoning as
# TOPHER_IDENTITY_TEXT in identity.py) - orchestrator.py's next-speaker parser
# depends on agents actually following this convention

TEAM_CONVERSATION_PROTOCOL_TEXT = (
    "## How this conversation works\n"
    "You are in a live conversation with four other named agents: Architect, "
    "Research, Developer, Testing, Analytics. You will see the transcript so far as "
    "your input - read it before responding, since anyone may have already asked "
    "you something directly.\n\n"
    "End every reply with exactly one of the following, on its own line:\n"
    "- `@<AgentName>: <one-sentence reason>` - to hand off to a specific teammate "
    "(e.g. `@Developer: build the plan above`). Use this whenever you need someone "
    "else to act next.\n"
    "- `DONE` - only once the goal is fully satisfied and nobody else needs to act.\n\n"
    "If you end your reply with neither, the orchestrator will pick the next speaker "
    "for you - so always address someone or say DONE explicitly, never leave it "
    "ambiguous."
)
