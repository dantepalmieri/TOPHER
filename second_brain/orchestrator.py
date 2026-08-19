# routes a request to the right subagent(s). every agent stays independently callable
# for narrower asks, and run_team_conversation runs the whole team as a real, bounded
# conversation: each agent sees the transcript so far and hands off to a specific
# teammate (or declares the goal DONE) per conversation_protocol.py's convention,
# rather than a fixed 5-step relay

from second_brain.agents.architect_agent import ask_architect
from second_brain.agents.research_agent import ask_research_agent
from second_brain.agents.developer_agent import ask_developer
from second_brain.agents.testing_agent import ask_testing_agent
from second_brain.agents.analytics_agent import ask_analytics_agent
from second_brain.config import MAXIMUM_CONVERSATION_TURNS

ARCHITECT_STAGE_NAME = "Architect"
RESEARCH_STAGE_NAME = "Research"
DEVELOPER_STAGE_NAME = "Developer"
TESTING_STAGE_NAME = "Testing"
ANALYTICS_STAGE_NAME = "Analytics"

# the canonical roster, in the order the original fixed pipeline used - now just a
# deterministic fallback for when an agent's reply does not address a specific
# teammate, not a hard schedule
TEAM_AGENT_NAMES = [
    ARCHITECT_STAGE_NAME, RESEARCH_STAGE_NAME, DEVELOPER_STAGE_NAME, TESTING_STAGE_NAME, ANALYTICS_STAGE_NAME
]

_ASK_FUNCTION_BY_AGENT_NAME = {
    ARCHITECT_STAGE_NAME: ask_architect,
    RESEARCH_STAGE_NAME: ask_research_agent,
    DEVELOPER_STAGE_NAME: ask_developer,
    TESTING_STAGE_NAME: ask_testing_agent,
    ANALYTICS_STAGE_NAME: ask_analytics_agent
}

DONE_SIGNAL_LINE = "DONE"
MENTION_PREFIX = "@"


def handle_architect_request(user_request):
    # routes a request to the architect agent and returns its plan
    architect_plan = ask_architect(user_request)
    return architect_plan


def handle_research_request(user_request):
    # routes a request to the research agent and returns its findings
    research_findings = ask_research_agent(user_request)
    return research_findings


def handle_developer_request(user_request):
    # routes a request to the developer agent and returns its build report
    developer_report = ask_developer(user_request)
    return developer_report


def handle_testing_request(user_request):
    # routes a request to the testing agent and returns its review
    testing_report = ask_testing_agent(user_request)
    return testing_report


def handle_analytics_request(user_request):
    # routes a request to the analytics agent and returns its analysis
    analytics_report = ask_analytics_agent(user_request)
    return analytics_report


class TeamConversationMessage:
    # one turn of the team conversation, before it has a database identity (run_id,
    # message_id, created_at) - run_trigger.py's on_message callback is what persists
    # this into a real TeamMessage via run_store.record_message
    def __init__(self, turn_number, sender_agent_name, recipient_agent_name, content, is_done_signal):
        self.turn_number = turn_number
        self.sender_agent_name = sender_agent_name
        self.recipient_agent_name = recipient_agent_name
        self.content = content
        self.is_done_signal = is_done_signal


def _render_transcript_for_prompt(goal, messages_so_far):
    # builds a text block summarizing the goal plus every message posted so far, for
    # the next speaker's input
    transcript_text = "Goal: " + goal + "\n\n"

    for message_index in range(len(messages_so_far)):
        current_message = messages_so_far[message_index]
        speaker_label = "[" + current_message.sender_agent_name + "]: "
        transcript_text = transcript_text + speaker_label + current_message.content + "\n\n"

    return transcript_text


def _last_non_empty_line(response_text):
    response_lines = response_text.strip().splitlines()
    for line_index in range(len(response_lines) - 1, -1, -1):
        current_line = response_lines[line_index].strip()
        if current_line != "":
            return current_line
    return ""


def _parse_mentioned_agent_name(trailing_line, sender_agent_name):
    # matches an exact "@<AgentName>: <reason>" trailing line, naming one of the
    # known agents and not the sender itself - anything else (typo, self-mention,
    # no colon) is treated as no mention, so the caller falls back to round-robin
    if trailing_line.startswith(MENTION_PREFIX) is False:
        return None

    colon_index = trailing_line.find(":")
    if colon_index == -1:
        return None

    candidate_name = trailing_line[1:colon_index].strip()
    if candidate_name not in TEAM_AGENT_NAMES:
        return None
    if candidate_name == sender_agent_name:
        return None

    return candidate_name


def _parse_response_for_handoff(response_text, sender_agent_name):
    # returns (is_done, mentioned_agent_name) per conversation_protocol.py's
    # convention - checked in precedence: an exact DONE line first, then an exact
    # valid @mention line, otherwise neither (caller falls back to round-robin)
    trailing_line = _last_non_empty_line(response_text)

    if trailing_line == DONE_SIGNAL_LINE:
        return True, None

    mentioned_agent_name = _parse_mentioned_agent_name(trailing_line, sender_agent_name)
    return False, mentioned_agent_name


def _resolve_next_speaker(current_speaker, mentioned_agent_name):
    # an explicit, valid mention always wins - that is the actual dynamism this
    # conversation model exists for. otherwise, deterministic round-robin: the next
    # agent after the current speaker in the canonical roster, wrapping around
    if mentioned_agent_name is not None:
        return mentioned_agent_name

    current_index = TEAM_AGENT_NAMES.index(current_speaker)
    next_index = (current_index + 1) % len(TEAM_AGENT_NAMES)
    return TEAM_AGENT_NAMES[next_index]


def run_team_conversation(goal, on_message=None):
    # runs a goal through the team as a bounded, real conversation: each turn calls
    # the current speaker with the full transcript so far, parses its reply for a
    # handoff or DONE, and continues until either DONE or MAXIMUM_CONVERSATION_TURNS
    # is reached - the latter always terminates the loop, so this can never run away.
    # on_message, if given, is called with each TeamConversationMessage right after
    # that turn finishes, mirroring the old pipeline's on_stage_complete callback.
    # returns (messages, reached_done) - reached_done is False if the turn cap was
    # hit without any agent ever saying DONE
    messages = []
    current_speaker = ARCHITECT_STAGE_NAME

    for turn_number in range(1, MAXIMUM_CONVERSATION_TURNS + 1):
        transcript_so_far = _render_transcript_for_prompt(goal, messages)
        ask_function = _ASK_FUNCTION_BY_AGENT_NAME[current_speaker]

        try:
            response_text = ask_function(transcript_so_far)
        except (Exception, KeyboardInterrupt) as agent_error:
            raise RuntimeError(current_speaker + " failed: " + str(agent_error)) from agent_error

        is_done, mentioned_agent_name = _parse_response_for_handoff(response_text, current_speaker)
        current_message = TeamConversationMessage(
            turn_number=turn_number,
            sender_agent_name=current_speaker,
            recipient_agent_name=mentioned_agent_name,
            content=response_text,
            is_done_signal=is_done
        )
        messages.append(current_message)
        if on_message is not None:
            on_message(current_message)

        if is_done:
            return messages, True

        current_speaker = _resolve_next_speaker(current_speaker, mentioned_agent_name)

    return messages, False
