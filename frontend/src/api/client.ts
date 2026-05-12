const _rawToken = import.meta.env.VITE_API_TOKEN as string | undefined;

if (!_rawToken) {
  throw new Error(
    "VITE_API_TOKEN is not set — create frontend/.env.local with VITE_API_TOKEN=<your-token>",
  );
}

const TOKEN: string = _rawToken;

export async function apiFetch<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const resp = await fetch(`/api${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${TOKEN}`,
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
  return TOKEN;
}
