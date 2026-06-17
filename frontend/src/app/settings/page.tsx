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
 *  - Premium Glass 2.0 overhaul
 */
import React, { useCallback, useEffect, useRef, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { BriefcaseBusiness, Smile, Zap, Volume2, Globe, Moon, Sun, Shield, Check, Trash2 } from 'lucide-react';
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
          initial={{ opacity: 0, scale: 0.8, x: 5 }}
          animate={{ opacity: 1, scale: 1, x: 0 }}
          exit={{ opacity: 0, scale: 0.8, x: 5 }}
          className="inline-flex items-center gap-1 text-emerald-400 text-xs font-bold"
        >
          <Check size={12} className="stroke-[3px]" />
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
      <div className="flex-1 flex items-center justify-center bg-[var(--bg)]">
        <div className="w-6 h-6 border-2 border-[var(--accent)] border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  const rateLabel = settings.speech_rate <= 149 ? 'Slow' : settings.speech_rate <= 174 ? 'Normal' : settings.speech_rate <= 199 ? 'Fast' : 'Very Fast';

  return (
    <div className="flex-1 p-6 md:p-10 overflow-y-auto max-w-4xl mx-auto w-full bg-transparent scrollbar-hide">
      
      {/* Header */}
      <header className="mb-10">
        <h1 className="text-3xl font-extrabold text-[var(--text)] tracking-tight font-sans">
          System Configuration
        </h1>
        <p className="text-sm text-[var(--text)] opacity-45 mt-1 font-medium">
          Manage JARVIS core parameters, tone presets, and ambient settings profiles.
        </p>
      </header>

      <div className="space-y-8">

        {/* ── Persona Studio ─────────────────────── */}
        <motion.section 
          initial={{ y: 15, opacity: 0 }} 
          animate={{ y: 0, opacity: 1 }}
          className="space-y-4"
        >
          <div className="flex items-center justify-between mb-2 px-1">
            <h2 className="text-xs font-black tracking-[0.15em] text-[var(--text)] opacity-40 uppercase">
              Persona Studio
            </h2>
            <SaveBadge visible={savedField === 'tone' || savedField === 'persona_custom'} />
          </div>

          {/* Tone cards grid */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            {presets.map(preset => {
              const Icon = TONE_ICONS[preset.id] ?? BriefcaseBusiness;
              const isActive = settings.tone === preset.id;
              return (
                <motion.button
                  id={`tone-${preset.id}`}
                  key={preset.id}
                  whileTap={{ scale: 0.98 }}
                  onClick={() => handleToneSelect(preset.id)}
                  className={`
                    relative text-left p-6 rounded-[24px] border transition-all duration-300 cursor-pointer flex flex-col justify-between h-40
                    ${isActive
                      ? 'bg-[var(--accent)]/15 border-[var(--accent)] text-[var(--text)] glow-active'
                      : 'glass-interactive border-[var(--border-glass)] text-[var(--text)]'
                    }
                  `}
                >
                  <div className="flex justify-between items-start w-full">
                    <div className={`
                      p-3 rounded-2xl
                      ${isActive ? 'bg-[var(--accent)]/20 text-[var(--accent)]' : 'bg-slate-500/5 opacity-60'}
                    `}>
                      <Icon size={18} />
                    </div>
                    {isActive && (
                      <motion.span
                        layoutId="tone-active-dot"
                        className="w-2.5 h-2.5 rounded-full bg-emerald-400 shadow-[0_0_8px_rgba(52,211,153,0.8)]"
                      />
                    )}
                  </div>
                  <div>
                    <p className="font-extrabold text-sm tracking-tight mb-1 text-[var(--text)]">{preset.label}</p>
                    <p className="text-[11px] leading-relaxed text-[var(--text)] opacity-50">
                      {preset.description}
                    </p>
                  </div>
                </motion.button>
              );
            })}
          </div>

          {/* Custom System Prompt Area */}
          <div className="glass-minimal rounded-[28px] p-6 space-y-4 border border-[var(--border-glass)]">
            <div className="flex items-center justify-between">
              <p className="text-[10px] font-black uppercase tracking-wider text-[var(--text)] opacity-40">
                Custom System Prompt Override
              </p>
              <p className="text-[9px] text-[var(--text)] opacity-30 font-bold">Leave empty to use active card preset</p>
            </div>
            <textarea
              id="persona-textarea"
              rows={4}
              value={settings.persona_custom}
              onChange={e => handlePersonaChange(e.target.value)}
              placeholder="Enter custom instructions to fully override the assistant's persona..."
              className="w-full bg-transparent resize-none outline-none text-sm font-mono text-[var(--text)] opacity-70 focus:opacity-100 transition-opacity placeholder:opacity-20 placeholder:font-sans leading-relaxed"
            />
          </div>
        </motion.section>

        {/* ── Voice & Speech rate ────────────────── */}
        <motion.section 
          initial={{ y: 15, opacity: 0 }} 
          animate={{ y: 0, opacity: 1 }}
          transition={{ delay: 0.05 }}
          className="space-y-4"
        >
          <div className="flex items-center justify-between mb-2 px-1">
            <h2 className="text-xs font-black tracking-[0.15em] text-[var(--text)] opacity-40 uppercase">
              Voice & Speech Synthesizer
            </h2>
            <SaveBadge visible={savedField === 'speech_rate'} />
          </div>

          <div className="glass-minimal rounded-[28px] overflow-hidden border border-[var(--border-glass)]">
            {/* Slider */}
            <div className="p-6 border-b border-[var(--border-glass)]">
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-4">
                  <div className="p-3 rounded-2xl bg-slate-500/5 text-[var(--accent)] border border-[var(--border-glass)]">
                    <Volume2 size={18} />
                  </div>
                  <div>
                    <p className="font-extrabold text-sm tracking-tight text-[var(--text)]">Speech Speed</p>
                    <p className="text-xs text-[var(--text)] opacity-40 mt-0.5">{rateLabel} — {settings.speech_rate} words/min</p>
                  </div>
                </div>
                <button
                  id="voice-preview-btn"
                  onClick={handleVoicePreview}
                  className="px-5 py-2 text-[10px] font-black uppercase tracking-widest bg-[rgba(var(--accent-rgb),0.08)] border border-[rgba(var(--accent-rgb),0.15)] text-[var(--accent)] rounded-xl hover:bg-[var(--accent)] hover:text-white transition-all cursor-pointer"
                >
                  Test Synth
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
                className="w-full accent-[var(--accent)] cursor-pointer h-1.5 bg-slate-500/10 rounded-full"
              />
              <div className="flex justify-between text-[9px] opacity-30 font-bold uppercase tracking-wider mt-2 text-[var(--text)]">
                <span>Adagio</span>
                <span>Presto</span>
              </div>
            </div>

            {/* Language details */}
            <div className="flex items-center justify-between p-6 bg-slate-500/2">
              <div className="flex items-center gap-4">
                <div className="p-3 rounded-2xl bg-slate-500/5 text-[var(--text)] opacity-60 border border-[var(--border-glass)]">
                  <Globe size={18} />
                </div>
                <p className="font-extrabold text-sm tracking-tight text-[var(--text)]">Language Protocol</p>
              </div>
              <span className="text-xs font-bold text-[var(--accent)] bg-[rgba(var(--accent-rgb),0.08)] px-3 py-1 rounded-full border border-[rgba(var(--accent-rgb),0.15)]">
                {settings.language}
              </span>
            </div>
          </div>
        </motion.section>

        {/* ── System Variables ───────────────────── */}
        <motion.section 
          initial={{ y: 15, opacity: 0 }} 
          animate={{ y: 0, opacity: 1 }}
          transition={{ delay: 0.1 }}
          className="space-y-4"
        >
          <h2 className="text-xs font-black tracking-[0.15em] text-[var(--text)] opacity-40 uppercase mb-2 px-1">
            Visual & System Configuration
          </h2>
          <div className="glass-minimal rounded-[28px] overflow-hidden border border-[var(--border-glass)]">
            <div
              onClick={toggleTheme}
              className="flex items-center justify-between p-6 hover:bg-slate-500/5 transition-colors cursor-pointer group border-b border-[var(--border-glass)]"
            >
              <div className="flex items-center gap-4">
                <div className="p-3 rounded-2xl bg-slate-500/5 text-[var(--accent)] border border-[var(--border-glass)]">
                  {theme === 'dark' ? <Sun size={18} /> : <Moon size={18} />}
                </div>
                <p className="font-extrabold text-sm tracking-tight text-[var(--text)]">Dark Interface</p>
              </div>
              <span className="text-xs font-bold text-[var(--text)] opacity-50">{theme === 'dark' ? 'Enabled' : 'Disabled'}</span>
            </div>
            
            <div className="flex items-center justify-between p-6">
              <div className="flex items-center gap-4">
                <div className="p-3 rounded-2xl bg-slate-500/5 text-[var(--text)] opacity-60 border border-[var(--border-glass)]">
                  <Shield size={18} />
                </div>
                <p className="font-extrabold text-sm tracking-tight text-[var(--text)]">Data Guardrails</p>
              </div>
              <span className="text-xs font-bold text-emerald-400 bg-emerald-500/10 px-3 py-1 rounded-full border border-emerald-500/20">
                Active Local Sandboxing
              </span>
            </div>
          </div>
        </motion.section>

        {/* ── Emergency Overrides ────────────────── */}
        <motion.div
          initial={{ y: 15, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          transition={{ delay: 0.15 }}
          className="p-6 md:p-8 rounded-[28px] bg-rose-500/5 border border-rose-500/15 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-6"
        >
          <div className="space-y-1">
            <h3 className="text-rose-500 font-extrabold text-sm tracking-tight">Factory Resets</h3>
            <p className="text-rose-500/60 text-xs font-medium leading-relaxed max-w-lg">
              Revert all local dynamic configurations, tone preferences, custom prompts, and rate parameters back to factory values.
            </p>
          </div>
          <button
            id="factory-reset-btn"
            className="flex items-center justify-center gap-2 px-6 py-3.5 rounded-2xl bg-rose-600/10 border border-rose-500/20 text-rose-500 hover:bg-rose-600 hover:text-white text-xs font-black tracking-widest uppercase transition-all shadow-sm cursor-pointer whitespace-nowrap"
          >
            <Trash2 size={14} />
            <span>Reset Profile</span>
          </button>
        </motion.div>

      </div>
    </div>
  );
}
