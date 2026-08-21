import React, { useEffect, useRef } from 'react';
import { MessageBubble } from './MessageBubble';
import { FileText, Database, Code2 } from 'lucide-react';
import { SiLanggraph } from 'react-icons/si';
import CardSwap, { Card } from '../ui/CardSwap';

export function ChatContainer({
  messages = [],
  _isLoading,
  onSelectCitation,
  onSelectSuggestion
}) {
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // ── Empty state ─────────────────────────────────────────────────────────
  // Render a separate layout: position:relative parent fills the workspace,
  // left-side text is absolutely centred, and CardSwap self-positions at
  // bottom-right via its own CSS — exactly matching the React Bits demo.
  if (messages.length === 0) {
    return (
      <div className="flex-1 relative overflow-hidden w-full select-none">

        {/* Left: OmniGraph branding — vertically centred, logo + title only */}
        <div className="absolute left-8 top-1/2 -translate-y-1/2 text-left">
          <div className="w-16 h-16 rounded-3xl bg-gradient-to-tr from-sky-500 to-indigo-600 flex items-center justify-center text-white shadow-2xl shadow-sky-500/30 mb-5">
            <SiLanggraph className="w-8 h-8 drop-shadow-[0_0_14px_rgba(6,182,212,0.9)]" />
          </div>

          <h2 className="text-3xl font-bold text-slate-100 leading-tight">
            OmniGraph
          </h2>
        </div>

        {/* CardSwap: self-positions at bottom-right via CardSwap.css
            (position:absolute; bottom:0; right:0; transform:translate(5%,20%))
            The parent's overflow:hidden clips the animation drop cleanly. */}
        <CardSwap
          width={300}
          height={190}
          cardDistance={60}
          verticalDistance={70}
          delay={5000}
          pauseOnHover={false}
          skewAmount={6}
          easing="elastic"
        >
          {/* Card 1 — Omni Persona */}
          <Card className="p-5 flex flex-col gap-2">
            <div className="p-2 bg-slate-800/80 rounded-xl border border-slate-700/50 w-fit">
              <FileText className="w-4 h-4 text-sky-400" />
            </div>
            <h3 className="text-sm font-semibold text-slate-200">Omni Persona</h3>
            <p className="text-xs text-slate-400 leading-relaxed">
              Got a tricky question? Hand it over to our lineup of specialized agents
              and let the right expert take the wheel.
            </p>
          </Card>

          {/* Card 2 — Document Analysis */}
          <Card className="p-5 flex flex-col gap-2">
            <div className="p-2 bg-slate-800/80 rounded-xl border border-slate-700/50 w-fit">
              <Database className="w-4 h-4 text-emerald-400" />
            </div>
            <h3 className="text-sm font-semibold text-slate-200">Document Analysis</h3>
            <p className="text-xs text-slate-400 leading-relaxed">
              Staring at a massive PDF and zero time to read it? Drop it here and
              we'll dig up the exact answers for you.
            </p>
          </Card>

          {/* Card 3 — Omni Math */}
          <Card className="p-5 flex flex-col gap-2">
            <div className="p-2 bg-slate-800/80 rounded-xl border border-slate-700/50 w-fit">
              <Code2 className="w-4 h-4 text-indigo-400" />
            </div>
            <h3 className="text-sm font-semibold text-slate-200">Omni Math</h3>
            <p className="text-xs text-slate-400 leading-relaxed">
              Tired of messy calculations? Feed it to our polymath engine and get
              the precise breakdown instantly.
            </p>
          </Card>
        </CardSwap>

      </div>
    );
  }

  // ── Messages view ────────────────────────────────────────────────────────
  return (
    <div className="flex-1 overflow-y-auto px-4 py-6 max-w-4xl w-full mx-auto space-y-4 [&::-webkit-scrollbar]:w-1.5 [&::-webkit-scrollbar-track]:bg-transparent [&::-webkit-scrollbar-thumb]:bg-slate-800 [&::-webkit-scrollbar-thumb]:rounded-full">
      {messages.map((message) => (
        <MessageBubble
          key={message.id}
          message={message}
          onSelectCitation={onSelectCitation}
          onSelectSuggestion={onSelectSuggestion}
        />
      ))}
      <div ref={messagesEndRef} />
    </div>
  );
}