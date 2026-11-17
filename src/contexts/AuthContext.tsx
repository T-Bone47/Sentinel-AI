import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import { ApiError, getCurrentUser, hasSession, login, logout } from '../services/api';
import { ACCESS_TOKEN_KEY, SESSION_ENDED_EVENT } from '../services/http';
import type { ApiUser } from '../services/types';

export const ROLE_LABEL: Record<string, string> = {
  admin: 'Administrator',
  compliance_officer: 'Compliance Officer',
  security_analyst: 'Security Analyst',
  auditor: 'Auditor',
  employee: 'Employee'
};

type AuthState =
{status: 'loading';} |
{status: 'anonymous';notice?: string;} |
{status: 'authenticated';user: ApiUser;};

interface AuthContextValue {
  state: AuthState;
  signIn: (email: string, password: string) => Promise<void>;
  signOut: () => Promise<void>;
  /** Whether the signed-in role may read a resource. For hiding UI only: the
   * server makes the real decision on every request. */
  can: (resource: string) => boolean;
}

const AuthContext = createContext<AuthContextValue | null>(null);

const SESSION_ENDED_NOTICE = 'Your session has ended. Sign in again to continue.';

export function AuthProvider({ children }: {children: React.ReactNode;}) {
  // A stored token is only a claim; the user is authenticated once /auth/me confirms it.
  const [state, setState] = useState<AuthState>(() =>
  hasSession() ? { status: 'loading' } : { status: 'anonymous' }
  );

  useEffect(() => {
    if (state.status !== 'loading') return;
    let cancelled = false;
    getCurrentUser().
    then((user) => {
      if (!cancelled) setState({ status: 'authenticated', user });
    }).
    catch((error) => {
      if (cancelled) return;
      const offline = error instanceof ApiError && error.isOffline;
      setState({ status: 'anonymous', notice: offline ? error.message : SESSION_ENDED_NOTICE });
    });
    return () => {
      cancelled = true;
    };
  }, [state.status]);

  useEffect(() => {
    const onEnded = () => setState({ status: 'anonymous', notice: SESSION_ENDED_NOTICE });
    // Signing out in one tab signs out every tab.
    const onStorage = (event: StorageEvent) => {
      if (event.key === ACCESS_TOKEN_KEY && !event.newValue) setState({ status: 'anonymous' });
    };
    window.addEventListener(SESSION_ENDED_EVENT, onEnded);
    window.addEventListener('storage', onStorage);
    return () => {
      window.removeEventListener(SESSION_ENDED_EVENT, onEnded);
      window.removeEventListener('storage', onStorage);
    };
  }, []);

  const signIn = useCallback(async (email: string, password: string) => {
    await login(email, password);
    setState({ status: 'loading' });
  }, []);

  const signOut = useCallback(async () => {
    await logout();
    setState({ status: 'anonymous' });
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({
      state,
      signIn,
      signOut,
      can: (resource) =>
      state.status === 'authenticated' && state.user.permissions.includes(resource)
    }),
    [state, signIn, signOut]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const value = useContext(AuthContext);
  if (!value) throw new Error('useAuth must be used inside <AuthProvider>');
  return value;
}

/** The signed-in user. Only call from screens rendered behind the sign-in gate. */
export function useCurrentUser(): ApiUser {
  const { state } = useAuth();
  if (state.status !== 'authenticated') throw new Error('useCurrentUser requires a signed-in user');
  return state.user;
}
