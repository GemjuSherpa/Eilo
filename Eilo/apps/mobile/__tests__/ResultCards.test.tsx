import Renderer, { act } from 'react-test-renderer';
import { Image, Linking, Text } from 'react-native';
import tokens from '@eilo/design-tokens';
import {
  parseResultEnvelope,
  ResultCards,
  sourceHost,
  type ResultCardData,
} from '../src/ResultCards';
import type { SpokenPresentation } from '../src/SpokenPresentation';
jest.mock('../src/specs/NativeEiloControl', () => ({
  __esModule: true,
  default: null,
}));

const context = {
  sessionId: '00000000-0000-4000-8000-000000000001',
  operationId: '00000000-0000-4000-8000-000000000002',
  generation: 1,
  privacyEpoch: 2,
};
const result: ResultCardData = {
  id: '00000000-0000-4000-8000-000000000003',
  kind: 'article',
  title: 'Synthetic source title',
  summary: 'A source-provided fixture summary.',
  source: { name: 'Fixture publisher', url: 'https://example.org/article' },
  details: [],
  media: { images: 'available', video: 'unavailable' },
};
const spoken: SpokenPresentation = {
  ...context,
  version: 1,
  revision: 1,
  clauses: ['Completed fixture answer.'],
  interrupted: false,
  earlierClausesOmitted: false,
};
const preferences = {
  text: true,
  images: false,
  video: false,
  voiceOnly: false,
};
function words(view: Renderer.ReactTestRenderer) {
  return view.root
    .findAllByType(Text)
    .map(node => node.props.children)
    .flat()
    .join(' ');
}
let view: Renderer.ReactTestRenderer | undefined;
afterEach(async () => {
  await act(() => view?.unmount());
  view = undefined;
  jest.restoreAllMocks();
});

test('missing sources, stale scope, duplicate IDs and unknown fields produce no cards', () => {
  expect(
    parseResultEnvelope({ context, items: [result] }, context),
  ).toHaveLength(1);
  for (const items of [
    [{ ...result, source: null }],
    [{ ...result, rating: 5 }],
    [result, result],
    Array(9).fill(result),
    [{ ...result, kind: { toString: 'x' } }],
    [{ ...result, title: '<script>bad</script>' }],
    [{ ...result, summary: 'x'.repeat(1025) }],
  ]) {
    expect(parseResultEnvelope({ context, items }, context)).toEqual([]);
  }
  expect(
    parseResultEnvelope(
      { context: { ...context, privacyEpoch: 3 }, items: [result] },
      context,
    ),
  ).toEqual([]);
  const getter = jest.fn(() => result.title);
  const bad = { ...result };
  Object.defineProperty(bad, 'title', { get: getter, enumerable: true });
  expect(parseResultEnvelope({ context, items: [bad] }, context)).toEqual([]);
  expect(getter).not.toHaveBeenCalled();
});
test('source attribution rejects unsafe targets without making any request', () => {
  for (const url of [
    'http://example.org',
    'https://user:secret@example.org',
    'https://localhost/a',
    'https://127.0.0.1/a',
    'https://[::1]/',
    'file:///private',
    'https://a..org',
    'https://example.org:443/a',
    'https://example.org\\@private.local',
  ]) {
    expect(sourceHost(url)).toBeNull();
  }
  expect(sourceHost('https://example.org/a?private=value')).toBe('example.org');
});
test('source cards replace default text while retaining a recoverable spoken answer', async () => {
  const open = jest.spyOn(Linking, 'openURL');
  await act(() => {
    view = Renderer.create(
      <ResultCards
        envelope={{ context, items: [result] }}
        expected={context}
        spoken={spoken}
        preferences={preferences}
        colors={tokens.colors.light}
      />,
    );
  });
  expect(words(view!)).toContain('Synthetic source title');
  expect(words(view!)).toContain('Fixture publisher');
  expect(words(view!)).not.toContain('Completed fixture answer.');
  expect(words(view!)).not.toContain('rating');
  expect(
    view!.root.findByProps({ accessibilityLabel: 'Places unavailable' }).props
      .disabled,
  ).toBe(true);
  await act(() =>
    view!.root
      .findByProps({ accessibilityLabel: 'Show spoken answer' })
      .props.onPress(),
  );
  expect(words(view!)).toContain('Completed fixture answer.');
  expect(open).not.toHaveBeenCalled();
  expect(view!.root.findAllByType(Image)).toHaveLength(0);
});
test('media flags never authorize loading, and Voice only suppresses all result content', async () => {
  const video = {
    ...result,
    kind: 'video',
    media: { images: 'available', video: 'available' },
  };
  await act(() => {
    view = Renderer.create(
      <ResultCards
        envelope={{ context, items: [video] }}
        expected={context}
        spoken={spoken}
        preferences={{ ...preferences, images: true, video: true }}
        colors={tokens.colors.dark}
      />,
    );
  });
  expect(words(view!)).toContain('Images unavailable');
  expect(words(view!)).toContain('Video unavailable');
  expect(view!.root.findAllByType(Image)).toHaveLength(0);
  await act(() =>
    view!.update(
      <ResultCards
        envelope={{ context, items: [video] }}
        expected={context}
        spoken={spoken}
        preferences={{ ...preferences, voiceOnly: true }}
        colors={tokens.colors.dark}
      />,
    ),
  );
  expect(view!.toJSON()).toBeNull();
});
test('malformed result falls back to speech, but stale speech cannot resurface', async () => {
  await act(() => {
    view = Renderer.create(
      <ResultCards
        envelope={{ context, items: [{ ...result, source: {} }] }}
        expected={context}
        spoken={spoken}
        preferences={preferences}
        colors={tokens.colors.light}
      />,
    );
  });
  expect(words(view!)).toContain('Completed fixture answer.');
  await act(() =>
    view!.update(
      <ResultCards
        expected={{ ...context, generation: 2 }}
        spoken={spoken}
        preferences={preferences}
        colors={tokens.colors.light}
      />,
    ),
  );
  expect(view!.toJSON()).toBeNull();
});
