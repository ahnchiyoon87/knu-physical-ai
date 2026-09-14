"""Configuration is explicit; missing credentials never select another provider."""
import json
import os
from functools import lru_cache
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]


@lru_cache
def settings() -> dict:
    return yaml.safe_load((ROOT / "config.yaml").read_text(encoding="utf-8"))


@lru_cache
def mapping() -> dict:
    return json.loads((ROOT / "mapping.json").read_text(encoding="utf-8"))


def env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise ValueError(f"설정이 없습니다: {name}")
    return value


def configured_path(value: str) -> Path:
    path = Path(value).expanduser()
    return path if path.is_absolute() else ROOT / path


def source(source_id: str, profile: str) -> dict:
    sources = mapping()["profiles"].get(profile, {}).get("sources", {})
    if source_id not in sources:
        raise ValueError(f"등록되지 않은 원천: {profile}/{source_id}")
    return sources[source_id]


def analysis_source(source_id:str,profile:str)->dict:
    config=dict(source(source_id,profile))
    selection=config.get('analysis_view','raw')
    if selection not in {'raw','clean'}:raise ValueError('analysis_view는 raw 또는 clean입니다')
    config['raw_table']=config['table']
    if selection=='clean':
        if not config.get('quality_rules'):raise ValueError('정제 분석에는 확인된 quality_rules가 필요합니다')
        config['table']=config.get('clean_table',config['table']+'_clean')
        config['provenance']+='; analysis_view=clean: 원본 보존 정제 뷰'
    return config

