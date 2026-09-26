import { useCallback, useEffect, useState } from "react";
import { errorMessage } from "../services/api/client";
export function useAsync<T>(loader: () => Promise<T>) {
  const [attempt, setAttempt] = useState(0);
  const [result, setResult] = useState<{
    loader: typeof loader;
    attempt: number;
    data?: T;
    error?: string;
  }>();
  useEffect(() => {
    let active = true;
    Promise.resolve()
      .then(loader)
      .then((data) => {
        if (active) setResult({ loader, attempt, data });
      })
      .catch((error: unknown) => {
        if (active)
          setResult({
            loader,
            attempt,
            error: errorMessage(error),
          });
      });
    return () => {
      active = false;
    };
  }, [loader, attempt]);
  const retry = useCallback(() => setAttempt((x) => x + 1), []);
  const current =
    result?.loader === loader && result.attempt === attempt
      ? result
      : undefined;
  return {
    data: current?.data,
    error: current?.error,
    loading: !current,
    retry,
  };
}
