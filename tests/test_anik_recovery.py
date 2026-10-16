import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from examples.fe_walter.legacy.anik_experiment import RunJournal, JournalBackend, append_json, digest
from examples.fe_walter.legacy.anik_recovery import OffsetPolicy, validate_prefix, acquire_lock, run_recovery
from examples.fe_walter.legacy.anik_adapter import load_anik
from examples.fe_walter.legacy.anik_experiment import native_config, prepare_case
from examples.fe_walter.legacy.case import PROJECT_ROOT
from examples.fe_walter.legacy.hydrocnhs_bridge import run_hydrocnhs
from test_anik_experiment import FakeBackend


class RecoveryTests(unittest.TestCase):
    def test_failed_worker_receipt_is_terminal_and_releases_lock(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp)
            with patch('examples.fe_walter.legacy.anik_recovery.prepare_recovery', side_effect=ValueError('drift')):
                with self.assertRaisesRegex(ValueError, 'drift'):
                    run_recovery(Path('unused'), output, {})
            receipt = json.loads((output / 'recovery_process.json').read_text())
            self.assertEqual(receipt['status'], 'failed')
            self.assertEqual(receipt['known_committed_days'], 1276)
            self.assertIn('ended_at_utc', receipt)
            acquire_lock(output).close()

    def test_native_host_runs_only_two_suffix_dates_from_saved_storage(self):
        case, rows = prepare_case(PROJECT_ROOT / 'cases/fe_walter_anik_daily_2016_2020.json')
        _, config = native_config(case, load_anik(PROJECT_ROOT))
        config['start_date'] = '2019-06-30'
        config['agent_config']['Attributes']['Physical']['initial_storage_m3'] = 25453146.95119963
        class Policy:
            policy_id = 'offline-boundary'
            network_calls = 0
            def __init__(self): self.observations, self.records = [], []
            def decide(self, observation):
                self.observations.append(observation)
                return {'schema_version': 'reservoir-action.v1', 'release_cms': observation['inflow_cms']}
            def record_transition(self, record): self.records.append(record)
        inner = Policy()
        logs, engine = run_hydrocnhs(config, rows[1276:1278], policy=OffsetPolicy(inner, 1276))
        self.assertEqual([o['timestep'] for o in inner.observations], [1276, 1277])
        self.assertEqual([o['timestamp'][:10] for o in inner.observations], ['2019-06-30', '2019-07-01'])
        self.assertEqual(inner.observations[0]['state']['storage_m3'], 25453146.95119963)
        self.assertEqual(len(logs), 2)
        self.assertFalse(engine['hydrology_recomputed'])
        self.assertTrue(all(r['transition']['mass_balance_residual_m3'] == 0 for r in logs))

    def test_second_process_cannot_acquire_run_lock(self):
        with tempfile.TemporaryDirectory() as tmp:
            first = acquire_lock(Path(tmp))
            try:
                with self.assertRaisesRegex(RuntimeError, 'holds the run lock'):
                    acquire_lock(Path(tmp))
            finally:
                first.close()
            acquire_lock(Path(tmp)).close()

    def test_offset_changes_only_global_clock_and_never_calls_prefix(self):
        class Policy:
            policy_id = 'test'
            network_calls = 0
            def decide(self, observation):
                self.seen = observation
                return {'release_cms': 1}
            def record_transition(self, record):
                self.record = record
        inner = Policy()
        policy = OffsetPolicy(inner, 1276)
        observation = {'timestep': 0, 'timestamp': '2019-06-30T00:00:00'}
        policy.decide(observation)
        policy.record_transition({'observation': observation, 'transition': {'storage_end_m3': 42}})
        self.assertEqual(inner.seen['timestep'], 1276)
        self.assertEqual(inner.record['observation']['timestep'], 1276)
        self.assertEqual(observation['timestep'], 0)
        self.assertEqual(inner.record['transition']['storage_end_m3'], 42)

    def test_pending_requires_exact_authorized_signature_and_remaining_attempt(self):
        with tempfile.TemporaryDirectory() as tmp:
            journal = RunJournal(Path(tmp) / 'run', {'test': True})
            inner = FakeBackend()
            inner.max_attempts = 2
            signature = digest(['s', 'p', None, inner.request_options])
            pending = {'date': '2019-06-30', 'signature': signature,
                       'event': 'decision_started'}
            attempt = {'date': '2019-06-30', 'attempt_id': 1,
                       'event': 'attempt_started', 'prompt_sha256': digest(['s', 'p', None]),
                       'request_options': inner.request_options}
            append_json(journal.output / 'backend_decisions.jsonl', pending)
            append_json(journal.output / 'api_attempts.jsonl', attempt)
            journal.chat_attempts = 1
            with self.assertRaisesRegex(ValueError, 'unresolved generation'):
                JournalBackend(inner, journal)
            backend = JournalBackend(inner, journal, interrupted={'decision': pending, 'attempt': attempt})
            backend.observation = {'timestamp': '2019-06-30T00:00:00'}
            with self.assertRaisesRegex(ValueError, 'interrupted prompt differs'):
                backend.decide('s', 'different')
            self.assertEqual(inner.calls, 0)
            backend.decide('s', 'p')
            self.assertEqual(inner.calls, 1)
            self.assertEqual(journal.chat_attempts, 2)
            self.assertEqual(inner.max_attempts, 2)
            events = [json.loads(x) for x in (journal.output / 'api_attempts.jsonl').read_text().splitlines()]
            self.assertEqual(events[1]['event'], 'attempt_interrupted')
            self.assertTrue(events[1]['unknown_outcome'])
            replay = JournalBackend(FakeBackend(), journal)
            replay.observation = backend.observation
            replay.decide('s', 'p')

    def test_prefix_validator_rejects_gap_or_state_discontinuity(self):
        records = [{'observation': {'timestep': 0, 'timestamp': '2016-01-01T00:00:00',
                    'inflow_cms': 1, 'state': {'storage_m3': 3}},
                    'transition': {'storage_start_m3': 3, 'storage_end_m3': 4,
                                   'mass_balance_residual_m3': 0}}]
        rows = [{'date': '2016-01-01', 'simulated_inflow_cfs': '1'}]
        with self.assertRaisesRegex(ValueError, 'inflow'):
            validate_prefix(records, rows, 3)
        rows[0]['simulated_inflow_cfs'] = str(1 / 0.028316846592)
        validate_prefix(records, rows, 3)
        records[0]['observation']['timestep'] = 1
        with self.assertRaisesRegex(ValueError, 'clock'):
            validate_prefix(records, rows, 3)


if __name__ == '__main__':
    unittest.main()
