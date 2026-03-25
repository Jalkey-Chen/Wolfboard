import type { ReactNode } from "react";
import type { Metadata } from "next";

import { LanguageProvider } from "@/components/language-provider";

import "./globals.css";


export const metadata: Metadata = {
  title: "Wolfboard",
  description: "狼人杀赛事记录与管理平台。",
};


export default function RootLayout({
  children,
}: Readonly<{
  children: ReactNode;
}>) {
  // The app shell stays intentionally small in Milestone 1 because navigation
  // depends on client-side authentication state retrieved after login.
  return (
    <html lang="zh-CN">
      <body>
        <LanguageProvider>{children}</LanguageProvider>
      </body>
    </html>
  );
}
