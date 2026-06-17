'use client';

/**
 * Copyright (c) 2024-2026 Darsh Shah
 * Licensed under the Business Source License 1.1
 *
 * Persona Studio — full settings page with:
 *  - Visual tone-card selector
 *  - System prompt textarea editor with debounced auto-save
 *  - Speech rate slider
 *  - Save-confirmation micro-animation
 */
import React, { useCallback, useEffect, useRef, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { BriefcaseBusiness, Smile, Zap, Volume2, Globe, Moon, Sun, Shield, Check } from 'lucide-react';
import { useTheme } from '@/components/ThemeProvider';

interface PersonaPreset {
  id: string;
  label: string;
  description: string;
}

interface Settings {
  persona_custom: string;
  tone: string;
  voice_id: number;
  speech_rate: number;
  sensitivity: string;
  language: string;
  dark_mode: boolean;
}

const TONE_ICONS: Record<string, React.ElementType> = {
  professional: BriefcaseBusiness,
  friendly: Smile,
  sarcastic: Zap,
};

/** Saved-confirmation badge that auto-dismisses */
function SaveBadge({ visible }: { visible: boolean }) {
  return (
    <AnimatePresence>
      {visible && (
        <motion.span
          key="badge"
          initial={{ opacity: 0, scale: 0.8 }}
          animate={{ opacity: 1, scale: 1 }}
          exit={{ opacity: 0, scale: 0.8 }}
          className="inline-flex items-center gap-1 text-emerald-600 text-xs font-bold"
        >
          <Check size={12} />
          Saved
        </motion.span>
      )}
    </AnimatePresence>
  );
}

export default function SettingsPage() {
  const { theme, toggleTheme } = useTheme();
  const [settings, setSettings] = useState<Settings | null>(null);
  const [presets, setPresets] = useState<PersonaPreset[]>([]);
  /** Which field just saved — used to show the micro-badge */
  const [savedField, setSavedField] = useState<string | null>(null);
  const savedTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // ── Fetch initial data ───────────────────────
  useEffect(() => {
    const load = async () => {
      const [settingsRes, presetsRes] = await Promise.all([
        fetch('http://localhost:8000/settings'),
        fetch('http://localhost:8000/settings/personas'),
      ]);
      if (settingsRes.ok) {
        const data = await settingsRes.json();
        setSettings({
          persona_custom: data.persona_custom ?? '',
          tone: data.jarvis_tone ?? data.tone ?? 'professional',
          voice_id: data.voice_id ?? 0,
          speech_rate: data.speech_rate ?? 175,
          sensitivity: data.sensitivity ?? 'High',
          language: data.language ?? 'English (US)',
          dark_mode: data.dark_mode ?? false,
        });
      }
      if (presetsRes.ok) setPresets(await presetsRes.json());
    };
    load();
  }, []);

  // ── Send a setting update to the API ────────
  const postUpdate = useCallback(async (patch: Partial<Settings>, fieldKey: string) => {
    await fetch('http://localhost:8000/settings', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(patch),
    });
    if (savedTimerRef.current) clearTimeout(savedTimerRef.current);
    setSavedField(fieldKey);
    savedTimerRef.current = setTimeout(() => setSavedField(null), 2000);
  }, []);

  // ── Tone card selection ─────────────────────
  const handleToneSelect = useCallback((toneId: string) => {
    if (!settings) return;
    const next = { ...settings, tone: toneId };
    setSettings(next);
    postUpdate({ tone: toneId }, 'tone');
  }, [settings, postUpdate]);

  // ── System prompt editor (debounced 500ms) ──
  const handlePersonaChange = useCallback((value: string) => {
    if (!settings) return;
    setSettings(prev => prev ? { ...prev, persona_custom: value } : prev);
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => {
      postUpdate({ persona_custom: value }, 'persona_custom');
    }, 500);
  }, [settings, postUpdate]);

  // ── Speech rate slider ──────────────────────
  const handleRateChange = useCallback((value: number) => {
    if (!settings) return;
    setSettings(prev => prev ? { ...prev, speech_rate: value } : prev);
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => {
      postUpdate({ speech_rate: value }, 'speech_rate');
    }, 400);
  }, [settings, postUpdate]);

  // ── Voice preview ───────────────────────────
  const handleVoicePreview = useCallback(async () => {
    await fetch('http://localhost:8000/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: 'Give me a brief one-sentence example of how you sound right now.' }),
    });
  }, []);

  if (!settings) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <div className="w-6 h-6 border-2 border-slate-900 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  const rateLabel = settings.speech_rate <= 149 ? 'Slow' : settings.speech_rate <= 174 ? 'Normal' : settings.speech_rate <= 199 ? 'Fast' : 'Very Fast';

  return (
    <div className="flex-1 p-8 md:p-12 overflow-y-auto max-w-4xl mx-auto w-full">
      <header className="mb-10">
        <h1 className="text-2xl font-bold mb-1 tracking-tight">System Configuration</h1>
        <p className="text-sm opacity-50 font-medium">Manage JARVIS core parameters and interaction style.</p>
      </header>

      <div className="space-y-10">

        {/* ── Persona Studio ─────────────────────── */}
        <motion.section initial={{ y: 20, opacity: 0 }} animate={{ y: 0, opacity: 1 }} transition={{ delay: 0 }}>
          <div className="flex items-center justify-between mb-4 px-1">
            <h2 className="text-xs font-bold tracking-[0.1em] opacity-40 uppercase">Persona Studio</h2>
            <SaveBadge visible={savedField === 'tone' || savedField === 'persona_custom'} />
          </div>

          {/* Tone cards */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 mb-4">
            {presets.map(preset => {
              const Icon = TONE_ICONS[preset.id] ?? BriefcaseBusiness;
              const isActive = settings.tone === preset.id;
              return (
                <motion.button
                  id={`tone-${preset.id}`}
                  key={preset.id}
                  whileTap={{ scale: 0.97 }}
                  onClick={() => handleToneSelect(preset.id)}
                  className={`
                    relative text-left p-5 rounded-2xl border-2 transition-all duration-200
                    ${isActive
                      ? 'border-slate-900 bg-slate-900 text-white shadow-lg'
                      : 'border-slate-200 bg-white hover:border-slate-400 text-slate-700'
                    }
                  `}
                >
                  {isActive && (
                    <motion.span
                      layoutId="tone-active-dot"
                      className="absolute top-3 right-3 w-2 h-2 rounded-full bg-emerald-400"
                    />
                  )}
                  <Icon size={20} className="mb-3 opacity-80" />
                  <p className="font-bold text-sm mb-1">{preset.label}</p>
                  <p className={`text-xs leading-snug ${isActive ? 'opacity-60' : 'opacity-40'}`}>
                    {preset.description}
                  </p>
                </motion.button>
              );
            })}
          </div>

          {/* System prompt override */}
          <div className="glass-minimal rounded-2xl p-5">
            <div className="flex items-center justify-between mb-3">
              <p className="text-xs font-bold uppercase tracking-widest opacity-50">
                Custom System Prompt
              </p>
              <p className="text-[10px] opacity-30">Leave empty to use tone preset above</p>
            </div>
            <textarea
              id="persona-textarea"
              rows={4}
              value={settings.persona_custom}
              onChange={e => handlePersonaChange(e.target.value)}
              placeholder="Enter a custom system prompt to fully override the persona..."
              className="w-full bg-transparent resize-none outline-none text-sm font-mono opacity-70 focus:opacity-100 transition-opacity placeholder:opacity-30 placeholder:font-sans"
            />
          </div>
        </motion.section>

        {/* ── Voice Settings ─────────────────────── */}
        <motion.section initial={{ y: 20, opacity: 0 }} animate={{ y: 0, opacity: 1 }} transition={{ delay: 0.1 }}>
          <div className="flex items-center justify-between mb-4 px-1">
            <h2 className="text-xs font-bold tracking-[0.1em] opacity-40 uppercase">Voice & Speech</h2>
            <SaveBadge visible={savedField === 'speech_rate'} />
          </div>

          <div className="glass-minimal rounded-[24px] overflow-hidden">
            {/* Speech rate slider */}
            <div className="p-5 border-b border-slate-500/10">
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-3">
                  <div className="p-2.5 rounded-xl bg-slate-500/10">
                    <Volume2 size={18} />
                  </div>
                  <div>
                    <p className="font-bold text-sm tracking-tight">Speech Rate</p>
                    <p className="text-xs opacity-40 mt-0.5">{rateLabel} — {settings.speech_rate} wpm</p>
                  </div>
                </div>
                <button
                  id="voice-preview-btn"
                  onClick={handleVoicePreview}
                  className="px-4 py-1.5 text-[10px] font-bold uppercase tracking-widest border border-slate-300 rounded-full hover:bg-slate-100 transition-colors"
                >
                  Test Voice
                </button>
              </div>
              <input
                id="speech-rate-slider"
                type="range"
                min={140}
                max={220}
                step={10}
                value={settings.speech_rate}
                onChange={e => handleRateChange(Number(e.target.value))}
                className="w-full accent-slate-900 cursor-pointer"
              />
              <div className="flex justify-between text-[9px] opacity-30 font-bold uppercase tracking-wider mt-1">
                <span>Slow</span>
                <span>Fast</span>
              </div>
            </div>

            {/* Language */}
            <div className="flex items-center justify-between p-5 opacity-60">
              <div className="flex items-center gap-4">
                <div className="p-2.5 rounded-xl bg-slate-500/10">
                  <Globe size={18} />
                </div>
                <p className="font-bold text-sm tracking-tight">Language</p>
              </div>
              <span className="text-xs font-bold opacity-40">{settings.language}</span>
            </div>
          </div>
        </motion.section>

        {/* ── Visual & System ────────────────────── */}
        <motion.section initial={{ y: 20, opacity: 0 }} animate={{ y: 0, opacity: 1 }} transition={{ delay: 0.2 }}>
          <h2 className="text-xs font-bold tracking-[0.1em] opacity-40 uppercase mb-4 px-1">Visual & System</h2>
          <div className="glass-minimal rounded-[24px] overflow-hidden">
            <div
              onClick={toggleTheme}
              className="flex items-center justify-between p-5 hover:bg-slate-500/5 transition-colors cursor-pointer group border-b border-slate-500/10"
            >
              <div className="flex items-center gap-4">
                <div className="p-2.5 rounded-xl bg-slate-500/10 opacity-60 group-hover:opacity-100 transition-opacity">
                  {theme === 'dark' ? <Sun size={18} /> : <Moon size={18} />}
                </div>
                <p className="font-bold text-sm tracking-tight">Dark Mode</p>
              </div>
              <span className="text-xs font-bold opacity-40">{theme === 'dark' ? 'Enabled' : 'Disabled'}</span>
            </div>
            <div className="flex items-center justify-between p-5 opacity-60">
              <div className="flex items-center gap-4">
                <div className="p-2.5 rounded-xl bg-slate-500/10">
                  <Shield size={18} />
                </div>
                <p className="font-bold text-sm tracking-tight">Privacy Mode</p>
              </div>
              <span className="text-xs font-bold opacity-40">Local Context Only</span>
            </div>
          </div>
        </motion.section>

        {/* ── Emergency Overrides ────────────────── */}
        <motion.div
          initial={{ y: 20, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          transition={{ delay: 0.3 }}
          className="p-8 rounded-[24px] bg-red-500/5 border border-red-500/10"
        >
          <h3 className="text-red-500 font-bold mb-1 text-sm">Emergency Overrides</h3>
          <p className="text-red-500/60 text-xs mb-6 font-medium">Reset all neural weights to factory defaults. This action is irreversible.</p>
          <button
            id="factory-reset-btn"
            className="px-6 py-2.5 rounded-xl bg-red-600 text-white text-xs font-bold uppercase tracking-widest hover:bg-red-700 transition-all shadow-sm"
          >
            Initiate Factory Reset
          </button>
        </motion.div>

      </div>
    </div>
  );
}
