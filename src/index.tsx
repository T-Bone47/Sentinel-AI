import "./index.css";
import React from "react";
import ReactDOM from "react-dom/client";
import { App } from "./App";

class ErrorBoundary extends React.Component<{children: React.ReactNode}, {hasError: boolean, error: Error | null}> {
  constructor(props: {children: React.ReactNode}) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error) {
    return { hasError: true, error };
  }

  render() {
    if (this.state.hasError) {
      return (
        <div style={{ padding: 20, color: 'red', fontFamily: 'monospace' }}>
          <h2>React Runtime Error:</h2>
          <pre>{this.state.error?.toString()}</pre>
          <pre>{this.state.error?.stack}</pre>
        </div>
      );
    }
    return this.props.children;
  }
}

window.onerror = function (message, source, lineno, colno, error) {
  document.body.innerHTML = `<div style="padding: 20px; color: red; font-family: monospace;"><h2>Global Error:</h2><pre>${message}</pre><pre>${error?.stack}</pre></div>`;
};

const rootEl = document.getElementById("root");
if (rootEl) {
  ReactDOM.createRoot(rootEl).render(
    <ErrorBoundary>
      <App />
    </ErrorBoundary>
  );
}