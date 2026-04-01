# Agent Role Contracts

Contracts for all 7 agents in the research-to-engineering handoff system. Each contract defines the agent's interface: what it receives, what it produces, what it can access, and how its output quality is measured.

---

## Contract Summary

| Agent | Input | Output | Tool Access | Key Eval Criterion |
|-------|-------|--------|-------------|--------------------|
| Research Orchestrator | Problem statement + all agent artifacts | Gate decision + current understanding | Artifact store (all), LangGraph state | Gate decisions cite specific artifacts |
| UX Research | Problem statement + user research data | Personas, problem validation, signals | Internal research repos, artifact store | Personas grounded in data, not invented |
| PM | Problem statement + UXR + prior artifacts | Product pitch, requirements, prioritization | Artifact store, comms interface | Requirements are testable with rationale |
| Data Science | Problem statement + UXR + PM requirements | Feasibility, data availability, experiments | Data systems, artifact store | Claims reference specific data sources |
| Evaluation | All prior phase artifacts | Success criteria, test harness concept | Artifact store | Criteria are measurable |
| Pressure Testing | Pitch + requirements + UXR + DS | Adversarial challenge report | Artifact store (read-only) | Objections are specific and named |
| Feedback Synthesis | Stakeholder responses + internal artifacts | Alignment/conflict report | Comms interface (read), artifact store | Surfaces real divergence, not paraphrasing |

---

## Agent 1: Research Orchestrator

### Input Schema

| Field | Type | Source |
|-------|------|--------|
| `problem_statement` | `str` | Human input (NL text) |
| `phase_artifacts` | `dict[str, BaseArtifact]` | Artifact store — all agent outputs for current phase |
| `current_phase` | `str` | LangGraph state — Discovery / Definition / Pitch & Evaluation / Handoff |
| `prior_gate_decisions` | `list[GateDecision]` | Own prior outputs from earlier phases |

### Output Schema

`OrchestratorArtifact`:
- `gate_decision`: `approve` | `reject`
- `cited_artifacts`: `list[str]` — artifact IDs that informed the decision
- `rationale`: `str` — structured reasoning for the decision
- `gaps`: `list[str]` — specific gaps if rejecting
- `current_understanding`: `str` — maintained "best current understanding" document

### Tool Access

- Artifact store: **read all** agent artifacts across all phases
- LangGraph state: **read/write** — sets phase, records gate decisions
- No external system access — Orchestrator is internal only

### Evaluation Rubric

| Criterion | Pass | Fail |
|-----------|------|------|
| Citation | Gate decision cites ≥1 specific artifact per agent whose output was evaluated | Decision references "the research" or "the findings" generically |
| Rejection specificity | Reject decisions name specific gaps (e.g., "UXR artifact lacks data sources for Persona 2") | Reject says "not ready" without specifics |
| Approve rigor | Approve decisions confirm each required artifact meets its contract | Approve without checking all required artifacts |
| Understanding maintenance | Current understanding doc updated at every phase transition | Stale or missing understanding doc |

---

## Agent 2: UX Research

### Input Schema

| Field | Type | Source |
|-------|------|--------|
| `problem_statement` | `str` | From Orchestrator intake |
| `research_data` | `list[DataSource]` | Meta internal research repos |
| `prior_artifacts` | `dict[str, BaseArtifact]` | Artifact store — prior phase outputs if any |

### Output Schema

`UXRArtifact`:
- `personas`: `list[Persona]` — each with name, description, needs, pain_points, data_sources
- `problem_validation`: `list[EvidenceItem]` — evidence supporting/challenging the problem statement
- `user_signals`: `list[str]` — behavioral signals from analytics or research
- `methodology`: `str` — how research was conducted

### Tool Access

- Meta internal research repos: **read** — user research databases, behavioral analytics
- Artifact store: **write** own artifact

### Evaluation Rubric

| Criterion | Pass | Fail |
|-----------|------|------|
| Data grounding | Every persona cites ≥1 data source | Personas read like marketing archetypes with no evidence |
| Problem validation | Evidence items cite specific sources and findings | Validation restates the problem statement as evidence |
| Signal specificity | User signals reference specific metrics or observations | Signals are generic ("users are frustrated") |
| Methodology | States method, sample, and limitations | No methodology section or "various research" |

---

## Agent 3: PM

### Input Schema

| Field | Type | Source |
|-------|------|--------|
| `problem_statement` | `str` | From Orchestrator intake |
| `uxr_artifact` | `UXRArtifact` | Artifact store |
| `prior_artifacts` | `dict[str, BaseArtifact]` | Artifact store — all available |

### Output Schema

`PMArtifact`:
- `product_pitch`: `ProductPitch` — title, summary, value_proposition, target_audience, differentiation
- `requirements`: `list[Requirement]` — each with id, description, priority, rationale, acceptance_criteria
- `prioritization_rationale`: `str` — why this ordering
- `stakeholder_comms`: `list[CommsRecord]` — record of outbound/inbound stakeholder messages

### Tool Access

- Artifact store: **read/write**
- Comms interface: **send** messages to stakeholders, **receive** responses
- Content schema check: output must pass before comms adapter sends

### Evaluation Rubric

| Criterion | Pass | Fail |
|-----------|------|------|
| Testable requirements | Every requirement has ≥1 acceptance criterion | Requirements are vague desires ("make it fast") |
| Priority rationale | Prioritization references UXR findings or business constraints | Priority ordering with no justification |
| Pitch grounding | Value proposition references validated problem and user needs | Pitch reads like marketing copy disconnected from research |
| Comms record | Stakeholder interactions logged with timestamps | No comms record or incomplete log |

---

## Agent 4: Data Science

### Input Schema

| Field | Type | Source |
|-------|------|--------|
| `problem_statement` | `str` | From Orchestrator intake |
| `uxr_artifact` | `UXRArtifact` | Artifact store |
| `pm_artifact` | `PMArtifact` | Artifact store |

### Output Schema

`DSArtifact`:
- `feasibility_assessment`: `str` — structured feasibility analysis
- `data_availability`: `list[DataSourceAssessment]` — each with source, availability, quality, gaps
- `experiment_design`: `ExperimentDesign` — hypothesis, methodology, metrics, sample requirements
- `quantitative_findings`: `list[str]` — key quantitative insights

### Tool Access

- Meta data systems: **read** — analytics, data catalogs, data quality reports
- Artifact store: **write** own artifact

### Evaluation Rubric

| Criterion | Pass | Fail |
|-----------|------|------|
| Source specificity | Feasibility claims reference specific data sources and their availability | Claims reference "the data" generically |
| Actionable experiments | Experiment design includes hypothesis, method, metrics, and sample size | Experiment design is a vague research plan |
| Gap identification | Missing data explicitly identified with impact assessment | Data gaps not mentioned or hand-waved |
| Quantitative rigor | Findings include specific numbers from actual data sources | Numbers appear fabricated or unsourced |

---

## Agent 5: Evaluation

### Input Schema

| Field | Type | Source |
|-------|------|--------|
| `all_phase_artifacts` | `dict[str, BaseArtifact]` | Artifact store — all outputs from Discovery + Definition phases |
| `pm_requirements` | `list[Requirement]` | From PM artifact |

### Output Schema

`EvaluationArtifact`:
- `success_criteria`: `list[SuccessCriterion]` — each with metric, target, measurement_method
- `test_harness_concept`: `TestHarnessConcept` — intent, structure (test cases), coverage_areas
- `eval_schema`: `dict` — how to score each artifact type

### Tool Access

- Artifact store: **read** all, **write** own artifact

### Evaluation Rubric

| Criterion | Pass | Fail |
|-----------|------|------|
| Measurability | Every success criterion has a numeric target or binary condition | Criteria are subjective ("users should like it") |
| Requirement coverage | Test harness concept maps to PM requirements | Test cases exist in isolation from requirements |
| Harness specificity | Test cases describe expected behavior, not just test names | Test plan is a list of names ("test login", "test search") |
| Eval schema completeness | Scoring rubric covers all agent artifact types | Some artifact types have no quality measure |

---

## Agent 6: Pressure Testing

### Input Schema

| Field | Type | Source |
|-------|------|--------|
| `product_pitch` | `ProductPitch` | From PM artifact |
| `requirements` | `list[Requirement]` | From PM artifact |
| `uxr_artifact` | `UXRArtifact` | Artifact store |
| `ds_artifact` | `DSArtifact` | Artifact store |

### Output Schema

`PressureTestArtifact`:
- `objections`: `list[Objection]` — each with target_claim, objection, severity, evidence, category
- `overall_assessment`: `str` — summary of pressure test findings
- `recommended_actions`: `list[str]` — what should change based on findings

### Tool Access

- Artifact store: **read only** — reads all prior artifacts but cannot modify them
- No external system access

### Evaluation Rubric

| Criterion | Pass | Fail |
|-----------|------|------|
| Specificity | Every objection names a specific claim from the pitch or requirements | Objections are generic ("this might not work") |
| Evidence basis | Objections cite evidence (from UXR, DS, or external knowledge) | Objections are opinions without supporting evidence |
| Non-trivial | Objections challenge substantive assumptions, not formatting | Objections are stylistic or trivial |
| Adversarial stance | Agent actively looks for weaknesses, not just confirms the pitch | Report reads like a positive review with mild caveats |

---

## Agent 7: Feedback Synthesis

### Input Schema

| Field | Type | Source |
|-------|------|--------|
| `stakeholder_responses` | `list[StakeholderResponse]` | Comms interface — responses collected by PM agent |
| `internal_artifacts` | `dict[str, BaseArtifact]` | Artifact store — all internal findings |

### Output Schema

`FeedbackSynthesisArtifact`:
- `stakeholder_inputs`: `list[StakeholderInput]` — raw inputs with attribution
- `alignments`: `list[AlignmentItem]` — where external input confirms internal findings
- `conflicts`: `list[ConflictItem]` — where external input contradicts internal findings, with severity and recommended resolution
- `synthesis_summary`: `str` — overall assessment of stakeholder alignment

### Tool Access

- Comms interface: **read** — accesses stakeholder responses
- Artifact store: **read** all internal artifacts, **write** own artifact

### Evaluation Rubric

| Criterion | Pass | Fail |
|-----------|------|------|
| Alignment specificity | Each alignment cites the specific internal finding it confirms | Alignments are vague ("stakeholders agree") |
| Conflict specificity | Each conflict cites the specific internal finding it contradicts | Conflicts are surface-level paraphrasing differences |
| Minimum coverage | Report surfaces ≥1 alignment and ≥1 conflict per run | Report is all alignments or all conflicts |
| Resolution quality | Conflicts include severity and recommended resolution path | Conflicts listed without actionable resolution |
