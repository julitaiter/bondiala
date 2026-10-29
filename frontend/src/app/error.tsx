"use client";
import { ErrorState } from "@/components/ui";
export default function ErrorPage({
  reset,
}: {
  error: Error;
  reset: () => void;
}) {
  return (
    <ErrorState
      message="La aplicación encontró un problema. Volvé a intentar en un momento."
      retry={reset}
    />
  );
}
