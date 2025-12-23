import dynamic from 'next/dynamic';
import { Suspense } from 'react';

// Lazy load Analytics component with recharts
const Analytics = dynamic(() => import('@/pages/Analytics'), {
  loading: () => (
    <div className="flex items-center justify-center min-h-screen">
      <div className="text-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
        <p className="text-gray-600">Loading Analytics...</p>
      </div>
    </div>
  ),
  ssr: false, // Disable SSR for recharts
});

export default function AnalyticsPage() {
  return (
    <Suspense fallback={<div>Loading...</div>}>
      <Analytics />
    </Suspense>
  );
}
