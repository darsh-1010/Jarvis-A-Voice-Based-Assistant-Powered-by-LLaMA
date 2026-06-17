/**
 * Copyright (c) 2024-2026 Darsh Shah
 * Licensed under the Business Source License 1.1
 */
'use client';

import React, { useState, useEffect, useRef, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Mic, Shield, Activity, List, MessageSquare, StopCircle, ArrowUp, Sparkles, Terminal } from 'lucide-react';

interface Stats {
  cpu_percent: number;
  ram_percent: number;
  disk_usage: number;
}

type OrbState = 'idle' | 'listening' | 'thinking' | 'streaming' | 'error';

/**
 * Suggested starting commands for premium empty state.
 */
const SUGGESTED_PROMPTS = [
  { label: 'Check Morning Briefing', command: 'what is my morning briefing' },
  { label: 'System Health Diagnostic', command: 'check system health' },
  { label: 'Internet Speed Check', command: 'test internet speed' },
  { label: 'Weather Forecast', command: 'what is the weather forecast for today' },
];

export default function AssistantDashboard() {
  const [messages, setMessages] = useState<{ role: 'user' | 'assistant', text: string }[]>([]);
  const [input, setInput] = useState('');
  const [orbState, setOrbState] = useState<OrbState>('idle');
  const [stats, setStats] = useState<Stats>({ cpu_percent: 0, ram_percent: 0, disk_usage: 0 });
  const [isApiOnline, setIsApiOnline] = useState(true);
  const [streamingText, setStreamingText] = useState('');
  const scrollRef = useRef<HTMLDivElement>(null);
  const abortControllerRef = useRef<AbortController | null>(null);

  // Auto-scroll to latest message
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, streamingText]);

  // Poll system stats
  useEffect(() => {
    const interval = setInterval(async () => {
      try {
        const res = await fetch('http://localhost:8000/system/stats');
        if (res.ok) {
          const data = await res.json();
          setStats(data);
          setIsApiOnline(true);
        } else {
          setIsApiOnline(false);
        }
      } catch {
        setIsApiOnline(false);
      }
    }, 2000);
    return () => clearInterval(interval);
  }, []);

  const handleStop = useCallback(() => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }
    setOrbState('idle');
    setStreamingText(prev => {
      if (prev) {
        setMessages(msgs => [...msgs, { role: 'assistant', text: prev + ' [stopped]' }]);
      }
      return '';
    });
  }, []);

  const handleSend = useCallback(async (customMsg?: string) => {
    const messageToSend = (customMsg || input).trim();
    if (!messageToSend || orbState === 'streaming') return;

    setInput('');
    setMessages(prev => [...prev, { role: 'user', text: messageToSend }]);
    setOrbState('thinking');
    setStreamingText('');

    const controller = new AbortController();
    abortControllerRef.current = controller;

    try {
      const res = await fetch('http://localhost:8000/chat/stream', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: messageToSend }),
        signal: controller.signal,
      });

      if (!res.ok || !res.body) {
        throw new Error(`HTTP ${res.status}`);
      }

      setOrbState('streaming');

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let accumulated = '';

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value, { stream: true });
        const lines = chunk.split('\n').filter(l => l.startsWith('data: '));
        for (const line of lines) {
          const payload = line.slice(6).trim();
          if (payload === '[DONE]') {
            setMessages(prev => [...prev, { role: 'assistant', text: accumulated }]);
            setStreamingText('');
            setOrbState('idle');
            return;
          }
          try {
            const token: string = JSON.parse(payload);
            accumulated += token;
            setStreamingText(accumulated);
          } catch {
            // Ignore parse errors
          }
        }
      }
    } catch (err: unknown) {
      if (err instanceof Error && err.name === 'AbortError') return;
      setOrbState('error');
      setStreamingText('');
      setMessages(prev => [...prev, { role: 'assistant', text: 'Neural link lost. Attempting reconnection...' }]);
      setTimeout(() => setOrbState('idle'), 3000);
    } finally {
      abortControllerRef.current = null;
    }
  }, [input, orbState]);

  const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
    if (e.key === 'Enter') handleSend();
  }, [handleSend]);

  const isAnimating = orbState === 'thinking' || orbState === 'listening' || orbState === 'streaming';

  const getOrbGradient = () => {
    switch (orbState) {
      case 'listening':
        return 'from-cyan-400 via-blue-500 to-sky-400';
      case 'thinking':
        return 'from-violet-500 via-purple-600 to-indigo-700';
      case 'streaming':
        return 'from-emerald-400 via-teal-500 to-cyan-400';
      case 'error':
        return 'from-rose-500 via-red-600 to-orange-500';
      default:
        return 'from-slate-600 via-slate-800 to-slate-950 dark:from-slate-800 dark:via-slate-900 dark:to-black';
    }
  };

  const getOrbShadow = () => {
    switch (orbState) {
      case 'listening':
        return 'shadow-[0_0_50px_rgba(6,182,212,0.4)]';
      case 'thinking':
        return 'shadow-[0_0_50px_rgba(139,92,246,0.4)]';
      case 'streaming':
        return 'shadow-[0_0_50px_rgba(16,185,129,0.4)]';
      case 'error':
        return 'shadow-[0_0_50px_rgba(239,68,68,0.4)]';
      default:
        return 'shadow-[0_0_30px_rgba(0,0,0,0.15)] dark:shadow-[0_0_30px_rgba(255,255,255,0.02)]';
    }
  };

  return (
    <div className="flex-1 flex flex-col p-6 md:p-10 min-w-0 h-full relative overflow-hidden bg-[var(--bg)]">
      
      {/* Dynamic Ambient Reacting Background Glow */}
      <div className="absolute inset-0 pointer-events-none overflow-hidden">
        <motion.div 
          animate={{ 
            scale: orbState === 'thinking' ? [1, 1.25, 1] : orbState === 'streaming' ? [1, 1.1, 1] : 1,
            opacity: orbState === 'listening' ? 0.08 : orbState === 'thinking' ? 0.09 : orbState === 'streaming' ? 0.06 : 0.02 
          }}
          transition={{ duration: 3, repeat: Infinity, ease: 'easeInOut' }}
          className={`absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[800px] h-[800px] rounded-full blur-[140px] transition-colors duration-1000 bg-gradient-to-tr ${getOrbGradient()}`} 
        />
      </div>

      {/* Header bar */}
      <header className="mb-6 flex justify-between items-center z-10">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-black text-[var(--text)] tracking-tight font-sans">
              JARVIS <span className="text-xs font-medium text-[var(--accent)] tracking-normal ml-1">v3.2</span>
            </h1>
          </div>
          <div className="flex items-center gap-1.5 mt-1">
            <div className={`w-1.5 h-1.5 rounded-full ${isApiOnline ? 'bg-emerald-400 animate-pulse' : 'bg-rose-500'}`} />
            <p className="text-[9px] text-[var(--text)] opacity-40 font-black uppercase tracking-widest">
              {isApiOnline ? 'Neural Link Online' : 'Neural Link Offline'}
            </p>
          </div>
        </div>
        
        {/* Resource Gauges */}
        <div className="hidden lg:flex gap-6">
          <StatMini label="Neural Load" value={stats.cpu_percent} />
          <StatMini label="Synaptic RAM" value={stats.ram_percent} />
        </div>
      </header>

      {/* Central View Area */}
      <div className="flex-1 flex flex-col items-center justify-between min-h-0 z-10 py-4">
        
        {/* Welcoming Empty State OR Chat View */}
        <div className="w-full max-w-3xl flex-1 flex flex-col justify-center min-h-0 relative">
          <AnimatePresence mode="wait">
            {messages.length === 0 && !streamingText ? (
              <motion.div 
                key="empty-state"
                initial={{ opacity: 0, y: 15 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -15 }}
                className="flex flex-col items-center text-center px-4"
              >
                {/* Micro Ambient Sparkle icon */}
                <div className="w-12 h-12 rounded-full bg-slate-500/5 border border-[var(--border-glass)] flex items-center justify-center text-[var(--accent)] mb-6 shadow-sm">
                  <Sparkles size={18} className="animate-pulse" />
                </div>
                
                <h2 className="text-4xl font-extrabold tracking-tight text-[var(--text)] font-sans max-w-xl leading-tight">
                  How can I assist you, <span className="bg-clip-text text-transparent bg-gradient-to-r from-[var(--accent)] to-violet-400">Commander?</span>
                </h2>
                
                <p className="text-sm text-[var(--text)] opacity-55 mt-3 max-w-md leading-relaxed font-medium">
                  I can run system diagnostics, check schedule lists, monitor network stats, or respond to voice commands.
                </p>

                {/* Grid of suggest task chips */}
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 max-w-lg w-full mt-10">
                  {SUGGESTED_PROMPTS.map((prompt) => (
                    <button
                      key={prompt.label}
                      onClick={() => handleSend(prompt.command)}
                      className="glass-interactive text-left px-5 py-4 rounded-2xl flex items-center justify-between group cursor-pointer text-[var(--text)]"
                    >
                      <div>
                        <p className="text-xs font-bold tracking-tight text-left">{prompt.label}</p>
                        <p className="text-[10px] opacity-40 text-left mt-0.5 font-mono">/{prompt.command.slice(0, 24)}...</p>
                      </div>
                      <ArrowUp size={14} className="opacity-0 group-hover:opacity-100 group-hover:translate-y-[-2px] transition-all text-[var(--accent)]" />
                    </button>
                  ))}
                </div>
              </motion.div>
            ) : (
              <motion.div 
                key="chat-history"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="w-full h-full flex flex-col min-h-0"
              >
                {/* Scrollable messages container */}
                <div 
                  ref={scrollRef}
                  className="flex-1 overflow-y-auto space-y-4 pr-2 scrollbar-hide pb-6"
                >
                  {messages.map((msg, i) => (
                    <div 
                      key={i}
                      className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
                    >
                      <div 
                        className={`
                          max-w-[80%] rounded-[24px] px-6 py-4 text-sm leading-relaxed shadow-sm
                          ${msg.role === 'user' 
                            ? 'bg-[var(--accent)] text-white font-medium border border-[rgba(var(--accent-rgb),0.2)] rounded-tr-sm' 
                            : 'glass-minimal text-[var(--text)] border border-[var(--border-glass)] rounded-tl-sm font-medium'
                          }
                        `}
                      >
                        {msg.role === 'assistant' && (
                          <div className="flex items-center gap-1.5 mb-1.5">
                            <div className="w-1.5 h-1.5 rounded-full bg-[var(--accent)]" />
                            <span className="text-[9px] font-black uppercase tracking-widest opacity-40">JARVIS</span>
                          </div>
                        )}
                        <p className="whitespace-pre-wrap">{msg.text}</p>
                      </div>
                    </div>
                  ))}

                  {/* Active token stream bubble */}
                  {streamingText && (
                    <div className="flex justify-start">
                      <div className="max-w-[80%] glass-minimal text-[var(--text)] border border-[var(--border-glass)] rounded-[24px] rounded-tl-sm px-6 py-4 text-sm leading-relaxed shadow-sm">
                        <div className="flex items-center gap-1.5 mb-1.5">
                          <div className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-ping" />
                          <span className="text-[9px] font-black uppercase tracking-widest text-emerald-400">Streaming</span>
                        </div>
                        <p className="streaming-cursor whitespace-pre-wrap">{streamingText}</p>
                      </div>
                    </div>
                  )}
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>

        {/* Dynamic Glowing Ambient Core */}
        <div className="flex flex-col items-center my-6 z-20">
          <div className="relative w-28 h-28 flex items-center justify-center">
            
            {/* Concentric Glow pulse ring */}
            <AnimatePresence>
              {isAnimating && (
                <motion.div 
                  initial={{ scale: 0.9, opacity: 0 }}
                  animate={{ scale: 1.4, opacity: [0.15, 0, 0.15] }}
                  exit={{ opacity: 0 }}
                  transition={{ duration: 2, repeat: Infinity, ease: 'easeInOut' }}
                  className={`absolute inset-0 rounded-full border border-current opacity-20 text-[var(--accent)]`}
                />
              )}
            </AnimatePresence>
            
            {/* Morphing core orb */}
            <motion.div 
              layout
              className={`
                absolute w-20 h-20 rounded-full bg-gradient-to-tr transition-all duration-700 ambient-orb
                ${getOrbGradient()} ${getOrbShadow()}
              `}
            />

            {/* Glowing particle ring */}
            <div className={`w-24 h-24 absolute border border-white/5 rounded-full ${orbState === 'thinking' ? 'animate-spin' : ''}`} />
          </div>
        </div>

      </div>

      {/* Floating Control Input pill */}
      <footer className="mt-auto z-20 w-full max-w-2xl mx-auto">
        <div className="flex flex-col items-center gap-6">
          
          {/* Action Chips */}
          <div className="flex gap-2 overflow-x-auto pb-1 scrollbar-hide w-full justify-center">
            {[
              { label: 'Check Schedule', icon: List, cmd: 'what is my schedule' },
              { label: 'System Diagnostics', icon: Activity, cmd: 'check system health' },
              { label: 'Security Protocols', icon: Shield, cmd: 'run security audit' }
            ].map((action) => (
              <button
                key={action.label}
                onClick={() => handleSend(action.cmd)}
                className="flex items-center gap-2 px-5 py-2 bg-[var(--card)] border border-[var(--border)] rounded-full text-[9px] font-black text-[var(--text)] opacity-60 hover:opacity-100 hover:border-slate-500 transition-all shadow-sm uppercase tracking-widest cursor-pointer"
              >
                <action.icon size={12} className="text-[var(--accent)]" />
                <span>{action.label}</span>
              </button>
            ))}
          </div>

          {/* Floating glass pill capsule input */}
          <div className="w-full flex items-center gap-3 bg-[var(--card-glass)] backdrop-blur-xl p-2 pl-6 rounded-[24px] border border-[var(--border-glass)] shadow-lg focus-within:border-[rgba(var(--accent-rgb),0.5)] focus-within:glow-active transition-all">
            <Terminal size={16} className="text-[var(--text)] opacity-30" />
            <input 
              id="chat-input"
              type="text" 
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder={orbState === 'listening' ? 'Listening for audio link...' : 'Type instructions for Jarvis...'} 
              className="bg-transparent flex-1 text-sm outline-none font-medium text-[var(--text)] placeholder:text-[var(--text)] placeholder:opacity-30" 
              disabled={orbState === 'streaming'}
            />
            {orbState === 'streaming' ? (
              <button 
                id="stop-stream-btn"
                onClick={handleStop}
                className="w-11 h-11 rounded-2xl flex items-center justify-center bg-rose-500/10 text-rose-500 hover:bg-rose-500 hover:text-white transition-all cursor-pointer"
                title="Stop generation"
              >
                <StopCircle size={18} />
              </button>
            ) : (
              <button 
                id="send-btn"
                onClick={() => {
                  if (input) handleSend();
                  else setOrbState(orbState === 'listening' ? 'idle' : 'listening');
                }}
                className={`w-11 h-11 rounded-2xl flex items-center justify-center transition-all cursor-pointer ${
                  orbState === 'listening' 
                    ? 'bg-rose-500 text-white animate-pulse' 
                    : 'bg-[rgba(var(--accent-rgb),0.08)] border border-[rgba(var(--accent-rgb),0.15)] text-[var(--accent)] hover:bg-[var(--accent)] hover:text-white'
                }`}
              >
                {orbState === 'listening' ? <Mic size={18} /> : <ArrowUp size={18} />}
              </button>
            )}
          </div>
        </div>
      </footer>
    </div>
  );
}

function StatMini({ label, value }: { label: string, value: number }) {
  return (
    <div className="flex flex-col items-end">
      <span className="text-[8px] font-black text-[var(--text)] opacity-30 uppercase tracking-[0.2em] leading-none mb-1.5">{label}</span>
      <div className="flex items-center gap-3">
        <div className="w-16 h-1 bg-[var(--border)] rounded-full overflow-hidden">
          <motion.div 
            initial={{ width: 0 }}
            animate={{ width: `${value}%` }}
            className={`h-full ${value > 80 ? 'bg-rose-500' : 'bg-[var(--accent)]'}`}
          />
        </div>
        <span className="text-[10px] font-black text-[var(--text)] opacity-60 min-w-[2.2rem] text-right">{value.toFixed(0)}%</span>
      </div>
    </div>
  );
}
