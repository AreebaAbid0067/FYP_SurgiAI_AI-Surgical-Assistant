import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "SurgiAI | Pre-surgery Planning",
  description:
    "A pre-surgery planning workflow that brings patient records into one structured report.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
