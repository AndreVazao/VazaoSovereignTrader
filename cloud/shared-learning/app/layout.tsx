import type { Metadata } from "next";
import type { ReactNode } from "react";
export const metadata: Metadata = { title: "Vazao Sovereign Trader — Shared Learning API", description: "Authenticated privacy-preserving shared learning API." };
export default function RootLayout({ children }: { children: ReactNode }) { return <html lang="en"><body>{children}</body></html>; }
