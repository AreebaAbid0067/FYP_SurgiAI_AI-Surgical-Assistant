import { ReactNode } from "react";
import { shellLayout } from "../lib/shell-layout";

export default async function Layout({ children }: { children: ReactNode }) {
  return shellLayout(children);
}
