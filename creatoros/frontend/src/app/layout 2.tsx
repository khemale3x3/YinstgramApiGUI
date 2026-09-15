import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import AuthGate from "@/components/AuthGate";
import Nav from "@/components/Nav";
import TopHeader from "@/components/TopHeader";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "KreatOS — Instagram Creator Intelligence",
  description: "Creator discovery, analysis and campaign automation platform.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html
      lang="en"
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
    >
      <body className="min-h-full flex text-gray-200 bg-gray-950">
        <AuthGate>
          <Nav />
          <main className="flex min-w-0 flex-1 flex-col overflow-auto">
            <TopHeader />
            {children}
          </main>
        </AuthGate>
      </body>
    </html>
  );
}