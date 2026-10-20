import { Switch, Text, View } from 'react-native';
import type { ControlCommand, DisplayPreferences } from './ControlClient';
import { styles, type Colors } from './Onboarding';

export function effectiveDisplay(
  value: DisplayPreferences,
): DisplayPreferences {
  return value.voiceOnly
    ? { text: false, images: false, video: false, voiceOnly: true }
    : value;
}

export function DisplaySettings({
  colors,
  preferences,
  disabled,
  run,
}: {
  colors: Colors;
  preferences: DisplayPreferences | undefined;
  disabled: boolean;
  run: (name: ControlCommand, value: string) => void;
}) {
  return (
    <View>
      <Text
        accessibilityRole="header"
        style={[styles.body, { color: colors.text }]}
      >
        Conversation display
      </Text>
      {(
        [
          ['voiceOnly', 'Voice only', 'voiceOnly'],
          ['text', 'Show spoken text', 'displayText'],
          ['images', 'Allow result images', 'displayImages'],
          ['video', 'Allow result video', 'displayVideo'],
        ] as const
      ).map(([key, label, command]) => (
        <View key={key}>
          <Text style={[styles.body, { color: colors.text }]}>{label}</Text>
          <Switch
            accessibilityLabel={label}
            value={preferences?.[key] ?? false}
            accessibilityState={{
              checked: preferences?.[key] ?? false,
              disabled,
            }}
            disabled={disabled}
            onValueChange={value => run(command, String(value))}
          />
        </View>
      ))}
      <Text style={[styles.body, { color: colors.secondary_text }]}>
        Voice only hides conversation visuals and keeps your individual choices
        for later. Start, Stop and settings remain available. Allowing images or
        video never starts a download or playback. Rich results are unavailable
        until a verified source is connected.
      </Text>
    </View>
  );
}
