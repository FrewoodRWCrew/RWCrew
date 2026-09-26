// Holds "who is logged in" for the whole app, so any screen can read it.

import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";

import { fetchCurrentUser, hasStoredSession, login, logout, type CurrentUser } from "./api";

type Session = {
  // true while we check the stored tokens at startup
  loading: boolean;
  user: CurrentUser | null;
  signIn: (email: string, password: string) => Promise<void>;
  signOut: () => Promise<void>;
};

const SessionContext = createContext<Session | null>(null);

export function SessionProvider({ children }: { children: ReactNode }) {
  const [loading, setLoading] = useState(true);
  const [user, setUser] = useState<CurrentUser | null>(null);

  // At startup: if tokens are stored, ask the backend who they belong to
  // (this silently refreshes an expired access token when needed).
  useEffect(() => {
    (async () => {
      try {
        if (await hasStoredSession()) setUser(await fetchCurrentUser());
      } catch {
        // No connection / server error: show the login screen.
        setUser(null);
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  const signIn = useCallback(async (email: string, password: string) => {
    setUser(await login(email, password));
  }, []);

  const signOut = useCallback(async () => {
    await logout();
    setUser(null);
  }, []);

  const value = useMemo(() => ({ loading, user, signIn, signOut }), [loading, user, signIn, signOut]);
  return <SessionContext.Provider value={value}>{children}</SessionContext.Provider>;
}

// Use inside any screen: const { user, signOut } = useSession();
export function useSession(): Session {
  const session = useContext(SessionContext);
  if (session === null) throw new Error("useSession must be used inside <SessionProvider>");
  return session;
}
