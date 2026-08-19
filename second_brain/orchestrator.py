# phase 4: routes a request to the right subagent(s). every agent stays independently
# callable for narrower asks, and run_full_team_pipeline chains all five in the natural
# handoff order they were designed around - architect plans, research investigates,
# developer builds, testing reviews, analytics measures/organizes - threading each
# stage's output into the next stage's input as context

from second_brain.agents.architect_agent import ask_architect
from second_brain.agents.research_agent import ask_research_agent
from second_brain.agents.developer_agent import ask_developer
from second_brain.agents.testing_agent import ask_testing_agent
from second_brain.agents.analytics_agent import ask_analytics_agent
from second_brain.types import PipelineStageResult

ARCHITECT_STAGE_NAME = "Architect"
RESEARCH_STAGE_NAME = "Research"
DEVELOPER_STAGE_NAME = "Developer"
TESTING_STAGE_NAME = "Testing"
ANALYTICS_STAGE_NAME = "Analytics"


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


def _build_pipeline_context(goal, completed_stages):
    # builds a text block summarizing the goal plus every stage completed so far,
    # for the next stage's input
    context_text = "Goal: " + goal + "\n\n"

    for stage_index in range(len(completed_stages)):
        current_stage = completed_stages[stage_index]
        context_text = context_text + current_stage.agent_name + " output:\n" + current_stage.output_text + "\n\n"

    return context_text


def run_full_team_pipeline(goal, on_stage_complete=None):
    # runs a goal through the whole team in order, threading each completed stage into
    # the next stage's input as context. on_stage_complete, if given, is called with
    # each PipelineStageResult right after that stage finishes - callers that want to
    # show progress (e.g. a cli) pass a callback rather than this function doing i/o itself.
    completed_stages = []

    architect_plan = handle_architect_request(goal)
    architect_stage = PipelineStageResult(agent_name=ARCHITECT_STAGE_NAME, output_text=architect_plan)
    completed_stages.append(architect_stage)
    if on_stage_complete is not None:
        on_stage_complete(architect_stage)

    research_context = _build_pipeline_context(goal, completed_stages)
    research_findings = handle_research_request(research_context)
    research_stage = PipelineStageResult(agent_name=RESEARCH_STAGE_NAME, output_text=research_findings)
    completed_stages.append(research_stage)
    if on_stage_complete is not None:
        on_stage_complete(research_stage)

    developer_context = _build_pipeline_context(goal, completed_stages)
    developer_report = handle_developer_request(developer_context)
    developer_stage = PipelineStageResult(agent_name=DEVELOPER_STAGE_NAME, output_text=developer_report)
    completed_stages.append(developer_stage)
    if on_stage_complete is not None:
        on_stage_complete(developer_stage)

    testing_context = _build_pipeline_context(goal, completed_stages)
    testing_report = handle_testing_request(testing_context)
    testing_stage = PipelineStageResult(agent_name=TESTING_STAGE_NAME, output_text=testing_report)
    completed_stages.append(testing_stage)
    if on_stage_complete is not None:
        on_stage_complete(testing_stage)

    analytics_context = _build_pipeline_context(goal, completed_stages)
    analytics_report = handle_analytics_request(analytics_context)
    analytics_stage = PipelineStageResult(agent_name=ANALYTICS_STAGE_NAME, output_text=analytics_report)
    completed_stages.append(analytics_stage)
    if on_stage_complete is not None:
        on_stage_complete(analytics_stage)

    return completed_stages
