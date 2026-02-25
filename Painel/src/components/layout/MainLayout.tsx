import type { CSSProperties, ReactNode } from 'react';
import { Navigate } from 'react-router-dom';
import { useAuth } from '@/contexts/AuthContext';
import { SidebarInset, SidebarProvider } from '@/components/ui/sidebar';
import { AppSidebar } from './AppSidebar';
import { AppHeader } from './AppHeader';
import { ChatWidget } from '@/components/chat/ChatWidget';

interface MainLayoutProps {
  children: ReactNode;
}

export function MainLayout({ children }: MainLayoutProps) {
  const { isAuthenticated } = useAuth();

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  return (
    <SidebarProvider style={{ "--sidebar-width": "12rem" } as CSSProperties}>
      <div className="flex min-h-screen w-full">
        <AppSidebar />
        
        <SidebarInset className="min-w-0 flex-1">
          <AppHeader />
          
          <div className="min-w-0 flex-1 overflow-x-hidden">
            <div className="mx-auto w-full max-w-[1500px]">
              {children}
            </div>
          </div>
        </SidebarInset>
      </div>

      {/* <ChatWidget /> */}
    </SidebarProvider>
  );
}