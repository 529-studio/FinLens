import React from 'react';
import ReactDOM from 'react-dom/client';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Sidebar } from './components/Sidebar';
import './index.css';

const queryClient = new QueryClient();

const App = () => (
  <QueryClientProvider client={queryClient}>
    <Sidebar />
  </QueryClientProvider>
);

const renderApp = () => {
  const rootElement = document.getElementById('root');
  if (rootElement && !rootElement.hasChildNodes()) {
    ReactDOM.createRoot(rootElement).render(
      <React.StrictMode>
        <App />
      </React.StrictMode>
    );
  }
};

if (typeof Office !== 'undefined' && Office.onReady) {
  Office.onReady(() => {
    renderApp();
  }).catch(() => {
    renderApp();
  });
} else {
  renderApp();
}

// Fallback for standalone browser dev/e2e testing
if (typeof window !== 'undefined') {
  window.addEventListener('DOMContentLoaded', renderApp);
  setTimeout(renderApp, 300);
}
