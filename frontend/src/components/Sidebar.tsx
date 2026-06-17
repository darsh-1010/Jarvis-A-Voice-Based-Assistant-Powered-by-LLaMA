'use client';

/**
 * Copyright (c) 2024-2026 Darsh Shah
 * Licensed under the Business Source License 1.1
 */

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
 * Redesigned for visual excellence (Glass 2.0 + Sliding Indicator).
 */
export function Sidebar() {
  const pathname = usePathname();
  const { theme, toggleTheme } = useTheme();

  return (
    <motion.div 
      initial={{ x: -20, opacity: 0 }}
      animate={{ x: 0, opacity: 1 }}
      className="w-20 md:w-64 h-[calc(100vh-2rem)] glass-minimal rounded-[32px] flex flex-col py-8 z-50 transition-all duration-300 ml-4 my-4"
    >
      {/* Brand Logo */}
      <div className="px-8 mb-10 flex items-center gap-3">
        <div className="w-8 h-8 rounded-xl bg-[var(--accent)] flex items-center justify-center shadow-lg shadow-[rgba(var(--accent-rgb),0.3)]">
          <div className="w-3 h-3 rounded-full bg-white dark:bg-slate-900 animate-pulse" />
        </div>
        <span className="hidden md:block font-bold text-xl tracking-tighter text-[var(--text)] font-sans">
          JARVIS
        </span>
      </div>

      {/* Navigation Links */}
      <nav className="flex-1 px-4 space-y-2 relative">
        {navItems.map((item) => {
          const isActive = pathname === item.path;
          return (
            <Link key={item.id} href={item.path} className="block">
              <motion.div
                whileTap={{ scale: 0.98 }}
                className={`
                  relative flex items-center gap-3 px-4 py-3 rounded-2xl transition-all duration-200 group cursor-pointer
                  ${isActive ? 'text-[var(--text)] font-semibold' : 'text-[var(--text)] opacity-60 hover:opacity-100'}
                `}
              >
                {/* Sliding indicator background */}
                {isActive && (
                  <motion.div
                    layoutId="active-nav"
                    className="absolute inset-0 bg-[rgba(var(--accent-rgb),0.08)] border border-[rgba(var(--accent-rgb),0.15)] rounded-2xl -z-10"
                    transition={{ type: 'spring', stiffness: 350, damping: 28 }}
                  />
                )}
                
                <item.icon 
                  size={18} 
                  className={`transition-colors duration-200 ${
                    isActive 
                      ? 'text-[var(--accent)]' 
                      : 'text-[var(--text)] opacity-70 group-hover:text-[var(--text)] group-hover:opacity-100'
                  }`} 
                />
                
                <span className="hidden md:block font-medium tracking-tight text-sm">
                  {item.label}
                </span>
              </motion.div>
            </Link>
          );
        })}
      </nav>

      {/* Sidebar Footer */}
      <div className="px-4 mt-auto space-y-4">
        {/* Theme Toggle Switch */}
        <button 
          onClick={toggleTheme}
          className="w-full flex items-center gap-3 px-4 py-3 rounded-2xl transition-all duration-200 opacity-60 hover:opacity-100 hover:bg-[rgba(var(--accent-rgb),0.04)] text-[var(--text)] cursor-pointer"
        >
          <motion.div
            animate={{ rotate: theme === 'dark' ? 180 : 0 }}
            transition={{ type: 'spring', stiffness: 200, damping: 15 }}
            className="text-[var(--accent)]"
          >
            {theme === 'dark' ? <Sun size={18} /> : <Moon size={18} />}
          </motion.div>
          
          <span className="hidden md:block font-medium tracking-tight text-sm">
            {theme === 'dark' ? 'Light Mode' : 'Dark Mode'}
          </span>
        </button>

        {/* Floating guide widget */}
        <div className="hidden md:block p-5 rounded-[20px] bg-slate-500/5 border border-[var(--border-glass)]">
          <p className="text-[9px] font-black opacity-30 uppercase tracking-[0.2em] mb-2 text-[var(--text)]">Help Center</p>
          <p className="text-xs opacity-60 mb-4 leading-relaxed text-[var(--text)]">Need assistance with commands?</p>
          <Link href="/help" className="block">
            <button className="w-full py-2.5 bg-[rgba(var(--accent-rgb),0.08)] border border-[rgba(var(--accent-rgb),0.15)] text-[var(--accent)] text-[10px] font-black tracking-widest rounded-xl hover:bg-[rgba(var(--accent-rgb),0.15)] transition-colors uppercase">
              View Guide
            </button>
          </Link>
        </div>
      </div>
    </motion.div>
  );
}
