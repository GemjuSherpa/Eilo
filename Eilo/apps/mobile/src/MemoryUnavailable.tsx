import { Text, View } from 'react-native';
import { styles, type Colors } from './Onboarding';

export function MemoryUnavailable({ colors }: { colors: Colors }) {
  return (
    <View>
      <Text
        accessibilityRole="header"
        style={[styles.title, { color: colors.text }]}
      >
        Memory
      </Text>
      <Text style={[styles.body, { color: colors.text }]}>
        Memory is not available in this build.
      </Text>
      <Text style={[styles.body, { color: colors.secondary_text }]}>
        Your conversations are not saved. Displaying a spoken reply does not add
        it to history. You can continue with private conversations when voice
        setup is ready.
      </Text>
    </View>
  );
}
