'use client';

/**
 * Copyright (c) 2024-2026 Darsh Shah
 * Licensed under the Business Source License 1.1
 */

import React from 'react';
import { motion } from 'framer-motion';
import { Cpu, Zap, Radio, Code2 } from 'lucide-react';

export default function AboutPage() {
  const specs = [
    { label: "Neural Engine", value: "V4.2 Quantum-Gate", icon: Cpu },
    { label: "Response Latency", value: "< 12.4ms", icon: Zap },
    { label: "Data Protocols", value: "HEVC, Opus, GSM", icon: Radio },
    { label: "Architecture", value: "Distributed Mesh", icon: Code2 },
  ];

  return (
    <div className="flex-1 p-6 md:p-10 overflow-y-auto max-w-4xl mx-auto w-full scrollbar-hide">
      <motion.div
        initial={{ opacity: 0, y: 15 }}
        animate={{ opacity: 1, y: 0 }}
        className="text-center mb-12"
      >
        <div className="w-16 h-16 bg-[var(--accent)] rounded-3xl mx-auto mb-6 flex items-center justify-center shadow-lg shadow-[rgba(var(--accent-rgb),0.3)]">
           <div className="w-6 h-6 border-4 border-white dark:border-slate-950 rounded-full flex items-center justify-center">
              <div className="w-2 h-2 bg-white dark:bg-slate-950 rounded-full" />
           </div>
        </div>
        <h1 className="text-3xl font-extrabold text-[var(--text)] mb-3 tracking-tight font-sans">
          JARVIS AI <span className="text-xs font-bold text-[var(--accent)] bg-[rgba(var(--accent-rgb),0.08)] px-2.5 py-1 rounded-full border border-[rgba(var(--accent-rgb),0.15)] ml-1.5">v4.2.0</span>
        </h1>
        <p className="text-[var(--text)] opacity-50 text-sm leading-relaxed max-w-xl mx-auto font-medium">
          Built as the ultimate personal digital life assistant, JARVIS utilizes state-of-the-art 
          neural processing to handle complex tasks, environmental control, and information synthesis.
        </p>
      </motion.div>

      {/* Stats specs grid */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-10">
        {specs.map((spec, i) => (
          <motion.div
            key={i}
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ delay: i * 0.08 }}
            className="glass-minimal rounded-2xl p-5 text-center border border-[var(--border-glass)]"
          >
            <div className="flex justify-center text-[var(--accent)] mb-3 opacity-80">
              <spec.icon size={18} />
            </div>
            <p className="text-[var(--text)] font-extrabold text-sm mb-1 tracking-tight">{spec.value}</p>
            <p className="text-[9px] text-[var(--text)] opacity-35 font-black uppercase tracking-widest">{spec.label}</p>
          </motion.div>
        ))}
      </div>

      {/* Philosophy Card */}
      <motion.div
        initial={{ opacity: 0, y: 15 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.3 }}
        className="glass-minimal rounded-[32px] p-8 md:p-10 border border-[var(--border-glass)] relative overflow-hidden"
      >
        <h2 className="text-xl font-extrabold text-[var(--text)] mb-4 tracking-tight font-sans">Development Philosophy</h2>
        <div className="space-y-4 text-[var(--text)] opacity-60 leading-relaxed font-medium text-sm">
          <p>
            The JARVIS project was founded on the principle of &quot;Invisible Assistance.&quot; We believe
            that technology should be most helpful when it is least intrusive. By leveraging 
            predictive modeling and natural language understanding, JARVIS becomes an extension 
            of your own workflow.
          </p>
          <p>
            Our core mission is to bridge the gap between human intent and machine execution, 
            providing a seamless interface for the complex digital landscape of the 21st century.
          </p>
        </div>
      </motion.div>
    </div>
  );
}
