"""One explicit approval checkpoint; never derive expected membership from live data."""
import copy
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts'))
from build_index import build
from build_usage_index import build_usage_index
from usage_profiles import load_profiles
from compare_evaluation_expansion import strict_equal

SNAPSHOT = ROOT/'tests/fixtures/approved-usage-membership.json'


class ApprovedUsageMembershipTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.approved = json.loads(SNAPSHOT.read_text(encoding='utf-8'))

    def assert_membership(self, profiles, entries):
        expected_ids = self.approved['reviewed_entry_ids']
        expected_pairs = [tuple(pair) for pair in self.approved['reviewed_usage_pairs']]
        for rows, id_key in ((profiles, 'entry_id'), (entries, 'id')):
            ids = [row[id_key] for row in rows if row['review_status'] == 'reviewed']
            pairs = [(row[id_key], usage['id']) for row in rows
                     if row['review_status'] == 'reviewed' for usage in row['usages']]
            # Counts catch duplicates; exact sets catch same-count replacements.
            self.assertEqual(len(ids), len(expected_ids))
            self.assertEqual(len(pairs), len(expected_pairs))
            self.assertEqual(set(ids), set(expected_ids))
            self.assertEqual(set(pairs), set(expected_pairs))

    def test_approval_snapshot_is_explicit_and_well_formed(self):
        value = self.approved
        self.assertEqual(set(value), {'schema_version', 'approved_revision', 'dictionary_entries',
                                     'reviewed_entries', 'reviewed_usages',
                                     'reviewed_entry_ids', 'reviewed_usage_pairs'})
        self.assertIs(type(value['schema_version']), int)
        self.assertEqual(value['schema_version'], 1)
        self.assertRegex(value['approved_revision'], r'^[a-f0-9]{40}$')
        for key in ('dictionary_entries', 'reviewed_entries', 'reviewed_usages'):
            self.assertIs(type(value[key]), int)
            self.assertGreater(value[key], 0)
        ids = value['reviewed_entry_ids']
        pairs = value['reviewed_usage_pairs']
        self.assertIsInstance(ids, list)
        self.assertIsInstance(pairs, list)
        self.assertEqual(len(ids), value['reviewed_entries'])
        self.assertEqual(len(pairs), value['reviewed_usages'])
        for identity in ids:
            self.assertIsInstance(identity, str)
            self.assertRegex(identity, r'^[a-z0-9]+(?:-[a-z0-9]+)*$')
        for pair in pairs:
            self.assertIsInstance(pair, list)
            self.assertEqual(len(pair), 2)
            for identity in pair:
                self.assertIsInstance(identity, str)
                self.assertRegex(identity, r'^[a-z0-9]+(?:-[a-z0-9]+)*$')
        self.assertEqual(len(set(ids)), len(ids))
        self.assertEqual(len(set(map(tuple, pairs))), len(pairs))
        self.assertEqual({pair[0] for pair in pairs}, set(ids))

    def test_approved_membership_and_canonical_index_profile_agree(self):
        profiles = load_profiles(ROOT)['profiles']
        canonical = build(ROOT)
        index = build_usage_index(ROOT)
        stored = json.loads((ROOT/'data/usage-index.json').read_text(encoding='utf-8'))
        self.assertEqual(len(canonical), self.approved['dictionary_entries'])
        canonical_ids = [row['id'] for row in canonical]
        self.assertEqual(len(set(canonical_ids)), len(canonical_ids))
        self.assert_membership(profiles, index['entries'])
        self.assert_membership(profiles, stored['entries'])
        expected_coverage = {
            'dictionary_entries': self.approved['dictionary_entries'],
            'annotated_entries': len(profiles),
            'reviewed_entries': self.approved['reviewed_entries'],
            'unannotated_entries': len(canonical) - len(profiles),
        }
        for candidate in (index, stored):
            self.assertTrue(strict_equal(candidate['coverage'], expected_coverage))
            rows = candidate['entries']
            self.assertEqual(len(rows), len(profiles))
            self.assertEqual(len({row['id'] for row in rows}), len(rows))
            by_id = {row['id']: row for row in rows}
            self.assertEqual(set(by_id), {profile['entry_id'] for profile in profiles})
            self.assertTrue(set(by_id).issubset(set(canonical_ids)))
            for profile in profiles:
                joined = by_id[profile['entry_id']]
                for field in ('review_status', 'source_sha', 'review_note', 'usages'):
                    self.assertTrue(strict_equal(joined[field], profile[field]),
                                    (profile['entry_id'], field))

    def test_same_count_entry_or_usage_replacement_is_rejected(self):
        profiles = load_profiles(ROOT)['profiles']
        entries = build_usage_index(ROOT)['entries']
        for side in ('profiles', 'index'):
            for change in ('entry', 'usage', 'duplicate-entry', 'duplicate-usage'):
                left, right = copy.deepcopy(profiles), copy.deepcopy(entries)
                rows, key = (left, 'entry_id') if side == 'profiles' else (right, 'id')
                selected = [row for row in rows if row['review_status'] == 'reviewed']
                if change == 'entry':
                    selected[0][key] = 'unapproved-replacement'
                elif change == 'usage':
                    selected[0]['usages'][0]['id'] = 'unapproved-replacement'
                elif change == 'duplicate-entry':
                    selected[0][key] = selected[1][key]
                else:
                    multi = next(row for row in selected if len(row['usages']) > 1)
                    multi['usages'][0]['id'] = multi['usages'][1]['id']
                with self.subTest(side=side, change=change), self.assertRaises(AssertionError):
                    self.assert_membership(left, right)
