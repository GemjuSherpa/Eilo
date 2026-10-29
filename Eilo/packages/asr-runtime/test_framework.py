import copy
import hashlib
from pathlib import Path
import plistlib
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import framework as f
import framework_report as report

MODULE='framework module CEiloAsr { umbrella header "eilo_asr.h" export * }\n'


def fixture():
    rows={}
    for sdk in ('iphoneos','iphonesimulator'):
        rows[sdk]=dict(architecture='arm64',platform='IOS' if sdk=='iphoneos' else 'IOSSIMULATOR',minimum_os='18.0',install_name=f.INSTALL,
            exports=f.EXPORTS,namespace='TWOLEVEL',code_signature='UNSIGNED',dependencies=[f.INSTALL,'/usr/lib/libSystem.B.dylib'],sha256='a'*64,bytes=100,
            header_sha256=f.sha(f.HERE/'include/eilo_asr.h'),module_sha256=hashlib.sha256(MODULE.encode()).hexdigest(),info_sha256=hashlib.sha256(plistlib.dumps(f.metadata(sdk))).hexdigest())
    return dict(schema_version=1,purpose='UNSIGNED_IOS_ASR_FRAMEWORK_EVALUATION',source_pins=f.pins(),asr_provenance_sha256=f.sha(f.HERE/'provenance.json'),
        llm_provenance_sha256=f.sha(f.PACKAGES/'llm-runtime/provenance.json'),frameworks=rows,xcframework='TWO_ARM64_SLICES',relocation='EXECUTED_WITH_ORIGINAL_CLIENT_DIRECTORY_ABSENT',framework_client_sha256='b'*64,
        client_rpaths=['/usr/lib/swift','@executable_path/Frameworks'],fixture_sha256=next(x['sha256'] for x in f.read(f.HERE/'tests/fixtures.json')['cases'] if x['id']=='question'),
        execution=dict(framework_asr_final=True,duplicate_final_rejected=True,stale_final_rejected=True,linked_llm_unloaded_gate_rejected=True,microphone='NOT_OPENED',llm_generation='NOT_RUN',physical='NOT_RUN'),
        llm_static_archives=[dict(name=n,sha256='c'*64) for n in ('libllama.a','libggml.a','libggml-cpu.a','libggml-base.a')],compiler='Apple clang version synthetic',**f.FLAGS)


class FrameworkTests(unittest.TestCase):
    def test_relocated_client_rejects_absolute_search_paths_not_filename_header(self):
        loads='/private/build/FrameworkProbe:\n '+f.INSTALL+' (compatibility version 1.0)\n @rpath/libswiftCore.dylib (compatibility version 1.0)\n'
        commands='cmd LC_RPATH\n cmdsize 32\n path /usr/lib/swift (offset 12)\n cmd LC_RPATH\n cmdsize 40\n path @executable_path/Frameworks (offset 12)\n'
        self.assertEqual(len(f.client_metadata(loads,commands)),2)
        with self.assertRaises(ValueError):f.client_metadata(loads,commands.replace('@executable_path/Frameworks','/private/build/Frameworks'))
        with self.assertRaises(ValueError):f.client_metadata(loads.replace(f.INSTALL,'/private/build/CEiloAsr'),commands)

    def test_report_keeps_real_scope_closed(self):
        result=report.validate(fixture());self.assertEqual(len(result['frameworks']),2)
        self.assertEqual(result['release'],'HOLD');self.assertEqual(result['execution']['llm_generation'],'NOT_RUN')

    def test_cannot_promote_signing_distribution_device_or_generation(self):
        for key in f.FLAGS:
            value=fixture();value[key]='APPROVED'
            with self.subTest(key=key),self.assertRaises(ValueError):report.validate(value)
        value=fixture();value['execution']['llm_generation']='PASS'
        with self.assertRaises(ValueError):report.validate(value)
        value=fixture();value['execution']['framework_asr_final']=1
        with self.assertRaises(ValueError):report.validate(value)

    def test_stale_source_metadata_and_extra_exports_rejected(self):
        for change in [lambda r:r['source_pins'].clear(),lambda r:r['frameworks']['iphoneos'].update(platform='IOSSIMULATOR'),
                       lambda r:r['frameworks']['iphoneos'].update(module_sha256='0'*64),lambda r:r['frameworks']['iphoneos'].update(info_sha256='0'*64),
                       lambda r:r['frameworks']['iphoneos'].update(exports=f.EXPORTS+['_vendor']),lambda r:r['frameworks'].pop('iphoneos'),
                       lambda r:r.update(relocation='NOT_RUN'),lambda r:r['frameworks']['iphoneos'].update(code_signature='DEVELOPER_SIGNED'),
                       lambda r:r['frameworks']['iphoneos'].update(dependencies=[f.INSTALL,'/tmp/libwrong.dylib'])]:
            value=fixture();change(value)
            with self.assertRaises(ValueError):report.validate(value)

    def test_binary_rejects_vendor_exports_wrong_platform_absolute_id(self):
        with tempfile.TemporaryDirectory() as folder:
            binary=Path(folder)/'CEiloAsr';binary.write_bytes(b'synthetic')
            outputs={'nm':'\n'.join(f.EXPORTS)+'\n','-hv':'TWOLEVEL','-archs':'arm64','-D':str(binary)+':\n'+f.INSTALL+'\n',
                     '-show-build':'platform IOS\n minos 18.0\n','-L':str(binary)+':\n '+f.INSTALL+' (compatibility version 1.0)\n /usr/lib/libSystem.B.dylib (compatibility version 1.0)\n'}
            def tool(cmd,timeout=180):
                return outputs['nm' if cmd[1]=='nm' else cmd[2]]
            with patch.object(f,'run',side_effect=tool),patch.object(f.subprocess,'run',return_value=SimpleNamespace(returncode=1,stderr='code object is not signed at all')):
                self.assertEqual(f.inspect_binary(binary,'IOS')['namespace'],'TWOLEVEL')
                for key,value in [('nm',outputs['nm']+'_vendor\n'),('-D',str(binary)+':\n/tmp/libwrong.dylib\n'),('-show-build','platform MACOS\n minos 18.0\n'),('-hv','NOUNDEFS')]:
                    old=outputs[key];outputs[key]=value
                    with self.assertRaises(ValueError):f.inspect_binary(binary,'IOS')
                    outputs[key]=old

    def test_xcframework_traversal_duplicate_or_other_arch_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            rows=[dict(LibraryIdentifier='ios-arm64',LibraryPath='CEiloAsr.framework',SupportedArchitectures=['arm64'],SupportedPlatform='ios'),
                  dict(LibraryIdentifier='ios-arm64-simulator',LibraryPath='CEiloAsr.framework',SupportedArchitectures=['arm64'],SupportedPlatform='ios',SupportedPlatformVariant='simulator')]
            def write(values):(root/'Info.plist').write_bytes(plistlib.dumps(dict(CFBundlePackageType='XFWK',XCFrameworkFormatVersion='1.0',AvailableLibraries=values)))
            with patch.object(f,'inspect_bundle',return_value={}):
                write(rows);self.assertEqual(set(f.xcframework_entries(root)),{'iphoneos','iphonesimulator'})
                for key,value in [('LibraryIdentifier','../outside'),('LibraryPath','../lib.dylib'),('SupportedArchitectures',['x86_64']),('SupportedPlatform','macos'),('SupportedPlatformVariant','other')]:
                    changed=copy.deepcopy(rows);changed[0][key]=value;write(changed)
                    with self.assertRaises(ValueError):f.xcframework_entries(root)
                write([rows[0],rows[0]])
                with self.assertRaises(ValueError):f.xcframework_entries(root)

    def test_framework_symlinks_and_header_changes_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)/'CEiloAsr.framework';(root/'Headers').mkdir(parents=True);(root/'Modules').mkdir()
            (root/'Headers/eilo_asr.h').write_bytes((f.HERE/'include/eilo_asr.h').read_bytes())
            (root/'Modules/module.modulemap').write_text(MODULE);(root/'Info.plist').write_bytes(plistlib.dumps(f.metadata('iphoneos')))
            with patch.object(f,'inspect_binary',return_value={}):
                f.inspect_bundle(root,'iphoneos')
                (root/'Headers/eilo_asr.h').write_text('modified')
                with self.assertRaises(ValueError):f.inspect_bundle(root,'iphoneos')
                (root/'Headers/eilo_asr.h').unlink();(root/'Headers/eilo_asr.h').symlink_to(f.HERE/'include/eilo_asr.h')
                with self.assertRaises(ValueError):f.inspect_bundle(root,'iphoneos')

    def test_private_paths_and_overwrite_not_exported(self):
        with tempfile.TemporaryDirectory() as folder:
            out=Path(folder)/'report';report.export(fixture(),out)
            self.assertNotIn('/Users/',(out/'summary.json').read_text())
            with self.assertRaises(ValueError):report.export(fixture(),out)

    @unittest.skipUnless((f.HERE/'framework-results.json').exists(),'native framework execution not completed')
    def test_recorded_native_execution(self):
        self.assertEqual(report.validate(f.read(f.HERE/'framework-results.json'))['ordinary_app'],'NOT_ENABLED')


if __name__=='__main__':unittest.main()
