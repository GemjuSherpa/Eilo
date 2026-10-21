import Renderer, { act } from 'react-test-renderer';
import { AccessibilityInfo, Text } from 'react-native';
import {
  useVisualInactivity,
  type VisualActivity,
} from '../src/VisualInactivity';

const idle: VisualActivity = {
  speech: false,
  processing: false,
  loading: false,
  video: false,
  pinned: false,
};
let controls: ReturnType<typeof useVisualInactivity>;
let changed: (enabled: boolean) => void;
let view: Renderer.ReactTestRenderer | undefined;
function Harness({
  card = 'card-a',
  revision = 1,
  activity = idle,
  onHidden = undefined,
}: {
  card?: string;
  revision?: number;
  activity?: VisualActivity;
  onHidden?: (key: string) => void;
}) {
  controls = useVisualInactivity(card, revision, activity, onHidden);
  return <Text>{controls.visible ? 'visible' : 'hidden'}</Text>;
}
beforeEach(() => {
  jest.useFakeTimers();
  jest
    .spyOn(AccessibilityInfo, 'isScreenReaderEnabled')
    .mockResolvedValue(false);
  jest
    .spyOn(AccessibilityInfo, 'addEventListener')
    .mockImplementation((_event, callback) => {
      changed = callback as (enabled: boolean) => void;
      return { remove: jest.fn() };
    });
});
afterEach(async () => {
  await act(() => view?.unmount());
  view = undefined;
  jest.useRealTimers();
  jest.restoreAllMocks();
});
test('19.9 seconds remains visible; 20 seconds hides exactly once without control actions', async () => {
  const hidden = jest.fn();
  await act(() => {
    view = Renderer.create(<Harness onHidden={hidden} />);
  });
  await act(() => jest.advanceTimersByTime(19900));
  expect(controls.visible).toBe(true);
  await act(() => jest.advanceTimersByTime(100));
  expect(controls.visible).toBe(false);
  await act(() => jest.advanceTimersByTime(30000));
  expect(hidden).toHaveBeenCalledTimes(1);
  expect(hidden).toHaveBeenCalledWith('card-a');
});
test.each(['speech', 'processing', 'loading', 'video', 'pinned'] as const)(
  '%s suppresses dismissal then starts a fresh idle period',
  async flag => {
    await act(() => {
      view = Renderer.create(<Harness activity={{ ...idle, [flag]: true }} />);
    });
    await act(() => jest.advanceTimersByTime(30000));
    expect(controls.visible).toBe(true);
    await act(() => view!.update(<Harness />));
    await act(() => jest.advanceTimersByTime(19999));
    expect(controls.visible).toBe(true);
    await act(() => jest.advanceTimersByTime(1));
    expect(controls.visible).toBe(false);
  },
);
test('touch/scroll interaction is synchronous at the deadline and new content resets idle', async () => {
  await act(() => {
    view = Renderer.create(<Harness />);
  });
  await act(() => jest.advanceTimersByTime(19999));
  await act(() => {
    controls.interact();
    jest.advanceTimersByTime(1);
  });
  expect(controls.visible).toBe(true);
  await act(() => jest.advanceTimersByTime(19900));
  expect(controls.visible).toBe(true);
  await act(() => view!.update(<Harness revision={2} />));
  await act(() => jest.advanceTimersByTime(19999));
  expect(controls.visible).toBe(true);
  await act(() => jest.advanceTimersByTime(1));
  expect(controls.visible).toBe(false);
});
test('screen-reader and keyboard focus preserve content; stale initial query cannot override accessibility', async () => {
  let resolve: (enabled: boolean) => void = () => {};
  jest.spyOn(AccessibilityInfo, 'isScreenReaderEnabled').mockReturnValue(
    new Promise(done => {
      resolve = done;
    }),
  );
  await act(() => {
    view = Renderer.create(<Harness />);
  });
  await act(() => changed(true));
  await act(() => resolve(false));
  await act(() => jest.advanceTimersByTime(30000));
  expect(controls.visible).toBe(true);
  await act(() => changed(false));
  await act(() => controls.focus());
  await act(() => jest.advanceTimersByTime(30000));
  expect(controls.visible).toBe(true);
  await act(() => controls.blur());
  await act(() => jest.advanceTimersByTime(20000));
  expect(controls.visible).toBe(false);
});
test('a hidden card stays hidden on old callbacks; a new card appears and old actions cannot hide it', async () => {
  await act(() => {
    view = Renderer.create(<Harness />);
  });
  const oldHide = controls.hide;
  await act(() => jest.advanceTimersByTime(20000));
  await act(() => view!.update(<Harness revision={2} />));
  expect(controls.visible).toBe(false);
  await act(() => view!.update(<Harness card="card-b" />));
  expect(controls.visible).toBe(true);
  await act(() => oldHide());
  expect(controls.visible).toBe(true);
});
