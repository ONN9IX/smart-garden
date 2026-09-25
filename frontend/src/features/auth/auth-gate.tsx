"use client";

/**
 * Routes users according to the server-supplied /auth/me context.
 * Backend independently enforces every permission and tenant boundary.
 */
import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "./auth-provider";
import { Button } from "@/components/ui/button";
import { Loading } from "@/components/ui/loading";

type Route = "login" | "change-password" | "dashboard" | "parent";

export function AuthGate({ route, children }: { route: Route; children: React.ReactNode }) {
  const { current, state, refresh } = useAuth();
  const router = useRouter();

  const destination = state !== "ready" ? null : !current
    ? (route === "login" ? null : "/login")
    : current.user.must_change_password
      ? (route === "change-password" ? null : "/change-password")
      : current.user.role === "PARENT"
        ? (route === "parent" ? null : "/parent")
        : (route === "dashboard" ? null : "/dashboard");

  useEffect(() => {
    if (destination) router.replace(destination);
  }, [destination, router]);

  if (state === "loading" || destination) return <Loading />;
  if (state === "error") return (
    <main className="center-screen" role="alert">
      <div className="card narrow">
        <h1>Не удалось проверить доступ</h1>
        <p>Проверьте соединение с сервером и попробуйте снова.</p>
        <Button onClick={() => void refresh().catch(() => undefined)}>Повторить</Button>
      </div>
    </main>
  );
  return <>{children}</>;
}
