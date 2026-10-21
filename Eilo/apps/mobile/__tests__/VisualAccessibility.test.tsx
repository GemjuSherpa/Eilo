import Renderer, { act } from 'react-test-renderer';
import { Text, StyleSheet } from 'react-native';
import tokens from '@eilo/design-tokens';
import { Action } from '../src/Onboarding';
import { rippleCycleMs } from '../src/VisualMotion';

function luminance(hex: string) {
  const channels = [1, 3, 5].map(start => {
    const value = parseInt(hex.slice(start, start + 2), 16) / 255;
    return value <= 0.04045 ? value / 12.92 : ((value + 0.055) / 1.055) ** 2.4;
  });
  return channels[0] * 0.2126 + channels[1] * 0.7152 + channels[2] * 0.0722;
}
function contrast(a: string, b: string) {
  const levels = [luminance(a), luminance(b)].sort((x, y) => x - y);
  return (levels[1] + 0.05) / (levels[0] + 0.05);
}
test.each(Object.entries(tokens.colors))(
  '%s semantic text/control contrast',
  (_theme, colors) => {
    for (const foreground of [
      colors.text,
      colors.secondary_text,
      colors.primary,
      colors.error,
      colors.warning,
    ]) {
      expect(contrast(foreground, colors.surface)).toBeGreaterThanOrEqual(4.5);
    }
    expect(contrast(colors.boundary, colors.surface)).toBeGreaterThanOrEqual(3);
  },
);
test('one-second preview remains adjustable, bounded and finite', () => {
  expect(rippleCycleMs()).toBe(1000);
  expect(rippleCycleMs(2000)).toBe(2000);
  for (const value of [0, -1, 499, 4001, Infinity, NaN]) {
    expect(rippleCycleMs(value)).toBe(1000);
  }
});
test('long controls retain scaling, wrapping and minimum touch dimensions', async () => {
  let view: Renderer.ReactTestRenderer | undefined;
  await act(() => {
    view = Renderer.create(
      <Action
        colors={tokens.colors.light}
        label="A deliberately long accessible conversation control that must wrap"
        onPress={() => {}}
      />,
    );
  });
  const button = view!.root.findByProps({ accessibilityRole: 'button' });
  const style = StyleSheet.flatten(button.props.style);
  expect(style.minHeight).toBeGreaterThanOrEqual(48);
  expect(style.minWidth).toBeGreaterThanOrEqual(48);
  expect(style.height).toBeUndefined();
  for (const text of view!.root.findAllByType(Text)) {
    expect(text.props.allowFontScaling).not.toBe(false);
    expect(text.props.numberOfLines).toBeUndefined();
    expect(text.props.maxFontSizeMultiplier).toBeUndefined();
  }
  await act(() => view?.unmount());
});
