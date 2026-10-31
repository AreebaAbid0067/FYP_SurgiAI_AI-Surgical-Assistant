import type { Metadata } from "next";
import "./globals.css";
import { NO_FLASH_SCRIPT } from "./lib/settings";

export const metadata: Metadata = {
  title: "SurgiAI | Clinical Decision Support",
  description:
    "SurgiAI clinical decision support and clinician-led answer verification.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: NO_FLASH_SCRIPT }} />
      </head>
      <body>{children}</body>
    </html>
  );
}
