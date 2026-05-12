const TOKEN = import.meta.env.VITE_API_TOKEN as string | undefined;

export async function apiFetch<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const resp = await fetch(`/api${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${TOKEN ?? "test-token"}`,
      ...options.headers,
    },
  });

  if (!resp.ok) {
    const text = await resp.text().catch(() => resp.statusText);
    throw new Error(`${resp.status}: ${text}`);
  }

  return resp.json() as Promise<T>;
}

export function apiToken(): string {
  return TOKEN ?? "test-token";
}
