"""Synthetic offline integrity checks, without downloading or running Android binaries."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import wave
import check_android


class AndroidIntegrityTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.here=self.root/'source';self.cache=self.root/'cache'
        (self.here/'tests/fixtures').mkdir(parents=True)
        for name in ['android','runtime','model','fixtures']:(self.cache/name).mkdir(parents=True)
        for name in ['android/runtime.tar.bz2','android/library.so','runtime.tar.bz2','runtime/header','model.tar.bz2','model/encoder']:
            (self.cache/name).write_bytes(b'synthetic verified asset')
        def checksum(name):return hashlib.sha256((self.cache/name).read_bytes()).hexdigest()
        self.write('android-provenance.json',{'archive':{'file':'runtime.tar.bz2','sha256':checksum('android/runtime.tar.bz2'),
            'files':[{'path':'library.so','sha256':checksum('android/library.so')}]}})
        self.write('provenance.json',{kind:{'directory':kind,'sha256':checksum(kind+'.tar.bz2'),
            'files':[{'path':file,'sha256':checksum(kind+'/'+file)}]} for kind,file in [('runtime','header'),('model','encoder')]})
        fixtures=[]
        for name,kind in [('wake.wav','wake'),('ordinary.wav','nonwake')]:
            with wave.open(str(self.cache/'fixtures'/name),'wb') as audio:
                audio.setnchannels(1);audio.setsampwidth(2);audio.setframerate(16000);audio.writeframes(b'\xf4\x01'*1600)
            fixtures.append({'file':name,'kind':kind,'sha256':checksum('fixtures/'+name)})
        self.write('tests/fixtures/manifest.json',{'fixtures':fixtures})
        self.addCleanup(patch.stopall);patch.object(check_android,'HERE',self.here).start();patch.object(check_android,'CACHE',self.cache).start()

    def write(self,name,value):(self.here/name).write_text(json.dumps(value))

    def testVerifiedCandidatesContainCompleteAcceptanceSet(self):
        root,host,fixtures=check_android.verify_candidates()
        self.assertEqual(root,self.cache/'android');self.assertEqual(host,self.cache/'runtime');self.assertEqual(len(fixtures),2)

    def testTamperedArchiveLibraryHeaderModelOrFixtureCannotRun(self):
        for name in ['android/runtime.tar.bz2','android/library.so','runtime.tar.bz2','runtime/header','model.tar.bz2','model/encoder','fixtures/wake.wav']:
            with self.subTest(asset=name):
                target=self.cache/name;original=target.read_bytes();target.write_bytes(b'tampered')
                with self.assertRaises(ValueError):check_android.verify_candidates()
                target.write_bytes(original)

    def testMissingArtifactCannotRun(self):
        (self.cache/'android/library.so').unlink()
        with self.assertRaises(OSError):check_android.verify_candidates()

    def testEmptyOrOneSidedAcceptanceCannotRun(self):
        for fixtures in [[],[{'file':'wake.wav','kind':'wake','sha256':'a'*64}]]:
            self.write('tests/fixtures/manifest.json',{'fixtures':fixtures})
            with self.assertRaises(ValueError):check_android.verify_candidates()

    def testPassingLabelCannotHideMissingOrFailedCase(self):
        fixtures=[{'file':'wake.wav','kind':'wake'},{'file':'ordinary.wav','kind':'nonwake'}]
        report={'fixture_count':2,'jni_invalid_stale_handles':'PASS','acoustic_acceptance':'PASS ON SYNTHETIC SET ONLY',
                'cases':[dict(f, detections=1 if f['kind']=='wake' else 0, closed_input_rejected=True,controller_stop_rejected=True) for f in fixtures]}
        check_android.verify_report(report,fixtures)
        for field,value in [('detections',0),('file','wrong.wav'),('closed_input_rejected',False),('controller_stop_rejected',False),('detections',True)]:
            altered=json.loads(json.dumps(report));altered['cases'][0][field]=value
            with self.assertRaises(ValueError):check_android.verify_report(altered,fixtures)
        report['cases'].pop()
        with self.assertRaises(ValueError):check_android.verify_report(report,fixtures)


if __name__=='__main__':unittest.main()
