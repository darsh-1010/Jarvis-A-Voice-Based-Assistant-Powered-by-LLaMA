'use client';

/**
 * Copyright (c) 2024-2026 Darsh Shah
 * Licensed under the Business Source License 1.1
 */

import React from 'react';
import { motion } from 'framer-motion';
import { Search, Terminal, MessageSquare, Lightbulb, PlayCircle, ShieldCheck } from 'lucide-react';

export default function HelpPage() {
  const commands = [
    { cmd: "Check my schedule", desc: "Syncs with calendars and provides brief summary.", icon: PlayCircle },
    { cmd: "Initialize project Omega", desc: "Starts background processing for preset project specs.", icon: Terminal },
    { cmd: "Analyze surrounding audio", desc: "Uses environmental sensors to identify sound sources.", icon: MessageSquare },
    { cmd: "System status report", desc: "Provides detailed technical health of all subsystems.", icon: ShieldCheck },
    { cmd: "Brainstorm design ideas", desc: "Activates creativity mode for conceptual synthesis.", icon: Lightbulb },
  ];

  const faqs = [
    { q: "How do I update JARVIS?", a: "System updates are handled automatically via the neural backbone. No manual action is required." },
    { q: "Is my voice data private?", a: "All vocal processing occurs locally on your encrypted hardware nodes. No data is sent to external clouds." },
    { q: "Can I connect external IoT?", a: "Yes, use the Integration Hub in the Advanced Settings to pair smart devices." },
  ];

  return (
    <div className="flex-1 p-6 md:p-10 overflow-y-auto max-w-5xl mx-auto w-full scrollbar-hide">
      <header className="flex flex-col md:flex-row md:items-center justify-between gap-6 mb-12">
        <div>
          <h1 className="text-3xl font-extrabold text-[var(--text)] mb-1 tracking-tight font-sans">
            Assistance Center
          </h1>
          <p className="text-sm text-[var(--text)] opacity-40 font-medium">Master your interaction with the JARVIS neural network.</p>
        </div>
        <div className="relative group max-w-sm w-full">
          <Search className="absolute left-4 top-1/2 -translate-y-1/2 text-[var(--text)] opacity-30 group-focus-within:text-[var(--accent)] transition-colors" size={16} />
          <input 
            type="text" 
            placeholder="Search commands..." 
            className="w-full bg-[var(--card-glass)] border border-[var(--border-glass)] rounded-2xl py-2.5 pl-12 pr-6 outline-none focus:border-[var(--accent)] focus:glow-active transition-all text-[var(--text)] placeholder:text-[var(--text)] placeholder:opacity-30 text-sm font-medium"
          />
        </div>
      </header>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-10">
        
        {/* Commands section */}
        <section className="space-y-6">
          <h2 className="text-xs font-black tracking-[0.15em] text-[var(--text)] opacity-40 uppercase">
            Voice Command Library
          </h2>
          <div className="space-y-3">
            {commands.map((item, i) => (
              <motion.div
                key={i}
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: i * 0.08 }}
                className="glass-interactive rounded-2xl p-5 border border-[var(--border-glass)] group cursor-pointer"
              >
                <div className="flex items-center gap-4">
                  <div className="p-3 rounded-xl bg-slate-500/5 text-[var(--text)] opacity-60 group-hover:bg-[var(--accent)] group-hover:text-white group-hover:opacity-100 transition-all duration-300">
                    <item.icon size={18} />
                  </div>
                  <div className="flex-1 text-left">
                    <p className="text-[var(--text)] font-extrabold text-sm mb-0.5 tracking-tight">
                      &quot;{item.cmd}&quot;
                    </p>
                    <p className="text-[var(--text)] opacity-40 text-xs font-medium">{item.desc}</p>
                  </div>
                </div>
              </motion.div>
            ))}
          </div>
        </section>

        {/* FAQs section */}
        <section className="space-y-6">
          <h2 className="text-xs font-black tracking-[0.15em] text-[var(--text)] opacity-40 uppercase">
            System Intelligence FAQ
          </h2>
          <div className="space-y-6">
            {faqs.map((faq, i) => (
              <motion.div
                key={i}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.2 + (i * 0.08) }}
              >
                <h3 className="text-[var(--text)] font-extrabold mb-2 flex items-start gap-2.5 tracking-tight text-sm">
                   <div className="w-1.5 h-1.5 rounded-full bg-[var(--accent)] mt-2 shrink-0 shadow-[0_0_6px_var(--accent)]" />
                   {faq.q}
                </h3>
                <p className="text-[var(--text)] opacity-50 text-sm leading-relaxed pl-5 font-medium">
                  {faq.a}
                </p>
              </motion.div>
            ))}
          </div>
          
          {/* Diagnostic Action Block */}
          <div className="p-6 md:p-8 rounded-[28px] bg-slate-500/5 border border-[var(--border-glass)] space-y-4">
             <h3 className="text-[var(--text)] font-extrabold text-sm tracking-tight">Need Direct Support?</h3>
             <p className="text-[var(--text)] opacity-45 text-xs font-medium leading-relaxed">
               If the system is exhibiting atypical behavior or neural delays, initiate a local diagnostics link.
             </p>
             <button className="w-full py-3 rounded-xl bg-[var(--accent)] hover:bg-[var(--accent)]/80 text-white font-bold text-xs uppercase tracking-widest transition-all shadow-md shadow-[rgba(var(--accent-rgb),0.2)] cursor-pointer">
               Initiate System Diagnostic
             </button>
          </div>
        </section>

      </div>
    </div>
  );
}
