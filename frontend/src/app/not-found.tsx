/** Consistent 404 page for unknown Stage 1 routes. */
import Link from "next/link";
export default function NotFound() {
  return <main className="center-screen"><section className="card narrow"><h1>Страница не найдена</h1><p>Проверьте адрес страницы.</p><Link href="/dashboard" className="text-link">На главную</Link></section></main>;
}
