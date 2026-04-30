'use client';

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

/**
 * Task Progress Page.
 * Ported from reference AI Studio design.
 */
export default function TaskProgressPage() {
  return (
    <div className="flex-1 p-8 md:p-12 overflow-y-auto max-w-7xl mx-auto w-full">
      <header className="mb-10">
        <h1 className="text-2xl font-bold text-slate-900 mb-1 tracking-tight">Active Processes</h1>
        <p className="text-sm text-slate-500 font-medium">Monitoring real-time background operations.</p>
      </header>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {activeTasks.map((task, i) => (
          <motion.div
            key={task.id}
            initial={{ y: 20, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            transition={{ delay: i * 0.1 }}
            className="bg-white rounded-[24px] p-6 border border-slate-200 shadow-sm group hover:border-slate-300 transition-all duration-300"
          >
            <div className="flex items-start justify-between mb-8">
              <div className="p-3 rounded-xl bg-slate-50 text-slate-400 group-hover:bg-slate-900 group-hover:text-white transition-colors duration-500">
                <task.icon size={20} />
              </div>
              <span className="text-[10px] font-bold tracking-widest text-slate-400 uppercase px-3 py-1 rounded-full border border-slate-100">
                {task.type}
              </span>
            </div>

            <h3 className="text-lg font-bold text-slate-900 mb-1 tracking-tight">{task.name}</h3>
            <div className="flex items-center gap-2 text-slate-400 text-xs mb-6 font-medium">
              <Clock size={12} />
              <span>{task.time}</span>
            </div>

            <div className="space-y-3">
              <div className="flex justify-between items-end">
                <span className="text-xs font-bold text-slate-900">{task.progress}%</span>
                <span className="text-[10px] text-slate-400 font-bold uppercase tracking-tighter">Healthy</span>
              </div>
              <div className="h-2 w-full bg-slate-100 rounded-full overflow-hidden">
                <motion.div 
                  initial={{ width: 0 }}
                  animate={{ width: `${task.progress}%` }}
                  transition={{ duration: 1, delay: 0.5 + (i * 0.1) }}
                  className={`h-full rounded-full ${task.progress === 100 ? 'bg-emerald-500' : 'bg-slate-900'}`}
                />
              </div>
            </div>
          </motion.div>
        ))}
        
        {/* Analytics Card */}
        <motion.div
          initial={{ scale: 0.98, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          transition={{ delay: 0.6 }}
          className="lg:col-span-3 bg-slate-900 rounded-[32px] p-8 mt-4 relative overflow-hidden"
        >
          <div className="flex flex-col md:flex-row gap-12 items-center justify-between relative z-10">
            <div>
              <h2 className="text-xl font-bold text-white mb-2 tracking-tight">Total System Output</h2>
              <p className="text-slate-400 text-sm max-w-sm font-medium">JARVIS is currently processing 4.2 petabytes of data across distributed nodes.</p>
              <div className="flex gap-8 mt-8">
                <div>
                  <p className="text-2xl font-bold text-white mb-0.5">99.9%</p>
                  <p className="text-[10px] uppercase tracking-widest font-bold text-slate-500">Uptime</p>
                </div>
                <div>
                  <p className="text-2xl font-bold text-white mb-0.5">12ms</p>
                  <p className="text-[10px] uppercase tracking-widest font-bold text-slate-500">Latency</p>
                </div>
                <div>
                  <p className="text-2xl font-bold text-white mb-0.5">2.4k</p>
                  <p className="text-[10px] uppercase tracking-widest font-bold text-slate-500">Ops/s</p>
                </div>
              </div>
            </div>
            
            <div className="flex gap-2 items-end h-32">
              {[40, 70, 45, 90, 65, 80, 50, 40, 60, 85, 30, 20].map((h, i) => (
                <motion.div
                  key={i}
                  initial={{ height: 0 }}
                  animate={{ height: `${h}%` }}
                  transition={{ duration: 0.8, delay: 1 + (i * 0.05), repeat: Infinity, repeatType: 'reverse' }}
                  className="w-2 md:w-2.5 bg-white/20 rounded-t-sm"
                />
              ))}
            </div>
          </div>
          {/* Subtle background flair */}
          <div className="absolute top-0 right-0 w-32 h-32 bg-white/5 rounded-full -mr-16 -mt-16" />
        </motion.div>
      </div>
    </div>
  );
}
