import "./globals.css";
import React from "react";

export const metadata = {
  title: "Possible Studio — AI Marketing Employee",
  description: "Autonomous, human-governed AI social media and Meta ads platform",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <body className="antialiased selection:bg-indigo-500 selection:text-white">
        <div className="min-h-screen flex flex-col bg-[#080c14] text-slate-100">
          {children}
        </div>
      </body>
    </html>
  );
}
