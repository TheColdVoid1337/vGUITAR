"""Local-only persistence, rollup and clipboard report contract."""
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import vguitar_storage as store


def example_run(run_id='test_123'):
    return {
        'run_id': run_id,
        'started_at': '2026-10-21T10:00:00+00:00',
        'finished_at': '2026-10-21T10:00:42+00:00',
        'configuration': {'mode': 'name', 'active_strings': 2, 'active_frets': 5,
                          'tuning_midi': [64, 59, 55, 50, 45, 40], 'study_seconds': 60},
        'questions': [
            {'index': 1, 'string_number': 6, 'fret': 3, 'expected_note': 'G',
             'answer_note': 'G', 'correct': True, 'response_seconds': 0.8},
            {'index': 2, 'string_number': 5, 'fret': 3, 'expected_note': 'C',
             'answer_note': 'D', 'correct': False, 'response_seconds': 3.0},
        ]
    }


class StorageTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.env = patch.dict(os.environ, {'VGUITAR_DATA_DIR': self.temp.name})
        self.env.start()
        self.addCleanup(self.env.stop)

    def test_local_directories_and_preferences(self):
        store.ensure_dirs()
        self.assertTrue((Path(self.temp.name) / 'settings').is_dir())
        self.assertTrue((Path(self.temp.name) / 'results').is_dir())
        data = {'preset': 'Standard', 'volume': 75, 'lesson': {'study_seconds': 60}}
        store.save_preferences(data)
        self.assertEqual(store.read_preferences(), data)
        self.assertEqual(list(Path(self.temp.name).glob('*.json')), [])

    def test_corrupt_preferences_fail_open(self):
        store.ensure_dirs()
        store.preferences_path().write_text('{invalid', encoding='utf-8')
        self.assertEqual(store.read_preferences(), {})

    def test_separate_run_files_and_sorting(self):
        first = store.save_run(example_run('a'))
        self.assertTrue(first.exists())
        second = example_run('b')
        second['finished_at'] = '2026-10-21T11:00:00+00:00'
        store.save_run(second)
        runs, skipped = store.list_runs()
        self.assertEqual([x['run_id'] for x in runs], ['b', 'a'])
        self.assertEqual(skipped, 0)
        (store.results_dir() / 'invalid.json').write_text('{corrupt')
        self.assertEqual(store.list_runs()[1], 1)

    def test_statistics_and_llm_export(self):
        run = example_run()
        stats = store.run_statistics(run)
        self.assertEqual(stats['correct'], 1)
        self.assertEqual(stats['total'], 2)
        self.assertEqual(stats['accuracy_percent'], 50.0)
        self.assertEqual(stats['mean_seconds'], 1.9)
        self.assertEqual(stats['median_seconds'], 1.9)
        self.assertEqual(stats['by_string']['5']['average_seconds'], 3.0)
        exported = json.loads(store.export_runs_for_llm([run, example_run('other')]))
        self.assertEqual(exported['run_count'], 2)
        self.assertEqual(exported['runs'][0]['questions'][0]['response_seconds'], .8)
        self.assertEqual(exported['runs'][1]['run_id'], 'other')

    def test_save_malformed_rejected(self):
        with self.assertRaises(ValueError):
            store.save_run({})

if __name__ == '__main__':
    unittest.main()
