import type { ReactNode } from 'react';
import { Navigate } from 'react-router-dom';
import { useAuth } from '@/contexts/AuthContext';

import { AppHeader } from './AppHeader';
// import { SidebarInset, SidebarProvider } from '@/components/ui/sidebar';
// import { AppSidebar } from './AppSidebar';
// import { ChatWidget } from '@/components/chat/ChatWidget';

interface MainLayoutProps {
  children: ReactNode;
}

export function MainLayout({ children }: MainLayoutProps) {
  const { isAuthenticated } = useAuth();

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  return (
    <div className="min-h-screen w-full bg-background">
      <AppHeader />

      <main className="min-w-0 overflow-x-hidden">
        <div className="mx-auto min-w-0 max-w-[1700px] px-4 md:px-8">
          {children}
        </div>
      </main>
    </div>
  );
}