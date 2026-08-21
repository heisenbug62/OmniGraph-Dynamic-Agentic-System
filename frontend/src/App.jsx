import React, { useState } from 'react';
import { useChat } from './hooks/useChat';
import { useTraceWS } from './hooks/useTraceWS';
import { ChatContainer } from './components/chat/ChatContainer';
import { ChatInput } from './components/chat/ChatInput';
import { TracePanel } from './components/trace/TracePanel';
import { Activity } from 'lucide-react';
import { SiLanggraph } from 'react-icons/si';
import LandingScreen from './components/LandingScreen';

export default function App() {
  const [clientId] = useState(() => `client_${Math.random().toString(36).substring(2, 9)}_${Date.now()}`);
  const [isTraceOpen, setIsTraceOpen] = useState(true);
  // Landing screen gate — NOT persisted, so every page load shows the splash
  const [hasEnteredApp, setHasEnteredApp] = useState(false);

  const {
    messages,
    isLoading,
    currentPersona,
    setCurrentPersona,
    sendMessage,
  } = useChat(clientId);

  const { events, isConnected, clearEvents } = useTraceWS(clientId);

  return (
    <div className="h-screen w-screen bg-slate-950 text-slate-100 flex flex-col font-sans antialiased overflow-hidden relative">
      {/* ── Landing screen (fades out after Continue is clicked) ── */}
      <div
        className={`absolute inset-0 z-50 transition-opacity duration-500 ${
          hasEnteredApp ? 'opacity-0 pointer-events-none' : 'opacity-100'
        }`}
      >
        <LandingScreen onContinue={() => setHasEnteredApp(true)} />
      </div>
      {/* Navigation Header */}
      <header className="h-14 w-full border-b border-slate-800/80 bg-slate-900/60 backdrop-blur-md px-4 flex items-center justify-between shrink-0 z-30">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-xl bg-gradient-to-tr from-cyan-500/20 via-sky-500/30 to-indigo-600/30 border border-cyan-500/40 flex items-center justify-center text-cyan-300 shadow-md shadow-cyan-500/20 backdrop-blur-md">
            <SiLanggraph className="w-4 h-4 drop-shadow-[0_0_8px_rgba(6,182,212,0.8)]" />
          </div>
          <div>
            <h1 className="text-xs font-bold text-slate-100 flex items-center gap-1.5">
              OmniGraph
            </h1>
          </div>
        </div>

        {/* Right Controls */}
        <div className="flex items-center gap-2">

          <button
            onClick={() => setIsTraceOpen(!isTraceOpen)}
            className={`flex items-center gap-1.5 text-xs font-medium px-3 py-1.5 rounded-lg border transition-all cursor-pointer ${
              isTraceOpen
                ? 'bg-sky-500/20 text-sky-300 border-sky-500/50'
                : 'bg-slate-800 hover:bg-slate-700 text-slate-200 border-slate-700'
            }`}
          >
            <Activity className={`w-3.5 h-3.5 ${isConnected ? 'text-emerald-400' : 'text-slate-400'}`} />
            <span>Live Trace</span>
            {events.length > 0 && (
              <span className="ml-1 text-[10px] bg-sky-500 text-white font-bold px-1.5 py-0.2 rounded-full">
                {events.length}
              </span>
            )}
          </button>
        </div>
      </header>

      {/* Main Split-Screen Workspace */}
      <div className="flex-1 w-full flex overflow-hidden relative">
        {/* Left Side: Chat Workspace */}
        <main className="flex-1 h-full flex flex-col justify-between items-center relative overflow-hidden border-r border-slate-800/60">
          <ChatContainer
            messages={messages}
            isLoading={isLoading}
            onSelectCitation={(_meta) => {
              // Handled inline via modals/badges under message items
            }}
            onSelectSuggestion={(suggestion) => {
              if (!isLoading) {
                sendMessage(suggestion);
              }
            }}
          />

          <ChatInput
            onSendMessage={sendMessage}
            isLoading={isLoading}
            currentPersona={currentPersona}
            onPersonaChange={setCurrentPersona}
          />
        </main>

        {/* Mobile-only dimmed backdrop — tapping it closes the trace drawer.
            Hidden entirely at md+ since the panel isn't an overlay there. */}
        {isTraceOpen && (
          <div
            className="fixed inset-0 bg-black/60 z-30 md:hidden"
            onClick={() => setIsTraceOpen(false)}
          />
        )}

        {/* Right Side: Live Tracer Panel.
            Mobile (<768px): fixed, full-height slide-in drawer over the chat.
            Desktop (md+): original persistent sidebar, unchanged. */}
        <div
          className={`
            fixed inset-y-0 right-0 z-40
            md:static md:z-auto
            h-full bg-slate-900/40 backdrop-blur-md
            flex flex-col shrink-0 border-l border-slate-800/60 overflow-hidden
            transition-transform duration-300
            ${isTraceOpen ? 'translate-x-0' : 'translate-x-full md:translate-x-0'}
          `}
        >
          <TracePanel
            events={events}
            isConnected={isConnected}
            onClear={clearEvents}
            isOpen={isTraceOpen}
            onClose={() => setIsTraceOpen(false)}
          />
        </div>
      </div>
    </div>
  );
}