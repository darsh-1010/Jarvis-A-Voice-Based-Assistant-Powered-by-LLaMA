'use client';

import React from 'react';
import { motion } from 'framer-motion';
import { Search, Terminal, MessageSquare, Lightbulb, PlayCircle, ShieldCheck } from 'lucide-react';

/**
 * Help Page.
 * Ported from reference AI Studio design.
 */
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
    <div className="flex-1 p-8 md:p-12 overflow-y-auto max-w-5xl mx-auto w-full">
      <header className="flex flex-col md:flex-row md:items-center justify-between gap-6 mb-16">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 mb-1 tracking-tight">Assistance Center</h1>
          <p className="text-sm text-slate-500 font-medium">Master your interaction with the JARVIS neural network.</p>
        </div>
        <div className="relative group max-w-sm w-full">
          <Search className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400 group-hover:text-slate-900 transition-colors" size={16} />
          <input 
            type="text" 
            placeholder="Search commands..." 
            className="w-full bg-white border border-slate-200 rounded-2xl py-2.5 pl-12 pr-6 outline-none focus:border-slate-900 focus:ring-1 focus:ring-slate-900/5 transition-all text-slate-700 placeholder:text-slate-400 text-sm font-medium"
          />
        </div>
      </header>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-12">
        <section>
          <h2 className="text-xs font-bold tracking-[0.1em] text-slate-400 uppercase mb-8">Voice Command Library</h2>
          <div className="space-y-3">
            {commands.map((item, i) => (
              <motion.div
                key={i}
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: i * 0.1 }}
                className="bg-white rounded-2xl p-5 border border-slate-200 shadow-sm hover:border-slate-400 transition-all group cursor-pointer"
              >
                <div className="flex items-center gap-4">
                  <div className="p-3 rounded-xl bg-slate-50 text-slate-400 group-hover:bg-slate-900 group-hover:text-white transition-colors duration-300">
                    <item.icon size={18} />
                  </div>
                  <div className="flex-1 text-left">
                    <p className="text-slate-900 font-bold text-sm mb-0.5 tracking-tight group-hover:text-slate-900 transition-colors">"{item.cmd}"</p>
                    <p className="text-slate-400 text-xs font-medium">{item.desc}</p>
                  </div>
                </div>
              </motion.div>
            ))}
          </div>
        </section>

        <section>
          <h2 className="text-xs font-bold tracking-[0.1em] text-slate-400 uppercase mb-8">System Intelligence FAQ</h2>
          <div className="space-y-6">
            {faqs.map((faq, i) => (
              <motion.div
                key={i}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.5 + (i * 0.1) }}
              >
                <h3 className="text-slate-900 font-bold mb-2 flex items-start gap-2 tracking-tight">
                   <div className="w-1.5 h-1.5 rounded-full bg-slate-400 mt-2 shrink-0" />
                   {faq.q}
                </h3>
                <p className="text-slate-500 text-sm leading-relaxed pl-5 font-medium">
                  {faq.a}
                </p>
              </motion.div>
            ))}
          </div>
          
          <div className="mt-12 p-8 rounded-[32px] bg-slate-50 border border-slate-200">
             <h3 className="text-slate-900 font-bold mb-1 tracking-tight">Need Direct Support?</h3>
             <p className="text-slate-500 text-sm mb-6 font-medium">If the system is exhibiting atypical behavior, initiate a manual diagnostic link.</p>
             <button className="w-full py-3 rounded-xl bg-slate-900 text-white font-bold text-sm hover:bg-slate-800 transition-all shadow-md">
               Connect with Tech Support
             </button>
          </div>
        </section>
      </div>
    </div>
  );
}
