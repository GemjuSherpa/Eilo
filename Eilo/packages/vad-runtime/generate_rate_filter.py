"""Reproduce the 48-to-16 kHz Hamming FIR and verify committed Float32 coefficients."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import struct

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]

def require(value):
    if not value:raise ValueError("filter provenance or frequency bound changed")

def coefficients():
    taps=[]
    for i in range(193):
        x=i-96
        sinc=2*7000/48000 if x==0 else math.sin(2*math.pi*7000*x/48000)/(math.pi*x)
        taps.append(sinc*(0.54-0.46*math.cos(2*math.pi*i/192)))
    scale=sum(taps)
    return [struct.unpack('<f',struct.pack('<f',x/scale))[0] for x in taps]

def gain(taps,hz):
    return abs(sum(c*complex(math.cos(-2*math.pi*hz*i/48000),math.sin(-2*math.pi*hz*i/48000))for i,c in enumerate(taps)))

def generated():
    taps=coefficients()
    require(max(abs(20*math.log10(gain(taps,h)))for h in range(0,6001,25))<0.1)
    require(max(gain(taps,h)for h in range(8000,24001,25))<10**(-50/20))
    digest=hashlib.sha256(struct.pack('<193f',*taps)).hexdigest()
    return taps,{'recipe':'hamming-fir193-fc7000-decimate3-v1','coefficient_float32_le_sha256':digest,
        'source_rate':48000,'target_rate':16000,'taps':193,'delay_source_samples':96,
        'output_count':'floor(source_samples/3); causal zero startup; no EOF flush',
        'passband_hz':[0,6000],'max_passband_error_db':0.1,'stopband_hz':[8000,24000],'min_stopband_rejection_db':50}

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--check',action='store_true');a=p.parse_args()
    taps,record=generated()
    targets=[ROOT/'packages/native-test-seam/Sources/NativeTestSeam/StreamingRateConverter.swift',ROOT/'apps/mobile/android/app/src/main/java/com/eilo/foundation/StreamingRateConverter.kt']
    for path in targets:
        content=path.read_text();start=content.index('    // BEGIN GENERATED FIR')
        end=content.index('    // END GENERATED FIR',start)+len('    // END GENERATED FIR')
        suffix='f' if path.suffix=='.kt' else ''
        values=',\n      '.join(', '.join(format(x,'.9g')+suffix for x in taps[i:i+6])for i in range(0,len(taps),6))
        opening='private val coefficients=floatArrayOf(' if suffix else 'private static let coefficients:[Float]=['
        closing=')' if suffix else ']'
        region='    // BEGIN GENERATED FIR\n    '+opening+'\n      '+values+'\n    '+closing+'\n    // END GENERATED FIR'
        updated=content[:start]+region+content[end:]
        if a.check:require(content==updated)
        else:path.write_text(updated)
    manifest=HERE/'tests/rate-filter.json';data=json.dumps(record,indent=2)+'\n'
    if a.check:require(manifest.read_text()==data)
    else:manifest.write_text(data)
    print('Float32 FIR coefficients and frequency bounds PASS; no physical route claim.')
