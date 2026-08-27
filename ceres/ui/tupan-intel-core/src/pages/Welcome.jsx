import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '@/lib/AuthContext';
import Orb2D from '@/components/tupan/Orb2D';
import AboutSection from '@/components/tupan/AboutSection';
import Accordion08 from '@/components/tupan/Accordion08';

const STAGES = [
  'Loading portfolio',
  'Connecting market data',
  'Initializing analytical models',
  'Connecting AI agent',
];

export default function Welcome() {
  const navigate = useNavigate();
  const { isAuthenticated } = useAuth();
  const [stage, setStage] = useState(0);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    if (isAuthenticated) {
      navigate('/overview', { replace: true });
      return;
    }
    const t = setInterval(() => {
      setStage((s) => {
        if (s >= STAGES.length - 1) {
          clearInterval(t);
          setTimeout(() => setReady(true), 500);
          return s;
        }
        return s + 1;
      });
    }, 700);
    return () => clearInterval(t);
  }, [isAuthenticated, navigate]);

  return (
    <div className="min-h-screen bg-background text-foreground flex flex-col items-center grid-bg relative overflow-hidden">
      <div className="relative w-full min-h-screen flex items-center justify-center overflow-hidden">
        <div className="absolute inset-0 bg-gradient-to-b from-transparent via-background/40 to-background" />

        <div className="relative z-10 flex flex-col items-center gap-7 w-full max-w-md px-6">
          <Orb2D size={196} drift={34} />

          <div className="flex flex-col items-center gap-1.5 -mt-1">
            <h1 className="text-3xl font-bold tracking-[0.25em] leading-none">CERES</h1>
            <p className="text-[11px] text-text-secondary tracking-[0.18em] uppercase">Real Estate Intelligence</p>
          </div>

          <div className="w-full flex flex-col gap-2 mt-1">
            {STAGES.map((s, i) => (
              <div
                key={s}
                className={`flex items-center gap-3 text-sm transition-all duration-500 ${
                  i <= stage ? 'opacity-100' : 'opacity-30'
                }`}
              >
                <span className="w-4 h-4 flex items-center justify-center">
                  {i < stage ? (
                    <span className="w-2 h-2 rounded-full bg-positive" />
                  ) : i === stage ? (
                    <span className="w-3.5 h-3.5 rounded-full border-2 border-brand border-t-transparent animate-spin" />
                  ) : (
                    <span className="w-2 h-2 rounded-full border border-text-muted" />
                  )}
                </span>
                <span className={i <= stage ? 'text-text-secondary' : 'text-text-muted'}>{s}</span>
              </div>
            ))}
          </div>

          {ready && (
            <div className="flex flex-col items-center gap-3 mt-1">
              <button
                onClick={() => navigate('/login')}
                className="px-6 h-10 rounded-md bg-brand text-brand-foreground text-sm font-medium hover:bg-brand/90 transition-colors"
              >
                Enter Workspace
              </button>
              <button
                onClick={() => navigate('/voice')}
                className="text-[12px] text-text-secondary hover:text-brand transition-colors underline-offset-4 hover:underline"
              >
                Talk to Ceres →
                </button>
            </div>
          )}
        </div>
        <p className="absolute bottom-6 text-[10px] text-text-muted tracking-wider uppercase z-10">Ceres Intelligence Platform · v2.4</p>
      </div>

      <AboutSection />
      <Accordion08 />
    </div>
  );
}