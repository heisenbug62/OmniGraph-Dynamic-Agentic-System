import React from 'react';
import { AlertTriangle, PlusCircle, RefreshCw, X } from 'lucide-react';

export default function UploadConfirmModal({ isOpen, fileName, onClose, onConfirm }) {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/80 backdrop-blur-sm p-4">
      <div className="relative w-full max-w-md bg-slate-900 border border-slate-800 rounded-2xl shadow-2xl overflow-hidden p-6 space-y-6">
        
        {/* Close Button */}
        <button
          onClick={onClose}
          className="absolute top-4 right-4 text-slate-400 hover:text-white p-1 rounded-lg bg-slate-800/60 hover:bg-slate-800 transition-colors cursor-pointer"
        >
          <X className="w-4 h-4" />
        </button>

        {/* Header Icon & Title */}
        <div className="flex items-start gap-3.5">
          <div className="p-2.5 bg-amber-500/10 border border-amber-500/20 rounded-xl text-amber-400 shrink-0">
            <AlertTriangle className="w-5 h-5" />
          </div>
          <div>
            <h3 className="text-base font-bold text-slate-100">Existing Documents Found</h3>
            <p className="text-xs text-slate-400 mt-0.5">Pinecone Vector Database</p>
          </div>
        </div>

        <p className="text-xs text-slate-300 leading-relaxed">
          Your knowledge base already has indexed files. How would you like to process <strong className="text-sky-300">{fileName || "the new file"}</strong>?
        </p>

        {/* Action Buttons (Explicitly clickable with high z-index & cursor-pointer) */}
        <div className="space-y-3">
          <button
            type="button"
            onClick={() => onConfirm(false)}
            className="w-full flex items-center justify-between p-4 bg-slate-800/60 hover:bg-slate-800 border border-slate-700/60 hover:border-sky-500/50 rounded-xl transition-all cursor-pointer group text-left relative z-10"
          >
            <div className="flex items-center gap-3">
              <div className="p-2 bg-emerald-500/10 text-emerald-400 rounded-lg border border-emerald-500/20">
                <PlusCircle className="w-4 h-4" />
              </div>
              <div>
                <h4 className="text-xs font-semibold text-slate-200 group-hover:text-white">Keep & Append</h4>
                <p className="text-[11px] text-slate-400">Combine with previous documents</p>
              </div>
            </div>
            <span className="text-[10px] font-bold px-2.5 py-1 bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 rounded-md">
              Append
            </span>
          </button>

          <button
            type="button"
            onClick={() => onConfirm(true)}
            className="w-full flex items-center justify-between p-4 bg-slate-800/60 hover:bg-slate-800 border border-slate-700/60 hover:border-rose-500/50 rounded-xl transition-all cursor-pointer group text-left relative z-10"
          >
            <div className="flex items-center gap-3">
              <div className="p-2 bg-rose-500/10 text-rose-400 rounded-lg border border-rose-500/20">
                <RefreshCw className="w-4 h-4" />
              </div>
              <div>
                <h4 className="text-xs font-semibold text-slate-200 group-hover:text-white">Replace & Start Fresh</h4>
                <p className="text-[11px] text-slate-400">Delete previous docs & index new file only</p>
              </div>
            </div>
            <span className="text-[10px] font-bold px-2.5 py-1 bg-rose-500/10 text-rose-400 border border-rose-500/20 rounded-md">
              Replace
            </span>
          </button>
        </div>

      </div>
    </div>
  );
}