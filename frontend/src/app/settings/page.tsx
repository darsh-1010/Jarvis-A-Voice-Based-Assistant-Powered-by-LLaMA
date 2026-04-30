'use client';

import React, { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import { User, Shield, Sliders, Globe, Moon, Sun, ChevronRight, Volume2 } from 'lucide-react';
import { useTheme } from '@/components/ThemeProvider';

interface Settings {
  persona: string;
  tone: string;
  voice_id: number;
  speech_rate: number;
  sensitivity: string;
  language: string;
  dark_mode: boolean;
}

export default function SettingsPage() {
  const { theme, toggleTheme } = useTheme();
  const [settings, setSettings] = useState<Settings | null>(null);

  useEffect(() => {
    const fetchSettings = async () => {
      const res = await fetch('http://localhost:8000/settings');
      if (res.ok) {
        const data = await res.json();
        setSettings(data);
      }
    };
    fetchSettings();
  }, []);

  const updateSetting = async (key: keyof Settings, value: any) => {
    if (!settings) return;
    const newSettings = { ...settings, [key]: value };
    setSettings(newSettings);

    await fetch('http://localhost:8000/settings', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ [key]: value }),
    });
  };

  if (!settings) return (
    <div className="flex-1 flex items-center justify-center">
      <div className="w-6 h-6 border-2 border-slate-900 border-t-transparent rounded-full animate-spin" />
    </div>
  );

  const sections = [
    {
      title: "Assistant Preferences",
      items: [
        { 
          label: "Voice Personality", 
          value: settings.tone.charAt(0).toUpperCase() + settings.tone.slice(1), 
          icon: User,
          onClick: () => {
            const tones = ['professional', 'friendly', 'sarcastic'];
            const next = tones[(tones.indexOf(settings.tone) + 1) % tones.length];
            updateSetting('tone', next);
          }
        },
        { 
          label: "Speech Rate", 
          value: settings.speech_rate.toString(), 
          icon: Volume2,
          onClick: () => {
            const rates = [150, 175, 200];
            const next = rates[(rates.indexOf(settings.speech_rate) + 1) % rates.length];
            updateSetting('speech_rate', next);
          }
        },
        { label: "Language", value: settings.language, icon: Globe },
      ]
    },
    {
      title: "Visual & System",
      items: [
        { 
          label: "Dark Mode", 
          value: theme === 'dark' ? 'Enabled' : 'Disabled', 
          icon: theme === 'dark' ? Moon : Sun,
          onClick: toggleTheme
        },
        { label: "Privacy Mode", value: "Local Context Only", icon: Shield },
      ]
    }
  ];

  return (
    <div className="flex-1 p-8 md:p-12 overflow-y-auto max-w-4xl mx-auto w-full">
      <header className="mb-10">
        <h1 className="text-2xl font-bold mb-1 tracking-tight">System Configuration</h1>
        <p className="text-sm opacity-50 font-medium">Manage JARVIS core parameters and user interaction settings.</p>
      </header>

      <div className="space-y-10">
        {sections.map((section, idx) => (
          <motion.section 
            key={section.title}
            initial={{ y: 20, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            transition={{ delay: idx * 0.1 }}
          >
            <h2 className="text-xs font-bold tracking-[0.1em] opacity-40 uppercase mb-4 px-1">
              {section.title}
            </h2>
            <div className="glass-minimal rounded-[24px] overflow-hidden">
              {section.items.map((item, i) => (
                <div 
                  key={item.label}
                  onClick={item.onClick}
                  className={`
                    flex items-center justify-between p-5 hover:bg-slate-500/5 transition-colors cursor-pointer group
                    ${i !== section.items.length - 1 ? 'border-b border-slate-500/10' : ''}
                  `}
                >
                  <div className="flex items-center gap-4">
                    <div className="p-2.5 rounded-xl bg-slate-500/10 opacity-60 group-hover:opacity-100 transition-opacity">
                      <item.icon size={18} />
                    </div>
                    <div>
                      <p className="font-bold text-sm tracking-tight">{item.label}</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-3">
                    <span className="text-xs font-bold opacity-40">{item.value}</span>
                    <div className="opacity-20 group-hover:opacity-100 transition-opacity">
                       <ChevronRight size={14} />
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </motion.section>
        ))}

        <motion.div 
          initial={{ y: 20, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          transition={{ delay: 0.4 }}
          className="p-8 rounded-[24px] bg-red-500/5 border border-red-500/10"
        >
          <h3 className="text-red-500 font-bold mb-1 text-sm">Emergency Overrides</h3>
          <p className="text-red-500/60 text-xs mb-6 font-medium">Reset all neural weights to factory defaults. This action is irreversible.</p>
          <button className="px-6 py-2.5 rounded-xl bg-red-600 text-white text-xs font-bold uppercase tracking-widest hover:bg-red-700 transition-all shadow-sm">
            Initiate Factory Reset
          </button>
        </motion.div>
      </div>
    </div>
  );
}


