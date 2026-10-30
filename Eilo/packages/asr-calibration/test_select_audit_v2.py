import unittest

from select_audit_v2 import select_rows
from preprocess import opaque


class AuditV2SelectionTests(unittest.TestCase):
    def rows(self, count):
        return [{'client_id': f'opaque-{i}', 'sentence': f'nonpersonal fixed sentence {i}',
                 'path': f'clip-{i}.mp3'} for i in range(count)]

    def test_selection_is_deterministic_and_partitions_ids_and_texts(self):
        rows = self.rows(700)
        first = select_rows(rows, set(), set())
        second = select_rows(list(reversed(rows)), set(), set())
        self.assertEqual(first, second)
        self.assertEqual([len(first[name]) for name in ('development', 'validation', 'audit')], [200] * 3)
        speakers = [{opaque(row['client_id']) for row in first[name]}
                    for name in ('development', 'validation', 'audit')]
        paths = [{row['path'] for row in first[name]} for name in ('development', 'validation', 'audit')]
        self.assertFalse(speakers[0] & speakers[1] or speakers[0] & speakers[2] or speakers[1] & speakers[2])
        self.assertFalse(paths[0] & paths[1] or paths[0] & paths[2] or paths[1] & paths[2])

    def test_prior_ids_and_normalized_text_are_excluded(self):
        rows = self.rows(604)
        blocked_id = opaque(rows[0]['client_id'])
        blocked_text = 'NONPERSONAL FIXED SENTENCE 1!'
        selected = select_rows(rows, {blocked_id}, {blocked_text})
        flat = [row for group in selected.values() for row in group]
        self.assertNotIn('clip-0.mp3', {row['path'] for row in flat})
        self.assertNotIn('clip-1.mp3', {row['path'] for row in flat})

    def test_insufficient_eligible_rows_fail_without_relaxing_the_protocol(self):
        with self.assertRaisesRegex(ValueError, 'fewer than 600'):
            select_rows(self.rows(599), set(), set())

    def test_duplicate_paths_and_unsafe_paths_fail(self):
        rows = self.rows(601)
        rows[1]['path'] = rows[0]['path']
        with self.assertRaisesRegex(ValueError, 'duplicate clip path'):
            select_rows(rows, set(), set())
        rows = self.rows(601)
        rows[0]['path'] = '../escape.mp3'
        with self.assertRaisesRegex(ValueError, 'unsafe clip path'):
            select_rows(rows, set(), set())


if __name__ == '__main__':
    unittest.main()
