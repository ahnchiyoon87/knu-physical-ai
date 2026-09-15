"""Small offline checks. Not a student agent run or Docker integration test."""
from pathlib import Path
import ast
import hashlib
import json
import statistics
import tempfile
from prepare_day01 import extract

ROOT = Path(__file__).resolve().parents[1]


def main():
    (ROOT / "작업기록/현재검증").mkdir(parents=True, exist_ok=True)
    data = json.loads((ROOT / "실습자료/1일차/시작코드/data/sensor_windows.json").read_text(encoding="utf-8"))
    records = data["windows"]
    assert len(records) == 27 and data["is_synthetic"] is False
    assert len({(r["sensor"], r["origin_cycle_id"], r["elapsed_s"]) for r in records}) == 27
    expected = []
    for row in records:
        values = row["samples"]
        assert len(values) == row["hz"]
        expected.append({k: row[k] for k in ("sensor", "origin_cycle_id", "elapsed_s", "unit")} |
                        {"mean": statistics.mean(values), "min": min(values), "max": max(values), "n": len(values)})
    # Source fixture here tests the extractor only; never reported as real UCI data.
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        for sensor, hz in (("TS1", 1), ("PS1", 100), ("FS1", 10)):
            (base / f"{sensor}.txt").write_text(("\t".join(["2"] * (60 * hz)) + "\n") * 103)
        output = base / "sample.json"
        extract(base, output)
        trial = json.loads(output.read_text(encoding="utf-8"))
        assert len(trial["windows"]) == 27
        try:
            extract(base, output)
        except FileExistsError:
            pass
        else:
            raise AssertionError("Existing student input overwritten")
        (base / "TS1.txt").write_text("2\n" * 103)
        try:
            extract(base, base / "invalid.json")
        except ValueError:
            assert not (base / "invalid.json").exists()
        else:
            raise AssertionError("Malformed source accepted")
    files = list((ROOT / "플랫폼코드").rglob("*.py")) + list((ROOT / "제작도구").glob("*.py"))
    for p in files:
        ast.parse(p.read_text(encoding="utf-8-sig"), filename=str(p))
    record = {"scope": "offline structure and extraction only", "sample_windows": len(records),
              "python_files_parsed": len(files), "extractor_normal_input": "passed",
              "extractor_overwrite_rejected": "passed", "extractor_invalid_width_rejected": "passed",
              "sample_sha256": hashlib.sha256((ROOT / "실습자료/1일차/시작코드/data/sensor_windows.json").read_bytes()).hexdigest(),
              "docker_runtime": "not run in this preparation check", "model_calls": "not run",
              "student_completion": "not run", "new_ui_capture": "not run in this preparation check"}
    (ROOT / "작업기록/현재검증/1일차_참고값.json").write_text(json.dumps(expected, ensure_ascii=False, indent=2), encoding="utf-8")
    (ROOT / "작업기록/현재검증/준비검사.json").write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(record, ensure_ascii=True))


if __name__ == "__main__":
    main()
