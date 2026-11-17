"""Bounded source-integrity regressions for the intro rehearsal only."""
import copy
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts'))
import replay_first_greeting_promotion_scope as intro
from compare_evaluation_expansion import strict_equal

OWN = 'eval/first-greeting-promotion-scope/plans.json'
AUDIT = 'eval/challenge/audit-inputs.json'
WELCOME = 'eval/welcome-interest-scope/plans.json'
HISTORICAL = tuple('eval/'+source+'/'+group+'-plans.json'
                   for source in ('challenge', 'regression-v3')
                   for group in ('audit', 'editorial'))
SOURCES = (OWN, AUDIT, WELCOME) + HISTORICAL


class IntroSourceIntegrityTests(unittest.TestCase):
    def read(self, relative):
        return json.loads((ROOT/relative).read_text(encoding='utf-8'))

    def replace_source(self, relative, data):
        original = Path.read_text
        def edited(path, *args, **kwargs):
            if path == ROOT/relative:
                return json.dumps(data)
            return original(path, *args, **kwargs)
        return patch.object(Path, 'read_text', edited)

    def test_all_seven_sources_keep_order_and_normal_trace(self):
        for relative in SOURCES:
            key = 'inputs' if relative == AUDIT else 'plans'
            data = self.read(relative)
            _, rows = intro.read_records(ROOT, relative, key)
            self.assertTrue(strict_equal(list(rows.values()), data[key]))
        actual = intro.evaluate(ROOT)
        frozen = self.read('eval/first-greeting-promotion-scope/retrieval.json')
        def behavior(rows):
            rows = copy.deepcopy(rows)
            for row in rows:
                row['retrieval'].pop('coverage', None)
            return rows
        self.assertTrue(strict_equal(behavior(actual['results']), behavior(frozen['results'])))

    def test_duplicate_and_required_missing_ids_fail_in_evaluate(self):
        for relative in SOURCES:
            key = 'inputs' if relative == AUDIT else 'plans'
            for mutation in ('duplicate', 'missing'):
                data = self.read(relative)
                if mutation == 'duplicate':
                    data[key].append(copy.deepcopy(data[key][0]))
                else:
                    identity = 'A13' if relative == AUDIT else 'W-welcome' if relative == WELCOME else data[key][0]['id']
                    data[key] = [row for row in data[key] if row['id'] != identity]
                with self.subTest(source=relative, mutation=mutation):
                    with self.replace_source(relative, data), self.assertRaises(ValueError):
                        intro.evaluate(ROOT)

    def test_all_sources_reject_malformed_prompt_and_plan_fields(self):
        for relative in SOURCES:
            key = 'inputs' if relative == AUDIT else 'plans'
            mutations = [('prompt', None), ('prompt', ''), ('prompt', '  '), ('prompt', 1)]
            if key == 'plans':
                mutations += [('action', None), ('action', []), ('action', 'unknown'),
                              ('filters', None), ('filters', []), ('filters', 'lookup')]
            for field, value in mutations:
                data = self.read(relative)
                data[key][0][field] = value
                with self.subTest(source=relative, field=field, value=value):
                    with self.replace_source(relative, data), self.assertRaises(ValueError):
                        intro.read_records(ROOT, relative, key)

    def test_intro_requires_its_version_but_plain_inputs_need_no_action_or_version(self):
        inputs = self.read(AUDIT)
        self.assertNotIn('prompt_version', inputs)
        self.assertTrue(all('action' not in row for row in inputs['inputs']))
        intro.read_records(ROOT, AUDIT, 'inputs', required_ids={'A13', 'A23', 'A26'})
        for value in (None, True, 'contextual-v2', 'unknown'):
            data = self.read(OWN)
            data['prompt_version'] = value
            with self.subTest(version=value):
                with self.replace_source(OWN, data), self.assertRaises(ValueError):
                    intro.evaluate(ROOT)

    def test_no_search_metadata_is_preserved_without_search_calls(self):
        data = self.read(OWN)
        for row in data['plans']:
            if row['action'] in ('clarify', 'abstain'):
                row['filters'] = {'mode': 'lookup', 'limit': 5}
        expected_calls = sum(row['action'] not in ('clarify', 'abstain') for row in data['plans'])
        for relative in HISTORICAL:
            expected_calls += 2 * sum(row['action'] not in ('clarify', 'abstain')
                                      for row in self.read(relative)['plans'])
        with self.replace_source(OWN, data), patch.object(intro, 'search', wraps=intro.search) as searched:
            actual = intro.evaluate(ROOT)
        self.assertEqual(searched.call_count, expected_calls)
        for row in actual['results']:
            if row['action'] in ('clarify', 'abstain'):
                self.assertEqual(row['filters'], {'mode': 'lookup', 'limit': 5})
                self.assertEqual(row['retrieval'],
                                 {'status': 'not_searched', 'reason': row['action'], 'results': []})
