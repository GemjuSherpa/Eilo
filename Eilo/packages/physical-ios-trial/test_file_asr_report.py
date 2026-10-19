import copy
import hashlib
import json
import re
import unittest
from pathlib import Path
from file_asr_report import FIXTURES,validate

def report():
 r=dict(schema_version=1,scope='IOS_DEVICE_FILE_ASR_DIAGNOSTIC',phase='COMPLETED',input_kind='FROZEN_SYNTHETIC_FILES',microphone='NOT_OPENED',physical_quality_acceptance='NOT_RUN',acoustic_timing='NOT_RUN',raw_text_exported=False,fixture_manifest_sha256=hashlib.sha256(FIXTURES.read_bytes()).hexdigest(),os_build='synthetic test fixture',physical_memory_bytes=12*1024**3,updated_utc='2026-10-19T00:00:00Z',cases=[])
 for f,pin in zip(json.loads(FIXTURES.read_text())['cases'],json.loads((Path(__file__).parent/'tests/asr-pcm-pins.json').read_text())):r['cases'].append(dict(fixture_id=f['id'],pcm_sha256=pin['sha256'],samples=f['samples'],runtime_elapsed_ms=100,reference_words=len(re.findall(r"[a-z0-9]+(?:'[a-z]+)?",f['reference'].lower())),substitutions=0,deletions=0,insertions=0,errors=0))
 return r
class FileReportTests(unittest.TestCase):
 def test_full_and_cancelled_scope(self):
  validate(report());r=report();r.update(phase='CANCELLED',cases=[]);validate(r)
  r['cases']=report()['cases']
  with self.assertRaises(ValueError):validate(r)
 def test_missing_forged_and_content_fields_rejected(self):
  for key,value in [('cases',[]),('physical_quality_acceptance','PASS'),('raw_text_exported',True),('transcript','content')]:
   r=report();r[key]=value
   with self.subTest(key=key),self.assertRaises(ValueError):validate(r)
 def test_inconsistent_or_nonfinite_metrics_rejected(self):
  for key,value in [('runtime_elapsed_ms',float('nan')),('samples',True),('errors',1),('reference_words',0),('substitutions',99),('fixture_id','other'),('pcm_sha256','x')]:
   r=report();r['cases'][0][key]=value
   with self.subTest(key=key),self.assertRaises(ValueError):validate(r)
if __name__=='__main__':unittest.main()
