import ReactTestRenderer, {act} from 'react-test-renderer';
import {Text} from 'react-native';
import App from '../App';
import {Home} from '../src/Home';
import {decodeSnapshot, type ControlClient, type ControlSnapshot} from '../src/ControlClient';
import tokens from '@eilo/design-tokens';
jest.mock('react-native-safe-area-context', () => jest.requireActual('react-native-safe-area-context/jest/mock').default);
jest.mock('../src/specs/NativeEiloControl', () => ({__esModule: true, default: null}));
jest.mock('@react-navigation/native', () => ({NavigationContainer: ({children}: {children: React.ReactNode}) => children, DefaultTheme: {colors: {}}, DarkTheme: {colors: {}}}));
jest.mock('@react-navigation/native-stack', () => ({createNativeStackNavigator: () => ({Navigator: ({children}: {children: React.ReactNode}) => children, Screen: ({children}: {children: () => React.ReactNode}) => children()})}));
jest.mock('@react-navigation/bottom-tabs', () => ({createBottomTabNavigator: () => ({Navigator: ({children}: {children: React.ReactNode}) => children, Screen: ({children}: {children: () => React.ReactNode}) => children()})}));
const fixture = (state: ControlSnapshot['controller']['state']): ControlSnapshot => ({version: 1, revision: 1,
  controller: {version: 1, state, sessionId: '00000000-0000-4000-8000-000000000001', operationId: '00000000-0000-4000-8000-000000000002', generation: 2, privacyEpoch: 0, modelStatus: 'missing'},
  capturePending: false, speakerConfirmationRequired: false});
function fakeClient() {
  let state = fixture('stopped'); let receive: ((value: ControlSnapshot) => void) | undefined;
  const commands: string[] = [];
  const client: ControlClient = {snapshot: async () => state, command: async name => {commands.push(name); return state;}, subscribe: listener => {receive = listener;return () => {receive = undefined;};}};
  return {client, commands, change(value: ControlSnapshot) {state = value;receive?.(value);}};
}
test('guest disclosure reaches native setup without account or Start request', async () => {
  const fake = fakeClient(); let view: ReactTestRenderer.ReactTestRenderer | undefined;
  await act(() => {view = ReactTestRenderer.create(<App client={fake.client} />);});
  if (!view) {throw new Error('missing view');}
  const words = view.root.findAllByType(Text).map(node => node.props.children).join(' ');
  expect(words).toContain('AI companion'); expect(words).toContain('audio is not saved or uploaded'); expect(words).toContain('permanently lose');
  await act(() => view?.root.findByProps({accessibilityLabel: 'Continue as guest'}).props.onPress());
  expect(view.root.findByProps({accessibilityLabel: 'Start'})).toBeDefined();expect(fake.commands).toEqual([]);
  await act(() => view?.unmount());
});
test('native state changes while detached are read on reconnect, and Stop stays native', async () => {
  const fake = fakeClient(); let view: ReactTestRenderer.ReactTestRenderer | undefined;
  await act(() => {view = ReactTestRenderer.create(<App client={fake.client} />);});
  await act(() => view?.unmount()); fake.change(fixture('standby'));
  await act(() => {view = ReactTestRenderer.create(<App client={fake.client} />);});
  await act(() => view?.root.findByProps({accessibilityLabel: 'Continue as guest'}).props.onPress());
  await act(() => view?.root.findByProps({accessibilityLabel: 'Stop'}).props.onPress());
  expect(fake.commands).toEqual(['stop']); await act(() => view?.unmount());
});
test('pending Start offers Stop, with an accessible speaker confirmation', async () => {
  const commands: string[] = []; let view: ReactTestRenderer.ReactTestRenderer | undefined;
  await act(() => {view = ReactTestRenderer.create(<Home colors={tokens.colors.light} snapshot={{...fixture('stopped'), capturePending: true, speakerConfirmationRequired: true}} busy={false} error={false} run={name => commands.push(name)} />);});
  await act(() => view?.root.findByProps({accessibilityLabel: 'Stop'}).props.onPress());
  await act(() => view?.root.findByProps({accessibilityLabel: 'Confirm speaker output'}).props.onPress());
  expect(commands).toEqual(['stop', 'confirmSpeaker']); await act(() => view?.unmount());
});
test('bridge decoder rejects personal fields, invalid states and oversized payloads', () => {
  expect(decodeSnapshot(JSON.stringify(fixture('stopped'))).controller.state).toBe('stopped');
  expect(() => decodeSnapshot(JSON.stringify({...fixture('stopped'), transcript: 'synthetic'}))).toThrow();
  expect(() => decodeSnapshot(JSON.stringify({...fixture('stopped'), controller: {...fixture('stopped').controller, state: 'fake'}}))).toThrow();
  expect(() => decodeSnapshot(' '.repeat(4097))).toThrow();
});

test('an older snapshot cannot replace a newer native event', async () => {
  let deliver: ((value: ControlSnapshot) => void) | undefined;
  let finish: ((value: ControlSnapshot) => void) | undefined;
  const client: ControlClient = {
    snapshot: () => new Promise(resolve => {finish = resolve;}),
    command: async () => fixture('stopped'),
    subscribe: listener => {deliver = listener;return () => {};},
  };
  let view: ReactTestRenderer.ReactTestRenderer | undefined;
  await act(() => {view = ReactTestRenderer.create(<App client={client} />);});
  await act(() => deliver?.({...fixture('standby'), revision: 5}));
  await act(() => finish?.(fixture('stopped')));
  await act(() => view?.root.findByProps({accessibilityLabel: 'Continue as guest'}).props.onPress());
  expect(view?.root.findByProps({accessibilityLabel: 'Stop'})).toBeDefined();
  await act(() => view?.unmount());
});
test('unknown native state still offers Stop and never Start', async () => {
  const commands: string[] = [];let view: ReactTestRenderer.ReactTestRenderer | undefined;
  await act(() => {view = ReactTestRenderer.create(<Home colors={tokens.colors.light} snapshot={null} busy={false} error={true} run={name => commands.push(name)} />);});
  await act(() => view?.root.findByProps({accessibilityLabel: 'Stop'}).props.onPress());
  expect(commands).toEqual(['stop']);await act(() => view?.unmount());
});
