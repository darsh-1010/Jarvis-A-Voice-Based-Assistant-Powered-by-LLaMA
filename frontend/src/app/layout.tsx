/**
 * Copyright (c) 2024-2026 Darsh Shah
 * Licensed under the Business Source License 1.1
 */
import type { Metadata } from "next";
import "./globals.css";
import { Sidebar } from "@/components/Sidebar";
import { PageWrapper } from "@/components/PageWrapper";

export const metadata: Metadata = {
  title: "Jarvis AI | Advanced Voice Intelligence",
  description: "A premium, voice-powered AI assistant with a minimalist, high-performance interface.",
};

import { ThemeProvider } from '@/components/ThemeProvider';

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="h-full antialiased">
      <body className="h-full font-sans selection:bg-blue-900/20 antialiased overflow-hidden bg-slate-950">
        <ThemeProvider>
          <div className="flex h-screen w-screen overflow-hidden bg-[radial-gradient(ellipse_at_top_right,rgba(var(--accent-rgb),0.08),transparent_50%),radial-gradient(ellipse_at_bottom_left,rgba(139,92,246,0.05),transparent_50%)]">
            {/* Global Sidebar */}
            <Sidebar />

            {/* Main Floating Content Area */}
            <main className="flex-1 relative overflow-hidden flex flex-col my-4 mr-4 glass-minimal rounded-[32px]">
              <PageWrapper>
                {children}
              </PageWrapper>
            </main>
          </div>
        </ThemeProvider>
      </body>
    </html>
  );
}


