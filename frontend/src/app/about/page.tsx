'use client';

import React from 'react';
import { motion } from 'framer-motion';
import { Cpu, Zap, Radio, Code2 } from 'lucide-react';

/**
 * About Page.
 * Ported from reference AI Studio design.
 */
export default function AboutPage() {
  const specs = [
    { label: "Neural Engine", value: "V4.2 Quantum-Gate", icon: Cpu },
    { label: "Response Latency", value: "< 12.4ms", icon: Zap },
    { label: "Data Protocols", value: "HEVC, Opus, GSM", icon: Radio },
    { label: "Architecture", value: "Distributed Mesh", icon: Code2 },
  ];

  return (
    <div className="flex-1 p-8 md:p-12 overflow-y-auto max-w-4xl mx-auto w-full">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="text-center mb-16"
      >
        <div className="w-16 h-16 bg-slate-900 rounded-2xl mx-auto mb-8 flex items-center justify-center">
           <div className="w-6 h-6 border-4 border-white rounded-full flex items-center justify-center">
              <div className="w-2 h-2 bg-white rounded-full" />
           </div>
        </div>
        <h1 className="text-3xl font-bold text-slate-900 mb-4 tracking-tight">JARVIS AI v4.2.0</h1>
        <p className="text-slate-500 text-base leading-relaxed max-w-2xl mx-auto font-medium">
          Built as the ultimate personal digital life assistant, JARVIS utilizes state-of-the-art 
          neural processing to handle complex tasks, environmental control, and information synthesis.
        </p>
      </motion.div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-16">
        {specs.map((spec, i) => (
          <motion.div
            key={i}
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ delay: i * 0.1 }}
            className="bg-white rounded-2xl p-6 text-center border border-slate-200 shadow-sm"
          >
            <div className="flex justify-center text-slate-400 mb-4">
              <spec.icon size={20} />
            </div>
            <p className="text-slate-900 font-bold mb-1">{spec.value}</p>
            <p className="text-[10px] text-slate-400 font-bold uppercase tracking-widest">{spec.label}</p>
          </motion.div>
        ))}
      </div>

      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.5 }}
        className="bg-white rounded-[40px] p-10 border border-slate-200 shadow-sm relative overflow-hidden"
      >
        <h2 className="text-2xl font-bold text-slate-900 mb-6 tracking-tight">Development Philosophy</h2>
        <div className="space-y-6 text-slate-600 leading-relaxed font-medium text-sm">
          <p>
            The JARVIS project was founded on the principle of "Invisible Assistance." We believe
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

