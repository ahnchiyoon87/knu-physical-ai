"""합성 기록으로 미측정·재시도·중복·잘못된 금액의 판별을 검사한다. 실측 아님."""
from pathlib import Path
import importlib.util
import json
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('measurement',Path(__file__).with_name('실습측정.py'))
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class MeasurementTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.folder = Path(self.tmp.name)
        self.session = {'trial_id':'SYNTHETIC-TEST', 'participant_id':'TEST-001','school_session_id':'실1'}
        (self.folder/'session.json').write_text(json.dumps(self.session),encoding='utf-8')
        (self.folder/'evidence.txt').write_text('SYNTHETIC UNIT TEST ONLY\nA\nB\n',encoding='utf-8')
        self.base = dict(self.session,record_kind='실측',request_path='coding',cost_scope='session_recurring',
            status='success',logical_task_id='synthetic-task',actual_provider_model_id='synthetic-model',
            provider_name='synthetic-provider',attempt=1,provider_request_id='req-A',gateway_request_id='gw-A',
            started_at='2026-09-15T10:00:00+09:00',finished_at='2026-09-15T10:01:00+09:00',
            evidence_path='evidence.txt',evidence_record_id='A',provider_billed_usd='0.10',proxy_estimated_usd='0.12')

    def run_records(self, records):
        (self.folder/'requests.jsonl').write_text('\n'.join(json.dumps(r) for r in records),encoding='utf-8')
        return module.summarize(self.folder)

    def test_empty_is_unknown_not_zero(self):
        result=self.run_records([])
        self.assertEqual(result['status'],'미측정')
        self.assertEqual(result['groups'],[])

    def test_provider_and_proxy_are_separate(self):
        group=self.run_records([self.base])['groups'][0]
        self.assertEqual(group['provider_billed_usd']['complete_total'],'0.10')
        self.assertEqual(group['proxy_estimated_usd']['complete_total'],'0.12')

    def test_failed_retry_unknown_cost_keeps_total_unknown(self):
        second=dict(self.base,attempt=2,provider_request_id='req-B',evidence_record_id='B',
                    status='failed',provider_billed_usd=None)
        group=self.run_records([self.base,second])['groups'][0]
        self.assertEqual(group['requests'],2)
        self.assertEqual(group['non_success'],1)
        self.assertEqual(group['provider_billed_usd']['known_subtotal'],'0.10')
        self.assertEqual(group['provider_billed_usd']['unknown_requests'],1)
        self.assertIsNone(group['provider_billed_usd']['complete_total'])
        self.assertEqual(group['proxy_estimated_usd']['complete_total'],'0.24')

    def test_duplicates_rejected_for_provider_gateway_and_evidence(self):
        for changes in [dict(gateway_request_id='gw-B',evidence_record_id='B'),
                        dict(provider_request_id='req-B',evidence_record_id='B'),
                        dict(provider_request_id='req-B',gateway_request_id='gw-B')]:
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                self.run_records([self.base,dict(self.base,**changes)])

    def test_no_provider_id_uses_evidence_and_gateway_attempt(self):
        first=dict(self.base,provider_request_id=None)
        second=dict(first,attempt=2,evidence_record_id='B')
        self.assertEqual(self.run_records([first,second])['requests'],2)

    def test_invalid_money_rejected(self):
        for value in ['-0.01','NaN','Infinity',True,'not-money']:
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.run_records([dict(self.base,provider_billed_usd=value)])

    def test_zero_is_confirmed_zero(self):
        group=self.run_records([dict(self.base,provider_billed_usd=0)])['groups'][0]
        self.assertEqual(group['provider_billed_usd']['complete_total'],'0')

    def test_mixed_rehearsal_rejected(self):
        with self.assertRaises(ValueError): self.run_records([dict(self.base,trial_id='OTHER')])

    def test_missing_evidence_and_outside_path_rejected(self):
        for path in ['missing.txt','../outside.txt']:
            with self.subTest(path=path), self.assertRaises(ValueError):
                self.run_records([dict(self.base,evidence_path=path)])

    def test_unexpected_secret_field_rejected(self):
        with self.assertRaises(ValueError):
            self.run_records([dict(self.base,api_key='synthetic-placeholder')])

    def test_template_not_counted(self):
        with self.assertRaises(ValueError):
            self.run_records([dict(self.base,record_kind='양식_실측아님')])

    def test_setup_and_recurring_separated(self):
        second=dict(self.base,provider_request_id='req-B',gateway_request_id='gw-B',
                    evidence_record_id='B',cost_scope='student_once')
        self.assertEqual(len(self.run_records([self.base,second])['groups']),2)


if __name__=='__main__': unittest.main(verbosity=2)
