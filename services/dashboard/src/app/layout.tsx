import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'VantageNet Dashboard',
  description: 'Emotion Analytics Platform',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
