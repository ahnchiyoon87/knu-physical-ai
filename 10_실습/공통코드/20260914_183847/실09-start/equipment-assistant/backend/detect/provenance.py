"""Bind held-out predictions to immutable imported rows without inventing LOTs."""

def bind_predictions(result, rows, profile, source_id, import_record, artifact_id):
    by_row = {row["row_no"]: row for row in rows}
    if len(by_row) != len(rows):
        raise ValueError("원본 행 번호가 중복됩니다")
    required = ("id", "file_hash", "mapping_hash")
    if not import_record or any(not import_record.get(key) for key in required):
        raise ValueError("원천 적재와 파일/매핑 해시를 확인하세요")
    prefix = f"{profile}:{source_id}"
    provenance = f"import={import_record['id']}; artifact={artifact_id}"
    predictions, edges, seen = [], [], set()
    for item in result["predictions"]:
        number = item["row_no"]
        if type(number) is not int or number < 1 or number not in by_row or number in seen:
            raise ValueError("평가 행이 원본에 없거나 중복됩니다")
        seen.add(number)
        lot = by_row[number].get("lot_id")
        row_id = f"{prefix}:row:{number}"
        lot_target = None if lot is None or str(lot) == "" else f"{prefix}:lot:{lot}"
        predictions.append({**item, "profile": profile, "source_id": source_id,
                            "import_id": import_record["id"], "row_id": row_id,
                            "lot_id": lot, "lot_target": lot_target})
        edges.append({"source": artifact_id, "source_type": "model_result", "relation": "evaluated_row",
                      "target": row_id, "target_type": "source_row", "provenance": provenance})
        if lot_target:
            edges.append({"source": row_id, "source_type": "source_row", "relation": "belongs_to_lot",
                          "target": lot_target, "target_type": "lot", "provenance": f"import={import_record['id']}"})
    return {**result, "predictions": predictions, "input_import": {key: import_record[key] for key in required}}, edges
