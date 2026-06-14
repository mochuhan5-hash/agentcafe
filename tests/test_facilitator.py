from world_cafe.facilitator import _parse_facilitation


def test_parse_facilitation_strips_markdown_fence() -> None:
    result = _parse_facilitation(
        """
```json
{
  "facilitation_note": "按利益相关者、场景、风险和行动拆分。",
  "tables": [
    {"table_id": "table_01", "question": "谁会受到影响？"},
    {"table_id": "table_02", "question": "关键场景是什么？"},
    {"table_id": "table_03", "question": "主要风险在哪里？"},
    {"table_id": "table_04", "question": "下一步实验怎么做？"}
  ]
}
```
        """
    )

    assert result["facilitation_note"] == "按利益相关者、场景、风险和行动拆分。"
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
    {"table_id": "table_01", "question": "谁会受到影响？"},
    {"table_id": "table_02", "question": "关键场景是什么？"}
  ]
}
        """,
        table_count=2,
        parent_question="如何改善老龄社区服务？",
    )

    assert [table["parent_question"] for table in result["tables"]] == [
        "如何改善老龄社区服务？",
        "如何改善老龄社区服务？",
    ]
