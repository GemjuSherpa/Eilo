import Renderer, { act } from 'react-test-renderer';
import { AccessibilityInfo } from 'react-native';
import tokens from '@eilo/design-tokens';
import { Home } from '../src/Home';
import { Action } from '../src/Onboarding';
import type { ControlSnapshot } from '../src/ControlClient';
import type { SpokenPresentation } from '../src/SpokenPresentation';
const mockDiscard = jest.fn();
const mockDismiss = jest.fn<Promise<boolean>, unknown[]>(async () => true);
let mockSpoken: SpokenPresentation | null = null;
jest.mock('@react-navigation/native', () => ({ useIsFocused: () => true }));
jest.mock('../src/SpokenPresentation', () => ({
  ...jest.requireActual('../src/SpokenPresentation'),
  useSpokenPresentation: () => ({ value: mockSpoken, discard: mockDiscard }),
  dismissNativePresentation: (...args: unknown[]) => mockDismiss(...args),
}));
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
const snapshot: ControlSnapshot = {
  version: 1,
  revision: 1,
  capturePending: false,
  speakerConfirmationRequired: false,
  controller: { ...context, version: 1, state: 'standby' },
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
let view: Renderer.ReactTestRenderer;
const action = (label: string) =>
  view.root.findAllByType(Action).find(node => node.props.label === label);
afterEach(async () => {
  await act(() => view?.unmount());
  jest.useRealTimers();
  jest.restoreAllMocks();
  jest.clearAllMocks();
});
test('pin survives idle and normal completion; dismiss works while pinned without an audio command; new query replaces it', async () => {
  jest.useFakeTimers();
  jest
    .spyOn(AccessibilityInfo, 'isScreenReaderEnabled')
    .mockResolvedValue(false);
  mockSpoken = {
    ...context,
    version: 1,
    revision: 1,
    cardId: '00000000-0000-4000-8000-000000000009',
    clauses: ['Completed fixture.'],
    interrupted: false,
    earlierClausesOmitted: false,
  };
  const run = jest.fn();
  const render = (value = snapshot) => (
    <Home
      colors={tokens.colors.light}
      snapshot={value}
      busy={false}
      error={false}
      run={run}
    />
  );
  await act(() => {
    view = Renderer.create(render());
  });
  await act(() => action('Pin card')!.props.onPress());
  await act(() => jest.advanceTimersByTime(30000));
  expect(action('Unpin card')).toBeDefined();
  expect(mockDismiss).not.toHaveBeenCalled();
  mockSpoken = {
    ...mockSpoken,
    generation: 2,
    operationId: '00000000-0000-4000-8000-000000000004',
  };
  await act(() =>
    view.update(
      render({
        ...snapshot,
        controller: {
          ...snapshot.controller,
          generation: 2,
          operationId: mockSpoken!.operationId,
        },
      }),
    ),
  );
  expect(action('Unpin card')).toBeDefined();
  await act(() => action('Dismiss card')!.props.onPress());
  expect(mockDiscard).toHaveBeenCalledWith(mockSpoken.cardId);
  expect(mockDismiss).toHaveBeenCalledWith(mockSpoken, false);
  expect(run).not.toHaveBeenCalled();
  expect(action('Pin card')).toBeUndefined();
  mockSpoken = {
    ...mockSpoken,
    cardId: '00000000-0000-4000-8000-000000000008',
  };
  await act(() => view.update(render()));
  expect(action('Pin card')).toBeDefined();
  expect(action('Unpin card')).toBeUndefined();
});
