import pytest

from src.agents.ds import DataScienceAgent
from src.agents.evaluation import EvaluationAgent
from src.agents.feedback_synthesis import FeedbackSynthesisAgent
from src.agents.pm import PMAgent
from src.agents.pressure_test import PressureTestAgent
from src.agents.uxr import UXResearchAgent
from src.integrations.comms import MockCommsAdapter


PROBLEM = "Users cannot discover relevant content in large catalogs"


class TestUXResearchAgent:
    def test_produces_valid_artifact(self):
        agent = UXResearchAgent()
        result = agent.run(PROBLEM, run_id="test-001")
        assert result.metadata.agent_id == "uxr"
        assert len(result.personas) >= 1
        assert all(p.data_sources for p in result.personas)
        assert len(result.problem_validation) >= 1
        assert result.methodology


class TestPMAgent:
    def test_produces_valid_artifact(self):
        uxr = UXResearchAgent().run(PROBLEM, run_id="test-001")
        uxr_dict = uxr.model_dump()

        adapter = MockCommsAdapter()
        agent = PMAgent(comms_adapter=adapter)
        result = agent.run(PROBLEM, uxr_dict, run_id="test-001")

        assert result.metadata.agent_id == "pm"
        assert result.product_pitch.title
        assert result.product_pitch.value_proposition
        assert len(result.requirements) >= 1
        assert result.prioritization_rationale

    def test_comms_cycle_runs(self):
        adapter = MockCommsAdapter()
        agent = PMAgent(comms_adapter=adapter)
        uxr = UXResearchAgent().run(PROBLEM).model_dump()
        result = agent.run(PROBLEM, uxr)

        assert len(adapter.sent) == 1
        assert any(c.direction == "outbound" for c in result.stakeholder_comms)
        assert any(c.direction == "inbound" for c in result.stakeholder_comms)


class TestDataScienceAgent:
    def test_produces_valid_artifact(self):
        uxr = UXResearchAgent().run(PROBLEM).model_dump()
        pm = PMAgent(MockCommsAdapter()).run(PROBLEM, uxr).model_dump()

        agent = DataScienceAgent()
        result = agent.run(PROBLEM, uxr, pm, run_id="test-001")

        assert result.metadata.agent_id == "ds"
        assert result.feasibility_assessment
        assert result.experiment_design is not None
        assert result.experiment_design.hypothesis
        assert len(result.quantitative_findings) >= 1


class TestEvaluationAgent:
    def test_produces_valid_artifact(self):
        uxr = UXResearchAgent().run(PROBLEM).model_dump()
        pm = PMAgent(MockCommsAdapter()).run(PROBLEM, uxr).model_dump()

        agent = EvaluationAgent()
        result = agent.run({"pm": pm, "uxr": uxr}, run_id="test-001")

        assert result.metadata.agent_id == "evaluation"
        assert len(result.success_criteria) >= 1
        assert result.test_harness_concept.intent
        assert result.eval_schema


class TestPressureTestAgent:
    def test_produces_specific_objections(self):
        uxr = UXResearchAgent().run(PROBLEM).model_dump()
        pm = PMAgent(MockCommsAdapter()).run(PROBLEM, uxr).model_dump()
        ds = DataScienceAgent().run(PROBLEM, uxr, pm).model_dump()

        agent = PressureTestAgent()
        result = agent.run({"pm": pm, "uxr": uxr, "ds": ds}, run_id="test-001")

        assert result.metadata.agent_id == "pressure_test"
        assert len(result.objections) >= 1
        for obj in result.objections:
            assert obj.target_claim, "Objection must name a specific claim"
            assert obj.objection, "Objection must have substance"
        assert result.overall_assessment

    def test_objections_are_not_generic(self):
        uxr = UXResearchAgent().run(PROBLEM).model_dump()
        pm = PMAgent(MockCommsAdapter()).run(PROBLEM, uxr).model_dump()
        ds = DataScienceAgent().run(PROBLEM, uxr, pm).model_dump()

        result = PressureTestAgent().run({"pm": pm, "uxr": uxr, "ds": ds})
        for obj in result.objections:
            assert len(obj.target_claim) > 10, "Target claim should be specific, not a stub"


class TestFeedbackSynthesisAgent:
    def test_produces_alignments_and_conflicts(self):
        uxr = UXResearchAgent().run(PROBLEM).model_dump()
        pm = PMAgent(MockCommsAdapter()).run(PROBLEM, uxr).model_dump()

        agent = FeedbackSynthesisAgent()
        result = agent.run({"pm": pm, "uxr": uxr}, run_id="test-001")

        assert result.metadata.agent_id == "feedback_synthesis"
        assert len(result.alignments) >= 1
        assert len(result.conflicts) >= 1
        assert result.synthesis_summary

    def test_conflict_has_resolution(self):
        uxr = UXResearchAgent().run(PROBLEM).model_dump()
        pm = PMAgent(MockCommsAdapter()).run(PROBLEM, uxr).model_dump()

        result = FeedbackSynthesisAgent().run({"pm": pm, "uxr": uxr})
        for conflict in result.conflicts:
            assert conflict.recommended_resolution
