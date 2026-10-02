# Paper Options Lab design

Code-native concept, respecting the request to avoid external LLM inference. No generated art or remote fonts. React + Vite; a Python server serves the built UI and computes every result locally.

Primary surface: a dark navy header with a simple offset-line logo, Paper Options Lab title, a permanent paper-only status, and a source import button. White working surface, slate text, cobalt for selections, teal for eligible results, amber for rejection details. Inter/system sans for text; system monospace for figures. Open table and chart composition, fine separators, small radii, no decorative cards.

Workflow: synthetic scenario selector → call/put comparison table sorted by risk → selected spread payoff and explicit Greek units → risk/cost controls → deterministic replay ledger → inspect rejection reasons. Imported data carries provenance and a user-supplied/unverified label. No claims of performance or profit recommendations. Every selected comparison says PAPER. The open action is explicitly a local paper ledger event. No buttons, endpoints, adapters, or configuration for live trading.

Responsive: main inspector falls beneath table on narrow screens; table scrolls inside its own region. Keyboard-visible focus, native form labels, chart text alternatives, inline errors.

Allowed core copy: Paper Options Lab; Paper only; Compare defined-risk spreads; Synthetic scenarios, not historical returns; Risk budget; Compare; Local paper ledger; Import chain JSON; Export report; Expiration payoff; Model Greeks; Rejection log; Research & limits.
