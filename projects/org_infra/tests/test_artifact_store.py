import pytest

from src.schemas.agent_artifacts import (
    ArtifactMetadata,
    FeedbackSynthesisArtifact,
    Objection,
    PressureTestArtifact,
    UXRArtifact,
)
from src.schemas.handoff_package import AlignmentItem, ConflictItem, EvidenceItem, Persona
from src.store.artifact_store import ArtifactStore


@pytest.fixture
def store(tmp_path):
    return ArtifactStore(base_dir=tmp_path)


@pytest.fixture
def metadata():
    return ArtifactMetadata(agent_id="test", phase="discovery", run_id="run-001")


class TestArtifactStoreWriteRead:
    def test_write_and_read_uxr(self, store, metadata):
        artifact = UXRArtifact(
            metadata=metadata,
            personas=[
                Persona(
                    name="Power User",
                    description="Frequent user",
                    needs=["speed"],
                    pain_points=["latency"],
                    data_sources=["logs"],
                )
            ],
            problem_validation=[
                EvidenceItem(source="analytics", finding="High bounce", confidence="high")
            ],
            user_signals=["low filter usage"],
            methodology="Interviews",
        )

        path = store.write("run-001", "uxr", artifact)
        assert path.endswith("uxr.json")

        loaded = store.read("run-001", "uxr", UXRArtifact)
        assert loaded.personas[0].name == "Power User"
        assert loaded.methodology == "Interviews"

    def test_write_and_read_pressure_test(self, store, metadata):
        artifact = PressureTestArtifact(
            metadata=metadata,
            objections=[
                Objection(
                    target_claim="40% reduction",
                    objection="No baseline exists",
                    severity="high",
                    evidence="Analytics lacks intent tracking",
                )
            ],
            overall_assessment="Unsupported claims",
        )

        store.write("run-001", "pressure_test", artifact)
        loaded = store.read("run-001", "pressure_test", PressureTestArtifact)
        assert len(loaded.objections) == 1
        assert loaded.objections[0].target_claim == "40% reduction"


class TestArtifactStoreList:
    def test_list_multiple(self, store, metadata):
        uxr = UXRArtifact(metadata=metadata)
        feedback = FeedbackSynthesisArtifact(
            metadata=metadata,
            alignments=[
                AlignmentItem(
                    internal_finding="Discovery gap",
                    external_input="Confirmed",
                )
            ],
            conflicts=[
                ConflictItem(
                    internal_finding="Real-time needed",
                    external_input="Batch preferred",
                    severity="medium",
                )
            ],
        )

        store.write("run-001", "uxr", uxr)
        store.write("run-001", "feedback_synthesis", feedback)

        agents = store.list_artifacts("run-001")
        assert agents == ["feedback_synthesis", "uxr"]

    def test_list_empty_run(self, store):
        assert store.list_artifacts("nonexistent-run") == []


class TestArtifactStoreExists:
    def test_exists_true(self, store, metadata):
        store.write("run-001", "uxr", UXRArtifact(metadata=metadata))
        assert store.exists("run-001", "uxr") is True

    def test_exists_false(self, store):
        assert store.exists("run-001", "uxr") is False


class TestArtifactStoreErrors:
    def test_read_nonexistent_raises(self, store):
        with pytest.raises(FileNotFoundError):
            store.read("run-001", "nonexistent", UXRArtifact)


class TestArtifactStoreOverwrite:
    def test_overwrite_replaces(self, store, metadata):
        v1 = UXRArtifact(metadata=metadata, methodology="V1")
        v2 = UXRArtifact(metadata=metadata, methodology="V2")

        store.write("run-001", "uxr", v1)
        store.write("run-001", "uxr", v2)

        loaded = store.read("run-001", "uxr", UXRArtifact)
        assert loaded.methodology == "V2"
