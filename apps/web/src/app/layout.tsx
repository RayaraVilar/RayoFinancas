import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Rayo Finanças — Clareza para decidir melhor",
  description:
    "Transforme seus gastos em decisões melhores para a sua vida financeira.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="pt-BR">
      <body>{children}</body>
    </html>
  );
}
