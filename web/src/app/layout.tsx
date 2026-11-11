import type { Metadata } from "next";
import "katex/dist/katex.min.css";
import "./globals.css";
import { AuthProvider } from "@/hooks/use-auth";
import { LangProvider } from "@/hooks/use-lang";

export const metadata: Metadata = {
  title: "PrepIBA",
  description: "IBA MBA admission test preparation: past papers, mock exams and solutions.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="h-full antialiased">
      <body className="flex min-h-full flex-col">
        <AuthProvider>
          <LangProvider>{children}</LangProvider>
        </AuthProvider>
      </body>
    </html>
  );
}
