import { ReactNode, useState } from 'react';
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
  const [open, setOpen] = useState(true);

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  return (
    <SidebarProvider open={open} onOpenChange={setOpen}>
      <div className="flex min-h-svh w-full">
        <AppSidebar />
        
        <SidebarInset className="flex min-h-svh flex-1 flex-col">
          <AppHeader />
          
          <div className="flex-1 overflow-auto px-8 py-6">
            <div className="mx-auto w-full max-w-[1400px]">
              {children}
            </div>
          </div>
        </SidebarInset>
      </div>

      <ChatWidget />
    </SidebarProvider>
  );
}