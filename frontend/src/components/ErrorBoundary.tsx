import { Component } from "react";
import type { ReactNode, ErrorInfo } from "react";

interface Props {
  children: ReactNode;
}

interface State {
  error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
  state: State = { error: null };

  static getDerivedStateFromError(error: Error): State {
    return { error };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error("ErrorBoundary caught:", error, info);
  }

  render() {
    if (this.state.error) {
      return (
        <div className="p-6 text-destructive">
          <h2 className="font-semibold mb-2">Something went wrong</h2>
          <pre className="text-sm whitespace-pre-wrap">
            {this.state.error.message}
          </pre>
        </div>
      );
    }
    return this.props.children;
  }
}
