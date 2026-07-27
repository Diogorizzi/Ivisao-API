# JSON Schemas Reference

Schemas for all files used by skill-creator. Keep these exact field names — the viewer and scripts depend on them.

---

## evals.json

Test cases for evaluating a skill.

```json
{
  "skill_name": "my-skill",
  "evals": [
    {
      "id": 0,
      "prompt": "The task prompt the agent will receive",
      "expected_output": "Human-readable description of what a good output looks like",
      "files": ["path/to/input/file.csv"],
      "assertions": [
        {
          "text": "Output contains a summary table with correct totals",
          "type": "output_check"
        },
        {
          "text": "All revenue figures are positive numbers",
          "type": "data_validation"
        }
      ]
    }
  ]
}
```

Fields:
- `id`: integer, unique within the file
- `prompt`: the task string passed to the agent
- `expected_output`: description for human reviewers
- `files`: list of input file paths (relative to skill directory), can be empty
- `assertions`: list of things to check; `text` is required, `type` is optional metadata

---

## eval_metadata.json

Per-eval metadata written into each eval directory during a run.

```json
{
  "eval_id": 0,
  "eval_name": "summary-table-generation",
  "prompt": "The task prompt the agent received",
  "assertions": [
    {
      "text": "Output contains a summary table with correct totals"
    }
  ]
}
```

---

## grading.json

Output from the grader agent. **Field names are exact — the viewer requires `text`, `passed`, `evidence`.**

```json
{
  "expectations": [
    {
      "text": "Output contains a summary table with correct totals",
      "passed": true,
      "evidence": "output.csv rows 1-5 contain totals column; verified sum matches 47,230"
    },
    {
      "text": "All revenue figures are positive numbers",
      "passed": false,
      "evidence": "Row 8 contains revenue value of -1200. All other rows are positive."
    }
  ],
  "summary": {
    "passed": 1,
    "failed": 1,
    "total": 2,
    "pass_rate": 0.5
  },
  "execution_metrics": {
    "total_tool_calls": 14,
    "files_created": 2,
    "errors_encountered": 0,
    "output_chars": 3800,
    "transcript_chars": 9200
  },
  "extracted_claims": [
    {
      "claim": "Agent claimed data was sorted by date ascending",
      "verified": true,
      "evidence": "Date column in output: 2024-01-01, 2024-01-02, 2024-01-03..."
    }
  ],
  "eval_feedback": [
    "Assertion 1 would pass even if the table has wrong column names — add header check"
  ]
}
```

---

## timing.json

Wall-clock timing captured from task completion notification.

```json
{
  "total_tokens": 84852,
  "duration_ms": 23332,
  "total_duration_seconds": 23.3
}
```

---

## benchmark.json

Aggregate benchmark produced by `scripts/aggregate_benchmark.py`. Put `with_skill` configurations before baselines.

```json
{
  "metadata": {
    "skill_name": "my-skill",
    "skill_path": "src/skills/shared/my-skill",
    "executor_model": "claude-sonnet-4-6",
    "analyzer_model": "claude-sonnet-4-6",
    "timestamp": "2026-04-30T12:00:00Z",
    "evals_run": [0, 1, 2],
    "runs_per_configuration": 3
  },
  "runs": [
    {
      "eval_id": 0,
      "configuration": "with_skill",
      "run_number": 1,
      "result": {
        "pass_rate": 1.0,
        "passed": 2,
        "failed": 0,
        "total": 2,
        "time_seconds": 18.4,
        "tokens": 82000,
        "tool_calls": 14,
        "errors": 0
      },
      "expectations": [
        {"text": "Summary table present", "passed": true, "evidence": "..."},
        {"text": "Revenue values positive", "passed": true, "evidence": "..."}
      ],
      "notes": []
    }
  ],
  "run_summary": {
    "with_skill": {
      "pass_rate": {"mean": 0.89, "stddev": 0.11, "min": 0.5, "max": 1.0},
      "time_seconds": {"mean": 21.3, "stddev": 2.4, "min": 18.1, "max": 24.7},
      "tokens": {"mean": 84500, "stddev": 3200, "min": 80100, "max": 89000}
    },
    "without_skill": {
      "pass_rate": {"mean": 0.54, "stddev": 0.22, "min": 0.0, "max": 1.0},
      "time_seconds": {"mean": 9.1, "stddev": 1.8, "min": 7.2, "max": 11.4},
      "tokens": {"mean": 41200, "stddev": 2800, "min": 38000, "max": 44500}
    },
    "delta": {
      "pass_rate": "+0.35",
      "time_seconds": "+12.2",
      "tokens": "+43300"
    }
  },
  "notes": [
    "with_skill substantially improves calculation verification (+0.56 delta on that assertion)",
    "File creation assertion is non-discriminating — passes at 1.0 for both configurations"
  ]
}
```

---

## comparison.json

Output from the blind comparator agent.

```json
{
  "winner": "A",
  "reasoning": "Output A addressed all requirements; Output B skipped the trend analysis",
  "rubric": {
    "A": {
      "correctness": 4, "completeness": 5, "accuracy": 4,
      "organization": 4, "formatting": 3, "usability": 4,
      "total": 24
    },
    "B": {
      "correctness": 3, "completeness": 2, "accuracy": 4,
      "organization": 4, "formatting": 4, "usability": 3,
      "total": 20
    }
  },
  "quality_summary": {
    "A": {
      "strengths": ["Complete coverage", "Accurate calculations"],
      "weaknesses": ["Inconsistent header levels"]
    },
    "B": {
      "strengths": ["Clean formatting"],
      "weaknesses": ["Missing trend analysis", "Arithmetic error in summary"]
    }
  }
}
```

---

## analysis.json

Output from the post-hoc analyzer agent.

```json
{
  "winner_analysis": {
    "root_cause": "Skill's verification step prevented calculation errors",
    "key_differentiators": [
      "Skill includes explicit validation pass before output",
      "Skill provides output template ensuring consistent structure"
    ]
  },
  "instruction_following": {
    "with_skill": {"score": 8, "notes": "Followed 4-step process; skipped optional citation"},
    "without_skill": {"score": null, "notes": "No skill instructions"}
  },
  "improvement_suggestions": [
    {
      "priority": "high",
      "category": "validation",
      "suggestion": "Add: verify column sums match row sums before outputting",
      "expected_impact": "Would prevent arithmetic errors observed in baseline"
    }
  ]
}
```
