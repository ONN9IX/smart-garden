/** Reserved forbidden-access screen for Stage 1. */
import Link from "next/link";
export default function Forbidden() {
  return <main className="center-screen"><section className="card narrow"><h1>Доступ запрещён</h1><p>Для этого действия у вас нет прав.</p><Link href="/dashboard" className="text-link">На главную</Link></section></main>;
}
