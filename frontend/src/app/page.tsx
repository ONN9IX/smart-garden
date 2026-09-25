/** Entry point: route guard chooses the correct screen after /auth/me. */
import { redirect } from "next/navigation";

export default function Home() {
  redirect("/login");
}
