import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from src.schemas.handoff_package import HandoffPackage


SCHEMA_PATH = Path("src/schemas/handoff-package-schema.json")


class TestHandoffPackageValidation:
    def test_valid_package_from_fixture(self, sample_handoff_data):
        package = HandoffPackage(**sample_handoff_data)
        assert package.problem_statement.statement
        assert package.problem_statement.validated is True
        assert len(package.user_research.personas) == 1
        assert len(package.requirements.build) == 1
        assert len(package.feedback_synthesis.conflicts) == 1

    def test_missing_required_field_raises(self):
        with pytest.raises(ValidationError):
            HandoffPackage()

    def test_missing_problem_statement_raises(self, sample_handoff_data):
        data = {k: v for k, v in sample_handoff_data.items() if k != "problem_statement"}
        with pytest.raises(ValidationError):
            HandoffPackage(**data)

    def test_invalid_priority_raises(self, sample_handoff_data):
        data = sample_handoff_data.copy()
        data["requirements"] = {
            "build": [
                {
                    "id": "REQ-01",
                    "description": "Test",
                    "priority": "not_a_priority",
                }
            ],
            "not_build": [],
        }
        with pytest.raises(ValidationError):
            HandoffPackage(**data)

    def test_all_nine_sections_present(self, sample_handoff_data):
        package = HandoffPackage(**sample_handoff_data)
        expected_sections = [
            "problem_statement",
            "user_research",
            "product_pitch",
            "requirements",
            "eval_criteria",
            "test_harness_concept",
            "feedback_synthesis",
            "risk_log",
            "open_assumptions",
        ]
        for section in expected_sections:
            assert hasattr(package, section), f"Missing section: {section}"


class TestJSONSchema:
    def test_schema_file_exists(self):
        assert SCHEMA_PATH.exists()

    def test_schema_loads_valid_json(self):
        schema = json.loads(SCHEMA_PATH.read_text())
        assert "properties" in schema

    def test_schema_has_all_sections(self):
        schema = json.loads(SCHEMA_PATH.read_text())
        expected = [
            "metadata",
            "problem_statement",
            "user_research",
            "product_pitch",
            "requirements",
            "eval_criteria",
            "test_harness_concept",
            "feedback_synthesis",
            "risk_log",
            "open_assumptions",
        ]
        for section in expected:
            assert section in schema["properties"], f"Missing schema section: {section}"


class TestRoundTrip:
    def test_model_to_json_to_model(self, sample_handoff_data):
        original = HandoffPackage(**sample_handoff_data)
        json_str = original.model_dump_json()
        reconstructed = HandoffPackage.model_validate_json(json_str)

        assert reconstructed.problem_statement.statement == original.problem_statement.statement
        assert len(reconstructed.user_research.personas) == len(original.user_research.personas)
        assert len(reconstructed.requirements.build) == len(original.requirements.build)
        assert len(reconstructed.feedback_synthesis.conflicts) == len(
            original.feedback_synthesis.conflicts
        )

    def test_model_to_dict_to_model(self, sample_handoff_data):
        original = HandoffPackage(**sample_handoff_data)
        as_dict = original.model_dump()
        reconstructed = HandoffPackage(**as_dict)
        assert reconstructed.product_pitch.title == original.product_pitch.title
