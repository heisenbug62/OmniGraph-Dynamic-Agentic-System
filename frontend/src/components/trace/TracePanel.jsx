import React, { useState, useEffect, useRef } from 'react';
import { 
  Activity, 
  CheckCircle2, 
  Clock, 
  Cpu, 
  ChevronRight, 
  Trash2, 
  FileText,
  Database,
  Calculator,
  Compass,
  UserCog,
  Lightbulb
} from 'lucide-react';

// Maps real backend node names -> friendly display labels.
// Keep this in sync with the node names registered in workflow.py.
const NODE_LABELS = {
  classifier_node: 'Classifying Query',
  route_decision: 'Routing Decision',
  doc_rag_node: 'Searching Documents',
  db_sql_node: 'Querying Database',
  math_exec_node: 'Running Calculation',
  suggestion_node: 'Generating Follow-ups',
  answer_formatter_node: 'Formatting Answer',
};

function getDisplayLabel(event) {
  if (event.event === 'workflow_start') return 'Workflow Started';
  if (event.event === 'workflow_complete') return 'Workflow Complete';
  if (event.node && NODE_LABELS[event.node]) return NODE_LABELS[event.node];
  return event.event || event.node || 'State Update';
}

export function TracePanel({ events = [], isConnected, onClear, isOpen, onClose }) {
  const [expandedIndices, setExpandedIndices] = useState({});
  const traceEndRef = useRef(null);

  const toggleExpand = (index) => {
    setExpandedIndices((prev) => ({
      ...prev,
      [index]: !prev[index],
    }));
  };

  // Auto-scroll to the newest trace event as they stream in — same
  // pattern ChatContainer.jsx uses for auto-scrolling chat messages.
  useEffect(() => {
    traceEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [events]);

  const getNodeIcon = (nodeName) => {
    switch (nodeName) {
      case 'classifier_node':
        return <UserCog className="w-4 h-4 text-amber-400" />;
      case 'route_decision':
        return <Compass className="w-4 h-4 text-amber-400" />;
      case 'doc_rag_node':
        return <FileText className="w-4 h-4 text-sky-400" />;
      case 'db_sql_node':
        return <Database className="w-4 h-4 text-emerald-400" />;
      case 'math_exec_node':
        return <Calculator className="w-4 h-4 text-purple-400" />;
      case 'suggestion_node':
        return <Lightbulb className="w-4 h-4 text-yellow-400" />;
      case 'answer_formatter_node':
        return <Cpu className="w-4 h-4 text-indigo-400" />;
      default:
        return <Activity className="w-4 h-4 text-slate-400" />;
    }
  };

  return (
    <aside className={`relative h-full bg-slate-950/95 border-l border-slate-800 shadow-2xl backdrop-blur-xl flex flex-col transition-all duration-300 shrink-0 ${isOpen ? 'w-80 sm:w-96' : 'w-12'}`}>
      {/* When collapsed, show minimal indicator icon */}
      {!isOpen ? (
        <div className="h-full flex flex-col items-center py-6 cursor-pointer" onClick={onClose} title="Expand Live Trace">
          <Activity className="w-5 h-5 text-sky-400 animate-pulse" />
        </div>
      ) : (
        /* Panel Content */
        <div className="h-full flex flex-col w-full overflow-hidden">
          {/* Panel Header */}
          <div className="flex items-center justify-between p-4 border-b border-slate-800/80 bg-slate-900/50 shrink-0">
            <div className="flex items-center gap-2">
              <Activity className="w-4 h-4 text-sky-400 animate-pulse" />
              <h2 className="text-sm font-semibold text-slate-200">Omni Trace</h2>
            </div>

            <div className="flex items-center gap-2">
              {/* Clear Trace Log */}
              <button
                onClick={onClear}
                title="Clear Trace Log"
                className="p-1.5 text-slate-400 hover:text-slate-200 hover:bg-slate-800 rounded-lg transition-colors cursor-pointer"
              >
                <Trash2 className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>

          {/* Trace Log Body */}
          <div className="flex-1 overflow-y-auto p-4 space-y-3 [&::-webkit-scrollbar]:w-1.5 [&::-webkit-scrollbar-track]:bg-transparent [&::-webkit-scrollbar-thumb]:bg-slate-800 [&::-webkit-scrollbar-thumb]:rounded-full">
            {events.length === 0 ? (
              <div className="h-full flex flex-col items-center justify-center text-center text-slate-500 py-12">
                <Cpu className="w-8 h-8 mb-2 stroke-1 opacity-50 text-slate-600" />
                <p className="text-xs font-medium">No execution trace events yet</p>
              </div>
            ) : (
              <>
                {events.map((event, idx) => {
                  const isExpanded = !!expandedIndices[idx];
                  const isComplete = event.event === 'workflow_complete';
                  const isStart = event.event === 'workflow_start';
                  const displayLabel = getDisplayLabel(event);

                  return (
                    <div
                      key={idx}
                      className={`rounded-xl border transition-all text-xs ${
                        isComplete
                          ? 'bg-emerald-950/20 border-emerald-800/40'
                          : isStart
                          ? 'bg-sky-950/20 border-sky-800/40'
                          : 'bg-slate-900/80 border-slate-800 hover:border-slate-700'
                      }`}
                    >
                      {/* Event Card Header */}
                      <div
                        onClick={() => toggleExpand(idx)}
                        className="p-3 flex items-center justify-between cursor-pointer select-none"
                      >
                        <div className="flex items-center gap-2.5 min-w-0">
                          {isComplete ? (
                            <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
                          ) : isStart ? (
                            <Clock className="w-4 h-4 text-sky-400 shrink-0" />
                          ) : (
                            getNodeIcon(event.node)
                          )}

                          <div className="flex flex-col min-w-0">
                            <span className="font-semibold text-slate-200 truncate">
                              {displayLabel}
                            </span>
                            {event.node && (
                              <span className="text-[10px] text-slate-400 font-mono">
                                Node: {event.node}
                              </span>
                            )}
                          </div>
                        </div>

                        <div className="flex items-center gap-1 shrink-0">
                          {event.status && (
                            <span className="text-[10px] font-mono px-1.5 py-0.5 bg-slate-800 text-slate-300 rounded border border-slate-700/50">
                              {event.status}
                            </span>
                          )}
                          {isExpanded ? (
                            <ChevronRight className="w-3.5 h-3.5 text-slate-400 rotate-90" />
                          ) : (
                            <ChevronRight className="w-3.5 h-3.5 text-slate-400" />
                          )}
                        </div>
                      </div>

                      {/* Collapsible Details Body */}
                      {isExpanded && (
                        <div className="px-3 pb-3 pt-1 border-t border-slate-800/60 bg-slate-950/50 rounded-b-xl">
                          <div className="text-[10px] font-mono text-slate-400 space-y-1">
                            {event.route_target && (
                              <div>
                                <strong className="text-sky-400">Route Target:</strong>{' '}
                                {event.route_target}
                              </div>
                            )}
                            {event.persona && (
                              <div>
                                <strong className="text-purple-400">Persona:</strong> {event.persona}
                              </div>
                            )}
                          </div>

                          {/* Raw State JSON Viewer */}
                          <div className="mt-2">
                            <span className="text-[10px] font-semibold text-slate-500 block mb-1">
                              State Payload
                            </span>
                            <pre className="p-2 bg-slate-950 border border-slate-800/80 rounded-lg text-[10px] font-mono text-slate-300 overflow-x-auto max-h-40">
                              {JSON.stringify(event, null, 2)}
                            </pre>
                          </div>
                        </div>
                      )}
                    </div>
                  );
                })}
                <div ref={traceEndRef} />
              </>
            )}
          </div>
        </div>
      )}
    </aside>
  );
}