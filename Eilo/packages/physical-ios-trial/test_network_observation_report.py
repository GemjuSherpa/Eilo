import copy
import json
from pathlib import Path
import unittest
from network_observation_report import validate


class NetworkObservationTests(unittest.TestCase):
    def test_actual_failure_retains_null_metrics(self):
        r=json.loads((Path(__file__).parent/'tests/network-observation-attempt.json').read_text())
        self.assertEqual(validate(r)['network_observation'],'NOT_RUN')
        for patch in [{'connection_count':0},{'sent_bytes':0},{'received_bytes':0},{'coverage':'COMPLETE'},
                      {'network_observation':'NO_TRAFFIC_VERIFIED'},{'payload':'secret'},
                      {'payload_exported':0},{'schema_version':True},{'status':'COMPLETED'}]:
            with self.assertRaises(ValueError):validate({**r,**patch})
        for patch in [{'exit_code':0,'result':'SUCCESS'},{'exit_code':True},{'instrument':'HTTP Traffic'},
                      {'target':'ALL_PROCESSES'},{'raw_url':'https://sensitive.invalid'}]:
            bad=copy.deepcopy(r);bad['attempts'][0].update(patch)
            with self.assertRaises(ValueError):validate(bad)
