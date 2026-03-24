import type { ReactNode } from "react";
import type { Metadata } from "next";

import "./globals.css";


export const metadata: Metadata = {
  title: "Wolfboard",
  description: "Werewolf tournament recording platform scaffold.",
};


export default function RootLayout({
  children,
}: Readonly<{
  children: ReactNode;
}>) {
  // The app shell stays intentionally small in Milestone 1 because navigation
  // depends on client-side authentication state retrieved after login.
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
