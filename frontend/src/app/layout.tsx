import "./globals.css";
import { AuthProvider } from "@/lib/auth";

export const metadata = {
  title: "QCM Intelligence - Plateforme d'évaluation individualisée",
  description: "Génération de QCM par IA et passation d'examens individualisés",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="fr">
      <body className="bg-slate-50 text-slate-900 antialiased min-h-screen">
        <AuthProvider>{children}</AuthProvider>
      </body>
    </html>
  );
}
