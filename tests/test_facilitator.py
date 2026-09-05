from world_cafe.facilitator import _parse_facilitation


def test_parse_facilitation_strips_markdown_fence() -> None:
    result = _parse_facilitation(
        """
```json
{
  "facilitation_note": "Split by stakeholders, situations, risks, and actions.",
  "tables": [
    {"table_id": "table_01", "question": "Who will be affected?"},
    {"table_id": "table_02", "question": "What situation matters most?"},
    {"table_id": "table_03", "question": "Where are the main risks?"},
    {"table_id": "table_04", "question": "What experiment should come next?"}
  ]
}
```
        """
    )

    assert result["facilitation_note"] == "Split by stakeholders, situations, risks, and actions."
    assert [table["table_id"] for table in result["tables"]] == [
        "table_01",
        "table_02",
        "table_03",
        "table_04",
    ]


def test_parse_facilitation_adds_parent_question_to_each_table() -> None:
    result = _parse_facilitation(
        """
{
  "tables": [
    {"table_id": "table_01", "question": "Who will be affected?"},
    {"table_id": "table_02", "question": "What situation matters most?"}
  ]
}
        """,
        table_count=2,
        parent_question="How might we improve services for aging communities?",
    )

    assert [table["parent_question"] for table in result["tables"]] == [
        "How might we improve services for aging communities?",
        "How might we improve services for aging communities?",
    ]
