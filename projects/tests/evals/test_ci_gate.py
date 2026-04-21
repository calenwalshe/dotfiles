import pytest
import pandas as pd
import asyncio
import json
import os
from pathlib import Path
from datetime import datetime, timezone

from phoenix.evals import ClassificationEvaluator, async_evaluate_dataframe
from phoenix.evals.llm import LLM

CORRECTNESS_TEMPLATE = """
You are evaluating whether an answer is factually correct.

Question: {question}
Answer: {answer}

Is the answer correct? Respond with exactly one word: "correct" if the answer is accurate, or "incorrect" if it is wrong or misleading.
"""

TEST_CASES = [
    {"question": "What is the capital of France?", "answer": "Paris"},
    {"question": "What is 2 + 2?", "answer": "4"},
    {"question": "What planet is closest to the Sun?", "answer": "Mercury"},
    {"question": "What is the chemical symbol for water?", "answer": "H2O"},
    {"question": "Who wrote Romeo and Juliet?", "answer": "William Shakespeare"},
    {"question": "How many sides does a hexagon have?", "answer": "6"},
    {"question": "What is the boiling point of water in Celsius?", "answer": "100"},
    {"question": "What is the largest ocean on Earth?", "answer": "Pacific Ocean"},
    {"question": "What is the square root of 144?", "answer": "12"},
    {"question": "In what year did World War II end?", "answer": "1945"},
]


@pytest.fixture(scope="module")
def eval_results():
    llm = LLM(provider="openai", model="gpt-4o-mini")
    evaluator = ClassificationEvaluator(
        name="correctness",
        prompt_template=CORRECTNESS_TEMPLATE,
        llm=llm,
        choices={"correct": 1.0, "incorrect": 0.0},  # MUST be dict — list form silently produces NaN
    )
    df = pd.DataFrame(TEST_CASES)
    results = asyncio.run(
        async_evaluate_dataframe(dataframe=df, evaluators=[evaluator])
    )
    return results


def test_correctness_gate(eval_results):
    scores = eval_results["correctness_score"].apply(
        lambda x: x["score"] if isinstance(x, dict) else None
    ).dropna()

    # NaN guard: ensure no silent NaN regression from wrong choices format
    assert scores.count() == len(eval_results), (
        f"NaN scores detected: {scores.count()}/{len(eval_results)} valid. "
        "Check that choices= is dict form, not list form."
    )

    mean_score = scores.mean()

    # Write current.json for eval-gate.py
    current = {
        "metadata": {
            "created_at": datetime.now(timezone.utc).isoformat(),
            "model": "gpt-4o-mini",
            "eval_suite": "core-v1",
            "n_cases": len(eval_results),
        },
        "scores": {
            "correctness": round(float(mean_score), 4),
        },
    }
    evals_dir = Path(__file__).parent.parent.parent / "evals"
    evals_dir.mkdir(exist_ok=True)
    with open(evals_dir / "current.json", "w") as f:
        json.dump(current, f, indent=2)

    assert mean_score >= 0.75, (
        f"Correctness score {mean_score:.3f} below threshold 0.75. "
        f"Scores: {scores.tolist()}"
    )
