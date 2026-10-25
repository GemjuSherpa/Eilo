"""Bounded inspection of explicitly supplied local normal-build artifacts; no network or signing."""
import argparse
import ast
import hashlib
import json
from pathlib import Path,PurePosixPath
import plistlib
import re
import subprocess
import tempfile
import xml.etree.ElementTree as ET
import zipfile

HERE=Path(__file__).resolve().parent
LIMIT=256*1024*1024
AUDIO_MODEL={'.mp3','.wav','.f32','.gguf','.onnx','.ort'}
REPO=HERE.parent.parent
REPO_PINS=('package-lock.json','apps/mobile/package.json','apps/mobile/android/app/build.gradle','apps/mobile/android/gradle.properties','apps/mobile/ios/Podfile.lock','apps/mobile/ios/Eilo.xcodeproj/project.pbxproj')


def need(condition):
    if not condition:raise ValueError('invalid build inventory evidence')


def sha(path):
    digest=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda:stream.read(1024*1024),b''):digest.update(block)
    return digest.hexdigest()


def text(value,maximum=300):
    need(type(value) is str and 0<len(value)<=maximum and all(ord(c)>=32 for c in value))
    return value


def safe_name(name):
    p=PurePosixPath(name)
    need(type(name) is str and name and not p.is_absolute() and '..' not in p.parts and '\\' not in name and '\x00' not in name)
    need(p.as_posix()==name.rstrip('/') and len(name)<=2000 and all(ord(c)>=32 for c in name))
    return name


def command(tool,*args):
    return subprocess.run([str(tool),*map(str,args)],capture_output=True,text=True,check=True,timeout=60).stdout


def sdk_dependencies(raw):
    need(len(raw.encode())<=4*1024*1024)
    blocks=re.findall(r'^library \{\n(.*?)^\}',raw,re.S|re.M)
    need(0<len(blocks)<=1000 and len(blocks)==raw.count('maven_library {'))
    rows=[]
    for block in blocks:
        fields=re.findall(r'(groupId|artifactId|version): "([^"\n]+)"',block);need(len(fields)==3)
        c=dict(fields);need(set(c)=={'groupId','artifactId','version'})
        for value in c.values():need(re.fullmatch(r'[A-Za-z0-9_.+\-]+',value))
        digests=re.findall(r'sha256: ("(?:[^"\\]|\\.)*")',block)
        need(len(digests)<=1 and len(digests)==int('digests {' in block))
        digest=None
        if digests:
            digest=ast.literal_eval('b'+digests[0]);need(type(digest) is bytes and len(digest)==32)
        rows.append(dict(group=c['groupId'],artifact=c['artifactId'],version=c['version'],artifact_sha256=digest.hex() if digest else None))
    need(len({(r['group'],r['artifact'],r['version']) for r in rows})==len(rows))
    return sorted(rows,key=lambda r:(r['group'],r['artifact'],r['version']))


def pom_licenses(path):
    raw=path.read_bytes();need(len(raw)<=2*1024*1024 and b'<!DOCTYPE' not in raw and b'<!ENTITY' not in raw)
    root=ET.fromstring(raw)
    def tag(e):return e.tag.rsplit('}',1)[-1]
    result=[]
    for section in root:
        if tag(section)!='licenses':continue
        for item in section:
            if tag(item)!='license':continue
            fields={tag(e):(e.text or '').strip() for e in item if tag(e) in ('name','url')}
            name=text(fields.get('name') or 'UNNAMED_DECLARATION')
            url=fields.get('url') or None
            if url is not None:need(url.startswith(('https://','http://')));text(url,512)
            result.append(dict(name=name,url=url))
    need(len(result)<=20)
    return result


def maven_inventory(raw,cache):
    rows=sdk_dependencies(raw)
    for row in rows:
        folder=cache/row['group']/row['artifact']/row['version']
        artifacts=sorted(p for p in folder.glob('*/*') if p.is_file() and p.suffix in ('.aar','.jar'))
        need(len(artifacts)<=30 and all(p.stat().st_size<=512*1024*1024 for p in artifacts))
        matches=[p for p in artifacts if sha(p)==row['artifact_sha256']]
        row['cache_match']='NOT_RECORDED' if row['artifact_sha256'] is None else 'VERIFIED' if matches else 'MISMATCH' if artifacts else 'MISSING'
        poms=sorted(folder.glob('*/*.pom'));need(len(poms)<=5)
        row['poms']=[dict(sha256=sha(p),licenses=pom_licenses(p)) for p in poms]
        row['license_review']='REQUIRED'
    return rows


def npm_inventory(lock):
    need(lock['lockfileVersion'] in (2,3) and type(lock['packages']) is dict and len(lock['packages'])<=10000)
    rows=[]
    for key,value in sorted(lock['packages'].items()):
        if not key:continue
        safe_name(key)
        if value.get('link') is True:
            need(value.get('resolved') in lock['packages'] and not lock['packages'][value['resolved']].get('link'))
            continue
        workspace='node_modules/' not in key
        name=value.get('name') if workspace else key.rsplit('node_modules/',1)[-1];need(re.fullmatch(r'(?:@[A-Za-z0-9_.\-]+/)?[A-Za-z0-9_.\-]+',name))
        version=text(value['version']);declared=value.get('license')
        if declared is not None:text(declared)
        dev=value.get('dev',False);need(type(dev) is bool)
        rows.append(dict(lock_entry=key,name=name,version=version,declared_license=declared,development_only=dev,workspace=workspace))
    need(rows)
    return rows


def pods_inventory(raw,acknowledgements):
    need(raw.startswith('PODS:\n') and len(raw.encode())<=1024*1024)
    section=raw.split('\nDEPENDENCIES:',1)[0]
    pairs=re.findall(r'^  - ([A-Za-z0-9_./+\-]+) \(([A-Za-z0-9_.+\-]+)\)',section,re.M)
    need(0<len(pairs)<=1000 and len(set(pairs))==len(pairs))
    notices=[]
    for item in acknowledgements['PreferenceSpecifiers']:
        if 'Title' not in item or not item.get('FooterText'):continue
        title=text(item['Title'] or 'UNTITLED_ACKNOWLEDGEMENT');body=item['FooterText'].encode();need(len(body)<=2*1024*1024)
        notices.append(dict(title=title,bytes=len(body),sha256=hashlib.sha256(body).hexdigest()))
    need(notices and len(notices)<=1000)
    return dict(components=[dict(name=n,version=v) for n,v in sorted(pairs)],notice_evidence=sorted(notices,key=lambda n:n['title']))


def apk_inventory(path,readelf,aapt):
    libraries=[];names=set();resources=[]
    with zipfile.ZipFile(path) as archive,tempfile.TemporaryDirectory() as tmp:
        infos=archive.infolist();need(0<len(infos)<=50000 and sum(i.file_size for i in infos)<=2*1024**3)
        for item in infos:
            safe_name(item.filename);need(item.file_size<=LIMIT and not item.flag_bits&1 and ((item.external_attr>>16)&0o170000)!=0o120000)
            need(item.filename not in names);names.add(item.filename)
            if item.is_dir():continue
            if PurePosixPath(item.filename).suffix.lower() in AUDIO_MODEL:resources.append(item.filename)
            if not item.filename.startswith('lib/') or not item.filename.endswith('.so'):continue
            parts=PurePosixPath(item.filename).parts;need(len(parts)==3 and re.fullmatch(r'[A-Za-z0-9_.+\-]+',parts[2]))
            data=archive.read(item);need(data[:4]==b'\x7fELF')
            local=Path(tmp)/'library.so';local.write_bytes(data)
            dynamic=command(readelf,'--dynamic','--wide',local)
            needed=sorted(set(re.findall(r'\(NEEDED\).*?\[([^\]]+)\]',dynamic)))
            for name in needed:need(re.fullmatch(r'[A-Za-z0-9_.+\-]+',name))
            libraries.append(dict(path=item.filename,bytes=len(data),sha256=hashlib.sha256(data).hexdigest(),needed=needed))
        need(archive.testzip() is None)
    badging=command(aapt,'dump','badging',path)
    permissions=sorted(set(re.findall(r"uses-permission(?:-sdk-\d+)?: name='([^']+)'",badging)))
    for name in permissions:need(re.fullmatch(r'[A-Za-z0-9_.]+',name))
    need(libraries and permissions)
    return dict(sha256=sha(path),bytes=path.stat().st_size,entries=len(names),native_libraries=sorted(libraries,key=lambda x:x['path']),
                permissions=permissions,prohibited_audio_model_resources=sorted(resources),build_kind='ANDROID_RELEASE_VARIANT_NOT_DISTRIBUTION_APPROVAL')


def ios_inventory(root,otool):
    need(root.is_dir() and root.name.endswith('.app'))
    entries=list(root.rglob('*'));need(all(not p.is_symlink() for p in entries))
    files=sorted(p for p in entries if p.is_file())
    need(0<len(files)<=50000 and sum(p.stat().st_size for p in files)<=2*1024**3)
    rows=[];binaries=[];resources=[];privacy=[]
    for path in files:
        need(not path.is_symlink() and path.resolve().is_relative_to(root.resolve()) and path.stat().st_size<=LIMIT)
        name=path.relative_to(root).as_posix();safe_name(name)
        digest=sha(path);rows.append(dict(path=name,bytes=path.stat().st_size,sha256=digest))
        if path.suffix.lower() in AUDIO_MODEL:resources.append(name)
        with path.open('rb') as stream:magic=stream.read(4)
        if magic in (b'\xcf\xfa\xed\xfe',b'\xce\xfa\xed\xfe',b'\xca\xfe\xba\xbe',b'\xbe\xba\xfe\xca',b'\xfe\xed\xfa\xcf'):
            output=command(otool,'-L',path)
            deps=sorted(set(PurePosixPath(line.strip().split(' (compatibility version',1)[0]).name for line in output.splitlines() if '(compatibility version' in line))
            for dep in deps:text(dep,200)
            binaries.append(dict(path=name,bytes=path.stat().st_size,sha256=digest,linked_basenames=deps))
        if path.name=='PrivacyInfo.xcprivacy':
            p=plistlib.loads(path.read_bytes())
            need(type(p) is dict)
            privacy.append(dict(path=name,sha256=digest,declared_tracking=p.get('NSPrivacyTracking'),
                accessed_api_types=sorted({text(x['NSPrivacyAccessedAPIType']) for x in p.get('NSPrivacyAccessedAPITypes',[])}),
                collected_data_types=sorted({text(x['NSPrivacyCollectedDataType']) for x in p.get('NSPrivacyCollectedDataTypes',[])})))
    need(binaries and privacy)
    raw=json.dumps(rows,sort_keys=True,separators=(',',':')).encode()
    return dict(tree_sha256=hashlib.sha256(raw).hexdigest(),files=len(rows),bytes=sum(r['bytes'] for r in rows),native_binaries=binaries,
                privacy_declarations=privacy,prohibited_audio_model_resources=resources,
                build_kind='UNSIGNED_IOS_SIMULATOR_RELEASE_NOT_DEVICE_ARCHIVE')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('apk','sdk-metadata','gradle-cache','ios-app','pods-lock','acknowledgements','npm-lock','readelf','aapt','otool','output'):
        parser.add_argument('--'+name,type=Path,required=True)
    args=parser.parse_args();need(not args.output.exists())
    maven=maven_inventory(args.sdk_metadata.read_text(),args.gradle_cache)
    report=dict(schema_version=1,purpose='NORMAL_BUILD_ARTIFACT_INVENTORY',release_acceptance='BLOCKED',license_approval='NOT_GRANTED',
        network_privacy='NOT_ESTABLISHED',physical='NOT_RUN',memory='DISABLED',
        source_pins={n:sha(HERE/n) for n in ('collect.py',)},
        repository_pins={name:sha(REPO/name) for name in REPO_PINS},
        input_pins={key:sha(getattr(args,key)) for key in ('sdk_metadata','pods_lock','acknowledgements','npm_lock')},
        tool_pins={key:sha(getattr(args,key)) for key in ('readelf','aapt','otool')},
        android=apk_inventory(args.apk,args.readelf,args.aapt),ios=ios_inventory(args.ios_app,args.otool),
        maven=maven,npm_lock_only=npm_inventory(json.loads(args.npm_lock.read_text())),
        pods_lock_and_notices=pods_inventory(args.pods_lock.read_text(),plistlib.loads(args.acknowledgements.read_bytes())),
        sbom_completeness='NOT_ESTABLISHED',redistribution_review='REQUIRED',signing_provenance='NOT_REVIEWED')
    args.output.parent.mkdir(parents=True,exist_ok=True)
    with args.output.open('x') as stream:stream.write(json.dumps(report,indent=2,allow_nan=False)+'\n')


if __name__=='__main__':main()
