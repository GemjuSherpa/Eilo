"""Reject unsafe upgrades and preserve unknowns in paired noise observations."""
import unittest
from framework_noise_report import HERE,validate,framework_module
from framework_noise import FLAGS


class NoisePairTests(unittest.TestCase):
    def current(self):return framework_module().read(HERE/'tests/ios-framework-noise-results.json')
    def reject(self,mutate):
        r=self.current();mutate(r)
        with self.assertRaises((ValueError,KeyError,TypeError)):validate(r)

    def test_actual_collection(self):
        r=validate(self.current());self.assertEqual([g['cases'] for g in r['groups']],[1,12,3,3])
        self.assertEqual(r['end_to_end_false_activation'],'NOT_MEASURED')

    def test_unavailable_outputs_remain_unknown(self):
        r=self.current();row=next(v for v in r['execution']['cases'][1:] if v['joined_opens']==1)
        row.update(metadata=0,recognized=0,joined_nonempty=False,outcome='unavailable',consumed_samples=0,direct_available=False,direct_nonempty=False)
        g=validate(r)['groups'][1]
        self.assertEqual(g['joined_unavailable'],1);self.assertEqual(g['direct_unavailable'],1)
        self.assertEqual(g['joined_no_asr_opened'],10)

    def test_scope_cannot_promote(self):
        for k in FLAGS:self.reject(lambda r:r.update({k:'PASS'}))
        self.reject(lambda r:r['execution'].update(worker_verified=False))
        self.reject(lambda r:r['execution'].update(temporary_pack_removed=False))

    def test_same_input_pairing_required(self):
        self.reject(lambda r:r['execution']['cases'].reverse())
        self.reject(lambda r:r['execution']['cases'][1].update(input_sha256='0'*64))
        self.reject(lambda r:r['execution']['cases'][1].update(input_samples=True))
        self.reject(lambda r:r['execution']['cases'].pop())
        self.reject(lambda r:r.update(controls_sha256='0'*64))

    def test_worker_model_cleanup_and_endpoint_accounting(self):
        for key,value in [('vad_closes',0),('joined_closes',1),('direct_finals',0),('metadata',True),('recognized',1),('joined_nonempty',True),('consumed_samples',0)]:
            self.reject(lambda r:r['execution']['cases'][-1].update({key:value}))
        self.reject(lambda r:r['execution']['cases'][0].update(joined_nonempty=False))
        self.reject(lambda r:r['execution']['cases'][-1].update(outcome='complete'))

    def test_source_loader_and_content_boundaries(self):
        self.reject(lambda r:r['source_pins'].pop())
        self.reject(lambda r:r['framework'].update(sha256='0'*64))
        self.reject(lambda r:r.update(client_rpaths=['/private/frameworks']))
        self.reject(lambda r:r.update(relocation='NOT_RUN'))
        self.reject(lambda r:r['execution']['cases'][0].update(transcript='private'))
        self.reject(lambda r:r.update(schema_version=True))
        self.reject(lambda r:r.update(binary_sha256='bad'))


if __name__=='__main__':unittest.main()
