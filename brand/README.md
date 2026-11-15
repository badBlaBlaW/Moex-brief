# Mark — identity

`mark-avatar-512.png` is the Telegram avatar. To set it:
**@BotFather** → `/setuserpic` → choose the bot → send the file **as a photo**,
not as a document.

| File | What it is |
|------|------------|
| `mark-avatar-512.png` | the avatar, what Telegram wants |
| `mark-avatar-1024.png` | same mark, larger |
| `mark-avatar-scales.png` | proof it holds at 512 / 160 / 96 / 48 px |
| `make-avatar.py` | regenerates all three; edit this, not the PNGs |
| `PHILOSOPHY.md` | the design rules the mark answers to |
| `mark-description.png` | the 640×360 card shown above the bot's description |
| `mark-portrait-source.png` | the generated portrait, ungraded |
| `make-description.py` | rebuilds the card from the portrait |

## The mark

A bold **M** and a lighter **W** — MarkWatch — sharing a baseline over a chart
grid. The W is deliberately asymmetric: its final stroke breaks above where it
started, so the rising trend is the letterform's own anatomy rather than an
ornament added to it.

Ink `#0B1725`, gold `#D9A441`, grid `#1E3752`, baseline `#2C4C6C`.

Drawn in code at 8× and downsampled, so it is resolution-independent: change
`S` in `make-avatar.py` for any size.

## The description card

`mark-description.png` is what Telegram shows above the bot's description on an
empty chat. Set it in **@BotFather** → `/mybots` → your bot → **Edit Bot** →
**Edit Description Picture**.

The portrait was generated with FLUX.1 Krea-dev, prompted for a navy-black
backdrop and a warm rim light from camera left — the avatar's ink and gold — so
the photograph is lit for the card rather than pasted onto it. It is then
graded cooler, its blacks lifted to the ink value, and its left edge feathered
so the figure emerges from the ground instead of sitting on a visible rectangle.

The man is invented. He is not a real analyst and should not be presented as one.
