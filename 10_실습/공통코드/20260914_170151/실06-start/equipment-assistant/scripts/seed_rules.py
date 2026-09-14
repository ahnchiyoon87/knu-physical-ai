"""Create named teaching rules once. Existing rules are never updated here."""
import json
import sys
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from psycopg.types.json import Jsonb
from backend.common.config import ROOT,source
from backend.common.gateway import database


def main():
    definitions=json.loads((ROOT/'rules.json').read_text(encoding='utf-8'))
    with database() as db:
        for rule in definitions:
            definition=rule['definition']
            source(definition['source_id'],definition['profile'])
            result=db.execute("INSERT INTO lab.rules(id,version,definition,active) VALUES(%s,1,%s,true) "
                "ON CONFLICT(id) DO NOTHING RETURNING id",(rule['id'],Jsonb(definition))).fetchone()
            print(rule['id'], 'created' if result else 'preserved')


if __name__=='__main__':
    main()
