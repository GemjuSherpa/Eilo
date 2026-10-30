"""iOS domains, missing coverage and independent math controls cannot be promoted."""
import copy
import unittest
from check_ios import HERE,FLAGS,f
import ios_report as report
import ios_math


class IosScoreTests(unittest.TestCase):
    def current(self):return f.read(HERE/'ios-results.json')
    def reject(self,change):
        r=self.current();change(r)
        with self.assertRaises((ValueError,KeyError,TypeError)):report.validate(r)

    def test_actual_collection_preserves_gap_and_precision(self):
        s=report.validate(self.current())
        self.assertEqual((s['diagnostic_paths'],s['not_exercised_paths'],s['fault_cases_unavailable']),(35,1,54))
        self.assertEqual(s['path_coverage']['accepted_draft'],5)
        self.assertEqual(s['coverage'],'GAPS_RETAINED')
        self.assertEqual(s['independent_math_controls']['scope'],'SYNTHETIC_HELPER_ONLY_NOT_ALL_MODEL_ROWS')
        self.assertEqual(s['independent_math_controls']['precision_digits'],80)

    def test_flags_runtime_and_source_boundaries(self):
        for k in FLAGS:self.reject(lambda r:r.update({k:'PASS'}))
        for k,v in [('ort_version','1.28.2'),('ort_origin','cached-1.28.2'),('ort_archive_sha256','0'*64),('rpaths',['/private/cache']),('custom_dynamic_dependencies','UNKNOWN'),('schema_version',True)]:
            self.reject(lambda r:r.update({k:v}))
        self.reject(lambda r:r['source_pins'].pop())
        self.reject(lambda r:r['numeric'].update(long_double_mantissa_bits=113))

    def test_not_exercised_is_never_a_pass_or_a_usable_score(self):
        def change(r,key,value):
            row=next(p for c in r['cases'] for p in c['paths'] if p['status']=='NOT_EXERCISED');row[key]=value
        for k,v in [('status','DIAGNOSTIC_ONLY'),('reported_scores',1),('mode','greedy'),('reason','PASSED'),('mean_probability',.9)]:
            self.reject(lambda r:change(r,k,v))
        self.reject(lambda r:r['cases'][1]['paths'].pop())

    def test_actual_row_and_fault_guards_stay_strict(self):
        self.reject(lambda r:r['cases'][0]['paths'][0].update(baseline_tokens_equal=False))
        self.reject(lambda r:r['cases'][0]['paths'][0].update(oracle_max_error=1e-4))
        self.reject(lambda r:r['cases'][0]['shape_comparison'].update(same_shape_repeat_delta=1e-4))
        self.reject(lambda r:r['cases'][0]['faults'].update(usable_partial_scores=1))
        self.reject(lambda r:r['cases'][0]['faults'].update(fault_cases_unavailable=8))
        self.reject(lambda r:r['cases'][0]['paths'][0].update(transcript='private'))

    def test_helper_decimal_rejects_wrong_nonfinite_or_unbounded_scores(self):
        for value in (.1,float('nan'),float('inf'),0,True):
            r=f.read(HERE/'ios-math-results.json');r['execution']['points'][0]['probability']=value
            with self.assertRaises((ValueError,ArithmeticError)):ios_math.validate(r)
        r=f.read(HERE/'ios-math-results.json');r['execution']['points'].pop()
        with self.assertRaises(ValueError):ios_math.validate(r)

    def test_helper_independent_precision_and_guards_required(self):
        for change in [lambda r:r['source_pins'].pop(),lambda r:r.update(calibrated=True),
                       lambda r:r['execution'].update(invalid_rejected=5),lambda r:r['execution']['points'][0].update(path=2)]:
            r=f.read(HERE/'ios-math-results.json');change(r)
            with self.assertRaises(ValueError):ios_math.validate(r)
        s=ios_math.validate(f.read(HERE/'ios-math-results.json'))
        self.assertEqual((s['synthetic_rows'],s['path_checks'],s['invalid_rejected']),(8,24,6))
        self.assertLess(s['max_relative_error'],1e-12)


if __name__=='__main__':unittest.main()
