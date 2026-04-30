# Changelog

All notable changes to this project will be documented in this file.

## [2026-04-28]
### Added
- New **AI Studio** minimalist frontend design.
- Global `Sidebar` component for improved navigation.
- Dedicated `Tasks` page for monitoring background processes.
- Dedicated `Help` page with voice command library and FAQ.
- `PageWrapper` component for smooth motion transitions between pages.
- Tailwind 4 design system with custom theme tokens (`globals.css`).

### Changed
- Replaced "Zenith" dark-mode HUD with a professional light-mode dashboard.
- Updated `layout.tsx` to support the new sidebar-based multi-page architecture.
- Integrated existing backend logic (Chat, System Stats) into the new dashboard UI.
- Switched from "VoiceOrb" 3D visualization to a minimalist bar-style visualizer.

### Fixed
- Improved frontend navigation state detection using `usePathname`.
- Corrected Tailwind 4 utility definitions for better performance.
