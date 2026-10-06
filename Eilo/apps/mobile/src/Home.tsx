import { Text, View } from 'react-native';
import { Action, styles, type Colors } from './Onboarding';
import type { ControlCommand, ControlSnapshot } from './ControlClient';
export function Home({
  colors,
  snapshot,
  busy,
  error,
  run,
}: {
  colors: Colors;
  snapshot: ControlSnapshot | null;
  busy: boolean;
  error: boolean;
  run: (name: ControlCommand) => void;
}) {
  const state = snapshot?.controller.state;
  const active =
    snapshot?.capturePending ||
    (state !== undefined &&
      ['standby', 'listening', 'thinking', 'speaking'].includes(state));
  return (
    <View>
      <Text
        accessibilityRole="header"
        style={[styles.title, { color: colors.text }]}
      >
        Eilo
      </Text>
      <Text style={[styles.body, { color: colors.secondary_text }]}>Guest</Text>
      <Text
        accessibilityLiveRegion="polite"
        style={[styles.body, { color: colors.text }]}
      >
        {error
          ? 'Native controls unavailable. Reopen the app to reconnect.'
          : snapshot?.capturePending
          ? 'Starting microphone…'
          : state
          ? state.replace('_', ' ')
          : 'Connecting…'}
      </Text>
      {snapshot?.controller.modelStatus !== 'ready' && (
        <Text style={[styles.body, { color: colors.text }]}>
          Model setup is required before conversation can start.
        </Text>
      )}
      <Text style={[styles.body, { color: colors.secondary_text }]}>
        After permissions are granted, choose Start again if listening has not
        begun.
      </Text>
      <Action
        colors={colors}
        label={active || error ? 'Stop' : 'Start'}
        disabled={(!snapshot && !error) || busy}
        onPress={() => run(active || error ? 'stop' : 'start')}
      />
      {snapshot?.speakerConfirmationRequired && (
        <>
          <Text style={[styles.body, { color: colors.text }]}>
            Headphones disconnected. Speech is paused to protect your privacy.
          </Text>
          <Action
            colors={colors}
            label="Confirm speaker output"
            disabled={busy || error}
            onPress={() => run('confirmSpeaker')}
          />
        </>
      )}
    </View>
  );
}
