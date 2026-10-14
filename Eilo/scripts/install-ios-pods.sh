#!/usr/bin/env bash
# Run from apps/mobile/ios with the existing locked Ruby bundle.
# React Native probes Maven once per install and may fall back to a different
# pod graph on a transient HTTP failure. Retry a fresh locked install, bounded.
set -eu
for attempt in 1 2 3; do
  if bundle exec pod install --deployment; then
    exit 0
  fi
  if [ "$attempt" -eq 3 ]; then
    printf '%s\n' 'Locked CocoaPods installation failed after three attempts.' >&2
    exit 1
  fi
  printf 'Locked CocoaPods install attempt %s failed; retrying in five seconds.\n' "$attempt" >&2
  sleep 5
done
