import { Outlet, Link, useNavigate } from '@tanstack/react-router';
import { useAuth } from '../hooks/useAuth';
import { LayoutDashboard, Users, BarChart2, ListTodo, Megaphone, LogOut, Menu, X, Zap, Image, Settings } from 'lucide-react';
import { useEffect, useState } from 'react';

const navItems = [
  { to: '/', label: 'Dashboard', icon: LayoutDashboard },
  { to: '/accounts', label: 'Accounts', icon: Users },
  { to: '/personas', label: 'Personas', icon: Zap },
  { to: '/campaigns', label: 'Campaigns', icon: Megaphone },
  { to: '/media', label: 'Media', icon: Image },
  { to: '/tasks', label: 'Tasks', icon: ListTodo },
  { to: '/analytics', label: 'Analytics', icon: BarChart2 },
  { to: '/settings', label: 'Settings', icon: Settings },
];

export default function Layout() {
  const { user, logout, isAuthenticated } = useAuth();
  const navigate = useNavigate();
  const [sidebarOpen, setSidebarOpen] = useState(false);

  useEffect(() => {
    if (!isAuthenticated) {
      navigate({ to: '/login' });
    }
  }, [isAuthenticated, navigate]);

  const handleLogout = () => {
    logout();
    navigate({ to: '/login' });
  };

  const closeSidebar = () => setSidebarOpen(false);

  if (!isAuthenticated) {
    return null;
  }

  return (
    <div className="flex h-screen bg-gray-50 flex-col md:flex-row">
      {/* Mobile header */}
      <div className="md:hidden bg-white border-b border-gray-200 flex items-center justify-between px-4 py-3">
        <h1 className="text-lg font-bold text-gray-900">SocialMind</h1>
        <button
          onClick={() => setSidebarOpen(!sidebarOpen)}
          className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
        >
          {sidebarOpen ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
        </button>
      </div>

      {/* Sidebar */}
      <aside className={`${
        sidebarOpen ? 'block' : 'hidden'
      } md:block md:w-64 bg-white border-b md:border-b-0 md:border-r border-gray-200 flex flex-col absolute md:static w-full z-50 h-screen md:h-auto top-16 md:top-0`}>
        <div className="px-6 py-4 border-b border-gray-200 hidden md:block">
          <h1 className="text-xl font-bold text-gray-900">SocialMind</h1>
        </div>
        <nav className="flex-1 px-4 py-4 space-y-1">
          {navItems.map(({ to, label, icon: Icon }) => (
            <Link
              key={to}
              to={to}
              onClick={closeSidebar}
              className="flex items-center gap-3 px-3 py-2 rounded-md text-sm font-medium text-gray-700 hover:bg-gray-100 hover:text-gray-900 transition-colors"
              activeProps={{ className: 'bg-blue-50 text-blue-700' }}
            >
              <Icon className="w-5 h-5" />
              {label}
            </Link>
          ))}
        </nav>
        <div className="px-4 py-4 border-t border-gray-200">
          <div className="flex items-center justify-between gap-2">
            <span className="text-sm text-gray-600 truncate">{user?.username}</span>
            <button onClick={handleLogout} className="text-gray-400 hover:text-gray-600 p-1 hover:bg-gray-100 rounded transition-colors">
              <LogOut className="w-4 h-4" />
            </button>
          </div>
        </div>
      </aside>

      {/* Main content */}
      <main className="flex-1 overflow-auto">
        <Outlet />
      </main>
    </div>
  );
}
