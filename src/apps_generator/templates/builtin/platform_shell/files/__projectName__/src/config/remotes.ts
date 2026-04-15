import type { RemoteApp } from "../types";

let _remotes: RemoteApp[] = [];
let _loaded = false;

export async function loadRemotes(): Promise<RemoteApp[]> {
  if (_loaded) return _remotes;

  try {
    const res = await fetch("/remotes.json");
    if (res.ok) {
      _remotes = await res.json();
    }
  } catch {
    console.warn("Failed to load remotes.json, no remote apps will be available.");
  }

  _loaded = true;
  return _remotes;
}

export function getRemotes(): RemoteApp[] {
  return _remotes;
}
