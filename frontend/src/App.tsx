import React, { useState, useEffect, useRef } from 'react';
import { Sidebar } from './components/Sidebar';
import { Navbar } from './components/Navbar';
import { DashboardPage } from './pages/DashboardPage';
import { ReconciliationPage } from './pages/ReconciliationPage';
import { IngestionPage } from './pages/IngestionPage';
import { TransactionsPage } from './pages/TransactionsPage';
import { ExceptionsPage } from './pages/ExceptionsPage';
import { ShiftsPage } from './pages/ShiftsPage';
import { AccountsPage } from './pages/AccountsPage';
import { BranchesPage } from './pages/BranchesPage';
import { AIInsightsPage } from './pages/AIInsightsPage';
import { ReportsPage } from './pages/ReportsPage';
import { AuditPage } from './pages/AuditPage';
import { TeamPage } from './pages/TeamPage';
import { SettingsPage } from './pages/SettingsPage';
import { LoginPage } from './pages/LoginPage';
import { OnboardingPage } from './pages/OnboardingPage';
import { ApiClient } from './api';
import { AuthResponse, User } from './types';

export const App: React.FC = () => {
  const [authData, setAuthData] = useState<AuthResponse | null>(null);
  const [currentPage, setCurrentPage] = useState('dashboard');
  const [isOnboarding, setIsOnboarding] = useState(false);
  const [analytics, setAnalytics] = useState<any>(null);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [analyticsError, setAnalyticsError] = useState('');
  const analyticsRequest = useRef(0);

  useEffect(() => {
    // Check saved session
    const savedToken = localStorage.getItem('reconos_token');
    const savedAuth = localStorage.getItem('reconos_auth');
    if (savedToken && savedAuth) {
      try {
        const parsed = JSON.parse(savedAuth);
        setAuthData(parsed);
      } catch (e) {
        localStorage.clear();
      }
    }
  }, []);

  useEffect(() => {
    if (authData) {
      loadAnalytics();
    }
    return () => { analyticsRequest.current += 1; };
  }, [authData]);

  const loadAnalytics = async () => {
    const request = ++analyticsRequest.current;
    setAnalytics(null);
    setAnalyticsError('');
    setIsRefreshing(true);
    try {
      const data = await ApiClient.get('/analytics/dashboard');
      if (request === analyticsRequest.current) setAnalytics(data);
    } catch (e) {
      if (request === analyticsRequest.current) setAnalyticsError('Could not load your dashboard. Please try refreshing.');
    } finally {
      if (request === analyticsRequest.current) setIsRefreshing(false);
    }
  };

  const handleLogout = () => {
    analyticsRequest.current += 1;
    localStorage.removeItem('reconos_token');
    localStorage.removeItem('reconos_auth');
    setAnalytics(null);
    setAnalyticsError('');
    setIsRefreshing(false);
    setAuthData(null);
    setCurrentPage('dashboard');
  };

  // If not logged in
  if (!authData) {
    if (isOnboarding) {
      return (
        <OnboardingPage
          onOnboardingSuccess={(data) => {
            setAuthData(data);
            setIsOnboarding(false);
          }}
          onGoToLogin={() => setIsOnboarding(false)}
        />
      );
    }
    return (
      <LoginPage
        onLoginSuccess={(data) => setAuthData(data)}
        onGoToOnboarding={() => setIsOnboarding(true)}
      />
    );
  }

  // Convert authData into User object for child components
  const currentUser: User = {
    id: authData.user_id,
    organization_id: authData.organization_id,
    email: authData.email,
    full_name: authData.full_name,
    role: analytics?.role || authData.role,
    is_active: true,
    created_at: new Date().toISOString(),
  };

  const renderCurrentPage = () => {
    switch (currentPage) {
      case 'dashboard':
        return analyticsError ? <div role="alert" className="text-rose-300">{analyticsError}</div> :
          analytics ? <DashboardPage analytics={analytics} onNavigate={setCurrentPage} /> :
          <div className="text-slate-400">Loading your dashboard...</div>;
      case 'reconciliation':
        return <ReconciliationPage user={currentUser} />;
      case 'ingestion':
        return <IngestionPage />;
      case 'transactions':
        return <TransactionsPage />;
      case 'exceptions':
        return <ExceptionsPage user={currentUser} />;
      case 'shifts':
        return <ShiftsPage user={currentUser} />;
      case 'accounts':
        return <AccountsPage user={currentUser} />;
      case 'branches':
        return <BranchesPage user={currentUser} />;
      case 'ai-insights':
        return <AIInsightsPage user={currentUser} />;
      case 'reports':
        return <ReportsPage />;
      case 'audit':
        return <AuditPage />;
      case 'team':
        return <TeamPage />;
      case 'settings':
        return <SettingsPage />;
      default:
        return <DashboardPage analytics={analytics} onNavigate={setCurrentPage} />;
    }
  };

  return (
    <div className="flex h-screen bg-slate-950 overflow-hidden font-sans">
      {/* Sidebar */}
      <Sidebar
        currentPage={currentPage}
        onNavigate={setCurrentPage}
        user={currentUser}
        onLogout={handleLogout}
      />

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        <Navbar
          user={currentUser}
          organizationName={authData.organization_name}
          onRefresh={loadAnalytics}
          isRefreshing={isRefreshing}
        />

        <main className="flex-1 overflow-y-auto p-6 md:p-8 bg-slate-950">
          <div className="max-w-7xl mx-auto">
            {renderCurrentPage()}
          </div>
        </main>
      </div>
    </div>
  );
};
