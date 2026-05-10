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
      <body className="h-full font-sans selection:bg-blue-100 antialiased overflow-hidden">
        <ThemeProvider>
          <div className="flex h-screen w-screen overflow-hidden">
            {/* Global Sidebar */}
            <Sidebar />

            {/* Main Content Area */}
            <main className="flex-1 relative overflow-hidden flex flex-col">
              <PageWrapper>
                {children}
              </PageWrapper>
              
              {/* Global Header Bar removed for cleaner UI */}

            </main>
          </div>
        </ThemeProvider>
      </body>
    </html>
  );
}


