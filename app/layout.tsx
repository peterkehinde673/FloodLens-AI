import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "FloodLens AI — Satellite Disaster Intelligence",
  description: "Map flood damage and potential community isolation from satellite evidence."
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="en"><body>{children}</body></html>;
}
