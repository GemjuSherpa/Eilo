import ReactTestRenderer, {act} from 'react-test-renderer';
import {Text} from 'react-native';
import App from '../App';

jest.mock('react-native-safe-area-context', () =>
  jest.requireActual('react-native-safe-area-context/jest/mock').default,
);

test('guest disclosure reaches setup without account input or a microphone request', async () => {
  let renderer: ReactTestRenderer.ReactTestRenderer | undefined;
  await act(() => {renderer = ReactTestRenderer.create(<App />);});
  if (!renderer) {throw new Error('App did not render');}
  const words = renderer.root.findAllByType(Text).map(node => node.props.children).join(' ');
  expect(words).toContain('AI companion');
  expect(words).toContain('audio is not saved or uploaded');
  expect(words).toContain('permanently lose');
  await act(() => renderer?.root.findByProps({accessibilityLabel: 'Continue as guest'}).props.onPress());
  expect(renderer.root.findAllByType(Text).map(node => node.props.children)).toEqual(['Eilo', 'Guest', 'Stopped']);
  await act(() => renderer?.unmount());
});
