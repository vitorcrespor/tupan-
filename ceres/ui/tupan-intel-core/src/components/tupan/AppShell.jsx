import React from 'react';
import { Outlet } from 'react-router-dom';
import VoiceNav from './VoiceNav';
import InsightTray from './InsightTray';

export default function AppShell() {
  return (
    <div className="app-shell h-screen overflow-hidden flex flex-col bg-background text-foreground">
      <VoiceNav />
      <div className="relative flex-1 flex flex-col min-w-0 overflow-hidden">
        <Outlet />
        <InsightTray />
      </div>
    </div>
  );
}
