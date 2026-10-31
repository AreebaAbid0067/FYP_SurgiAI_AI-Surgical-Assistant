import { redirect } from "next/navigation";
import { ReactNode } from "react";
import AppShell from "../components/app-shell";
import { getSession } from "./session";

export async function shellLayout(children: ReactNode) {
  const user = await getSession();
  if (!user) redirect("/login");
  return <AppShell user={user}>{children}</AppShell>;
}
