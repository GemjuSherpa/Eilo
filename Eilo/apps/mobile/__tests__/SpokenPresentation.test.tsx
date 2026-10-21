import Renderer, { act } from 'react-test-renderer';
import { AppState, Text, type AppStateStatus } from 'react-native';
import tokens from '@eilo/design-tokens';
import {
  decodePresentation,
  SpokenReply,
  useSpokenPresentation,
  type PresentationReader,
} from '../src/SpokenPresentation';
import type { ControlSnapshot } from '../src/ControlClient';
jest.mock('../src/specs/NativeEiloControl', () => ({
  __esModule: true,
  default: null,
}));

const snapshot: ControlSnapshot = {
  version: 1,
  revision: 1,
  capturePending: false,
  speakerConfirmationRequired: false,
  controller: {
    version: 1,
    state: 'speaking',
    sessionId: '00000000-0000-4000-8000-000000000001',
    operationId: '00000000-0000-4000-8000-000000000002',
    generation: 2,
    privacyEpoch: 3,
  },
  preferences: {
    version: 2,
    display: { text: true, images: false, video: false, voiceOnly: false },
    historyChoice: 'private',
    onboardingComplete: true,
    historyAvailable: false,
    historyEnabled: false,
    backgroundConsent: false,
    privateSession: true,
    volume: 100,
  },
};
const envelope = (control = snapshot.controller) => ({
  version: 1,
  sessionId: control.sessionId,
  operationId: control.operationId,
  generation: control.generation,
  privacyEpoch: control.privacyEpoch,
  revision: 1,
  cardId: '00000000-0000-4000-8000-000000000009',
  clauses: ['Completed synthetic clause.'],
  interrupted: false,
  earlierClausesOmitted: false,
});
let discardCurrent: (id: string) => void;
function HookView({
  value = snapshot,
  blocked = false,
  reader,
}: {
  value?: ControlSnapshot;
  blocked?: boolean;
  reader: PresentationReader;
}) {
  const { value: content, discard } = useSpokenPresentation(
    value,
    blocked,
    reader,
  );
  discardCurrent = discard;
  return <SpokenReply value={content} colors={tokens.colors.light} />;
}
let view: Renderer.ReactTestRenderer | undefined;
let changed: (state: AppStateStatus) => void;
beforeEach(() => {
  jest.useFakeTimers();
  jest
    .spyOn(AppState, 'addEventListener')
    .mockImplementation((_event, callback) => {
      changed = callback;
      return { remove: jest.fn() };
    });
});
afterEach(async () => {
  await act(() => view?.unmount());
  view = undefined;
  jest.useRealTimers();
  jest.restoreAllMocks();
});
test('closed content decoder rejects stale, unbounded, draft and unknown fields', () => {
  expect(
    decodePresentation(JSON.stringify(envelope()), snapshot.controller).clauses,
  ).toHaveLength(1);
  for (const patch of [
    { generation: 1 },
    { privacyEpoch: 2 },
    { revision: true },
    { revision: -1 },
    { clauses: Array(33).fill('x') },
    { clauses: ['x'.repeat(1025)] },
    { clauses: ['x\0'] },
    { clauses: Array(5).fill('x'.repeat(1024)) },
    { draft: 'not spoken' },
    { url: 'https://private.invalid' },
  ]) {
    expect(() =>
      decodePresentation(
        JSON.stringify({ ...envelope(), ...patch }),
        snapshot.controller,
      ),
    ).toThrow();
  }
  expect(() =>
    decodePresentation(' '.repeat(32769), snapshot.controller),
  ).toThrow();
});
test('renders plain completed speech with honest interruption and omission labels', async () => {
  await act(() => {
    view = Renderer.create(
      <SpokenReply
        colors={tokens.colors.light}
        value={{
          ...envelope(),
          version: 1,
          interrupted: true,
          earlierClausesOmitted: true,
        }}
      />,
    );
  });
  const words = view!.root
    .findAllByType(Text)
    .map(node => node.props.children)
    .join(' ');
  expect(words).toContain('Completed synthetic clause.');
  expect(words).toContain('Reply interrupted');
  expect(words).toContain('most recent completed clauses');
});
test('background drops in-flight content and prevents further reads', async () => {
  let finish: (source: string) => void = () => {};
  const reader = jest.fn(
    () =>
      new Promise<string>(resolve => {
        finish = resolve;
      }),
  );
  await act(() => {
    view = Renderer.create(<HookView reader={reader} />);
  });
  await act(() => changed('active'));
  await act(() => changed('background'));
  await act(() => finish(JSON.stringify(envelope())));
  await act(() => jest.advanceTimersByTime(1000));
  expect(view!.root.findAllByProps({ testID: 'spoken-reply' })).toHaveLength(0);
  expect(reader).toHaveBeenCalledTimes(1);
});
test('new generation rejects late old content and disabled text makes no reads', async () => {
  const completions: ((source: string) => void)[] = [];
  const reader = jest.fn(
    () => new Promise<string>(resolve => completions.push(resolve)),
  );
  await act(() => {
    view = Renderer.create(<HookView reader={reader} />);
  });
  await act(() => changed('active'));
  const replacement = {
    ...snapshot,
    controller: { ...snapshot.controller, generation: 4 },
  };
  await act(() =>
    view!.update(<HookView value={replacement} reader={reader} />),
  );
  await act(() => completions[0](JSON.stringify(envelope())));
  expect(view!.root.findAllByProps({ testID: 'spoken-reply' })).toHaveLength(0);
  await act(() =>
    completions[1](JSON.stringify(envelope(replacement.controller))),
  );
  expect(view!.root.findByProps({ testID: 'spoken-reply' })).toBeDefined();
  await act(() =>
    view!.update(<HookView value={replacement} blocked reader={reader} />),
  );
  expect(view!.root.findAllByProps({ testID: 'spoken-reply' })).toHaveLength(0);
  const count = reader.mock.calls.length;
  await act(() =>
    view!.update(
      <HookView
        reader={reader}
        value={{
          ...snapshot,
          preferences: {
            ...snapshot.preferences,
            display: { ...snapshot.preferences.display, text: false },
          },
        }}
      />,
    ),
  );
  await act(() => jest.advanceTimersByTime(1000));
  expect(reader).toHaveBeenCalledTimes(count);
});

test('dismiss releases current JS clauses, rejects late same-card polls and cannot dismiss a newer card', async () => {
  let current = envelope();
  const reader = jest.fn(async () => JSON.stringify(current));
  await act(() => {
    view = Renderer.create(<HookView reader={reader} />);
  });
  await act(() => changed('active'));
  const oldDiscard = discardCurrent;
  await act(() => discardCurrent(current.cardId));
  expect(view!.root.findAllByProps({ testID: 'spoken-reply' })).toHaveLength(0);
  await act(() => jest.advanceTimersByTime(250));
  expect(view!.root.findAllByProps({ testID: 'spoken-reply' })).toHaveLength(0);
  current = {
    ...current,
    cardId: '00000000-0000-4000-8000-000000000008',
    revision: 2,
  };
  await act(() => jest.advanceTimersByTime(250));
  expect(
    view!.root.findAllByProps({ testID: 'spoken-reply' }).length,
  ).toBeGreaterThan(0);
  await act(() => oldDiscard('00000000-0000-4000-8000-000000000009'));
  expect(
    view!.root.findAllByProps({ testID: 'spoken-reply' }).length,
  ).toBeGreaterThan(0);
});

test.each(['stop', 'privacyEpoch', 'voiceOnly', 'textOff'] as const)(
  '%s removes synthetic private content and rejects an in-flight prior response',
  async transition => {
    let finish: (source: string) => void = () => {};
    let defer = false;
    const reader = jest.fn(() =>
      defer
        ? new Promise<string>(done => {
            finish = done;
          })
        : Promise.resolve(JSON.stringify(envelope())),
    );
    await act(() => {
      view = Renderer.create(<HookView reader={reader} />);
    });
    await act(() => changed('active'));
    expect(
      view!.root.findAllByProps({ testID: 'spoken-reply' }).length,
    ).toBeGreaterThan(0);
    defer = true;
    await act(() => jest.advanceTimersByTime(250));
    const oldFinish = finish;
    const replacement: ControlSnapshot = {
      ...snapshot,
      controller: { ...snapshot.controller },
      preferences: {
        ...snapshot.preferences,
        display: { ...snapshot.preferences.display },
      },
    };
    if (transition === 'stop') {
      replacement.controller.state = 'stopped';
    }
    if (transition === 'privacyEpoch') {
      replacement.controller.privacyEpoch++;
    }
    if (transition === 'voiceOnly') {
      replacement.preferences.display.voiceOnly = true;
    }
    if (transition === 'textOff') {
      replacement.preferences.display.text = false;
    }
    await act(() =>
      view!.update(<HookView value={replacement} reader={reader} />),
    );
    await act(() => oldFinish(JSON.stringify(envelope())));
    expect(view!.root.findAllByProps({ testID: 'spoken-reply' })).toHaveLength(
      0,
    );
  },
);
