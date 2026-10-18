import copy
from datetime import datetime,timezone
import hashlib
import unittest
from voice_survey import FIXTURES,validate

def report():return dict(schema_version=1,scope='INTERNAL_IOS_LISTENING_SURVEY',physical_gate_acceptance='NOT_RUN',acoustic_timing='NOT_RUN',network_observation='NOT_RUN',radio_state='OPERATOR_DECLARED_OFF_AT_BUILD',radio_attestation_recorded_utc='2026-10-18T13:37:36Z',fixture_sha256=hashlib.sha256(FIXTURES.read_bytes()).hexdigest(),voice_id='public.test.voice',os_build='synthetic fixture',updated_utc=datetime.now(timezone.utc).isoformat(),attempts=[])
class SurveyTests(unittest.TestCase):
 def test_partial_retry_and_full_ratings(self):
  r=report();validate(r);r['attempts']=[dict(fixture_id='voice-01',attempt=1,sdk_status='INTERRUPTED')];validate(r)
  for n in range(1,13):r['attempts'].append(dict(fixture_id=f'voice-{n:02d}',attempt=n+1,sdk_status='SDK_COMPLETED',intelligibility=4));validate(r)
 def test_forged_rating_scope_content_or_order_rejected(self):
  r=report();r['attempts']=[dict(fixture_id='voice-01',attempt=1,sdk_status='SDK_COMPLETED',intelligibility=4)]
  for field,value in [('sdk_status','PLAYING'),('intelligibility',True),('intelligibility',6),('fixture_id','voice-02'),('transcript','content')]:
   bad=copy.deepcopy(r);bad['attempts'][0][field]=value
   with self.subTest(field=field),self.assertRaises(ValueError):validate(bad)
  for field,value in [('physical_gate_acceptance','PASS'),('network_observation','NO_TRAFFIC_VERIFIED'),('fixture_sha256','0'*64),('raw_audio','content')]:
   bad=copy.deepcopy(r);bad[field]=value
   with self.subTest(field=field),self.assertRaises(ValueError):validate(bad)
 def test_duplicate_ratings_and_unbounded_retries_rejected(self):
  r=report();r['attempts']=[dict(fixture_id='voice-01',attempt=i,sdk_status='INTERRUPTED') for i in range(1,5)]
  with self.assertRaises(ValueError):validate(r)
  r['attempts']=[dict(fixture_id='voice-01',attempt=i,sdk_status='SDK_COMPLETED',intelligibility=5) for i in range(1,3)]
  with self.assertRaises(ValueError):validate(r)
if __name__=='__main__':unittest.main()
