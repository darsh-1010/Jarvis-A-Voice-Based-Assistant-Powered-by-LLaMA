/**
 * Copyright (c) 2024-2026 Darsh Shah
 * Licensed under the Business Source License 1.1
 */
'use client';

import React, { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Mic, Settings, Shield, Activity, List, Terminal, MessageSquare } from 'lucide-react';

interface Stats {
  cpu_percent: number;
  ram_percent: number;
  disk_usage: number;
}

/**
 * Voice Assistant HUD.
 * Redesigned to focus on ambient voice interaction rather than a chat interface.
 */
export default function AssistantDashboard() {
  const [messages, setMessages] = useState<{ role: 'user' | 'assistant', text: string }[]>([]);
  const [input, setInput] = useState('');
  const [orbState, setOrbState] = useState<'idle' | 'listening' | 'thinking' | 'error'>('idle');
  const [stats, setStats] = useState<Stats>({ cpu_percent: 0, ram_percent: 0, disk_usage: 0 });
  const [isApiOnline, setIsApiOnline] = useState(true);
  const scrollRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to latest "caption"
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages]);

  // Fetch system stats periodically
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
      } catch (err) {
        setIsApiOnline(false);
      }
    }, 2000);
    return () => clearInterval(interval);
  }, []);

  /**
   * Handle sending a message to the AI
   */
  const handleSend = async () => {
    if (!input.trim()) return;
    const userMsg = input;
    setInput('');
    setMessages(prev => [...prev, { role: 'user', text: userMsg }]);
    setOrbState('thinking');
    
    try {
      const res = await fetch('http://localhost:8000/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: userMsg }),
      });
      const data = await res.json();
      setMessages(prev => [...prev, { role: 'assistant', text: data.response }]);
      setOrbState('idle');
    } catch (err) {
      setOrbState('error');
      setMessages(prev => [...prev, { role: 'assistant', text: "Neural link lost. Attempting reconnection..." }]);
      setTimeout(() => setOrbState('idle'), 3000);
    }
  };

  return (
    <div className="flex-1 flex flex-col p-8 md:p-12 min-w-0 h-full relative overflow-hidden">
      
      {/* Background Ambient Glow */}
      <div className="absolute inset-0 pointer-events-none overflow-hidden">
        <motion.div 
          animate={{ 
            scale: orbState === 'thinking' ? [1, 1.2, 1] : 1,
            opacity: orbState === 'listening' ? 0.05 : 0 
          }}
          transition={{ duration: 2, repeat: Infinity }}
          className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[800px] h-[800px] bg-slate-400 rounded-full blur-[120px]" 
        />
      </div>

      <header className="mb-8 flex justify-between items-start z-10">
        <div>
          <h1 className="text-3xl font-bold text-slate-900 tracking-tighter">Jarvis</h1>
          <div className="flex items-center gap-2 mt-1">
            <div className={`w-1.5 h-1.5 rounded-full ${isApiOnline ? 'bg-emerald-500 animate-pulse' : 'bg-red-500'}`} />
            <p className="text-[10px] text-slate-400 font-bold uppercase tracking-widest">
              {isApiOnline ? 'Neural Link Active' : 'Link Offline'}
            </p>
          </div>
        </div>
        
        <div className="hidden lg:flex gap-8">
          <StatMini label="Neural Load" value={stats.cpu_percent} />
          <StatMini label="Synaptic RAM" value={stats.ram_percent} />
        </div>
      </header>

      {/* Main Voice Assistant View */}
      <div className="flex-1 flex flex-col items-center justify-center z-10 relative">
        
        {/* Central Visualizer Hub */}
        <div className="relative mb-24">
           {/* Outer Pulsing Rings */}
           {orbState === 'listening' && (
             <motion.div 
               initial={{ scale: 0.8, opacity: 0 }}
               animate={{ scale: 1.5, opacity: 0.1 }}
               transition={{ duration: 1.5, repeat: Infinity }}
               className="absolute inset-0 border-2 border-slate-900 rounded-full"
             />
           )}

           <div className="flex items-end gap-3 h-24 relative">
            {[4, 12, 24, 18, 8, 14, 10].map((h, i) => (
              <motion.div
                key={i}
                animate={orbState === 'thinking' || orbState === 'listening' ? { 
                  height: [`${h * 2}px`, `${h * 4}px`, `${h * 2}px`] 
                } : { height: [`${h}px`] }}
                transition={{ 
                  duration: orbState === 'thinking' ? 0.6 : 1.2, 
                  repeat: Infinity, 
                  delay: i * 0.08 
                }}
                className={`w-2.5 rounded-full transition-colors duration-500 ${
                  orbState === 'error' ? 'bg-red-500' : 
                  orbState === 'thinking' ? 'bg-slate-900' : 
                  'bg-slate-200'
                }`}
              />
            ))}
          </div>
        </div>

        {/* Ambient Caption Stream (Instead of Chat Bubbles) */}
        <div 
          ref={scrollRef}
          className="w-full max-w-2xl h-32 overflow-y-auto scrollbar-hide flex flex-col items-center text-center px-6"
        >
          <AnimatePresence mode="wait">
            {messages.length === 0 ? (
              <motion.p 
                key="waiting"
                initial={{ opacity: 0 }}
                animate={{ opacity: 0.3 }}
                className="text-xl md:text-2xl font-light text-slate-400 tracking-tight"
              >
                "Waiting for instruction..."
              </motion.p>
            ) : (
              <motion.div 
                key={messages.length}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                className="space-y-4"
              >
                {/* User query (Small, subtle) */}
                {messages[messages.length - 1].role === 'user' && (
                  <p className="text-sm font-bold text-slate-300 uppercase tracking-widest">
                    {messages[messages.length - 1].text}
                  </p>
                )}
                {/* Assistant response (Large, primary) */}
                {messages[messages.length - 1].role === 'assistant' && (
                  <p className="text-2xl md:text-3xl font-light text-slate-900 leading-tight">
                    {messages[messages.length - 1].text}
                  </p>
                )}
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>

      {/* Footer Interface */}
      <div className="mt-auto z-10">
        <div className="flex flex-col items-center gap-8">
          
          {/* Action Chips */}
          <div className="flex gap-3 overflow-x-auto pb-2 scrollbar-hide w-full justify-center">
            {[
              { label: 'Check Schedule', icon: List },
              { label: 'System Logs', icon: Activity },
              { label: 'Security', icon: Shield }
            ].map((action) => (
              <button
                key={action.label}
                className="flex items-center gap-2 px-6 py-2.5 bg-white border border-slate-200 rounded-full text-[10px] font-bold text-slate-500 hover:text-slate-900 hover:border-slate-400 transition-all shadow-sm"
              >
                <action.icon size={14} />
                <span className="uppercase tracking-widest">{action.label}</span>
              </button>
            ))}
          </div>

          {/* New Voice-Centric Input Bar */}
          <div className="w-full max-w-xl flex items-center gap-4 bg-white/50 backdrop-blur-md p-2 pl-6 rounded-full border border-slate-200 shadow-minimal focus-within:border-slate-900 transition-all">
            <input 
              type="text" 
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleSend()}
              placeholder={orbState === 'listening' ? "Listening..." : "Type or speak a command..."} 
              className="bg-transparent flex-1 text-sm outline-none font-medium text-slate-700 placeholder:text-slate-400" 
            />
            <button 
              onClick={() => {
                if (input) handleSend();
                else setOrbState(orbState === 'listening' ? 'idle' : 'listening');
              }}
              className={`w-12 h-12 rounded-full flex items-center justify-center transition-all ${
                orbState === 'listening' ? 'bg-slate-900 text-white animate-pulse' : 'bg-slate-100 text-slate-400 hover:bg-slate-200 hover:text-slate-900'
              }`}
            >
              {orbState === 'listening' ? <Mic size={20} /> : <MessageSquare size={20} />}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

function StatMini({ label, value }: { label: string, value: number }) {
  return (
    <div className="flex flex-col items-end">
      <span className="text-[9px] font-black text-slate-300 uppercase tracking-[0.2em] leading-none mb-2">{label}</span>
      <div className="flex items-center gap-3">
        <div className="w-12 h-1 bg-slate-100 rounded-full overflow-hidden">
          <motion.div 
            initial={{ width: 0 }}
            animate={{ width: `${value}%` }}
            className={`h-full ${value > 80 ? 'bg-red-500' : 'bg-slate-900'}`}
          />
        </div>
        <span className="text-[10px] font-black text-slate-900 min-w-[2rem] text-right">{value.toFixed(0)}%</span>
      </div>
    </div>
  );
}


