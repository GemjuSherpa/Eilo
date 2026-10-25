import copy
import unittest
from noise_suite import validate_pairing, canonical_digest, NOISE_RECIPE


def fixtures():
    parent = dict(id='a'*24, reference='synthetic words', speaker='synthetic', task='asr',
                  samples=16000, split='test', source_sha256='b'*64, slice='common_voice')
    clean = dict(kind='public_corpus', dataset='common_voice', cases=[parent], receipt={}, release='synthetic')
    noise = dict(kind='public_corpus', dataset='musan', cases=[dict(id='c'*24, task='vad', vad=[])])
    cases=[]
    for snr in (20,10,0):
        cases.append(dict(parent, parent_id=parent['id'], noise_id='c'*24,
                          slice='common_voice/snr'+str(snr), mix=dict(target_snr_db=snr,seed=0)))
    noisy=dict(clean,cases=cases,parent_manifest_sha256=canonical_digest(clean),
               noise_manifest_sha256=canonical_digest(noise), recipe=NOISE_RECIPE,mix_seed=0)
    return clean,noisy,noise


class PairingTests(unittest.TestCase):
    def test_balanced_groups(self):
        self.assertEqual({k:len(v) for k,v in validate_pairing(*fixtures()).items()}, {20:1,10:1,0:1})

    def test_missing_duplicate_and_unknown_parent(self):
        for mutation in (lambda n:n['cases'].pop(), lambda n:n['cases'].append(copy.deepcopy(n['cases'][0])),
                         lambda n:n['cases'][0].update(parent_id='d'*24)):
            c,n,b=fixtures();mutation(n)
            with self.assertRaises(ValueError):validate_pairing(c,n,b)

    def test_reference_partition_and_recipe_tampering(self):
        mutations=[lambda n:n['cases'][0].update(reference='changed'),
                   lambda n:n['cases'][0].update(split='validation'),
                   lambda n:n['cases'][0]['mix'].update(seed=1),
                   lambda n:n['cases'][0]['mix'].update(target_snr_db=True),
                   lambda n:n.update(parent_manifest_sha256='0'*64),
                   lambda n:n.update(noise_manifest_sha256='0'*64),
                   lambda n:n.update(receipt={'changed':True})]
        for mutation in mutations:
            c,n,b=fixtures();mutation(n)
            with self.assertRaises(ValueError):validate_pairing(c,n,b)

    def test_noise_speech_is_rejected(self):
        c,n,b=fixtures();b['cases'][0]['vad']=[[0,1]];n['noise_manifest_sha256']=canonical_digest(b)
        with self.assertRaises(ValueError):validate_pairing(c,n,b)


if __name__=='__main__':unittest.main()
