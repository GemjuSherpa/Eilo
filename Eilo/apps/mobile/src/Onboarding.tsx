import {Pressable, StyleSheet, Text, View} from 'react-native';
import tokens from '@eilo/design-tokens';
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
export function Onboarding({colors, onContinue}: {colors: Colors; onContinue: () => void}) {
  return <View>
    <Text accessibilityRole="header" style={[styles.title, {color: colors.text}]}>Welcome to Eilo</Text>
    <Text style={[styles.body, {color: colors.text}]}>I am here for you</Text>
    <Text style={[styles.body, {color: colors.text}]}>Eilo is an AI companion for adults, not a person or an emergency or medical service.</Text>
    <Text style={[styles.body, {color: colors.text}]}>Conversations will run on this phone after model setup. Model downloads need internet access. Conversation audio is not saved or uploaded.</Text>
    <Text style={[styles.body, {color: colors.text}]}>You will choose private sessions or optional local history. Consented history will use encrypted text on this phone. History saving is not available in this build yet.</Text>
    <Text style={[styles.body, {color: colors.text}]}>Local history cannot be restored through an account. Removing the app, losing this phone or losing its keys can permanently lose it.</Text>
    <Text style={[styles.body, {color: colors.text}]}>Microphone access is requested after Start. Background listening is a separate choice, initially off. Android uses a generic listening notification with Stop.</Text>
    <Text style={[styles.body, {color: colors.text}]}>Continue as a guest. An account is optional and is not needed for offline conversation.</Text>
    <Action colors={colors} label="Continue as guest" onPress={onContinue} />
  </View>;
}
export const styles = StyleSheet.create({
  title: {fontSize: 32, fontWeight: '600', marginBottom: 16},
  body: {fontSize: 16, lineHeight: 24, marginVertical: 8},
  action: {minHeight: 48, minWidth: 48, borderWidth: 1, borderRadius: 12, padding: 12, marginVertical: 8, justifyContent: 'center'},
});
