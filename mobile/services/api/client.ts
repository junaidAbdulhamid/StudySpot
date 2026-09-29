import { getAuthBridge, AuthBridge } from "../auth/bridge";
import { z } from "zod";
export class ApiError extends Error {
  constructor(
    public code: string,
    message: string,
    public status?: number,
  ) {
    super(message);
    this.name = "ApiError";
  }
}
export const errorMessage = (error: unknown) =>
  error instanceof ApiError
    ? error.message
    : "Something went wrong. Please try again.";
export function createApiClient(
  baseUrl: string | undefined,
  timeoutMs = 10000,
  transport: typeof fetch = fetch,
  auth: () => AuthBridge | undefined = getAuthBridge,
) {
  return {
    async request<T>(
      path: string,
      schema: z.ZodType<T>,
      options: { method?: string; body?: unknown; signal?: AbortSignal } = {},
    ): Promise<T> {
      if (!baseUrl || !/^https?:\/\//.test(baseUrl))
        throw new ApiError(
          "CONFIGURATION",
          "Set EXPO_PUBLIC_API_URL to connect StudySpot to the API.",
        );
      const controller = new AbortController();
      let timedOut = false;
      const cancel = () => controller.abort();
      options.signal?.addEventListener("abort", cancel, { once: true });
      if (options.signal?.aborted) controller.abort();
      const timer = setTimeout(() => {
        timedOut = true;
        controller.abort();
      }, timeoutMs);
      try {
        const bridge = auth();
        const protectedRequest =
          path === "/me" ||
          path.startsWith("/me/") ||
          path.startsWith("/checkins") ||
          path.startsWith("/crowd-reports") ||
          path.startsWith("/occupancy-validations");
        const subject = bridge?.subject();
        const ensureIdentity = () => {
          if (protectedRequest && (!subject || bridge?.subject() !== subject))
            throw new ApiError(
              "SESSION_CHANGED",
              "Please sign in to continue.",
              401,
            );
        };
        ensureIdentity();
        let token = protectedRequest ? await bridge?.token() : null;
        ensureIdentity();
        const send = () =>
          transport(`${baseUrl.replace(/\/$/, "")}${path}`, {
            method: options.method ?? "GET",
            headers: {
              Accept: "application/json",
              ...(token ? { Authorization: `Bearer ${token}` } : {}),
              ...(options.body === undefined
                ? {}
                : { "Content-Type": "application/json" }),
            },
            body:
              options.body === undefined
                ? undefined
                : JSON.stringify(options.body),
            signal: controller.signal,
          });
        let response = await send();
        if (protectedRequest && response.status === 401 && bridge) {
          ensureIdentity();
          token = await bridge.refresh();
          ensureIdentity();
          if (token) response = await send(); // At most one retry; /me mutations are idempotent.
          if (!token || response.status === 401) {
            ensureIdentity();
            await bridge.invalidate();
            throw new ApiError(
              "UNAUTHORIZED",
              "Your session has expired. Please sign in again.",
              401,
            );
          }
        }
        ensureIdentity();
        let body: unknown;
        try {
          body = response.status === 204 ? undefined : await response.json();
        } catch {
          throw new ApiError(
            "INVALID_RESPONSE",
            "The server returned an unreadable response. Please retry.",
            response.status,
          );
        }
        if (!response.ok) {
          const parsed = z
            .object({
              error: z.object({ code: z.string(), message: z.string() }),
            })
            .safeParse(body);
          throw new ApiError(
            parsed.success ? parsed.data.error.code : "HTTP_ERROR",
            parsed.success
              ? parsed.data.error.message
              : "Couldn’t load study spots. Please try again.",
            response.status,
          );
        }
        const parsed = schema.safeParse(body);
        if (!parsed.success)
          throw new ApiError(
            "INVALID_RESPONSE",
            "The server returned unexpected data. Please retry.",
            response.status,
          );
        return parsed.data;
      } catch (error) {
        if (error instanceof ApiError) throw error;
        if (timedOut)
          throw new ApiError(
            "TIMEOUT",
            "The request took too long. Check your connection and try again.",
          );
        if (options.signal?.aborted)
          throw new ApiError("CANCELLED", "Request cancelled.");
        throw new ApiError(
          "NETWORK",
          "Couldn’t reach StudySpot. Check your connection and that the API is running.",
        );
      } finally {
        clearTimeout(timer);
        options.signal?.removeEventListener("abort", cancel);
      }
    },
  };
}
export const apiClient = createApiClient(process.env.EXPO_PUBLIC_API_URL);
export const dataSchema = <T extends z.ZodType>(schema: T) =>
  z.object({ data: schema });
export const pageSchema = <T extends z.ZodType>(schema: T) =>
  z.object({
    items: z.array(schema),
    page: z.number().int().positive(),
    page_size: z.number().int().positive(),
    total: z.number().int().nonnegative(),
  });
export type ApiPage<T> = {
  items: T[];
  page: number;
  page_size: number;
  total: number;
};
export async function collectPages<T>(
  load: (page: number) => Promise<ApiPage<T>>,
): Promise<T[]> {
  const items: T[] = [];
  let page = 1;
  for (;;) {
    const result = await load(page);
    items.push(...result.items);
    if (result.items.length === 0 || items.length >= result.total) return items;
    page++;
  }
}
