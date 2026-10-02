# Juvion design system

## Visual direction

Juvion is a warm literary studio for sustained fiction writing. It uses a quiet paper ground, deep wine accents, editorial serif typography for manuscript content, and a compact sans-serif interface. The layout gives the manuscript the most space, with navigation and narrative context kept available at the edges.

## Tokens

- Background: `#fbf9f6`
- Supporting surface: `#f5f3f0`
- Elevated paper: `#ffffff`
- Main ink: `#1b1c1a`
- Secondary ink: `#645d59`
- Accent: `#7b001f`
- Accent hover: `#9e1b32`
- Selection: `#ffdada`
- Border: `#e4e2df`

The only appearance choices are **Juvion Claro** and **Juvion Escuro**. The dark theme uses `#121212` as its off-black background, warm light text, and the same wine accent family.

## Typography

Use a native sans-serif face for controls and navigation. Manuscript content uses an available book serif (`Palatino Linotype`, `Book Antiqua`, or `Georgia`) at a generous reading size and line height.

## Components

- Controls have low visual weight, a 6px radius, and clear hover and focus states.
- Primary actions use wine fill and white labels.
- Panels use surface changes and a 1px divider; shadows are reserved for floating menus and the active manuscript surface.
- The manuscript editor appears as an elevated paper sheet within the studio.

## App layout

The writing workspace has a narrow activity rail, a manuscript outline, the main manuscript, and contextual tools. The layout may collapse panels while keeping the manuscript usable.

`A Obra` is a project-level panel in the activity rail. It keeps the cover, synopsis, series, volume, categories, tags, and current stage alongside the manuscript; the saved cover also represents the project in the works selector.
