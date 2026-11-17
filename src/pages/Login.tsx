import { useState } from 'react';
import { ShieldCheck } from 'lucide-react';
import { Button } from '../components/ui/Button';
import { Field, Input } from '../components/ui/Input';
import { useAuth } from '../contexts/AuthContext';
import { ApiError } from '../services/api';

function messageFor(error: unknown): string {
  if (!(error instanceof ApiError)) return 'Sign-in failed. Try again.';
  if (error.status === 401) return 'Incorrect email or password.';
  if (error.status === 422) return 'Enter a valid email address and your password.';
  // 429 (locked out), 403 (disabled) and offline carry a message written for the user.
  return error.message;
}

export function Login({ notice }: {notice?: string;}) {
  const { signIn } = useAuth();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const onSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await signIn(email.trim(), password);
    } catch (cause) {
      setError(messageFor(cause));
      setSubmitting(false);
    }
  };

  return (
    <main className="flex min-h-screen items-center justify-center bg-background p-6 text-foreground">
      <div className="w-full max-w-sm">
        <div className="mb-6 flex items-center gap-2.5">
          <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary/15 text-primary">
            <ShieldCheck className="h-5 w-5" aria-hidden />
          </span>
          <div>
            <h1 className="text-lg font-semibold leading-tight">Sentinel AI</h1>
            <p className="text-xs text-muted-foreground">Sign in to continue</p>
          </div>
        </div>

        {notice && !error &&
        <p role="status" className="mb-4 rounded-lg border border-border bg-surface-1 px-3 py-2 text-sm text-muted-foreground">
            {notice}
          </p>
        }

        <form onSubmit={onSubmit} className="space-y-4 rounded-xl border border-border bg-surface-1 p-5" noValidate>
          <Field label="Email">
            {({ id }) =>
            <Input
              id={id}
              type="email"
              name="email"
              autoComplete="username"
              autoFocus
              required
              value={email}
              onChange={(event) => setEmail(event.target.value)} />
            }
          </Field>
          <Field label="Password">
            {({ id }) =>
            <Input
              id={id}
              type="password"
              name="password"
              autoComplete="current-password"
              required
              value={password}
              onChange={(event) => setPassword(event.target.value)} />
            }
          </Field>

          {error &&
          <p role="alert" className="text-sm text-destructive">
              {error}
            </p>
          }

          <Button type="submit" className="w-full" loading={submitting} disabled={!email || !password}>
            Sign in
          </Button>
        </form>

        {(import.meta as any).env?.DEV &&
        <p className="mt-4 text-xs text-muted-foreground">
            Local development build. Sign in with an account created by{' '}
            <code className="font-mono">scripts/seed_users.py</code> (see the README).
          </p>
        }
      </div>
    </main>);

}
