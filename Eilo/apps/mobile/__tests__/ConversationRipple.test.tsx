import Renderer, { act } from 'react-test-renderer';
import {
  AccessibilityInfo,
  Animated,
  AppState,
  type AppStateStatus,
} from 'react-native';
import tokens from '@eilo/design-tokens';
import { controllerStates } from '@eilo/contracts';
import { ConversationRipple } from '../src/ConversationRipple';
import type { ControlSnapshot } from '../src/ControlClient';

const snapshot = (
  state: ControlSnapshot['controller']['state'],
): ControlSnapshot => ({
  version: 1,
  revision: 1,
  capturePending: false,
  speakerConfirmationRequired: false,
  controller: {
    version: 1,
    state,
    sessionId: '00000000-0000-4000-8000-000000000001',
    operationId: '00000000-0000-4000-8000-000000000002',
    generation: 1,
    privacyEpoch: 0,
  },
  preferences: {
    version: 1,
    historyChoice: 'private',
    onboardingComplete: true,
    historyAvailable: false,
    historyEnabled: false,
    backgroundConsent: false,
    privateSession: true,
    volume: 100,
  },
});
let view: Renderer.ReactTestRenderer;
let appChanged: (state: AppStateStatus) => void;
let motionChanged: (reduced: boolean) => void;
let start: jest.Mock;
let stop: jest.Mock;
const draw = (value: ControlSnapshot | null, error = false) => (
  <ConversationRipple
    colors={tokens.colors.light}
    snapshot={value}
    error={error}
  />
);
beforeEach(() => {
  jest
    .spyOn(AppState, 'addEventListener')
    .mockImplementation((_name, callback) => {
      appChanged = callback;
      return { remove: jest.fn() };
    });
  jest
    .spyOn(AccessibilityInfo, 'isReduceMotionEnabled')
    .mockResolvedValue(false);
  jest
    .spyOn(AccessibilityInfo, 'addEventListener')
    .mockImplementation((_name, callback) => {
      motionChanged = callback as (value: boolean) => void;
      return { remove: jest.fn() };
    });
  start = jest.fn();
  stop = jest.fn();
  jest
    .spyOn(Animated, 'loop')
    .mockReturnValue({ start, stop, reset: jest.fn() });
});
afterEach(async () => {
  await act(() => view?.unmount());
  jest.restoreAllMocks();
});

test.each(controllerStates)(
  'only actual listening/speaking can animate: %s',
  async state => {
    await act(() => {
      view = Renderer.create(draw(snapshot(state)));
    });
    await act(() => appChanged('active'));
    expect(view.root.findByProps({ testID: `ripple-${state}` })).toBeDefined();
    expect(start).toHaveBeenCalledTimes(
      ['listening', 'speaking'].includes(state) ? 1 : 0,
    );
    expect(
      view.root.findByProps({ testID: 'conversation-ripple' }).props
        .importantForAccessibility,
    ).toBe('no-hide-descendants');
  },
);
test('Stop, pending capture and unavailable controls cannot look active', async () => {
  await act(() => {
    view = Renderer.create(draw(snapshot('listening')));
  });
  await act(() => appChanged('active'));
  expect(start).toHaveBeenCalledTimes(1);
  await act(() => view.update(draw(snapshot('stopped'))));
  expect(stop).toHaveBeenCalledTimes(1);
  start.mockClear();
  await act(() =>
    view.update(draw({ ...snapshot('listening'), capturePending: true })),
  );
  expect(view.root.findByProps({ testID: 'ripple-starting' })).toBeDefined();
  await act(() => view.update(draw(snapshot('speaking'), true)));
  expect(view.root.findByProps({ testID: 'ripple-unavailable' })).toBeDefined();
  expect(start).not.toHaveBeenCalled();
});
test('reduced motion and background stop active decoration', async () => {
  await act(() => {
    view = Renderer.create(draw(snapshot('speaking')));
  });
  await act(() => appChanged('active'));
  await act(() => motionChanged(true));
  expect(stop).toHaveBeenCalledTimes(1);
  await act(() => motionChanged(false));
  await act(() => appChanged('background'));
  expect(stop).toHaveBeenCalledTimes(2);
});
test('late initial motion query cannot overwrite a new accessibility choice', async () => {
  let resolve: (value: boolean) => void = () => {};
  jest.spyOn(AccessibilityInfo, 'isReduceMotionEnabled').mockReturnValue(
    new Promise(done => {
      resolve = done;
    }),
  );
  await act(() => {
    view = Renderer.create(draw(snapshot('listening')));
  });
  await act(() => appChanged('active'));
  await act(() => motionChanged(true));
  await act(() => resolve(false));
  expect(start).not.toHaveBeenCalled();
});
