// Test-only entry: renders the real agent page without accessing a user account.
import React from 'react';
import { createRoot } from 'react-dom/client';
import { MemoryRouter } from 'react-router-dom';
import { AppContextProvider } from '@/lib/AppContext';
import VoiceAgent from '@/pages/VoiceAgent';
import '@/index.css';

createRoot(document.getElementById('root')).render(
  <MemoryRouter initialEntries={['/agent']}>
    <AppContextProvider><VoiceAgent /></AppContextProvider>
  </MemoryRouter>,
);
