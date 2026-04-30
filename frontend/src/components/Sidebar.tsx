'use client';

import React from 'react';
import { motion } from 'framer-motion';
import { Mic, Settings, HelpCircle, Info, CheckCircle2, Moon, Sun } from 'lucide-react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useTheme } from './ThemeProvider';

/**
 * Navigation item configuration
 */
const navItems = [
  { id: 'dashboard', icon: Mic, label: 'Assistant', path: '/' },
  { id: 'tasks', icon: CheckCircle2, label: 'Tasks', path: '/tasks' },
  { id: 'settings', icon: Settings, label: 'Settings', path: '/settings' },
  { id: 'about', icon: Info, label: 'About', path: '/about' },
  { id: 'help', icon: HelpCircle, label: 'Help', path: '/help' },
];

/**
 * Sidebar component for the global navigation layout.
 * Adapted from reference AI Studio design.
 */
export function Sidebar() {
  const pathname = usePathname();
  const { theme, toggleTheme } = useTheme();

  return (
    <motion.div 
      initial={{ x: -20, opacity: 0 }}
      animate={{ x: 0, opacity: 1 }}
      className="w-20 md:w-64 h-full glass-minimal flex flex-col py-8 z-50 transition-all duration-300"
    >
      <div className="px-8 mb-10 flex items-center gap-3">
        <div className="w-8 h-8 rounded-lg bg-slate-900 flex items-center justify-center">
          <div className="w-3 h-3 rounded-full bg-white" />
        </div>
        <span className="hidden md:block font-bold text-xl tracking-tight">JARVIS</span>
      </div>

      <nav className="flex-1 px-4 space-y-1">
        {navItems.map((item) => {
          const isActive = pathname === item.path;
          return (
            <Link key={item.id} href={item.path}>
              <motion.div
                whileTap={{ scale: 0.98 }}
                className={`
                  relative flex items-center gap-3 px-4 py-3 rounded-xl transition-all duration-200 group
                  ${isActive ? 'bg-slate-500/10' : 'opacity-60 hover:opacity-100 hover:bg-slate-500/5'}
                `}
              >
                <item.icon size={18} className={isActive ? 'opacity-100' : 'opacity-60 group-hover:opacity-100'} />
                <span className={`hidden md:block font-medium tracking-tight ${isActive ? 'opacity-100' : 'opacity-80'}`}>
                  {item.label}
                </span>
              </motion.div>
            </Link>
          );
        })}
      </nav>

      <div className="px-4 mt-auto space-y-4">
        {/* Theme Toggle */}
        <button 
          onClick={toggleTheme}
          className="w-full flex items-center gap-3 px-4 py-3 rounded-xl transition-all duration-200 opacity-60 hover:opacity-100 hover:bg-slate-500/5"
        >
          {theme === 'dark' ? <Sun size={18} /> : <Moon size={18} />}
          <span className="hidden md:block font-medium tracking-tight">
            {theme === 'dark' ? 'Light Mode' : 'Dark Mode'}
          </span>
        </button>

        <div className="hidden md:block p-5 rounded-2xl bg-slate-500/5 border border-slate-500/10">
          <p className="text-[10px] font-bold opacity-30 uppercase tracking-widest mb-2">Help Center</p>
          <p className="text-sm opacity-60 mb-3 leading-snug">Need assistance with commands?</p>
          <Link href="/help">
            <button className="w-full py-2 bg-white/10 border border-slate-500/10 text-xs font-bold rounded-lg hover:bg-white/20 transition-colors">
              VIEW GUIDE
            </button>
          </Link>
        </div>
      </div>
    </motion.div>
  );
}

