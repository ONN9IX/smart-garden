/** Screen-reader announced, safe user-facing feedback. */
export function Alert({ children, tone = "error" }: { children: React.ReactNode; tone?: "error" | "success" }) {
  return <div className={`alert alert-${tone}`} role={tone === "error" ? "alert" : "status"}>{children}</div>;
}
