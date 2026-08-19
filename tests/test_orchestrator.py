# unit coverage for the team conversation loop's pure logic - handoff/DONE parsing
# and next-speaker resolution are the load-bearing parts of decision 3's rewrite,
# and neither needs a real agent call to verify

from second_brain import orchestrator


def test_parse_response_for_handoff_recognizes_done():
    is_done, mentioned_agent = orchestrator._parse_response_for_handoff("All set.\n\nDONE", "Analytics")
    assert is_done is True
    assert mentioned_agent is None


def test_parse_response_for_handoff_recognizes_valid_mention():
    response_text = "Here is the plan.\n\n@Research: verify the third-party library versions"
    is_done, mentioned_agent = orchestrator._parse_response_for_handoff(response_text, "Architect")
    assert is_done is False
    assert mentioned_agent == "Research"


def test_parse_response_for_handoff_ignores_self_mention():
    response_text = "Still working.\n\n@Developer: keep going"
    is_done, mentioned_agent = orchestrator._parse_response_for_handoff(response_text, "Developer")
    assert is_done is False
    assert mentioned_agent is None


def test_parse_response_for_handoff_ignores_unknown_agent_name():
    response_text = "Handing off.\n\n@Deployment: ship it"
    is_done, mentioned_agent = orchestrator._parse_response_for_handoff(response_text, "Developer")
    assert is_done is False
    assert mentioned_agent is None


def test_parse_response_for_handoff_returns_no_mention_when_trailing_line_is_plain_text():
    response_text = "Just some findings with no explicit handoff."
    is_done, mentioned_agent = orchestrator._parse_response_for_handoff(response_text, "Research")
    assert is_done is False
    assert mentioned_agent is None


def test_resolve_next_speaker_honors_explicit_mention():
    next_speaker = orchestrator._resolve_next_speaker("Architect", "Testing")
    assert next_speaker == "Testing"


def test_resolve_next_speaker_falls_back_to_round_robin_in_canonical_order():
    assert orchestrator._resolve_next_speaker("Architect", None) == "Research"
    assert orchestrator._resolve_next_speaker("Research", None) == "Developer"
    assert orchestrator._resolve_next_speaker("Analytics", None) == "Architect"


def test_render_transcript_for_prompt_includes_goal_and_every_message():
    first_message = orchestrator.TeamConversationMessage(1, "Architect", "Research", "plan text", False)
    second_message = orchestrator.TeamConversationMessage(2, "Research", None, "findings text", False)
    transcript_text = orchestrator._render_transcript_for_prompt("build a thing", [first_message, second_message])

    assert "Goal: build a thing" in transcript_text
    assert "[Architect]: plan text" in transcript_text
    assert "[Research]: findings text" in transcript_text
