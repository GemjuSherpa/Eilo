import unittest
from quality_report import edits,summarize

class QualityReportTests(unittest.TestCase):
    def test_substitution_deletion_insertion_and_punctuation(self):
        self.assertEqual(edits('What time is it?','what time is it')['errors'],0)
        value=edits('one two three','one four')
        self.assertEqual((value['substitutions'],value['deletions'],value['insertions']),(1,1,0))
        self.assertEqual(edits('one','one two three')['wer'],2)
        with self.assertRaises(ValueError):edits('','word')

    def test_missing_or_changed_reference_cannot_be_a_quality_pass(self):
        fixture={'cases':[{'id':'one','slice':'english','reference':'hello'}]}
        report={'platform':'synthetic','cases':[]}
        with self.assertRaises(ValueError):summarize(report,fixture)
        report['cases']=[{'id':'one','slice':'english','reference':'changed','transcript':'changed'}]
        with self.assertRaises(ValueError):summarize(report,fixture)

if __name__=='__main__':unittest.main()
