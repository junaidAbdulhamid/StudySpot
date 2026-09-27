// Provider-neutral boundary keeps API transport testable without React Native.
export interface AuthBridge {
  subject(): string | null;
  token(): Promise<string | null>;
  refresh(): Promise<string | null>;
  invalidate(): Promise<void>;
}
let bridge: AuthBridge | undefined;
export const setAuthBridge = (value: AuthBridge) => {
  bridge = value;
};
export const getAuthBridge = () => bridge;
