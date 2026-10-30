"""Adversarial graph/scope checks for opt-in app framework integration."""
import copy
from pathlib import Path
import unittest
import app_framework as build
import app_framework_report as report
from framework import HERE, read


def project_fixture():
    return dict(objects=dict(target=dict(isa='PBXNativeTarget',name='Eilo',buildPhases=['frameworks'],buildConfigurationList='configs'),
        frameworks=dict(isa='PBXFrameworksBuildPhase',files=['existing']),configs=dict(buildConfigurations=['debug','release']),
        debug=dict(name='Debug',buildSettings={}),release=dict(name='Release',buildSettings={})))


class AppFrameworkTests(unittest.TestCase):
    def test_graph_links_and_embeds_without_signing_or_runtime_activation(self):
        original=project_fixture();before=copy.deepcopy(original)
        p=build.project(original,Path('/private/evaluation/CEiloAsr.framework'));self.assertEqual(original,before)
        o=p['objects'];ref,link,embed,phase=build.IDS
        self.assertEqual(o['frameworks']['files'],['existing',link]);self.assertIn(phase,o['target']['buildPhases'])
        self.assertEqual(o[phase]['dstSubfolderSpec'],'10');self.assertEqual(o[phase]['files'],[embed])
        self.assertNotIn('CodeSignOnCopy',o[embed]['settings']['ATTRIBUTES'])
        for config in ('debug','release'):
            self.assertEqual(o[config]['buildSettings']['CODE_SIGNING_ALLOWED'],'NO')
            self.assertNotIn('SWIFT_ACTIVE_COMPILATION_CONDITIONS',o[config]['buildSettings'])

    def test_ambiguous_target_graph_and_id_collision_fail(self):
        for mutate in [lambda p:p['objects'].update(other=copy.deepcopy(p['objects']['target'])),
                       lambda p:p['objects']['target'].update(name='Other'),
                       lambda p:p['objects']['frameworks'].update(isa='PBXResourcesBuildPhase'),
                       lambda p:p['objects'].update({build.IDS[0]:{}}),
                       lambda p:p['objects']['release'].update(name='Other')]:
            p=project_fixture();mutate(p)
            with self.assertRaises(ValueError):build.project(p,Path('/private/evaluation/CEiloAsr.framework'))

    def current(self):return read(HERE/'app-framework-results.json')

    def reject(self,mutate):
        r=self.current();mutate(r)
        with self.assertRaises((ValueError,KeyError,TypeError)):report.validate(r)

    def test_actual_record(self):
        r=report.validate(self.current());self.assertEqual(r['cold_launches'],3)
        self.assertEqual(r['ordinary_voice'],'NOT_ENABLED')

    def test_no_acceptance_or_model_activation_upgrade(self):
        for key in build.FLAGS:self.reject(lambda r:r.update({key:'APPROVED'}))
        self.reject(lambda r:r.update(swift_runtime_evaluation_flags='ENABLED'))
        self.reject(lambda r:r.update(project='PRODUCTION_PROJECT_CHANGED'))
        self.reject(lambda r:r.update(release_gate_probe='SOURCE_ONLY'))

    def test_require_real_launch_accounting_and_closed_schema(self):
        for key,value in [('cold_launches',True),('cold_launches',2),('dwell_seconds',0),('schema_version',True),('reply','private')]:
            self.reject(lambda r:r.update({key:value}))
        self.reject(lambda r:r['app'].update(required_framework_load=False))
        self.reject(lambda r:r['app'].update(code_signature='DEVELOPER_SIGNED'))
        self.reject(lambda r:r['app'].update(platform='iPhoneOS'))
        self.reject(lambda r:r['app'].update(rpaths=['/private/frameworks']))
        self.reject(lambda r:r['app'].update(packaged_model_audio_extensions='PRESENT'))

    def test_pin_framework_and_dependency_drift(self):
        self.reject(lambda r:r['source_pins'].pop())
        self.reject(lambda r:r['framework'].update(sha256='0'*64))
        self.reject(lambda r:r['dependency_archives'].pop())
        self.reject(lambda r:r['dependency_archives'][0].update(name='/private/input.tar.gz'))
        self.reject(lambda r:r['app'].update(framework_sha256='0'*64))
        self.reject(lambda r:r['app'].update(tree_sha256='not-a-digest'))


if __name__=='__main__':unittest.main()
