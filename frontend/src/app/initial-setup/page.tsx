import { InitialSetupPage } from "@/features/management/initial-setup";
import { AuthGate } from "@/features/auth/auth-gate";
import { AppShell } from "@/components/layout/app-shell";

export default function Page() {
  return <AuthGate route="director"><AppShell><InitialSetupPage /></AppShell></AuthGate>;
}
