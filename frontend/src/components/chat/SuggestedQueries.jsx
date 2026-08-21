import React from 'react';
import { FileText, Database, Code2 } from 'lucide-react';

export function SuggestedQueries() {
  const capabilities = [
    {
      icon: <FileText className="w-4 h-4 text-sky-400" />,
      badge: "Vector RAG",
      title: "PDF Document Analysis",
      description: "Search across your PDFs and uncover the information that matters, with context you can trust."
    },
    {
      icon: <Database className="w-4 h-4 text-emerald-400" />,
      badge: "Text-to-SQL",
      title: "Database Query Engine",
      description: "Converts natural language instructions into structured SQL queries safely."
    },
    {
      icon: <Code2 className="w-4 h-4 text-indigo-400" />,
      badge: "Python Engine",
      title: "Dynamic Computation",
      description: "Executes programmatic calculations and math logic in a secure runtime environment."
    }
  ];

  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-4 w-full max-w-4xl mx-auto px-4 my-6">
      {capabilities.map((item, index) => (
        <div
          key={index}
          className="bg-slate-900/60 border border-slate-800/80 rounded-2xl p-5 backdrop-blur-md flex flex-col justify-between cursor-default select-none shadow-lg"
        >
          <div>
            <div className="flex items-center justify-between mb-3">
              <div className="p-2 bg-slate-800/80 rounded-xl border border-slate-700/50">
                {item.icon}
              </div>
              <span className="text-[10px] font-bold uppercase tracking-wider px-2.5 py-1 bg-slate-800/80 text-slate-300 rounded-full border border-slate-700/40">
                {item.badge}
              </span>
            </div>
            <h3 className="text-sm font-semibold text-slate-200 mb-1">
              {item.title}
            </h3>
            <p className="text-xs text-slate-400 leading-relaxed">
              {item.description}
            </p>
          </div>
        </div>
      ))}
    </div>
  );
}