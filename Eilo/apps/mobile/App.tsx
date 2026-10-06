import {StatusBar, StyleSheet, Text, useColorScheme, View, ScrollView} from 'react-native';
import {SafeAreaProvider, SafeAreaView} from 'react-native-safe-area-context';
import tokens from '@eilo/design-tokens';
import {useState} from 'react';
import {Onboarding} from './src/Onboarding';

// The launch shell has no controller, account, capture or network adapters.
export default function App() {
  const [continued, setContinued] = useState(false);
  const dark = useColorScheme() === 'dark';
  const colors = dark ? tokens.colors.dark : tokens.colors.light;
  return (
    <SafeAreaProvider>
      <StatusBar barStyle={dark ? 'light-content' : 'dark-content'} />
      <SafeAreaView style={[styles.screen, {backgroundColor: colors.surface}]}>
        <ScrollView>
        {!continued ? <Onboarding colors={colors} onContinue={() => setContinued(true)} /> : <View accessible accessibilityLabel="Eilo. Guest. Stopped.">
          <Text accessibilityRole="header" style={[styles.title, {color: colors.text}]}>
            Eilo
          </Text>
          <Text style={[styles.body, {color: colors.secondary_text}]}>Guest</Text>
          <Text style={[styles.body, {color: colors.text}]}>Stopped</Text>
        </View>}
        </ScrollView>
      </SafeAreaView>
    </SafeAreaProvider>
  );
}

const styles = StyleSheet.create({
  screen: {flex: 1, justifyContent: 'center', padding: 24},
  title: {fontSize: 32, fontWeight: '600'},
  body: {fontSize: 16, lineHeight: 24, marginTop: 8},
});
