import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "ATLAS · KAG multidimensional (Neo4j)",
  description:
    "Grafo de conocimiento de seis dimensiones sobre Neo4j con índice vectorial nativo.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="es">
      <body>{children}</body>
    </html>
  );
}
