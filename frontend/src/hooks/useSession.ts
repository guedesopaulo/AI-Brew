import { useState, useEffect } from "react";
import { v4 as uuidv4 } from "uuid";

function storageKey(recipeId: string): string {
  return `brew_session_${recipeId}`;
}

export function useSession(recipeId: string): string {
  const [sessionId, setSessionId] = useState<string>(() => {
    const stored = localStorage.getItem(storageKey(recipeId));
    if (stored) return stored;
    const fresh = uuidv4();
    localStorage.setItem(storageKey(recipeId), fresh);
    return fresh;
  });

  useEffect(() => {
    const stored = localStorage.getItem(storageKey(recipeId));
    if (stored) {
      setSessionId(stored);
    } else {
      const fresh = uuidv4();
      localStorage.setItem(storageKey(recipeId), fresh);
      setSessionId(fresh);
    }
  }, [recipeId]);

  return sessionId;
}
