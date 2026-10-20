#!/usr/bin/env python3
"""Strict device/simulator typechecks of all native Swift sources; no app or OS operation runs."""
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def main():
    sources = sorted((ROOT / 'packages/native-test-seam/Sources/NativeTestSeam').glob('*.swift'))
    if not sources:
        raise ValueError('native Swift sources missing')
    trial = ROOT / 'packages/physical-ios-trial'
    sources.extend([trial / 'TrialApp.swift', trial / 'TrialEpoch.swift', trial / 'TrialVoiceSurvey.swift', trial / 'TrialAsrScore.swift', trial / 'TrialFileAsr.swift', trial / 'TrialModelDiagnostic.swift', trial / 'TrialModelQualitySession.swift', trial / 'TrialModelQualityText.swift', trial / 'TrialModelQuality.swift', trial / 'TrialPhaseDiagnostic.swift', trial / 'TrialResidentSchedule.swift', trial / 'TrialResidentDiagnostic.swift'])
    for sdk, target in [('iphonesimulator', 'arm64-apple-ios18.0-simulator'), ('iphoneos', 'arm64-apple-ios18.0')]:
        sysroot = subprocess.check_output(['xcrun', '--sdk', sdk, '--show-sdk-path'], text=True, timeout=30).strip()
        subprocess.run(['xcrun', 'swiftc', '-swift-version', '5', '-warnings-as-errors', '-parse-as-library', '-typecheck',
            '-target', target, '-sdk', sysroot, *map(str, sources)], check=True, timeout=120)
        subprocess.run(['xcrun', 'swiftc', '-swift-version', '5', '-warnings-as-errors', '-parse-as-library', '-typecheck',
            '-D', 'EILO_PHASE_MEASUREMENTS', '-I', str(trial / 'include'),
            '-target', target, '-sdk', sysroot, *map(str, sources)], check=True, timeout=120)
        subprocess.run(['xcrun', 'swiftc', '-swift-version', '5', '-warnings-as-errors', '-parse-as-library', '-typecheck',
            '-D', 'EILO_PHASE_MEASUREMENTS', '-D', 'EILO_RESIDENT_COMPARISON', '-I', str(trial / 'include'),
            '-target', target, '-sdk', sysroot, *map(str, sources)], check=True, timeout=120)
        print(sdk + ': all native Swift source typechecks PASS with warnings as errors.', flush=True)


if __name__ == '__main__':
    main()
