"""Extract a small real UCI sample. Does not call models or alter source data."""
from pathlib import Path
import argparse
import hashlib
import json
import math


def extract(raw: Path, output: Path):
    if output.exists():
        raise FileExistsError(f"Preserve existing student input: {output}")
    samples, sources = [], []
    for sensor, hz, unit in (("TS1", 1, "°C"), ("PS1", 100, "bar"), ("FS1", 10, "L/min")):
        source = raw / f"{sensor}.txt"
        digest = hashlib.sha256(source.read_bytes()).hexdigest()
        with source.open(encoding="utf-8") as f:
            for cycle_id, line in enumerate(f):
                if cycle_id > 102:
                    break
                if cycle_id < 100:
                    continue
                values = [float(x) for x in line.split()]
                if len(values) != 60 * hz or not all(math.isfinite(x) for x in values):
                    raise ValueError(f"Unexpected raw input: {sensor}, cycle={cycle_id}")
                for elapsed in range(3):
                    samples.append({"sensor": sensor, "origin_cycle_id": cycle_id,
                                    "elapsed_s": elapsed, "hz": hz, "unit": unit,
                                    "samples": values[elapsed * hz:(elapsed + 1) * hz]})
        sources.append({"file": source.name, "sha256": digest})
    if len(samples) != 27:
        raise ValueError("Expected 3 sensors × 3 cycles × 3 one-second windows")
    result = {"source": "UCI Condition monitoring of hydraulic systems; supplied HydOps raw copy",
              "is_synthetic": False, "cycle_numbering": "zero-based source row",
              "time_note": "elapsed_s is position within a 60-second cycle, not collection timestamp",
              "selection": {"origin_cycle_id": [100, 101, 102], "elapsed_s": [0, 1, 2]},
              "source_files": sources, "windows": samples}
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Prepared {len(samples)} sample windows: {output}")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--raw", required=True, type=Path)
    p.add_argument("--output", required=True, type=Path)
    a = p.parse_args()
    extract(a.raw, a.output)
