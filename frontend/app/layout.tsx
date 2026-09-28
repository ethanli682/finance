import type { Metadata, Viewport } from "next";
import "@fontsource-variable/public-sans/wght.css";
import "./globals.css";

export const metadata: Metadata = {
  title: { default: "Ledger", template: "%s | Ledger" },
  description: "Look up a public company's stock price and financial statements.",
};

export const viewport: Viewport = {
  themeColor: [
    { media: "(prefers-color-scheme: light)", color: "#f2f5f0" },
    { media: "(prefers-color-scheme: dark)", color: "#0f1d18" },
  ],
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en">
      <body className="min-h-dvh">{children}</body>
    </html>
  );
}
