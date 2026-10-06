import type { TurboModule, CodegenTypes } from 'react-native';
import { TurboModuleRegistry } from 'react-native';
export interface Spec extends TurboModule {
  getSnapshot(): Promise<string>;
  command(name: string, value: string): Promise<string>;
  readonly onSnapshot: CodegenTypes.EventEmitter<string>;
}
export default TurboModuleRegistry.get<Spec>('EiloControl');
