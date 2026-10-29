import asyncio

import pytest

from evaluation.run import load_scenarios, run_scenario
from shared.enums.workflow_status import WorkflowStage


def test_loads_all_benchmark_scenarios():
    scenarios = load_scenarios()

    assert {scenario.scenario_id for scenario in scenarios} == {
        "api_failure",
        "invalid_finance",
        "valid_startup",
        "weak_market",
    }


def test_valid_startup_runs_to_completion_without_replans():
    scenario = load_scenarios(["valid_startup"])[0]
    run = asyncio.run(run_scenario(scenario))

    assert run.final_state.current_stage == WorkflowStage.COMPLETED
    assert run.final_state.final_roadmap is not None
    assert run.final_state.replan_count == 0
    assert run.expectation_failures == []


@pytest.mark.parametrize("scenario_id", ["weak_market", "invalid_finance", "api_failure"])
def test_fault_scenarios_meet_expected_outcomes(scenario_id):
    scenario = load_scenarios([scenario_id])[0]
    run = asyncio.run(run_scenario(scenario))

    assert run.final_state.current_stage == WorkflowStage.COMPLETED
    assert run.expectation_failures == []
