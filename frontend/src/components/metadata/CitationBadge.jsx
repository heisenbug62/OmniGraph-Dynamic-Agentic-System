import React, { useState } from 'react';
import { FileText, Image as ImageIcon, ExternalLink, X } from 'lucide-react';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000';

export function CitationBadge({ pageNumbers = [], screenshots = [] }) {
  const [selectedImage, setSelectedImage] = useState(null);

  if (!pageNumbers.length && !screenshots.length) return null;

  return (
    <div className="mt-3 pt-3 border-t border-slate-800/80 flex flex-wrap items-center gap-2">
      <span className="text-[11px] font-semibold text-slate-400 flex items-center gap-1">
        <FileText className="w-3.5 h-3.5 text-sky-400" />
        Sources Cited:
      </span>

      {/* Page Badges */}
      {pageNumbers.map((page, idx) => (
        <span
          key={`page-${idx}`}
          className="inline-flex items-center gap-1 text-[11px] font-medium bg-sky-950/60 text-sky-300 border border-sky-800/50 px-2 py-0.5 rounded-md"
        >
          Page {page}
        </span>
      ))}

      {/* Screenshot Previews */}
      {screenshots.map((path, idx) => {
        const cleanedPath = path.startsWith('/') ? path : `/${path}`;
        const fullUrl = path.startsWith('http') 
          ? path 
          : `${API_BASE_URL}${cleanedPath}`;

        return (
          <button
            key={`img-${idx}`}
            onClick={() => setSelectedImage(fullUrl)}
            className="inline-flex items-center gap-1 text-[11px] font-medium bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 px-2 py-0.5 rounded-md transition-colors cursor-pointer"
          >
            <ImageIcon className="w-3 h-3 text-emerald-400" />
            <span>Page Preview {idx + 1}</span>
            <ExternalLink className="w-2.5 h-2.5 text-slate-400" />
          </button>
        );
      })}

      {/* Screenshot Modal */}
      {selectedImage && (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="relative max-w-4xl max-h-[90vh] bg-slate-900 border border-slate-800 rounded-2xl overflow-hidden shadow-2xl flex flex-col">
            <div className="flex items-center justify-between p-3 border-b border-slate-800 bg-slate-950">
              <span className="text-xs font-semibold text-slate-300 flex items-center gap-2">
                <ImageIcon className="w-4 h-4 text-emerald-400" />
                Document Citation Preview
              </span>
              <button
                onClick={() => setSelectedImage(null)}
                className="p-1 text-slate-400 hover:text-white rounded-lg hover:bg-slate-800 transition-colors cursor-pointer"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
            <div className="p-2 overflow-auto max-h-[80vh] flex justify-center bg-slate-950/50">
              <img
                src={selectedImage}
                alt="PDF Page Citation Screenshot"
                className="max-w-full h-auto rounded border border-slate-800 object-contain"
                onError={() => {
                  console.error('Failed to load citation screenshot image:', selectedImage);
                }}
              />
            </div>
          </div>
        </div>
      )}
    </div>
  );
}