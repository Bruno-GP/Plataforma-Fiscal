import { Navigate } from 'react-router-dom';

import { useAuth } from '@/contexts/AuthContext';
import Dashboard from '@/pages/dashboard/components/Dashboard';

export default function AnaliseFiscal() {
  const { user } = useAuth();

  if (!user?.tem_sped) {
    return <Navigate to="/dashboard" replace />;
  }

  return (
    <div></div>
  );
}