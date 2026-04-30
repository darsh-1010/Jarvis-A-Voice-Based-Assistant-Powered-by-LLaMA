'use client';

import React from 'react';
import { motion } from 'framer-motion';
import { usePathname } from 'next/navigation';

/**
 * PageWrapper component to provide consistent entry/exit animations for all pages.
 * Ported from reference App.tsx PageWrapper.
 */
export function PageWrapper({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  
  return (
    <motion.div
      key={pathname}
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -10 }}
      transition={{ duration: 0.3 }}
      className="flex-1 flex flex-col h-full overflow-hidden"
    >
      {children}
    </motion.div>
  );
}
