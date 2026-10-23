# VST — official brand and naming standard

Date: 2026-10-23  
Product: Vazão Sovereign Trader (VST)

## Official name

- **Short name / acronym:** VST.
- **Full product name:** Vazão Sovereign Trader.
- Use **VST** as the default visible name in the virtual office, desktop cockpit, mobile cockpit, page titles, compact navigation, and short status labels.
- At the first mention in technical documents, write **VST (Vazão Sovereign Trader)**; subsequent mentions may use VST.
- Keep repository/package/module identifiers stable unless a separate technical migration is explicitly planned. Brand shorthand does not require renaming the GitHub repository or Python paths.

## Virtual-office wordmark

The office header and prototype use a three-column lockup in which each initial is vertically aligned with its corresponding full word:

| Initial | Word |
|---|---|
| **V** | Vazão |
| **S** | Sovereign |
| **T** | Trader |

The VST initials must be visually prominent; the full words sit directly below their corresponding letters, not as an unrelated tagline. The existing VST sigil may remain as a compact mark alongside this lockup.

## Applied surfaces

- README.md: declares the official acronym and naming rules.
- virtual_office/prototype/full_cockpit_shell.html: full cockpit/virtual-office header now renders the aligned V / Vazão, S / Sovereign, T / Trader lockup, with smaller mobile sizing.
- virtual_office/prototype/index.html: standalone visual prototype uses the same lockup.
- Existing primary surfaces already use VST branding following PR #467; this change aligns the virtual-office brand presentation with the more explicit letter-to-word rule.

## Accessibility and responsive behavior

- Mark the purely visual individual glyphs as hidden from assistive technology and expose the complete product name as the lockup's accessible label.
- Keep the compact VST sigil available as a visual mark.
- Reduce wordmark size and spacing on narrow screens; do not make the acronym depend on animation.
- Avoid implying operational status through branding. Demo/connection status must continue to come from the actual backend.

## Scope and safety

This is a branding/documentation change only. It does not alter market feeds, agent activity, engine lifecycle, risk policy, API authorization, execution permissions, or PAPER/REAL gates. The virtual office remains a UI over the authoritative backend; demo mode must not be represented as a live-connected system.
