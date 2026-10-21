import { ScrollView, StyleSheet, Text, View } from 'react-native';
import { useIsFocused } from '@react-navigation/native';
import { Action, styles, type Colors } from './Onboarding';
import type { ControlCommand, ControlSnapshot } from './ControlClient';
import { ConversationRipple } from './ConversationRipple';
import { useSpokenPresentation } from './SpokenPresentation';
import { ResultCards } from './ResultCards';
export function Home({
  colors,
  snapshot,
  busy,
  error,
  run,
  resultEnvelope = null,
}: {
  colors: Colors;
  snapshot: ControlSnapshot | null;
  busy: boolean;
  error: boolean;
  run: (name: ControlCommand) => void;
  resultEnvelope?: unknown;
}) {
  const focused = useIsFocused();
  const spoken = useSpokenPresentation(snapshot, busy || error || !focused);
  const state = snapshot?.controller.state;
  const active =
    snapshot?.capturePending ||
    (state !== undefined &&
      ['standby', 'listening', 'thinking', 'speaking'].includes(state));
  const needsStop = !!active || error || !snapshot || state === 'error';
  return (
    <View style={layout.screen}>
      <ScrollView contentContainerStyle={layout.content}>
        <Text
          accessibilityRole="header"
          style={[styles.title, { color: colors.text }]}
        >
          Eilo
        </Text>
        <Text style={[styles.body, { color: colors.secondary_text }]}>
          Guest
        </Text>
        {!snapshot?.preferences.display.voiceOnly && (
          <ConversationRipple
            snapshot={snapshot}
            error={error}
            colors={colors}
          />
        )}
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
        <ResultCards
          envelope={
            focused &&
            !busy &&
            !error &&
            state !== undefined &&
            ['standby', 'listening', 'thinking', 'speaking'].includes(state)
              ? resultEnvelope
              : null
          }
          expected={snapshot?.controller ?? null}
          spoken={spoken}
          preferences={
            snapshot?.preferences.display ?? {
              text: false,
              images: false,
              video: false,
              voiceOnly: true,
            }
          }
          colors={colors}
        />
      </ScrollView>
      <View testID="conversation-safety-controls">
        <Action
          colors={colors}
          label={needsStop ? 'Stop' : 'Start'}
          disabled={!needsStop && busy}
          onPress={() => run(needsStop ? 'stop' : 'start')}
        />
      </View>
    </View>
  );
}

const layout = StyleSheet.create({
  screen: { flex: 1 },
  content: { paddingBottom: 16 },
});
