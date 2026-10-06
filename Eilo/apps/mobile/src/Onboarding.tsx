import {Pressable, StyleSheet, Text, View} from 'react-native';
import tokens from '@eilo/design-tokens';
import type {ControlPreferences} from './ControlClient';
export type Colors = typeof tokens.colors.light;
export function Action({label, onPress, colors, disabled = false}: {
  label: string; onPress: () => void; colors: Colors; disabled?: boolean;
}) {
  return <Pressable accessibilityRole="button" accessibilityLabel={label}
    accessibilityState={{disabled}} disabled={disabled} onPress={onPress}
    style={[styles.action, {borderColor: colors.primary}]}>
    <Text style={[styles.body, {color: disabled ? colors.secondary_text : colors.primary}]}>{label}</Text>
  </Pressable>;
}
export function HistoryChoices({colors, preferences, busy, choose}: {colors: Colors; preferences: ControlPreferences | undefined; busy: boolean; choose: (choice: 'private' | 'history') => void}) {
  return <View>
    <Text accessibilityRole="header" style={[styles.body, {color: colors.text}]}>Choose how to handle your conversations</Text>
    {(['private', 'history'] as const).map(choice => <Pressable key={choice} accessibilityRole="radio"
      accessibilityLabel={choice === 'private' ? 'Private sessions — save nothing' : 'Request local history'}
      accessibilityState={{checked: preferences?.historyChoice === choice, disabled: busy || !preferences}}
      disabled={busy || !preferences} onPress={() => choose(choice)} style={[styles.action, {borderColor: colors.primary}]}>
      <Text style={[styles.body, {color: colors.primary}]}>{choice === 'private' ? 'Private sessions — save nothing' : 'Request local history'}{preferences?.historyChoice === choice ? ' · selected' : ''}</Text>
    </Pressable>)}
    {preferences?.historyChoice === 'history' && !preferences.historyAvailable && <Text style={[styles.body, {color: colors.text}]}>History saving is not available yet. Choose a private session to continue without saving.</Text>}
  </View>;
}
export function Onboarding({colors, onContinue, preferences, busy, choose}: {colors: Colors; onContinue: () => void; preferences: ControlPreferences | undefined; busy: boolean; choose: (choice: 'private' | 'history') => void}) {
  return <View>
    <Text accessibilityRole="header" style={[styles.title, {color: colors.text}]}>Welcome to Eilo</Text>
    <Text style={[styles.body, {color: colors.text}]}>I am here for you</Text>
    <Text style={[styles.body, {color: colors.text}]}>Eilo is an AI companion for adults, not a person or an emergency or medical service.</Text>
    <Text style={[styles.body, {color: colors.text}]}>Conversations will run on this phone after model setup. Model downloads need internet access. Conversation audio is not saved or uploaded.</Text>
    <Text style={[styles.body, {color: colors.text}]}>You will choose private sessions or optional local history. Consented history will use encrypted text on this phone. History saving is not available in this build yet.</Text>
    <Text style={[styles.body, {color: colors.text}]}>Local history cannot be restored through an account. Removing the app, losing this phone or losing its keys can permanently lose it.</Text>
    <Text style={[styles.body, {color: colors.text}]}>Microphone access is requested after Start. Background listening is a separate choice, initially off. Android uses a generic listening notification with Stop.</Text>
    <Text style={[styles.body, {color: colors.text}]}>Continue as a guest. An account is optional and is not needed for offline conversation.</Text>
    <HistoryChoices colors={colors} preferences={preferences} busy={busy} choose={choose} />
    <Action colors={colors} label="Continue as guest" disabled={busy || !preferences || preferences.historyChoice === 'none'} onPress={onContinue} />
  </View>;
}
export const styles = StyleSheet.create({
  title: {fontSize: 32, fontWeight: '600', marginBottom: 16},
  body: {fontSize: 16, lineHeight: 24, marginVertical: 8},
  action: {minHeight: 48, minWidth: 48, borderWidth: 1, borderRadius: 12, padding: 12, marginVertical: 8, justifyContent: 'center'},
});
