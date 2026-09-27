// Chunking avoids native keychain per-item size limits. Only a small manifest
// is replaced after all new chunks are safely written; tokens never use AsyncStorage.
export interface SecureEngine {
  getItemAsync(key: string): Promise<string | null>;
  setItemAsync(key: string, value: string): Promise<void>;
  deleteItemAsync(key: string): Promise<void>;
}
export function createSecureStorage(engine: SecureEngine) {
  let queue: Promise<unknown> = Promise.resolve();
  let counter = 0;
  const serial = <T>(work: () => Promise<T>): Promise<T> => {
    const next = queue.then(work, work);
    queue = next.catch(() => {});
    return next;
  };
  const manifest = async (key: string): Promise<string[]> => {
    const raw = await engine.getItemAsync(key);
    if (!raw) return [];
    const value: unknown = JSON.parse(raw);
    if (
      !Array.isArray(value) ||
      value.length > 256 ||
      !value.every((x) => typeof x === "string" && x.startsWith(key + "."))
    )
      throw new Error("Secure session storage is unreadable");
    return value;
  };
  return {
    getItem: (key: string) =>
      serial(async () => {
        const keys = await manifest(key);
        if (!keys.length) return null;
        const parts = await Promise.all(
          keys.map((k) => engine.getItemAsync(k)),
        );
        if (parts.some((p) => p === null))
          throw new Error("Secure session storage is incomplete");
        return parts.join("");
      }),
    setItem: (key: string, value: string) =>
      serial(async () => {
        const old = await manifest(key);
        const version = Date.now().toString(36) + "-" + ++counter;
        const keys: string[] = [];
        if (value.length > 131072)
          throw new Error("Session exceeds secure storage capacity");
        for (let i = 0; i < value.length; i += 512) {
          const part = key + "." + version + "." + keys.length;
          keys.push(part);
          await engine.setItemAsync(part, value.slice(i, i + 512));
        }
        await engine.setItemAsync(key, JSON.stringify(keys));
        await Promise.all(
          old.map((k) => engine.deleteItemAsync(k).catch(() => {})),
        );
      }),
    removeItem: (key: string) =>
      serial(async () => {
        const keys = await manifest(key);
        await engine.deleteItemAsync(key);
        await Promise.all(
          keys.map((k) => engine.deleteItemAsync(k).catch(() => {})),
        );
      }),
  };
}
