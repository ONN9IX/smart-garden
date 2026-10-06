/** Root HTML and in-memory auth provider for every Stage 1 route. */
import type { Metadata } from "next";
import { AuthProvider } from "@/features/auth/auth-provider";
import "./globals.css";

export const metadata: Metadata = { title: "ПРОМАКС", description: "Рабочий кабинет детского сада ПРОМАКС" };

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="ru"><body><AuthProvider>{children}</AuthProvider></body></html>;
}
