'use client';

/**
 * Copyright (c) 2024-2026 Darsh Shah
 * Licensed under the Business Source License 1.1
 */

import React from 'react';
import { motion } from 'framer-motion';
import { Cpu, Database, Globe, Zap, Search, Clock } from 'lucide-react';

const activeTasks = [
  { id: 1, name: "Neural Link Aggregation", progress: 78, type: "Core", icon: Cpu, time: "2m remaining" },
  { id: 2, name: "Global Traffic Analysis", progress: 45, type: "Network", icon: Globe, time: "12m remaining" },
  { id: 3, name: "Data Encryption Sync", progress: 100, type: "Security", icon: Zap, time: "Completed" },
  { id: 4, name: "Sub-processing Query", progress: 15, type: "Storage", icon: Database, time: "45s remaining" },
  { id: 5, name: "Search Engine Crawling", progress: 62, type: "Web", icon: Search, time: "5m remaining" },
];

export default function TaskProgressPage() {
  return (
    <div className="flex-1 p-6 md:p-10 overflow-y-auto max-w-7xl mx-auto w-full scrollbar-hide">
      <header className="mb-10">
        <h1 className="text-3xl font-extrabold text-[var(--text)] mb-1 tracking-tight font-sans">
          Active Processes
        </h1>
        <p className="text-sm text-[var(--text)] opacity-40 font-medium">Monitoring real-time background operations.</p>
      </header>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {activeTasks.map((task, i) => (
          <motion.div
            key={task.id}
            initial={{ y: 15, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            transition={{ delay: i * 0.08 }}
            className="glass-minimal rounded-[28px] p-6 border border-[var(--border-glass)] group hover:border-[rgba(var(--accent-rgb),0.3)] transition-all duration-300 flex flex-col justify-between"
          >
            <div>
              <div className="flex items-start justify-between mb-8">
                <div className="p-3 rounded-2xl bg-slate-500/5 text-[var(--text)] opacity-60 group-hover:bg-[var(--accent)] group-hover:text-white group-hover:opacity-100 transition-all duration-300">
                  <task.icon size={18} />
                </div>
                <span className="text-[9px] font-black tracking-widest text-[var(--accent)] bg-[rgba(var(--accent-rgb),0.08)] border border-[rgba(var(--accent-rgb),0.15)] uppercase px-3 py-1 rounded-full">
                  {task.type}
                </span>
              </div>

              <h3 className="text-base font-extrabold text-[var(--text)] mb-1.5 tracking-tight font-sans">{task.name}</h3>
              <div className="flex items-center gap-1.5 text-[var(--text)] opacity-40 text-xs mb-6 font-medium">
                <Clock size={12} />
                <span>{task.time}</span>
              </div>
            </div>

            <div className="space-y-2.5">
              <div className="flex justify-between items-end">
                <span className="text-xs font-black text-[var(--text)]">{task.progress}%</span>
                <span className="text-[9px] text-[var(--text)] opacity-35 font-black uppercase tracking-widest">Active</span>
              </div>
              <div className="h-1.5 w-full bg-slate-500/10 rounded-full overflow-hidden">
                <motion.div 
                  initial={{ width: 0 }}
                  animate={{ width: `${task.progress}%` }}
                  transition={{ duration: 1, delay: 0.3 + (i * 0.08) }}
                  className={`h-full rounded-full ${task.progress === 100 ? 'bg-emerald-400 shadow-[0_0_6px_rgba(52,211,153,0.5)]' : 'bg-[var(--accent)]'}`}
                />
              </div>
            </div>
          </motion.div>
        ))}
        
        {/* Total System Output Banner */}
        <motion.div
          initial={{ scale: 0.98, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          transition={{ delay: 0.4 }}
          className="lg:col-span-3 glass-minimal rounded-[32px] p-8 border border-[var(--border-glass)] relative overflow-hidden"
        >
          <div className="flex flex-col md:flex-row gap-10 items-center justify-between relative z-10">
            <div className="space-y-4">
              <div>
                <h2 className="text-xl font-extrabold text-[var(--text)] mb-2 tracking-tight font-sans">Total System Output</h2>
                <p className="text-[var(--text)] opacity-45 text-xs max-w-md leading-relaxed font-medium">JARVIS is currently processing 4.2 petabytes of data across distributed local hardware mesh nodes.</p>
              </div>
              <div className="flex gap-8">
                <div>
                  <p className="text-2xl font-black text-[var(--text)] tracking-tight">99.9%</p>
                  <p className="text-[8px] uppercase tracking-[0.2em] font-black text-[var(--text)] opacity-30 mt-1">Uptime</p>
                </div>
                <div>
                  <p className="text-2xl font-black text-[var(--text)] tracking-tight">12ms</p>
                  <p className="text-[8px] uppercase tracking-[0.2em] font-black text-[var(--text)] opacity-30 mt-1">Latency</p>
                </div>
                <div>
                  <p className="text-2xl font-black text-[var(--text)] tracking-tight">2.4k</p>
                  <p className="text-[8px] uppercase tracking-[0.2em] font-black text-[var(--text)] opacity-30 mt-1">Ops/s</p>
                </div>
              </div>
            </div>
            
            {/* Visualizer bars representing data traffic */}
            <div className="flex gap-1.5 items-end h-28">
              {[40, 70, 45, 90, 65, 80, 50, 40, 60, 85, 30, 20].map((h, i) => (
                <motion.div
                  key={i}
                  initial={{ height: 0 }}
                  animate={{ height: `${h}%` }}
                  transition={{ duration: 1.2, delay: i * 0.05, repeat: Infinity, repeatType: 'reverse' }}
                  className="w-2 rounded-t-sm bg-gradient-to-t from-[var(--accent)]/10 to-[var(--accent)]/60"
                />
              ))}
            </div>
          </div>
        </motion.div>
      </div>
    </div>
  );
}
