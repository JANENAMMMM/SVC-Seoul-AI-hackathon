export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
  }
}
export async function api<T>(
  path: string,
  options: RequestInit = {},
  key = "",
): Promise<T> {
  const response = await fetch("/api" + path, {
    ...options,
    credentials: "same-origin",
    headers: {
      "Content-Type": "application/json",
      ...(key ? { "X-Trip-Key": key } : {}),
      ...options.headers,
    },
  });
  const body = await response
    .json()
    .catch(() => ({ detail: "응답을 읽을 수 없습니다." }));
  if (!response.ok)
    throw new ApiError(
      response.status,
      typeof body.detail === "string"
        ? body.detail
        : "입력 조건을 확인해주세요.",
    );
  return body;
}
export const post = (body: unknown = {}): RequestInit => ({
  method: "POST",
  body: JSON.stringify(body),
});
export const grade = (n: number | null | undefined) =>
  n == null ? null : n <= 3 ? "하" : n <= 5 ? "중" : "상";
export const safeUrl = (url: string | undefined) =>
  url && /^https?:\/\//i.test(url) ? url : undefined;
