import LiquidEther from './ui/LiquidEther';
import { ArrowRight } from 'lucide-react';
import { SiLanggraph } from 'react-icons/si';

/**
 * LandingScreen
 * ─────────────
 * Full-viewport splash screen backed by the LiquidEther WebGL fluid animation.
 * Overlays a centred hero card with title, tagline, and "Continue to Agent" CTA.
 *
 * Props
 * ─────
 * onContinue  function  Called when the user clicks the CTA button.
 */
export default function LandingScreen({ onContinue }) {
  return (
    <div className="relative h-screen w-screen overflow-hidden bg-slate-950">

      {/* ── LiquidEther background ─────────────────────────────────────── */}
      {/* Absolute-fill so the fluid simulation covers the whole viewport   */}
      <div className="absolute inset-0 z-0">
        <LiquidEther
          colors={['#0ea5e9', '#6366f1', '#8b5cf6', '#06b6d4']}
          resolution={0.5}
          mouseForce={25}
          cursorSize={120}
          autoDemo={true}
          autoSpeed={0.45}
          autoIntensity={2.5}
          autoResumeDelay={800}
          autoRampDuration={0.8}
          style={{ width: '100%', height: '100%' }}
        />
      </div>

      {/* ── Subtle vignette so the hero card text stays readable ─────────── */}
      <div
        className="absolute inset-0 z-10 pointer-events-none"
        style={{ background: 'radial-gradient(ellipse at center, transparent 30%, rgba(2,6,23,0.72) 100%)' }}
      />

      {/* ── Hero card ────────────────────────────────────────────────────── */}
      <div className="absolute inset-0 z-20 flex flex-col items-center justify-center px-4">
        <div
          className="flex flex-col items-center gap-6 text-center max-w-lg w-full rounded-2xl px-8 py-10"
          style={{
            background:   'rgba(15, 23, 42, 0.55)',
            backdropFilter: 'blur(20px)',
            WebkitBackdropFilter: 'blur(20px)',
            border:       '1px solid rgba(148, 163, 184, 0.12)',
            boxShadow:    '0 8px 64px rgba(0,0,0,0.5), inset 0 1px 0 rgba(255,255,255,0.06)',
          }}
        >
          {/* Logo badge */}
          <div className="flex items-center justify-center w-16 h-16 rounded-2xl bg-gradient-to-br from-cyan-500/25 via-sky-500/30 to-indigo-600/30 border border-cyan-500/40 shadow-xl shadow-cyan-500/25 backdrop-blur-xl">
            <SiLanggraph className="w-8 h-8 text-cyan-300 drop-shadow-[0_0_12px_rgba(6,182,212,0.9)]" />
          </div>

          {/* Title */}
          <div className="space-y-1.5">
            <h1 className="text-3xl sm:text-4xl font-bold tracking-tight text-white">
              OmniGraph
            </h1>
            <p className="text-sm sm:text-base text-slate-400 leading-relaxed">
              Contextual Query & Computation
            </p>
          </div>

          {/* CTA button */}
          <button
            id="landing-continue-btn"
            onClick={onContinue}
            className="group mt-2 flex items-center gap-2.5 px-7 py-3 rounded-xl font-semibold text-sm text-white cursor-pointer
                       bg-gradient-to-r from-sky-500 to-indigo-600
                       hover:from-sky-400 hover:to-indigo-500
                       active:scale-95
                       transition-all duration-200
                       shadow-lg shadow-sky-500/25 hover:shadow-sky-500/40"
          >
            Continue to Agent
            <ArrowRight className="w-4 h-4 transition-transform duration-200 group-hover:translate-x-1" />
          </button>

          {/* Footnote */}
        </div>
      </div>
    </div>
  );
}
