"""Independent Decimal80 controls for the actual iOS score helper; no model or audio."""
import argparse
from decimal import Decimal,localcontext
import json
from pathlib import Path
import re
from check_ios import HERE,PACKAGES,f


def pins():
    return [dict(path=str(p.relative_to(PACKAGES)),sha256=f.sha(p)) for p in
        [HERE/'ios_math.py',HERE/'ios/math-protocol.json',HERE/'score_trace.h',PACKAGES/'asr-runtime/framework.py']]


def protocol():
    p=f.read(HERE/'ios/math-protocol.json');f.need(set(p)=={'schema_version','decimal_precision','paths','cases'})
    f.need(type(p['schema_version']) is int and p['schema_version']==1 and type(p['decimal_precision']) is int and p['decimal_precision']==80 and p['paths']==[0,1,2])
    f.need(type(p['cases']) is list and len(p['cases'])==8 and len({r['id'] for r in p['cases']})==8)
    for r in p['cases']:
        f.need(set(r)=={'id','row','selected'} and type(r['id']) is str and re.fullmatch('[a-z_]+',r['id']))
        f.need(type(r['row']) is list and 1<=len(r['row'])<=64 and all(type(x) in (int,float) and -80<=x<=80 and float(x)*8==int(float(x)*8) for x in r['row']))
        f.need(type(r['selected']) is int and 0<=r['selected']<len(r['row']))
    return p


def validate(r):
    f.need(type(r) is dict and set(r)=={'schema_version','purpose','source_pins','binary_sha256','execution','physical','calibrated','policy_authorized'})
    f.need(type(r['schema_version']) is int and r['schema_version']==1 and r['purpose']=='IOS_HELPER_DECIMAL80_SYNTHETIC_CONTROLS')
    f.need(r['source_pins']==pins() and r['physical']=='NOT_RUN' and r['calibrated'] is False and r['policy_authorized'] is False)
    f.need(type(r['binary_sha256']) is str and re.fullmatch('[0-9a-f]{64}',r['binary_sha256']))
    p=protocol();e=r['execution'];f.need(type(e) is dict and set(e)=={'points','invalid_rejected'})
    f.need(type(e['invalid_rejected']) is int and e['invalid_rejected']==6)
    expected=[(c,path) for c in p['cases'] for path in p['paths']];points=e['points'];f.need(type(points) is list and len(points)==24)
    absolute=Decimal(0);relative=Decimal(0)
    with localcontext() as context:
        context.prec=p['decimal_precision']
        for (c,path),v in zip(expected,points):
            f.need(type(v) is dict and set(v)=={'id','path','probability'} and v['id']==c['id'] and type(v['path']) is int and v['path']==path)
            value=v['probability'];f.need(type(value) in (int,float) and 0<value<=1)
            row=[Decimal.from_float(float(x)) for x in c['row']];maximum=max(row)
            exponentials=[(x-maximum).exp() for x in row];reference=exponentials[c['selected']]/sum(exponentials)
            error=abs(Decimal.from_float(float(value))-reference);ratio=error/reference
            f.need(error<=Decimal('1e-14') and ratio<=Decimal('1e-12'))
            absolute=max(absolute,error);relative=max(relative,ratio)
    return dict(precision_digits=80,synthetic_rows=8,path_checks=24,invalid_rejected=6,max_absolute_error=float(absolute),max_relative_error=float(relative),
                scope='SYNTHETIC_HELPER_ONLY_NOT_ALL_MODEL_ROWS',calibrated=False,policy_authorized=False,physical='NOT_RUN')


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);p.add_argument('--udid',required=True);a=p.parse_args()
    out=a.output.resolve();f.need(not out.exists());before=pins();spec=protocol();out.mkdir(parents=True)
    text='#include "score_trace.h"\n#include <cstdio>\nint main(){EiloScoreTrace t;std::printf("{\\"points\\":[");bool first=true;\n'
    for c in spec['cases']:
        values=','.join(repr(float(x))+'f' for x in c['row'])
        for path in spec['paths']:
            text+='{{auto s=t.measure({'+values+'},'+str(c['selected'])+',static_cast<EiloScoreTrace::Path>('+str(path)+'));if(!first)std::printf(",");first=false;std::printf("{\\"id\\":\\"'+c['id']+'\\",\\"path\\":%d,\\"probability\\":%.17g}",int(s.path),s.probability);}}\n'
    text+='''int rejected=0;auto bad=[&](std::vector<float> row,int selected){try{t.measure(row,selected,EiloScoreTrace::GREEDY);}catch(const std::exception&){++rejected;return;}std::exit(2);};
bad({},0);bad({0},-1);bad({0},1);bad({std::numeric_limits<float>::quiet_NaN()},0);bad({std::numeric_limits<float>::infinity()},0);bad({-1e30f,1e30f},0);
std::printf("],\\"invalid_rejected\\":%d}\\n",rejected);return 0;}\n'''
    source=out/'math_probe.cpp';source.write_text(text);binary=out/'math_probe';sdk=f.run(['xcrun','--sdk','iphonesimulator','--show-sdk-path']).strip()
    f.run(['xcrun','clang++','-std=c++17','-O2','-Wall','-Wextra','-Werror','-target','arm64-apple-ios18.0-simulator','-isysroot',sdk,'-I',HERE,source,'-o',binary])
    e=json.loads(f.run(['xcrun','simctl','spawn',a.udid,binary]));f.need(before==pins())
    r=dict(schema_version=1,purpose='IOS_HELPER_DECIMAL80_SYNTHETIC_CONTROLS',source_pins=before,binary_sha256=f.sha(binary),execution=e,physical='NOT_RUN',calibrated=False,policy_authorized=False)
    summary=validate(r);(out/'results.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(summary,indent=2))


if __name__=='__main__':main()
