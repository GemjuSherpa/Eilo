import { useCallback, useEffect, useState, useRef } from 'react';
import {
  AppState,
  ScrollView,
  StatusBar,
  StyleSheet,
  Text,
  Switch,
  useColorScheme,
} from 'react-native';
import { SafeAreaProvider, SafeAreaView } from 'react-native-safe-area-context';
import {
  NavigationContainer,
  DarkTheme,
  DefaultTheme,
} from '@react-navigation/native';
import { createBottomTabNavigator } from '@react-navigation/bottom-tabs';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import tokens from '@eilo/design-tokens';
import {
  Onboarding,
  HistoryChoices,
  styles as textStyles,
} from './src/Onboarding';
import { Home } from './src/Home';
import {
  nativeControl,
  type ControlClient,
  type ControlCommand,
  type ControlSnapshot,
} from './src/ControlClient';
const Tabs = createBottomTabNavigator();
const Stack = createNativeStackNavigator();
export default function App({
  client = nativeControl,
}: {
  client?: ControlClient;
}) {
  const revision = useRef(-1);
  const [continued, setContinued] = useState(false);
  const [snapshot, setSnapshot] = useState<ControlSnapshot | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(false);
  const dark = useColorScheme() === 'dark';
  const colors = dark ? tokens.colors.dark : tokens.colors.light;
  useEffect(() => {
    let attached = true;
    revision.current = -1;
    const receive = (value: ControlSnapshot) => {
      if (attached && value.revision >= revision.current) {
        revision.current = value.revision;
        setSnapshot(value);
        setError(false);
      }
    };
    const refresh = () => {
      client
        .snapshot()
        .then(receive)
        .catch(() => {
          if (attached) {
            setSnapshot(null);
            setError(true);
          }
        });
    };
    const remove = client.subscribe(receive, () => {
      if (attached) {
        setSnapshot(null);
        setError(true);
      }
    });
    const appState = AppState.addEventListener('change', state => {
      if (state === 'active') {
        refresh();
      }
    });
    refresh();
    return () => {
      attached = false;
      remove();
      appState.remove();
    };
  }, [client]);
  const run = useCallback(
    (name: ControlCommand, argument = '') => {
      setBusy(true);
      client
        .command(name, argument)
        .then(value => {
          if (value.revision >= revision.current) {
            revision.current = value.revision;
            setSnapshot(value);
            setError(false);
          }
        })
        .catch(() => {
          setSnapshot(null);
          setError(true);
        })
        .finally(() => setBusy(false));
    },
    [client],
  );
  useEffect(() => {
    if (snapshot) {
      setContinued(snapshot.preferences.onboardingComplete);
    }
  }, [snapshot]);
  return (
    <SafeAreaProvider>
      <StatusBar barStyle={dark ? 'light-content' : 'dark-content'} />
      <NavigationContainer
        theme={{
          ...(dark ? DarkTheme : DefaultTheme),
          colors: {
            ...(dark ? DarkTheme.colors : DefaultTheme.colors),
            background: colors.surface,
            card: colors.surface,
            primary: colors.primary,
            text: colors.text,
            border: colors.boundary,
          },
        }}
      >
        <Stack.Navigator
          screenOptions={{ headerShown: false, animation: 'none' }}
        >
          {!continued ? (
            <Stack.Screen name="Welcome">
              {() => (
                <SafeAreaView
                  style={[styles.screen, { backgroundColor: colors.surface }]}
                >
                  <ScrollView>
                    <Onboarding
                      colors={colors}
                      preferences={snapshot?.preferences}
                      busy={busy}
                      choose={choice => run('history', choice)}
                      onContinue={() => run('completeOnboarding')}
                    />
                  </ScrollView>
                </SafeAreaView>
              )}
            </Stack.Screen>
          ) : (
            <Stack.Screen name="Companion">
              {() => (
                <Tabs.Navigator
                  screenOptions={{
                    tabBarStyle: { minHeight: 64 },
                    headerTitleStyle: { color: colors.text },
                  }}
                >
                  <Tabs.Screen name="Home">
                    {() => (
                      <SafeAreaView
                        style={styles.screen}
                        edges={['left', 'right']}
                      >
                        <ScrollView>
                          <Home
                            colors={colors}
                            snapshot={snapshot}
                            busy={busy}
                            error={error}
                            run={run}
                          />
                        </ScrollView>
                      </SafeAreaView>
                    )}
                  </Tabs.Screen>
                  <Tabs.Screen name="Settings">
                    {() => (
                      <SafeAreaView
                        style={styles.screen}
                        edges={['left', 'right']}
                      >
                        <ScrollView>
                          <Text
                            style={[textStyles.body, { color: colors.text }]}
                          >
                            History saving:{' '}
                            {snapshot?.preferences.historyEnabled
                              ? 'on'
                              : 'off'}
                          </Text>
                          <HistoryChoices
                            colors={colors}
                            preferences={snapshot?.preferences}
                            busy={busy}
                            choose={choice => run('history', choice)}
                          />
                          <Text
                            style={[textStyles.body, { color: colors.text }]}
                          >
                            Background listening requested
                          </Text>
                          <Switch
                            accessibilityLabel="Background listening requested"
                            accessibilityState={{
                              checked:
                                snapshot?.preferences.backgroundConsent ??
                                false,
                            }}
                            value={
                              snapshot?.preferences.backgroundConsent ?? false
                            }
                            disabled={busy || !snapshot}
                            onValueChange={value =>
                              run('background', String(value))
                            }
                          />
                          <Text
                            style={[
                              textStyles.body,
                              { color: colors.secondary_text },
                            ]}
                          >
                            This separate choice requires device authentication.
                            It never starts the microphone. Screen lock stops
                            listening.
                          </Text>
                        </ScrollView>
                      </SafeAreaView>
                    )}
                  </Tabs.Screen>
                </Tabs.Navigator>
              )}
            </Stack.Screen>
          )}
        </Stack.Navigator>
      </NavigationContainer>
    </SafeAreaProvider>
  );
}
const styles = StyleSheet.create({ screen: { flex: 1, padding: 24 } });
