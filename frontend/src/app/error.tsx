"use client";

export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <div className="flex min-h-screen items-center justify-center p-6">
      <div className="card max-w-md p-6 text-center">
        <div className="text-lg font-semibold text-fg">Something went wrong</div>
        <p className="mt-2 break-words text-sm text-muted">{error.message}</p>
        <div className="mt-4 flex justify-center gap-2">
          <button className="btn-primary" onClick={reset}>
            Try again
          </button>
          <a className="btn-ghost" href="/">
            Go home
          </a>
        </div>
      </div>
    </div>
  );
}
