import React from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import rehypeKatex from 'rehype-katex';
import 'katex/dist/katex.min.css';
import { User, Database, Calculator, FileText, Sparkles, HelpCircle } from 'lucide-react';
import { SiLanggraph } from 'react-icons/si';
import { CitationBadge } from '../metadata/CitationBadge';

export function MessageBubble({ message, onSelectSuggestion }) {
  const isUser = message.role === 'user';
  const metadata = message.metadata || {};
  const routeTarget = metadata.route_target;
  const sourceMetadata = metadata.source_metadata || {};
  
  const suggestions = message.suggested_queries || metadata.suggested_queries || sourceMetadata.suggested_queries || [];

  const renderRouteBadge = () => {
    if (!routeTarget) return null;
    
    let label = 'General';
    let Icon = SiLanggraph;
    let badgeStyle = 'bg-slate-800 text-slate-300 border-slate-700';

    if (routeTarget === 'doc') {
      label = 'PDF Vector RAG';
      Icon = FileText;
      badgeStyle = 'bg-sky-950/60 text-sky-300 border-sky-800/50';
    } else if (routeTarget === 'db') {
      label = 'Text-to-SQL';
      Icon = Database;
      badgeStyle = 'bg-emerald-950/60 text-emerald-300 border-emerald-800/50';
    } else if (routeTarget === 'math') {
      label = 'Python Math Engine';
      Icon = Calculator;
      badgeStyle = 'bg-purple-950/60 text-purple-300 border-purple-800/50';
    }

    return (
      <span className={`inline-flex items-center gap-1 text-[10px] font-semibold px-2 py-0.5 rounded-full border ${badgeStyle}`}>
        <Icon className="w-3 h-3" />
        {label}
      </span>
    );
  };

  return (
    <div className={`flex w-full my-4 gap-3 ${isUser ? 'justify-end' : 'justify-start'}`}>
      {!isUser && (
        <div className="w-8 h-8 rounded-xl bg-gradient-to-tr from-cyan-500/20 via-sky-500/30 to-indigo-600/30 border border-cyan-500/40 flex items-center justify-center text-cyan-300 shrink-0 shadow-lg shadow-cyan-500/20">
          <SiLanggraph className="w-4 h-4 drop-shadow-[0_0_6px_rgba(6,182,212,0.7)]" />
        </div>
      )}

      <div className={`flex flex-col max-w-[85%] sm:max-w-[75%] ${isUser ? 'items-end' : 'items-start'}`}>
        {!isUser && (
          <div className="flex items-center gap-2 mb-1.5 px-1">
            {message.persona && (
              <span className="text-xs font-medium text-sky-400 flex items-center gap-1">
                <Sparkles className="w-3 h-3" />
                {message.persona}
              </span>
            )}
            {renderRouteBadge()}
          </div>
        )}

        <div className={`p-4 rounded-2xl shadow-md transition-all ${isUser ? 'bg-sky-600 text-white rounded-tr-none' : 'bg-slate-900 border border-slate-800 text-slate-100 rounded-tl-none'}`}>
          {isUser ? (
            <p className="text-sm leading-relaxed whitespace-pre-wrap">{message.content}</p>
          ) : (
            <div className="prose prose-invert prose-sm max-w-none text-slate-200 leading-relaxed overflow-x-auto">
              <ReactMarkdown
                remarkPlugins={[remarkGfm]}
                rehypePlugins={[rehypeKatex]}
                components={{
                  table: ({ node: _node, ...props }) => <div className="my-3 overflow-x-auto rounded-lg border border-slate-800"><table className="min-w-full divide-y divide-slate-800 text-xs" {...props} /></div>,
                  thead: ({ node: _node, ...props }) => <thead className="bg-slate-800/80 text-slate-200" {...props} />,
                  th: ({ node: _node, ...props }) => <th className="px-3 py-2 text-left font-semibold" {...props} />,
                  td: ({ node: _node, ...props }) => <td className="px-3 py-2 border-t border-slate-800/50" {...props} />,
                  code: ({ node: _node, inline, className: _className, children, ...props }) => inline ? <code className="bg-slate-800 text-sky-300 px-1.5 py-0.5 rounded text-xs font-mono" {...props}>{children}</code> : <pre className="bg-slate-950 p-3 rounded-lg border border-slate-800 overflow-x-auto text-xs font-mono text-slate-200"><code {...props}>{children}</code></pre>,
                }}
              >
                {message.content}
              </ReactMarkdown>
            </div>
          )}

          {!isUser && <CitationBadge pageNumbers={sourceMetadata.page_numbers || []} screenshots={sourceMetadata.screenshots || []} />}

          {!isUser && suggestions && suggestions.length > 0 && (
            <div className="mt-4 pt-3 border-t border-slate-800/80 flex flex-col gap-2">
              <div className="flex items-center gap-1.5 text-[11px] font-medium text-slate-400">
                <HelpCircle className="w-3.5 h-3.5 text-sky-400" />
                <span>Suggested Follow-up Questions:</span>
              </div>
              <div className="flex flex-col gap-1.5">
                {suggestions.map((suggestion, idx) => (
                  <button key={idx} type="button" onClick={() => onSelectSuggestion && onSelectSuggestion(suggestion)} className="text-left text-xs bg-slate-800/60 hover:bg-slate-800 text-slate-300 hover:text-sky-300 border border-slate-700/50 hover:border-sky-500/30 rounded-xl px-3 py-2 transition-all cursor-pointer">
                    {suggestion}
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>

      {isUser && (
        <div className="w-8 h-8 rounded-xl bg-slate-800 border border-slate-700 flex items-center justify-center text-slate-300 shrink-0">
          <User className="w-4 h-4" />
        </div>
      )}
    </div>
  );
}