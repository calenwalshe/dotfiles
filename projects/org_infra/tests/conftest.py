import pytest


@pytest.fixture
def sample_handoff_data():
    return {
        "problem_statement": {
            "statement": "Users cannot discover relevant content in large catalogs",
            "evidence": [
                {
                    "source": "user_interviews_q1",
                    "finding": "78% of users abandon search after 3 failed queries",
                    "confidence": "high",
                }
            ],
            "target_users": ["catalog_browsers", "power_searchers"],
            "validated": True,
        },
        "user_research": {
            "personas": [
                {
                    "name": "Casual Browser",
                    "description": "Explores catalog without specific intent",
                    "needs": ["serendipitous discovery", "visual browsing"],
                    "pain_points": ["information overload", "poor filtering"],
                    "data_sources": ["session_logs", "exit_surveys"],
                }
            ],
            "problem_validation": [
                {
                    "source": "analytics",
                    "finding": "Average session depth is 2.1 pages",
                    "confidence": "high",
                }
            ],
            "user_signals": ["high bounce rate on search results", "low filter usage"],
            "methodology": "Mixed methods: behavioral analytics + 12 user interviews",
        },
        "product_pitch": {
            "title": "Smart Content Discovery",
            "summary": "AI-powered content recommendations based on browsing patterns",
            "value_proposition": "Reduce search abandonment by 40% through contextual recommendations",
            "target_audience": "Catalog browsers who struggle with discovery",
            "differentiation": "Uses behavioral signals, not just keyword matching",
        },
        "requirements": {
            "build": [
                {
                    "id": "REQ-01",
                    "description": "Recommendation engine based on browsing history",
                    "priority": "critical",
                    "rationale": "Core value prop — without this, no product",
                    "acceptance_criteria": [
                        "Returns relevant recommendations within 200ms",
                        "Recommendations improve with usage",
                    ],
                }
            ],
            "not_build": ["Full-text search replacement — existing search stays"],
            "prioritization_rationale": "Focus on recommendation engine first, iterate on UI second",
        },
        "eval_criteria": {
            "success_criteria": [
                {
                    "metric": "Search abandonment rate",
                    "target": "< 30% (down from 78%)",
                    "measurement_method": "Analytics funnel tracking",
                }
            ],
            "guardrails": ["No PII in recommendation signals", "Latency < 500ms p99"],
        },
        "test_harness_concept": {
            "intent": "Validate recommendation relevance and performance under load",
            "structure": [
                {
                    "name": "Relevance test",
                    "description": "Given known browsing pattern, recommendations match expected categories",
                    "category": "functional",
                    "expected_behavior": "Top-3 recommendations include at least 1 from browsed category",
                }
            ],
            "coverage_areas": ["relevance", "latency", "cold_start"],
        },
        "feedback_synthesis": {
            "stakeholder_inputs": [
                {
                    "stakeholder": "eng_lead",
                    "input_text": "Concerned about recommendation model training cost",
                    "sentiment": "cautious",
                }
            ],
            "alignments": [
                {
                    "internal_finding": "Users need better discovery",
                    "external_input": "Eng lead agrees discovery is the gap",
                    "assessment": "Strong alignment on problem definition",
                }
            ],
            "conflicts": [
                {
                    "internal_finding": "Real-time recommendations needed",
                    "external_input": "Eng lead prefers batch processing for cost",
                    "severity": "medium",
                    "recommended_resolution": "Start with batch, add real-time in v2",
                }
            ],
        },
        "risk_log": {
            "risks": [
                {
                    "id": "RISK-01",
                    "description": "Cold start problem for new users with no browsing history",
                    "severity": "medium",
                    "likelihood": "high",
                    "mitigation": "Fallback to popularity-based recommendations",
                    "owner": "engineering",
                }
            ]
        },
        "open_assumptions": {
            "assumptions": [
                {
                    "statement": "Browsing history data is available via existing analytics pipeline",
                    "status": "open",
                    "owner": "engineering",
                    "resolution_needed_by": "Before implementation starts",
                }
            ]
        },
    }
