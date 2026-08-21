import React, { useState, useRef, useEffect } from 'react';
import {
  UserCheck,
  ChevronDown,
  Sparkles,
  Paperclip,
  Check,
  FileText,
  X,
  ArrowUp
} from 'lucide-react';

import { uploadPDFFile, checkDocStatus } from '../../lib/api';
import UploadConfirmModal from './UploadConfirmModal';

const PERSONAS = [
  {
    id: 'Auto',
    name: 'Auto (Smart Router)',
    description: 'Automatically routes to the best specialist'
  },
  {
    id: 'Financial Analyst',
    name: 'Financial Analyst',
    description: 'Focuses on numerical accuracy, financial metrics & PDF analysis'
  },
  {
    id: 'Legal Advisor',
    name: 'Legal Advisor',
    description: 'Emphasizes compliance, terminology & structured arguments'
  },
  {
    id: 'General Assistant',
    name: 'General Assistant',
    description: 'Clear, concise everyday conversational helper'
  }
];

export function ChatInput({
  onSendMessage,
  isLoading,
  currentPersona,
  onPersonaChange
}) {
  const [input, setInput] = useState('');
  const [isDropdownOpen, setIsDropdownOpen] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadedFileName, setUploadedFileName] = useState(null);

  // Upload Confirmation Modal State
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [pendingFile, setPendingFile] = useState(null);

  const textareaRef = useRef(null);
  const dropdownRef = useRef(null);
  const fileInputRef = useRef(null);

  // Close dropdown on outside click
  useEffect(() => {
    function handleClickOutside(event) {
      if (
        dropdownRef.current &&
        !dropdownRef.current.contains(event.target)
      ) {
        setIsDropdownOpen(false);
      }
    }

    document.addEventListener('mousedown', handleClickOutside);
    return () =>
      document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // Auto-resize textarea
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${Math.min(
        textareaRef.current.scrollHeight,
        160
      )}px`;
    }
  }, [input]);

  // Handle file input change
  const handleFileSelection = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;

    try {
      setIsUploading(true);
      const status = await checkDocStatus();

      if (status && status.doc_count > 0) {
        setPendingFile(file);
        setIsModalOpen(true);
      } else {
        await executeUpload(file, false);
      }
    } catch (err) {
      console.error('Error checking doc status, proceeding with upload:', err);
      await executeUpload(file, false);
    } finally {
      setIsUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  // Perform upload
  const executeUpload = async (file, replace = false) => {
    setIsUploading(true);

    try {
      const res = await uploadPDFFile(file, replace);
      setUploadedFileName(res.filename || file.name);
    } catch (err) {
      console.error('Upload failed:', err);
      alert('Failed to upload and index PDF document. Please try again.');
    } finally {
      setIsUploading(false);
    }
  };

  // Handle modal decision
  const handleModalDecision = async (replace) => {
    setIsModalOpen(false);
    if (pendingFile) {
      await executeUpload(pendingFile, replace);
      setPendingFile(null);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    if (input.trim() && !isLoading) {
      onSendMessage(input.trim(), currentPersona);
      setInput('');
    }
  };

  return (
    <div className="w-full max-w-4xl mx-auto p-4 z-20">

      {/* Hidden PDF input */}
      <input
        type="file"
        ref={fileInputRef}
        onChange={handleFileSelection}
        accept=".pdf"
        className="hidden"
      />

      <form
        onSubmit={handleSubmit}
        className="relative bg-slate-900/90 border border-slate-800 focus-within:border-sky-500/50 rounded-2xl shadow-2xl backdrop-blur-md overflow-visible"
      >

        {/* Active Uploaded Document */}
        {uploadedFileName && (
          <div className="flex items-center justify-between px-4 py-2 bg-slate-800/80 border-b border-slate-700/60 text-xs text-slate-200">
            <div className="flex items-center gap-2 truncate">
              <FileText className="w-3.5 h-3.5 text-sky-400 shrink-0" />

              <span className="truncate font-medium">
                Active Document:{' '}
                <strong className="text-sky-300">
                  {uploadedFileName}
                </strong>
              </span>
            </div>

            <button
              type="button"
              onClick={() => setUploadedFileName(null)}
              className="p-1 rounded-md hover:bg-slate-700 text-slate-400 hover:text-white transition-colors cursor-pointer"
              title="Clear active document reference"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          </div>
        )}

        {/* Persona Selector */}
        <div className="flex items-center justify-between px-4 pt-3 pb-2 border-b border-slate-800/60">

          <div
            className="relative"
            ref={dropdownRef}
          >

            <button
              type="button"
              onClick={() =>
                setIsDropdownOpen((prev) => !prev)
              }
              className="flex items-center gap-2 text-xs font-medium text-slate-300 hover:text-white bg-slate-800/90 hover:bg-slate-700/90 px-3 py-1.5 rounded-lg border border-slate-700/60 transition-all cursor-pointer shadow-sm"
            >
              <UserCheck className="w-3.5 h-3.5 text-sky-400" />

              <span>
                Persona:{' '}
                <strong className="text-sky-300">
                  {currentPersona}
                </strong>
              </span>

              <ChevronDown
                className={`w-3.5 h-3.5 text-slate-400 transition-transform ${
                  isDropdownOpen ? 'rotate-180' : ''
                }`}
              />
            </button>

            {/* Persona Dropdown */}
            {isDropdownOpen && (
              <div className="absolute bottom-full mb-2 left-0 w-72 bg-slate-900 border border-slate-800 rounded-2xl shadow-2xl z-50 p-1.5 space-y-1 backdrop-blur-xl">

                <div className="px-3 py-1.5 border-b border-slate-800/80 text-[10px] font-bold tracking-wider text-slate-400 uppercase">
                  Select Active Agent Persona
                </div>

                {PERSONAS.map((p) => {
                  const isSelected = currentPersona === p.id;

                  return (
                    <button
                      key={p.id}
                      type="button"
                      onClick={() => {
                        onPersonaChange(p.id);
                        setIsDropdownOpen(false);
                      }}
                      className={`w-full text-left px-3 py-2 rounded-xl transition-all flex items-start justify-between group cursor-pointer ${
                        isSelected
                          ? 'bg-sky-950/60 border border-sky-800/50 text-white'
                          : 'hover:bg-slate-800/80 text-slate-300'
                      }`}
                    >
                      <div>
                        <div className="text-xs font-semibold flex items-center gap-1.5">
                          {p.name}

                          {p.id === 'Auto' && (
                            <Sparkles className="w-3 h-3 text-sky-400" />
                          )}
                        </div>

                        <p className="text-[10px] text-slate-400 mt-0.5 leading-tight">
                          {p.description}
                        </p>
                      </div>

                      {isSelected && (
                        <Check className="w-4 h-4 text-sky-400 shrink-0 mt-0.5" />
                      )}
                    </button>
                  );
                })}

              </div>
            )}

          </div>

        </div>

        {/* Input Area */}
        <div className="flex items-end gap-2 px-4 py-3">

          {/* Upload PDF */}
          <button
            type="button"
            onClick={() => fileInputRef.current?.click()}
            disabled={isUploading || isLoading}
            title="Upload PDF Document"
            className="p-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white transition-colors cursor-pointer shrink-0 disabled:opacity-50"
          >
            {isUploading ? (
              <div className="w-4 h-4 border-2 border-sky-400 border-t-transparent rounded-full animate-spin" />
            ) : (
              <Paperclip className="w-4 h-4" />
            )}
          </button>

          {/* Text Input */}
          <textarea
            ref={textareaRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={
              uploadedFileName
                ? `Ask a question about ${uploadedFileName}...`
                : 'Ask anything or upload a PDF document...'
            }
            rows={1}
            disabled={isLoading}
            className="w-full bg-transparent text-slate-100 placeholder-slate-500 text-sm focus:outline-none resize-none min-h-10 max-h-40 py-2"
          />

          {/* Submit Button */}
          <button
            type="submit"
            disabled={!input.trim() || isLoading}
            title="Execute Query"
            className={`relative group w-9 h-9 flex items-center justify-center rounded-xl transition-all duration-200 shrink-0 ${
              input.trim() && !isLoading
                ? 'bg-gradient-to-tr from-cyan-500 via-sky-500 to-indigo-600 text-white shadow-lg shadow-cyan-500/30 hover:shadow-cyan-500/50 hover:scale-105 active:scale-95 cursor-pointer'
                : 'bg-slate-800/60 border border-slate-700/40 text-slate-600 cursor-not-allowed'
            }`}
          >
            {isLoading ? (
              <div className="w-4 h-4 border-2 border-cyan-400 border-t-transparent rounded-full animate-spin" />
            ) : (
              <ArrowUp
                className={`w-4 h-4 transition-transform duration-200 ${
                  input.trim() ? 'group-hover:-translate-y-0.5' : ''
                }`}
                strokeWidth={2.5}
              />
            )}
          </button>

        </div>

      </form>

      {/* Upload Confirmation Modal */}
      <UploadConfirmModal
        isOpen={isModalOpen}
        fileName={pendingFile?.name}
        onClose={() => {
          setIsModalOpen(false);
          setPendingFile(null);

          if (fileInputRef.current) {
            fileInputRef.current.value = '';
          }
        }}
        onConfirm={handleModalDecision}
      />

    </div>
  );
}