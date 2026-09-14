"""Small offline checks; no model, database, network or student-run rehearsal."""
import pytest
from backend.common.response import reply
from backend.data.sql_guard import validate_select
from backend.detect.rules import classification_counts, detect_rows, first_threshold_crossing
from backend.rag.chunking import chunk_markdown, reciprocal_rank_fusion


@pytest.mark.parametrize("statement", [
    "SELECT count(*) FROM lab.synthetic_shots",
    "SELECT lot_id, avg(c22) FROM synthetic_shots GROUP BY lot_id",
    "WITH chosen AS (SELECT c22 FROM synthetic_shots) SELECT avg(c22) FROM chosen",
])
def test_readonly_queries_keep_original_text(statement):
    assert validate_select(statement, {"synthetic_shots"}) == statement


@pytest.mark.parametrize("statement", [
    "DELETE FROM synthetic_shots",
    "SELECT * FROM synthetic_shots; DROP TABLE synthetic_shots",
    "SELECT pg_sleep(20) FROM synthetic_shots",
    "SELECT * FROM lab.proposals",
    "SELECT * INTO copied FROM synthetic_shots",
    "SELECT * FROM synthetic_shots FOR UPDATE",
    "SELECT * FROM other.synthetic_shots",
    "WITH changed AS (DELETE FROM synthetic_shots RETURNING *) SELECT * FROM changed",
])
def test_sql_rejects_unregistered_operations(statement):
    with pytest.raises(ValueError):
        validate_select(statement, {"synthetic_shots"})


def test_none_requires_explanation_and_never_means_healthy():
    with pytest.raises(ValueError):
        reply("r", status="none")
    assert reply("r", status="none", reason="no rows").status == "none"


def test_table_chunks_keep_header_on_every_row():
    chunks = chunk_markdown("# Limits\n| Item | Unit |\n|---|---|\n| A | mm |\n| B | s |", 140, 10)
    assert len(chunks) == 2
    assert all("| Item | Unit |" in x["body"] and x["section"] == "Limits" for x in chunks)


def test_rrf_uses_both_lists_and_no_duplicate_bonus():
    assert reciprocal_rank_fusion(["a","a","b"], ["b","c"], 60) == ["b","a","c"]


def test_suppression_does_not_erase_observed_alarms():
    rows = [{"row_no": i, "lot_id": "0", "value": value} for i,value in enumerate([8,12,12,12,8,12])]
    result = detect_rows(rows, {"mode":"absolute","lower":0,"upper":10,"version":1,"suppression_shots":2})
    assert len(result) == 4
    assert sum(not x["suppressed"] for x in result) == 2


def test_relative_baseline_resets_between_lots():
    rows = [{"row_no": i, "lot_id": str(i//3), "value":value} for i,value in enumerate([8,8,8,12,12,12])]
    assert detect_rows(rows,{"mode":"relative","baseline_count":2,"width":3,"version":1}) == []


def test_class_imbalance_is_visible_beyond_accuracy():
    result = classification_counts([0]*99+[1], [0]*100)
    assert result["accuracy"] == .99 and result["recall"] == 0 and result["precision"] is None


def test_crossing_reports_horizon_censoring():
    assert first_threshold_crossing([8,7,6],5,"below") is None
    assert first_threshold_crossing([8,7,6],7,"below") == 2
