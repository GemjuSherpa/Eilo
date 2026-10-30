"""Audit frozen paired noise observations without corpus or native runtime access."""
import argparse
from collections import Counter
import html
import json
from pathlib import Path
import re
from framework_noise import HERE,FLAGS,framework_module,pins,policy
from check_framework_capture import require


def closed(v,keys):require(type(v) is dict and set(v)==set(keys.split()),'unexpected report fields')


def digest(v):require(type(v) is str and re.fullmatch('[0-9a-f]{64}',v),'invalid digest')


def validate(r):
    closed(r,'schema_version purpose protocol_commit source_pins controls_sha256 musan_manifest_sha256 framework vad_model_sha256 client_rpaths relocation binary_sha256 execution '+' '.join(FLAGS))
    require(type(r['schema_version']) is int and r['schema_version']==1 and r['purpose']=='PAIRED_IOS_DIRECT_VAD_ASR_NOISE_DIAGNOSTIC','schema changed')
    require(type(r['protocol_commit']) is str and re.fullmatch('[0-9a-f]{40}',r['protocol_commit']),'protocol commit missing')
    require(r['source_pins']==pins(),'evaluated sources changed');p=policy();f=framework_module()
    for k,v in FLAGS.items():require(r[k]==v,'acceptance scope changed')
    require(r['controls_sha256']==p['base_controls_sha256'] and r['musan_manifest_sha256']==p['musan_manifest_sha256'],'frozen controls changed')
    require(r['framework']==f.read(HERE.parent/'asr-runtime/framework-results.json')['frameworks']['iphonesimulator'],'framework changed')
    require(r['vad_model_sha256']==f.read(HERE.parent/'vad-runtime/provenance.json')['model_sha256'],'VAD model changed')
    require(r['relocation']=='EXECUTED_WITH_ORIGINAL_CLIENT_DIRECTORY_ABSENT','relocation missing');digest(r['binary_sha256'])
    require(type(r['client_rpaths']) is list and len(r['client_rpaths'])==2 and set(r['client_rpaths'])=={'/usr/lib/swift','@executable_path/Frameworks'},'unsafe loader path')
    e=r['execution'];closed(e,'cases temporary_pack_removed worker_verified')
    require(e['temporary_pack_removed'] is True and e['worker_verified'] is True,'cleanup/worker proof missing')
    rows=e['cases'];require(type(rows) is list and len(rows)==19,'case coverage changed')
    for row,input_row in zip(rows,p['inputs']):
        closed(row,'group input_sha256 input_samples direct_available direct_nonempty direct_opens direct_closes direct_finals vad_opens vad_closes joined_opens joined_closes joined_finals metadata recognized joined_nonempty outcome consumed_samples')
        require(row['group']==input_row['group'] and row['input_sha256']==input_row['sha256'] and type(row['input_samples']) is int and row['input_samples']==input_row['samples'],'input pairing changed')
        for k in ('direct_opens','direct_closes','direct_finals','vad_opens','vad_closes','joined_opens','joined_closes','joined_finals','metadata','recognized','consumed_samples'):
            require(type(row[k]) is int and 0<=row[k]<=row['input_samples'],'counter invalid')
        for k in ('direct_available','direct_nonempty','joined_nonempty'):require(type(row[k]) is bool,'boolean invalid')
        require(all(row[k]==1 for k in ('direct_opens','direct_closes','direct_finals','vad_opens','vad_closes')),'runtime/cleanup missing')
        require(row['direct_available'] or not row['direct_nonempty'],'unavailable text cannot be observed')
        require(row['joined_opens']==row['joined_closes'] and row['joined_opens']<=1 and row['joined_finals']<=row['joined_opens'],'joined cleanup invalid')
        require(0<=row['recognized']<=row['metadata']<=1 and (row['recognized']==1 or not row['joined_nonempty']),'text accounting invalid')
        if row['metadata']==0:
            require(row['outcome']=='unavailable' and row['consumed_samples']==0,'unavailable outcome promoted')
        else:
            require(row['outcome'] in ('noSpeech','incomplete','complete','limit') and row['consumed_samples']>0,'endpoint outcome missing')
            if row['outcome'] in ('noSpeech','incomplete'):
                require(row['joined_opens']==0 and row['recognized']==0,'ASR opened without endpoint')
                if row['outcome']=='noSpeech':require(row['consumed_samples']==80000,'no-speech boundary changed')
            else:
                require(row['joined_opens']==row['joined_finals']==row['recognized']==1,'ASR endpoint missing')
                if row['outcome']=='limit':require(row['consumed_samples']==480000,'limit boundary changed')
    positive=rows[0]
    require(positive['direct_available'] is True and positive['direct_nonempty'] is True and positive['joined_nonempty'] is True and positive['outcome']=='complete','positive runtime control failed')
    groups=[]
    for group in ('positive_question','musan_weak_noise','digital_silence','uniform_noise'):
        values=[x for x in rows if x['group']==group]
        groups.append(dict(group=group,cases=len(values),direct_available=sum(x['direct_available'] for x in values),
            direct_unavailable=sum(not x['direct_available'] for x in values),direct_nonempty=sum(x['direct_nonempty'] for x in values),
            joined_asr_opens=sum(x['joined_opens'] for x in values),joined_text_callbacks=sum(x['recognized'] for x in values),
            joined_nonempty=sum(x['joined_nonempty'] for x in values),joined_unavailable=sum(x['metadata']==0 for x in values),
            joined_no_asr_opened=sum(x['metadata']==1 and x['joined_opens']==0 for x in values),outcomes=dict(sorted(Counter(x['outcome'] for x in values).items()))))
    return dict(purpose=r['purpose'],groups=groups,musan_labels=p['musan_labels'],synthetic_labels=p['synthetic_labels'],pairing=p['pairing'],
        text_measure=p['text_measure'],comparison_to_android_raw_score_diagnostic='DIFFERENT_RUNTIME_AND_PADDED_INPUT_NOT_AN_EFFECT_ESTIMATE',**FLAGS)


def export(r,out):
    summary=validate(r);require(not out.exists(),'output exists');out.mkdir(parents=True)
    (out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    (out/'summary.html').write_text('<!doctype html><html lang="en"><meta charset="utf-8"><title>Paired iOS VAD/ASR noise observations</title><h1>Paired iOS VAD/ASR noise observations</h1><p>Same iOS runtime and padded input; endpoint consumption differs. Nonempty text is not accuracy. MUSAN labels are weak; unavailable results remain unknown. No threshold, wake, system or physical qualification.</p><pre>'+html.escape(json.dumps(summary,indent=2))+'</pre></html>\n')
    return summary


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--report',type=Path,default=HERE/'tests/ios-framework-noise-results.json');p.add_argument('--output',type=Path)
    a=p.parse_args();r=framework_module().read(a.report);print(json.dumps(export(r,a.output) if a.output else validate(r),indent=2))
