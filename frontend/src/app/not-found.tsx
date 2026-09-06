import Link from "next/link";

export default function NotFound() {
  return (
    <div className="flex min-h-screen items-center justify-center p-6">
      <div className="card max-w-md p-6 text-center">
        <div className="text-3xl font-bold text-brand-600 dark:text-brand-400">404</div>
        <p className="mt-2 text-sm text-muted">This page doesn&apos;t exist.</p>
        <Link href="/" className="btn-primary mt-4 inline-flex">
          Back to dashboard
        </Link>
      </div>
    </div>
  );
}
