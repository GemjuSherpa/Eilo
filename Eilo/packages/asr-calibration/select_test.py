"""Select new curator-test clips while excluding every previously inspected cohort."""
import argparse
from collections import Counter
import csv
import io
import json
from pathlib import Path,PurePosixPath
import tarfile
from calibrate import HERE,FRESH,policy,pins,need,read,sha,canonical_digest,normalize,validate_manifest
from shared import verify_receipt,opaque
from extract_subset import member_path,read_member
from preprocess import freeze


def exclusions(paths):
    need(len(paths)==3)
    manifests=[read(p) for p in paths]
    for p,m in zip(paths,manifests):validate_manifest(m,p.parent)
    prior=read(FRESH/'results.json')
    expected=[prior['selection']['prior_manifest_sha256']]+[prior['selection']['partitions'][k]['manifest_sha256'] for k in ('dev','test')]
    need([canonical_digest(m) for m in manifests]==expected)
    need(sum(len(m['cases']) for m in manifests)==policy()['excluded_prior_cases'])
    need(all(m['receipt']==manifests[0]['receipt'] for m in manifests))
    return manifests


def choose(tables,old):
    need(set(tables)=={'train','dev','test'})
    speakers={}
    for split,rows in tables.items():
        need(rows and len(rows)<=100000 and len({r['path'] for r in rows})==len(rows))
        need(all(all(type(r.get(k)) is str and r[k] for k in ('client_id','sentence','path')) for r in rows))
        need(all(PurePosixPath(r['path']).name==r['path'] and r['path'].endswith('.mp3') and '\\' not in r['path'] for r in rows))
        speakers[split]={opaque(r['client_id']) for r in rows}
    need(not speakers['train']&speakers['dev'] and not speakers['train']&speakers['test'] and not speakers['dev']&speakers['test'])
    blocked={c['speaker'] for m in old for c in m['cases']};texts={normalize(c['reference']) for m in old for c in m['cases']}
    used=Counter();chosen=[]
    rows=sorted(tables['test'],key=lambda r:opaque(str(policy()['seed'])+':test:'+r['path']))
    for round_number in range(1,policy()['max_clips_per_speaker']+1):
        for r in rows:
            speaker,text=opaque(r['client_id']),normalize(r['sentence'])
            if len(chosen)==policy()['fresh_test_cases']:break
            if speaker in blocked or text in texts or used[speaker]>=round_number:continue
            need(text);chosen.append(r);texts.add(text);used[speaker]+=1
    need(len(chosen)==policy()['fresh_test_cases']);return chosen


def verify(output,paths):
    old=exclusions(paths);m=read(output/'test/manifest.json');validate_manifest(m,output/'test')
    need(m['receipt']==old[0]['receipt'] and len(m['cases'])==policy()['fresh_test_cases'])
    need(all(c['split']=='test' and c['task']=='asr' and 0<c['samples']<=480000 for c in m['cases']))
    for key in ('speaker','source_sha256','pcm_sha256'):
        before={c[key] for p in old for c in p['cases']};after={c[key] for c in m['cases']};need(not before&after)
        if key!='speaker':need(len(after)==len(m['cases']))
    counts=Counter(c['speaker'] for c in m['cases']);need(max(counts.values())<=policy()['max_clips_per_speaker'])
    before={normalize(c['reference']) for p in old for c in p['cases']};after={normalize(c['reference']) for c in m['cases']}
    need(len(after)==len(m['cases']) and not before&after)
    return m


def prepare(archive,receipt,paths,output,decoder):
    need(not output.exists());old=exclusions(paths);verify_receipt(receipt,archive);need(receipt==old[0]['receipt'])
    before=pins();tables={};names=set();prefix=None
    with tarfile.open(archive,'r|*') as tar:
        for item in tar:
            name=member_path(item);need(name not in names);names.add(name)
            base=PurePosixPath(name).name
            if item.isfile() and base in ('train.tsv','dev.tsv','test.tsv'):
                split=base[:-4];parent=str(PurePosixPath(name).parent)
                need(split not in tables and (prefix is None or parent==prefix));prefix=parent
                tables[split]=list(csv.DictReader(io.StringIO(read_member(tar,item).decode()),delimiter='\t'))
    selected=choose(tables,old);prefix='' if prefix=='.' else prefix+'/'
    wanted={prefix+'clips/'+r['path'] for r in selected};need(len(wanted)==policy()['fresh_test_cases'] and wanted<=names)
    output.mkdir(parents=True);raw=output/'selected-private';(raw/'clips').mkdir(parents=True)
    with tarfile.open(archive,'r|*') as tar:
        for item in tar:
            name=member_path(item)
            if name in wanted:(raw/'clips'/PurePosixPath(name).name).write_bytes(read_member(tar,item))
    with (raw/'test.tsv').open('x',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=('client_id','sentence','path'),delimiter='\t',extrasaction='ignore');writer.writeheader();writer.writerows(selected)
    freeze('common_voice',raw,output/'test',receipt['version'],receipt,'test',len(selected),policy()['seed'],decoder,old[0]['decoder_sha256'],'afconvert')
    m=verify(output,paths);need(before==pins())
    evidence=dict(schema_version=1,source_pins=before,protocol_sha256=sha(HERE/'protocol.json'),excluded_manifest_sha256=[canonical_digest(x) for x in old],
        excluded_cases=90,test_cases=len(m['cases']),test_speakers=len({c['speaker'] for c in m['cases']}),manifest_sha256=canonical_digest(m),
        speaker_overlap=0,utterance_overlap=0,encoded_overlap=0,pcm_overlap=0,model_training_overlap='UNKNOWN')
    (output/'selection.json').write_text(json.dumps(evidence,indent=2)+'\n');return evidence


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('archive','receipt','prior','development','previous-test','output','decoder'):p.add_argument('--'+n,required=True,type=Path)
    a=p.parse_args();prepare(a.archive,read(a.receipt),[a.prior,a.development,a.previous_test],a.output,a.decoder)
    print('Thirty fresh test clips frozen; all ninety prior clips excluded. No inference performed.')
