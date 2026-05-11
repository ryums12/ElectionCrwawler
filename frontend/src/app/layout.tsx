import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Election News Summary",
  description: "Search and filter summarized election news.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="ko">
      <body>{children}</body>
    </html>
  );
}
