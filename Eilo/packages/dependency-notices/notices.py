"""Trace cached dependency notices without downloads, legal approval or source changes."""
import argparse
import base64
import hashlib
import io
import json
from pathlib import Path,PurePosixPath
import re
import stat
import sys
import tarfile
import xml.etree.ElementTree as ET
import zipfile

HERE=Path(__file__).resolve().parent
BUILD=HERE.parent/'build-inventory'
sys.path.insert(0,str(BUILD))
from collect import need,sha,safe_name,pom_licenses
from inventory_report import validate as validate_baseline,read


def pins():
    paths=[HERE/'notices.py',BUILD/'collect.py',BUILD/'inventory_report.py',BUILD/'observed.json',HERE.parent.parent/'package-lock.json']
    return {str(p.relative_to(HERE.parent.parent)):sha(p) for p in paths}


def coordinate(parts):
    need(type(parts) in (list,tuple) and len(parts)==3)
    need(all(type(x) is str and re.fullmatch(r'[A-Za-z0-9_.+\-]+',x) and x not in ('.','..') for x in parts))
    return ':'.join(parts)


def cache_files(cache,parts,suffix):
    coordinate(parts)
    folder=cache.joinpath(*parts)
    need(folder.resolve().is_relative_to(cache.resolve()))
    paths=sorted(folder.glob('*/*'+suffix))
    need(len(paths)<=30 and all(p.is_file() and not p.is_symlink() and p.resolve().is_relative_to(cache.resolve()) for p in paths))
    return paths


def zip_entries(archive):
    entries=archive.infolist();need(len(entries)<=50000 and sum(e.file_size for e in entries)<=2*1024**3)
    seen=set()
    for item in entries:
        safe_name(item.filename)
        need(item.filename not in seen and not item.flag_bits&1 and ((item.external_attr>>16)&0o170000)!=stat.S_IFLNK)
        need(item.file_size<=512*1024*1024)
        seen.add(item.filename)
    return entries


def is_notice(name):
    return re.fullmatch(r'(?:license|licence|notice|copying|copyright|acknowledg(?:e)?ments)(?:[._-].*)?',PurePosixPath(name).name.lower()) is not None


def scan_archive(path):
    """Hash notices at the archive root and one bounded AAR classes.jar layer."""
    need(path.stat().st_size<=512*1024*1024)
    records=[]
    def scan(archive,prefix='',nested=False):
        entries=zip_entries(archive)
        for item in entries:
            if item.is_dir():continue
            if is_notice(item.filename):
                need(item.file_size<=512*1024)
                raw=archive.read(item)
                records.append(dict(path=prefix+item.filename,bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest()))
            if not nested and item.filename=='classes.jar':
                need(item.file_size<=64*1024*1024)
                with zipfile.ZipFile(io.BytesIO(archive.read(item))) as child:scan(child,'classes.jar!',True)
    with zipfile.ZipFile(path) as archive:scan(archive)
    need(len(records)<=1000)
    return sorted(records,key=lambda r:r['path'])


def parse_pom(path,expected):
    raw=path.read_bytes();need(len(raw)<=2*1024*1024 and b'<!DOCTYPE' not in raw and b'<!ENTITY' not in raw)
    root=ET.fromstring(raw)
    def children(element):return {x.tag.rsplit('}',1)[-1]:x for x in element}
    fields=children(root);parent_fields=children(fields['parent']) if 'parent' in fields else {}
    def value(nodes,key):return (nodes[key].text or '').strip() if key in nodes else None
    actual=(value(fields,'groupId') or value(parent_fields,'groupId'),value(fields,'artifactId'),value(fields,'version') or value(parent_fields,'version'))
    need(coordinate(actual)==coordinate(expected))
    parent=tuple(value(parent_fields,k) for k in ('groupId','artifactId','version')) if parent_fields else None
    if parent is not None:coordinate(parent)
    return parent,pom_licenses(path)


def parent_declaration(cache,parts,child_pins,artifact):
    """Literal cached POM links only; no property/relative-path/BOM/effective-model inference."""
    chain=[];seen=set();current=tuple(parts);embedded=None
    for depth in range(4):
        name=coordinate(current);need(name not in seen);seen.add(name)
        poms=cache_files(cache,current,'.pom')
        if not poms:return dict(status='CACHED_POM_MISSING',chain=chain,child_embedded_pom_sha256=embedded)
        need(len({sha(p) for p in poms})==1)
        path=poms[0];digest=sha(path)
        if depth==0:
            need(digest in child_pins)
            if artifact is None:return dict(status='NO_VERIFIED_CHILD_ARTIFACT',chain=[],child_embedded_pom_sha256=None)
            entry='META-INF/maven/'+current[0]+'/'+current[1]+'/pom.xml'
            with zipfile.ZipFile(artifact) as archive:
                zip_entries(archive)
                if entry not in archive.namelist():return dict(status='CHILD_POM_NOT_EMBEDDED',chain=[],child_embedded_pom_sha256=None)
                need(archive.getinfo(entry).file_size<=2*1024*1024)
                embedded=hashlib.sha256(archive.read(entry)).hexdigest();need(embedded==digest)
        parent,licenses=parse_pom(path,current)
        chain.append(dict(coordinate=name,pom_sha256=digest,licenses=licenses))
        if licenses:return dict(status='CACHED_PARENT_DECLARATION' if depth else 'CACHED_DIRECT_DECLARATION',chain=chain,child_embedded_pom_sha256=embedded)
        if parent is None:return dict(status='NO_DECLARATION_IN_CHAIN',chain=chain,child_embedded_pom_sha256=embedded)
        current=parent
    return dict(status='DEPTH_BOUND_REACHED',chain=chain,child_embedded_pom_sha256=embedded)


def maven_notices(baseline,cache):
    records=[]
    for item in baseline['maven']:
        parts=(item['group'],item['artifact'],item['version']);name=coordinate(parts)
        artifacts=cache_files(cache,parts,'.jar')+cache_files(cache,parts,'.aar')
        need(sum(p.stat().st_size for p in artifacts)<=2*1024**3)
        matched=[p for p in artifacts if sha(p)==item['artifact_sha256']] if item['artifact_sha256'] else []
        if item['artifact_sha256']:need(matched)
        artifact=matched[0] if matched else None
        before=sha(artifact) if artifact else None
        notices=scan_archive(artifact) if artifact else None
        declaration=None
        if not any(p['licenses'] for p in item['poms']):
            declaration=parent_declaration(cache,parts,{p['sha256'] for p in item['poms']},artifact)
        if artifact:need(before==sha(artifact)==item['artifact_sha256'])
        records.append(dict(coordinate=name,artifact_sha256=item['artifact_sha256'],
            scan='NO_RECORDED_ARTIFACT_DIGEST' if artifact is None else 'NOTICE_HASHES_RECORDED' if notices else 'NO_MATCHING_EMBEDDED_NOTICE',
            notices=notices,parent_declaration=declaration))
    return records


def strict_json(raw):
    def unique(pairs):
        result={}
        for key,value in pairs:need(key not in result);result[key]=value
        return result
    def reject(_):raise ValueError('nonfinite JSON')
    return json.loads(raw,object_pairs_hook=unique,parse_constant=reject)


def npm_exit(lock,cache,node_modules):
    package=lock['packages']['node_modules/exit'];integrity=package['integrity'];need(package['version']=='0.1.2')
    need(integrity.startswith('sha512-') and ' ' not in integrity)
    expected=base64.b64decode(integrity[7:],validate=True);need(len(expected)==64)
    hex_digest=expected.hex();path=cache/'content-v2/sha512'/hex_digest[:2]/hex_digest[2:4]/hex_digest[4:]
    need(path.resolve().is_relative_to(cache.resolve()) and not path.is_symlink() and path.stat().st_size<=32*1024*1024)
    raw=path.read_bytes();need(hashlib.sha512(raw).digest()==expected)
    wanted={'package/package.json','package/LICENSE-MIT'};data={};seen=set();total=0
    with tarfile.open(fileobj=io.BytesIO(raw),mode='r:*') as archive:
        for item in archive:
            safe_name(item.name);need(item.name not in seen and len(seen)<5000)
            seen.add(item.name);need(item.isfile() or item.isdir());need(0<=item.size<=16*1024*1024)
            total+=item.size;need(total<=64*1024*1024)
            if item.name in wanted:
                need(item.isfile() and item.size<=512*1024)
                data[item.name]=archive.extractfile(item).read(item.size+1);need(len(data[item.name])==item.size)
    need(set(data)==wanted)
    metadata=strict_json(data['package/package.json']);need(type(metadata) is dict and metadata['name']=='exit' and metadata['version']==package['version'])
    licenses=metadata.get('licenses');need(type(licenses) is list and licenses==[{'type':'MIT','url':'https://github.com/cowboy/node-exit/blob/master/LICENSE-MIT'}])
    files=[]
    for name in sorted(wanted):
        installed=node_modules/'exit'/name.removeprefix('package/')
        need(installed.resolve().is_relative_to(node_modules.resolve()) and not installed.is_symlink())
        digest=hashlib.sha256(data[name]).hexdigest();need(sha(installed)==digest)
        files.append(dict(path=name,bytes=len(data[name]),sha256=digest,installed_bytes_match=True))
    return dict(name='exit',version=package['version'],integrity=integrity,archive_sha256=hashlib.sha256(raw).hexdigest(),
        archive_bytes=len(raw),legacy_license_declarations=licenses,files=files,source='LOCK_SRI_VERIFIED_CACHED_TARBALL_AND_INSTALLED_BYTES')


def packaged_notices(baseline,apk,ios_app):
    need(sha(apk)==baseline['android']['sha256'])
    android=scan_archive(apk)
    need(sha(apk)==baseline['android']['sha256'])
    entries=list(ios_app.rglob('*'));need(all(not p.is_symlink() for p in entries))
    files=sorted(p for p in entries if p.is_file());need(0<len(files)<=50000)
    rows=[];notices=[]
    for p in files:
        need(p.resolve().is_relative_to(ios_app.resolve()) and p.stat().st_size<=256*1024*1024)
        name=p.relative_to(ios_app).as_posix();safe_name(name)
        row=dict(path=name,bytes=p.stat().st_size,sha256=sha(p));rows.append(row)
        if is_notice(name):notices.append(row)
    tree=hashlib.sha256(json.dumps(rows,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    need(tree==baseline['ios']['tree_sha256'])
    return dict(android=dict(artifact_sha256=sha(apk),notices=android),ios=dict(tree_sha256=tree,notices=notices),
                scope='MATCHING_FILENAMES_AND_EXACT_BYTES_ONLY_NOT_COMPLETE_NOTICE_COVERAGE')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('gradle-cache','npm-cache','node-modules','apk','ios-app','output'):parser.add_argument('--'+name,type=Path,required=True)
    args=parser.parse_args();need(not args.output.exists())
    baseline=read(BUILD/'observed.json');validate_baseline(baseline);source_pins=pins()
    lock=read(HERE.parent.parent/'package-lock.json')
    result=dict(schema_version=1,purpose='CACHED_DEPENDENCY_NOTICE_PROVENANCE',source_pins=source_pins,
        baseline_inventory_sha256=sha(BUILD/'observed.json'),maven=maven_notices(baseline,args.gradle_cache),
        npm_exit=npm_exit(lock,args.npm_cache,args.node_modules),
        packaged=packaged_notices(baseline,args.apk,args.ios_app),
        own_workspace_license='OWNER_DECISION_PENDING',sbom_completeness='NOT_ESTABLISHED',redistribution_review='REQUIRED',
        release_acceptance='BLOCKED',network_privacy='NOT_ESTABLISHED',physical='NOT_RUN',memory='DISABLED')
    need(source_pins==pins())
    args.output.parent.mkdir(parents=True,exist_ok=True)
    with args.output.open('x') as stream:stream.write(json.dumps(result,indent=2,allow_nan=False)+'\n')


if __name__=='__main__':main()
