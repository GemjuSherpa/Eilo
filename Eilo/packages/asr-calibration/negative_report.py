"""Aggregate-only direct-ASR control report; unavailable text remains unknown."""
import argparse
import html
import json
from pathlib import Path
import re
from negative import HERE,CORPUS,SOURCES,GROUPS,FLAGS,policy,pins,read,sha,need,canonical_digest
from diagnostics import REASONS


def closed(value,keys):need(type(value) is dict and set(value)==set(keys.split()))


def validate(r):
    closed(r,'schema_version purpose protocol_commit source_pins controls_sha256 musan_manifest_sha256 private_counts_sha256 private_model_sha256 model_bundle_sha256 model_provenance_sha256 runtime_sha256 ort_sha256 cxx_sha256 overlay_pins groups rejected_inputs '+' '.join(FLAGS))
    need(type(r['schema_version']) is int and r['schema_version']==1 and r['purpose']==policy()['purpose'])
    need(type(r['protocol_commit']) is str and re.fullmatch('[0-9a-f]{40}',r['protocol_commit']))
    need(r['source_pins']==pins())
    for key,value in FLAGS.items():need(r[key]==value)
    for key in ('controls_sha256','private_counts_sha256','runtime_sha256','cxx_sha256'):
        need(type(r[key]) is str and re.fullmatch('[0-9a-f]{64}',r[key]))
    need(r['musan_manifest_sha256']==read(CORPUS/'noise-results/suite.json')['noise_manifest_sha256'])
    need(r['private_model_sha256']==read(HERE/'freeze.json')['private_model_sha256'])
    provenance=read(HERE.parent/'asr-runtime/provenance.json');baseline=read(HERE/'results.json')['native']['provenance']
    need(r['model_bundle_sha256']==canonical_digest(provenance['model'])==baseline['model_bundle_sha256'])
    need(r['model_provenance_sha256']==sha(HERE.parent/'asr-runtime/provenance.json')==baseline['model_provenance_sha256'])
    need(r['ort_sha256']==baseline['ort_sha256'] and r['cxx_sha256']==baseline['cxx_sha256'] and r['overlay_pins']==baseline['overlay_pins'])
    need(r['rejected_inputs']==['empty','unaligned','nan','out_of_range'])
    rows=r['groups'];need(type(rows) is list and len(rows)==6)
    for i,row in enumerate(rows):
        closed(row,'group source cases available unavailable unavailable_reasons observed_word_bearing observed_word_bearing_fraction_all_cases raw_accepted_word_bearing mapped_accepted_word_bearing outside_development_range')
        need(row['group']==GROUPS[i//2] and row['source']==SOURCES[i%2])
        total=(12,3,3)[i//2]
        for key in ('cases','available','unavailable','observed_word_bearing','raw_accepted_word_bearing','mapped_accepted_word_bearing','outside_development_range'):
            need(type(row[key]) is int and 0<=row[key]<=total)
        need(row['cases']==total and row['available']+row['unavailable']==total)
        need(row['observed_word_bearing']<=row['available'] and row['outside_development_range']<=row['available'])
        need(max(row['raw_accepted_word_bearing'],row['mapped_accepted_word_bearing'])<=row['observed_word_bearing'])
        need(type(row['observed_word_bearing_fraction_all_cases']) in (int,float) and row['observed_word_bearing_fraction_all_cases']==row['observed_word_bearing']/total)
        reasons=row['unavailable_reasons'];need(type(reasons) is dict and set(reasons)<=REASONS)
        need(all(type(n) is int and 0<n<=total for n in reasons.values()) and sum(reasons.values())==row['unavailable'])
    return dict(groups=rows,musan_labels=policy()['musan_labels'],synthetic_labels=policy()['synthetic_labels'],pairing=policy()['pairing'],
                unavailable=policy()['unavailable'],**FLAGS)


def export(r,out):
    result=validate(r);need(not out.exists());out.mkdir(parents=True)
    (out/'summary.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    keys=list(result['groups'][0]);table='<tr>'+''.join('<th>'+html.escape(k)+'</th>' for k in keys)+'</tr>'
    table+=''.join('<tr>'+''.join('<td>'+html.escape(str(row[k]))+'</td>' for k in keys)+'</tr>' for row in result['groups'])
    (out/'summary.html').write_text('<!doctype html><html lang="en"><meta charset="utf-8"><title>Direct ASR negative controls</title><h1>Direct ASR: noise-only controls</h1>'
        '<p>MUSAN labels are weak corpus categories, not verified speech absence. Synthetic silence/uniform noise have no speech by construction. '
        'Uniform levels share a waveform. Existing noise inputs were reused. Unavailable scores have unobservable text outcomes; they do not prove silence. '
        'No WER, correctness/calibration or end-to-end false-activation rate is inferred. VAD is bypassed. No refit, production or physical acceptance.</p><table border="1">'+table+'</table></html>\n')
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--report',type=Path,default=HERE/'negative-results.json');p.add_argument('--output',type=Path)
    a=p.parse_args();r=read(a.report);print(json.dumps(export(r,a.output) if a.output else validate(r),indent=2))
