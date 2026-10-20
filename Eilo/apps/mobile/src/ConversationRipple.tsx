import { useEffect, useRef, useState } from 'react';
import {
  AccessibilityInfo,
  Animated,
  AppState,
  StyleSheet,
  View,
} from 'react-native';
import type { ControlSnapshot } from './ControlClient';
import type { Colors } from './Onboarding';
import { rippleCycleMs } from './VisualMotion';

/** Decoration reflects native state; it never starts capture or synthesizes progress. */
export function ConversationRipple({
  snapshot,
  error,
  colors,
  cycleMs = 1000,
}: {
  snapshot: ControlSnapshot | null;
  error: boolean;
  colors: Colors;
  cycleMs?: number;
}) {
  const duration = rippleCycleMs(cycleMs) / 2;
  const pulse = useRef(new Animated.Value(0)).current;
  const [reduced, setReduced] = useState(true);
  const [foreground, setForeground] = useState(
    AppState.currentState === 'active',
  );
  const state =
    error || !snapshot
      ? 'unavailable'
      : snapshot.capturePending
      ? 'starting'
      : snapshot.controller.state;
  const moving =
    foreground && !reduced && (state === 'listening' || state === 'speaking');
  useEffect(() => {
    let attached = true;
    let changed = false;
    AccessibilityInfo.isReduceMotionEnabled()
      .then(value => {
        if (attached && !changed) {
          setReduced(value);
        }
      })
      .catch(() => {});
    const motion = AccessibilityInfo.addEventListener(
      'reduceMotionChanged',
      value => {
        changed = true;
        setReduced(value);
      },
    );
    const app = AppState.addEventListener('change', value =>
      setForeground(value === 'active'),
    );
    return () => {
      attached = false;
      motion.remove();
      app.remove();
    };
  }, []);
  useEffect(() => {
    pulse.setValue(0);
    if (!moving) {
      return;
    }
    const animation = Animated.loop(
      Animated.sequence([
        Animated.timing(pulse, {
          toValue: 1,
          duration,
          useNativeDriver: true,
          isInteraction: false,
        }),
        Animated.timing(pulse, {
          toValue: 0,
          duration,
          useNativeDriver: true,
          isInteraction: false,
        }),
      ]),
    );
    animation.start();
    return () => {
      animation.stop();
      pulse.stopAnimation();
      pulse.setValue(0);
    };
  }, [duration, moving, pulse, state]);
  const shape =
    state === 'listening'
      ? styles.listening
      : state === 'speaking'
      ? styles.speaking
      : state === 'thinking'
      ? styles.thinking
      : styles.idle;
  return (
    <View
      testID="conversation-ripple"
      accessible={false}
      accessibilityElementsHidden
      importantForAccessibility="no-hide-descendants"
      pointerEvents="none"
      style={styles.frame}
    >
      <Animated.View
        testID={`ripple-${state}`}
        style={[
          styles.ring,
          shape,
          {
            borderColor: colors.primary,
            backgroundColor: colors.gradient_start,
            transform: [
              {
                scale: pulse.interpolate({
                  inputRange: [0, 1],
                  outputRange: [1, 1.12],
                }),
              },
            ],
          },
        ]}
      >
        <View
          style={[
            styles.inner,
            {
              backgroundColor: colors.gradient_end,
              borderColor: colors.primary,
            },
          ]}
        />
      </Animated.View>
    </View>
  );
}

const styles = StyleSheet.create({
  frame: {
    height: 176,
    alignItems: 'center',
    justifyContent: 'center',
    marginVertical: 16,
  },
  ring: { alignItems: 'center', justifyContent: 'center', borderWidth: 2 },
  inner: { width: 60, height: 60, borderRadius: 30, borderWidth: 1 },
  listening: { width: 138, height: 138, borderRadius: 69 },
  speaking: { width: 152, height: 116, borderRadius: 58 },
  thinking: { width: 104, height: 104, borderRadius: 28 },
  idle: { width: 88, height: 88, borderRadius: 44, opacity: 0.55 },
});
