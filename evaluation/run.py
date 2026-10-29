"""Benchmark evaluation runner.

Runs the four standardized venture scenarios through the compiled LangGraph
workflow, records agent invocations and workflow events, computes the five
quantitative metrics, and prints a pass/fail summary table.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import math
import os
import time
from contextlib import ExitStack, contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence
from unittest.mock import patch

from langgraph.checkpoint.memory import MemorySaver
from pydantic import BaseModel

from evaluation.metrics import (
    MetricResult,
    TokenUsage,
    calculate_citation_rate,
    calculate_cost,
    calculate_latency,
    calculate_schema_compliance,
    calculate_workflow_completion,
)
from shared.contracts.business_model import BusinessModelOutput
from shared.contracts.critic import CriticValidationOutput
from shared.contracts.idea import FounderInput, IdeaAnalysisOutput
from shared.contracts.market import MarketResearchOutput
from shared.contracts.marketing import MarketingPlanOutput
from shared.contracts.revenue import RevenueEstimationOutput
from shared.contracts.roadmap import StartupRoadmap
from shared.contracts.venture_state import VentureState
from shared.enums.confidence_level import ValidationStatus
from shared.enums.workflow_status import WorkflowStage
from services.orchestrator.app.graph.workflow import build_venture_workflow
from services.orchestrator.app.state.checkpoint import get_thread_config
from services.orchestrator.app.state.state_manager import get_venture_state
from services.orchestrator.app.state.venture_state import create_initial_venture_state

import services.business_intelligence.app.interface as bi_interface
import services.finance.app.interface as finance_interface
import services.marketing_output.app.interface as marketing_interface
import services.orchestrator.app.graph.nodes as graph_nodes
import services.research.app.interface as research_interface

SCENARIO_DIR = Path(__file__).resolve().parent / "scenarios"


@dataclass(frozen=True)
class Faults:
    market_research_failures: int = 0
    critic_research_failures: int = 0
    finance_invalid_rounds: int = 0


@dataclass(frozen=True)
class Scenario:
    scenario_id: str
    description: str
    founder_input: Dict[str, Any]
    faults: Faults = field(default_factory=Faults)
    expected: Dict[str, Any] = field(default_factory=dict)


@dataclass
class InvocationRecord:
    node_name: str
    success: bool
    duration_ms: float
    input_chars: int
    output_chars: int
    error: Optional[str] = None

    @property
    def prompt_tokens(self) -> int:
        return max(1, math.ceil(self.input_chars / 4))

    @property
    def completion_tokens(self) -> int:
        return max(0, math.ceil(self.output_chars / 4))


@dataclass
class ScenarioRun:
    scenario: Scenario
    final_state: VentureState
    invocations: List[InvocationRecord]
    events: List[Dict[str, Any]]
    elapsed_seconds: float
    error: Optional[str] = None
    expectation_failures: List[str] = field(default_factory=list)

    @property
    def completed(self) -> bool:
        return self.final_state.current_stage == WorkflowStage.COMPLETED

    @property
    def warning_event_count(self) -> int:
        return sum(1 for event in self.events if event.get("event_type") == "WARNING")


def _jsonable(value: Any) -> Any:
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json")
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


def _payload_chars(*values: Any) -> int:
    try:
        return len(json.dumps(_jsonable(values), sort_keys=True, default=str))
    except Exception:
        return len(str(values))


def _validate_output(result: Any, expected_type: type[BaseModel]) -> tuple[bool, Optional[str]]:
    if isinstance(result, expected_type):
        return True, None
    try:
        expected_type.model_validate(result)
        return True, None
    except Exception as exc:
        return False, f"expected {expected_type.__name__}: {exc}"


def _forced_research_critique() -> CriticValidationOutput:
    return CriticValidationOutput(
        status=ValidationStatus.RESEARCH_REQUIRED,
        confidence_score=0.42,
        unsupported_claims=[
            "Simulated weak market scenario: market size claim lacks a verified primary source."
        ],
        verified_sources_count=1,
        feedback_notes="Add verified primary citations before the venture can proceed.",
    )


def _corrupt_finance_output(result: RevenueEstimationOutput) -> RevenueEstimationOutput:
    violations = list(result.invariant_violations)
    violations.append(
        "Simulated invalid finance scenario: market sizing and unit economics are contradictory."
    )
    return result.model_copy(
        update={
            "tam_sam_som_valid": False,
            "invariant_violations": violations,
        }
    )


class FaultInjector:
    def __init__(self, faults: Faults):
        self.faults = faults
        self.calls: Dict[str, int] = {}

    async def invoke(
        self,
        node_name: str,
        real: Any,
        *args: Any,
        sync: bool = False,
        **kwargs: Any,
    ) -> Any:
        call_number = self.calls.get(node_name, 0) + 1
        self.calls[node_name] = call_number

        if node_name == "market_research" and call_number <= self.faults.market_research_failures:
            raise RuntimeError("simulated external market research API outage")

        if node_name == "critic_validation" and call_number <= self.faults.critic_research_failures:
            return _forced_research_critique()

        if sync:
            result = await asyncio.to_thread(real, *args, **kwargs)
        else:
            result = await real(*args, **kwargs)

        if node_name == "revenue_estimation" and call_number <= self.faults.finance_invalid_rounds:
            result = _corrupt_finance_output(result)
        return result


def _make_wrapper(
    node_name: str,
    real: Any,
    expected_type: type[BaseModel],
    injector: FaultInjector,
    invocations: List[InvocationRecord],
    sync: bool,
) -> Any:
    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        started = time.perf_counter()
        input_chars = _payload_chars(args, kwargs)
        try:
            result = await injector.invoke(
                node_name,
                real,
                *args,
                sync=sync,
                **kwargs,
            )
        except Exception as exc:
            invocations.append(
                InvocationRecord(
                    node_name=node_name,
                    success=False,
                    duration_ms=(time.perf_counter() - started) * 1000,
                    input_chars=input_chars,
                    output_chars=0,
                    error=f"{type(exc).__name__}: {exc}",
                )
            )
            raise

        success, error = _validate_output(result, expected_type)
        invocations.append(
            InvocationRecord(
                node_name=node_name,
                success=success,
                duration_ms=(time.perf_counter() - started) * 1000,
                input_chars=input_chars,
                output_chars=_payload_chars(result),
                error=error,
            )
        )
        return result

    wrapper.__name__ = f"evaluated_{node_name}"
    return wrapper


def _event_capture(events: List[Dict[str, Any]]) -> Any:
    async def capture(**kwargs: Any) -> None:
        stage = kwargs.get("stage", "INITIALIZED")
        events.append(
            {
                "event_type": kwargs.get("event_type", "STAGE_PROGRESS"),
                "stage": stage.value if hasattr(stage, "value") else str(stage),
                "progress_pct": kwargs.get("progress_pct", 0),
                "message": kwargs.get("message", ""),
                "data": _jsonable(kwargs.get("data") or {}),
            }
        )

    return capture


@contextmanager
def _patched_domain_interfaces(
    injector: FaultInjector,
    invocations: List[InvocationRecord],
    events: List[Dict[str, Any]],
) -> Iterable[None]:
    wrappers = [
        (
            bi_interface,
            "run_idea_analysis",
            _make_wrapper(
                "idea_analysis",
                bi_interface.run_idea_analysis,
                IdeaAnalysisOutput,
                injector,
                invocations,
                sync=False,
            ),
        ),
        (
            research_interface,
            "run_market_research",
            _make_wrapper(
                "market_research",
                research_interface.run_market_research,
                MarketResearchOutput,
                injector,
                invocations,
                sync=False,
            ),
        ),
        (
            research_interface,
            "run_critic_validation",
            _make_wrapper(
                "critic_validation",
                research_interface.run_critic_validation,
                CriticValidationOutput,
                injector,
                invocations,
                sync=False,
            ),
        ),
        (
            bi_interface,
            "run_business_model",
            _make_wrapper(
                "business_model",
                bi_interface.run_business_model,
                BusinessModelOutput,
                injector,
                invocations,
                sync=False,
            ),
        ),
        (
            finance_interface,
            "run_revenue_estimation",
            _make_wrapper(
                "revenue_estimation",
                finance_interface.run_revenue_estimation,
                RevenueEstimationOutput,
                injector,
                invocations,
                sync=True,
            ),
        ),
        (
            marketing_interface,
            "run_marketing_plan",
            _make_wrapper(
                "marketing_plan",
                marketing_interface.run_marketing_plan,
                MarketingPlanOutput,
                injector,
                invocations,
                sync=True,
            ),
        ),
        (
            marketing_interface,
            "run_roadmap_synthesis",
            _make_wrapper(
                "roadmap_synthesis",
                marketing_interface.run_roadmap_synthesis,
                StartupRoadmap,
                injector,
                invocations,
                sync=True,
            ),
        ),
    ]

    with ExitStack() as stack:
        for module, name, wrapper in wrappers:
            stack.enter_context(patch.object(module, name, wrapper))
        stack.enter_context(patch.object(graph_nodes, "publish_event", _event_capture(events)))
        yield


def _coerce_state(raw: Any) -> VentureState:
    if isinstance(raw, VentureState):
        return raw
    return VentureState.model_validate(raw)


async def run_scenario(scenario: Scenario) -> ScenarioRun:
    invocations: List[InvocationRecord] = []
    events: List[Dict[str, Any]] = []
    injector = FaultInjector(scenario.faults)
    founder_input = FounderInput.model_validate(scenario.founder_input)
    venture_id = f"evaluation-{scenario.scenario_id}"
    initial_state = create_initial_venture_state(
        venture_id=venture_id,
        founder_input=founder_input,
    )
    config = get_thread_config(venture_id)
    workflow = build_venture_workflow(
        checkpointer=MemorySaver(),
        enable_hitl_interrupt=False,
    )

    started = time.perf_counter()
    error: Optional[str] = None
    try:
        with _patched_domain_interfaces(injector, invocations, events):
            raw_state = await workflow.ainvoke(initial_state, config=config)
        final_state = _coerce_state(raw_state)
    except Exception as exc:
        error = f"{type(exc).__name__}: {exc}"
        final_state = await get_venture_state(venture_id) or initial_state

    elapsed = time.perf_counter() - started
    run = ScenarioRun(
        scenario=scenario,
        final_state=final_state,
        invocations=invocations,
        events=events,
        elapsed_seconds=elapsed,
        error=error,
    )
    run.expectation_failures = _check_expectations(run)
    return run


def _check_expectations(run: ScenarioRun) -> List[str]:
    expected = run.scenario.expected
    state = run.final_state
    failures: List[str] = []

    if "completed" in expected:
        actual = state.current_stage == WorkflowStage.COMPLETED
        if actual != bool(expected["completed"]):
            failures.append(f"completed={actual}, expected {bool(expected['completed'])}")

    for field_name in ("replan_count", "market_replan_count", "finance_retune_count"):
        actual = getattr(state, field_name)
        if field_name in expected and actual != expected[field_name]:
            failures.append(f"{field_name}={actual}, expected {expected[field_name]}")
        min_key = f"min_{field_name}"
        max_key = f"max_{field_name}"
        if min_key in expected and actual < expected[min_key]:
            failures.append(f"{field_name}={actual}, expected >= {expected[min_key]}")
        if max_key in expected and actual > expected[max_key]:
            failures.append(f"{field_name}={actual}, expected <= {expected[max_key]}")

    if "replan_target" in expected and state.replan_target != expected["replan_target"]:
        failures.append(
            f"replan_target={state.replan_target!r}, expected {expected['replan_target']!r}"
        )

    for text in expected.get("warnings_contain", []):
        if not any(text in warning for warning in state.warnings):
            failures.append(f"missing state warning containing {text!r}")

    min_warning_events = expected.get("min_warning_events")
    if min_warning_events is not None and run.warning_event_count < min_warning_events:
        failures.append(
            f"warning_events={run.warning_event_count}, expected >= {min_warning_events}"
        )

    if run.error and expected.get("completed", True):
        failures.append(f"workflow raised {run.error}")
    return failures


def _usage_records(invocations: Iterable[InvocationRecord]) -> List[TokenUsage]:
    return [
        TokenUsage(
            prompt_tokens=record.prompt_tokens,
            completion_tokens=record.completion_tokens,
        )
        for record in invocations
    ]


def _run_metrics(run: ScenarioRun) -> Dict[str, MetricResult]:
    return {
        "citation": calculate_citation_rate([run.final_state.market_research]),
        "schema": calculate_schema_compliance(
            [record.success for record in run.invocations]
        ),
        "completion": calculate_workflow_completion([run.completed]),
        "latency": calculate_latency([run.elapsed_seconds]),
        "cost": calculate_cost(_usage_records(run.invocations)),
    }


def _aggregate_metrics(runs: Sequence[ScenarioRun]) -> Dict[str, MetricResult]:
    return {
        "citation": calculate_citation_rate(
            [run.final_state.market_research for run in runs]
        ),
        "schema": calculate_schema_compliance(
            [record.success for run in runs for record in run.invocations]
        ),
        "completion": calculate_workflow_completion([run.completed for run in runs]),
        "latency": calculate_latency([run.elapsed_seconds for run in runs]),
        "cost": calculate_cost(
            _usage_records(
                record for run in runs for record in run.invocations
            )
        ),
    }


def _metric_cell(result: MetricResult) -> str:
    if result.passed is None:
        return result.display
    return f"{result.display} {'ok' if result.passed else 'FAIL'}"


def _format_table(headers: Sequence[str], rows: Sequence[Sequence[str]]) -> str:
    widths = [
        max(len(header), *(len(str(row[index])) for row in rows))
        for index, header in enumerate(headers)
    ]
    header_line = " | ".join(
        header.ljust(widths[index]) for index, header in enumerate(headers)
    )
    separator = "-+-".join("-" * width for width in widths)
    body = [
        " | ".join(str(value).ljust(widths[index]) for index, value in enumerate(row))
        for row in rows
    ]
    return "\n".join([header_line, separator, *body])


def _replan_summary(state: VentureState) -> str:
    return f"{state.replan_count}/{state.market_replan_count}/{state.finance_retune_count}"


def _aggregate_replan_summary(runs: Sequence[ScenarioRun]) -> str:
    return "/".join(
        str(sum(getattr(run.final_state, field_name) for run in runs))
        for field_name in ("replan_count", "market_replan_count", "finance_retune_count")
    )


def _print_report(runs: Sequence[ScenarioRun], live: bool) -> bool:
    aggregate = _aggregate_metrics(runs)
    rows: List[List[str]] = []

    for run in runs:
        metrics = _run_metrics(run)
        verdict = "PASS" if not run.expectation_failures else "FAIL"
        rows.append(
            [
                run.scenario.scenario_id,
                _metric_cell(metrics["citation"]),
                _metric_cell(metrics["schema"]),
                _metric_cell(metrics["completion"]),
                _metric_cell(metrics["latency"]),
                _metric_cell(metrics["cost"]),
                _replan_summary(run.final_state),
                verdict,
            ]
        )

    aggregate_verdict = "PASS" if _overall_passed(runs, aggregate) else "FAIL"
    rows.append(
        [
            "OVERALL",
            _metric_cell(aggregate["citation"]),
            _metric_cell(aggregate["schema"]),
            _metric_cell(aggregate["completion"]),
            _metric_cell(aggregate["latency"]),
            _metric_cell(aggregate["cost"]),
            _aggregate_replan_summary(runs),
            aggregate_verdict,
        ]
    )

    print(
        _format_table(
            [
                "Scenario",
                "Citations",
                "Schema",
                "Complete",
                "Latency",
                "Cost (est.)",
                "R/M/F",
                "Verdict",
            ],
            rows,
        )
    )
    print()
    print(
        "Targets: citations 100%, schema >95%, completion >=90%, "
        "latency <480s, cost tracked."
    )
    print(f"Mode: {'live-provider' if live else 'offline deterministic'}")
    print(
        "Metric details: "
        f"citations {aggregate['citation'].details['verified_external_citations']}/"
        f"{aggregate['citation'].details['total_factual_market_claims']}; "
        f"schema {aggregate['schema'].details['valid_pydantic_contract_outputs']}/"
        f"{aggregate['schema'].details['total_agent_invocations']}; "
        f"completion {aggregate['completion'].details['ventures_reaching_completed']}/"
        f"{aggregate['completion'].details['total_ventures_started']}; "
        f"tokens {aggregate['cost'].details['total_tokens']}."
    )

    failed_expectations = [
        (run.scenario.scenario_id, failure)
        for run in runs
        for failure in run.expectation_failures
    ]
    if failed_expectations:
        print()
        print("Expectation failures:")
        for scenario_id, failure in failed_expectations:
            print(f"- {scenario_id}: {failure}")

    return _overall_passed(runs, aggregate)


def _overall_passed(
    runs: Sequence[ScenarioRun],
    aggregate: Dict[str, MetricResult],
) -> bool:
    expectations_met = all(not run.expectation_failures for run in runs)
    targets_met = all(
        result.passed is not False for result in aggregate.values()
    )
    return expectations_met and targets_met


def load_scenarios(selected: Optional[Sequence[str]] = None) -> List[Scenario]:
    selected_ids = set(selected or [])
    scenarios: List[Scenario] = []

    for path in sorted(SCENARIO_DIR.glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        scenario_id = data.get("scenario_id", path.stem)
        if selected_ids and scenario_id not in selected_ids:
            continue
        founder_payload = data.get("founder_input")
        if founder_payload is None:
            founder_payload = {
                "startup_idea": data.get("idea", "AI venture concept"),
                "target_market": data.get("target_market", "Technology"),
                "target_geography": data.get("target_geography", "Global"),
                "budget": data.get("budget", 50000.0),
                "timeline_months": data.get("timeline_months", 6),
                "goals": data.get("goals", "Achieve product-market fit"),
            }
        scenarios.append(
            Scenario(
                scenario_id=scenario_id,
                description=data.get("description", ""),
                founder_input=founder_payload,
                faults=Faults(**data.get("faults", {})),
                expected=data.get("expected", {}),
            )
        )

    if selected_ids:
        found = {scenario.scenario_id for scenario in scenarios}
        missing = selected_ids - found
        if missing:
            raise ValueError(f"Unknown scenario(s): {', '.join(sorted(missing))}")
    if not scenarios:
        raise ValueError(f"No scenario fixtures found in {SCENARIO_DIR}.")
    return scenarios


@contextmanager
def _provider_environment(live: bool) -> Iterable[None]:
    if live:
        previous_mock_search = os.environ.get("MOCK_SEARCH")
        os.environ["MOCK_SEARCH"] = "false"
        try:
            yield
        finally:
            if previous_mock_search is None:
                os.environ.pop("MOCK_SEARCH", None)
            else:
                os.environ["MOCK_SEARCH"] = previous_mock_search
        return

    overrides = {
        "OPENAI_API_KEY": "your-offline-evaluation",
        "ANTHROPIC_API_KEY": "your-offline-evaluation",
        "GOOGLE_API_KEY": "your-offline-evaluation",
        "TAVILY_API_KEY": "mock",
        "MOCK_SEARCH": "true",
    }
    previous = {key: os.environ.get(key) for key in overrides}
    os.environ.update(overrides)
    try:
        yield
    finally:
        for key, value in previous.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


async def run_all(scenarios: Sequence[Scenario]) -> List[ScenarioRun]:
    runs: List[ScenarioRun] = []
    for scenario in scenarios:
        runs.append(await run_scenario(scenario))
    return runs


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run the AI Co-Founder benchmark evaluation harness."
    )
    parser.add_argument(
        "--live",
        action="store_true",
        help="Allow configured live LLM/search providers instead of deterministic fallbacks.",
    )
    parser.add_argument(
        "--scenario",
        action="append",
        default=None,
        help="Run only the named scenario (repeatable). Defaults to all scenarios.",
    )
    args = parser.parse_args(argv)

    try:
        scenarios = load_scenarios(args.scenario)
    except ValueError as exc:
        parser.error(str(exc))

    with _provider_environment(args.live):
        runs = asyncio.run(run_all(scenarios))

    passed = _print_report(runs, live=args.live)
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
