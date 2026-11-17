import { Component, type ReactNode, type ErrorInfo } from 'react';
import { AlertTriangle, RefreshCw } from 'lucide-react';
import { Button } from '../ui/Button';

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
  public state: State = {
    hasError: false,
    error: null
  };

  public static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('Uncaught error inside ErrorBoundary:', error, errorInfo);
  }

  private handleReset = () => {
    this.setState({ hasError: false, error: null });
  };

  public render() {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback;
      }

      return (
        <div className="flex min-h-[400px] w-full flex-col items-center justify-center p-6 text-center">
          <div className="flex h-12 w-12 items-center justify-center rounded-xl border border-destructive/30 bg-destructive/10 text-destructive">
            <AlertTriangle className="h-6 w-6" aria-hidden />
          </div>
          <h2 className="mt-4 text-base font-semibold text-foreground">
            Something went wrong in this section
          </h2>
          <p className="mt-1 max-w-md text-xs text-muted-foreground">
            {this.state.error?.message ?? 'An unexpected error occurred while rendering.'}
          </p>
          <div className="mt-5 flex items-center gap-3">
            <Button
              variant="outline"
              size="sm"
              iconLeft={<RefreshCw className="h-3.5 w-3.5" />}
              onClick={this.handleReset}>
              Try again
            </Button>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => window.location.reload()}>
              Reload page
            </Button>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
