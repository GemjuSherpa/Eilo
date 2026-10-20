import Renderer, { act } from 'react-test-renderer';
import tokens from '@eilo/design-tokens';
import { DisplaySettings, effectiveDisplay } from '../src/DisplaySettings';

test('all individual choices survive Voice only on and off', () => {
  for (let bits = 0; bits < 8; bits++) {
    const choices = {
      text: bits % 2 === 1,
      images: Math.floor(bits / 2) % 2 === 1,
      video: Math.floor(bits / 4) % 2 === 1,
      voiceOnly: false,
    };
    const original = { ...choices };
    expect(effectiveDisplay({ ...choices, voiceOnly: true })).toEqual({
      text: false,
      images: false,
      video: false,
      voiceOnly: true,
    });
    expect(effectiveDisplay(choices)).toEqual(original);
    expect(choices).toEqual(original);
  }
});
test('screen toggles issue only bounded native preference commands', async () => {
  const run = jest.fn();
  let view: Renderer.ReactTestRenderer | undefined;
  await act(() => {
    view = Renderer.create(
      <DisplaySettings
        colors={tokens.colors.light}
        preferences={{
          text: true,
          images: false,
          video: false,
          voiceOnly: false,
        }}
        disabled={false}
        run={run}
      />,
    );
  });
  for (const [label, command] of [
    ['Voice only', 'voiceOnly'],
    ['Show spoken text', 'displayText'],
    ['Allow result images', 'displayImages'],
    ['Allow result video', 'displayVideo'],
  ]) {
    await act(() =>
      view!.root
        .findByProps({ accessibilityLabel: label })
        .props.onValueChange(true),
    );
    expect(run).toHaveBeenLastCalledWith(command, 'true');
  }
  expect(run).toHaveBeenCalledTimes(4);
  await act(() => view?.unmount());
});
test('unknown preferences keep every control disabled without inventing choices', async () => {
  let view: Renderer.ReactTestRenderer | undefined;
  await act(() => {
    view = Renderer.create(
      <DisplaySettings
        colors={tokens.colors.dark}
        preferences={undefined}
        disabled
        run={() => {}}
      />,
    );
  });
  for (const label of [
    'Voice only',
    'Show spoken text',
    'Allow result images',
    'Allow result video',
  ]) {
    expect(
      view!.root.findByProps({ accessibilityLabel: label }).props.disabled,
    ).toBe(true);
  }
  await act(() => view?.unmount());
});
