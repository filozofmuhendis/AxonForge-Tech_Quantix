import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "AxonForge Personal FinTech AI",
  description: "Kişisel finansal zeka, nicel analiz ve portföy risk yönetim platformu.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="tr">
      <body className="antialiased">
        {children}
      </body>
    </html>
  );
}


