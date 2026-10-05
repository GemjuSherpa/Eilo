import ReactTestRenderer, {act} from 'react-test-renderer';
import {Text} from 'react-native';
import App from '../App';

jest.mock('react-native-safe-area-context', () =>
  jest.requireActual('react-native-safe-area-context/jest/mock').default,
);

test('guest launch shows stopped state without active controls or sample links', async () => {
  let renderer: ReactTestRenderer.ReactTestRenderer | undefined;
  await act(() => {renderer = ReactTestRenderer.create(<App />);});
  if (!renderer) {throw new Error('App did not render');}
  expect(renderer.root.findAllByType(Text).map(node => node.props.children)).toEqual(['Eilo', 'Guest', 'Stopped']);
  expect(renderer.root.findAll(node => typeof node.props.onPress === 'function')).toHaveLength(0);
  await act(() => renderer?.unmount());
});
