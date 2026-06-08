# What context helps a CE-RCA — input guide

*This is a human-facing guide. The RCA never loads it into its context — it's
here for you to skim when the Step 1 prompt asks if you want to add context.*

At the Step 1 pause you can reply **"continue"** to run the default RCA, or add
any of the inputs below. The more specific and falsifiable your input, the more
targeted the investigation — but **the data always decides the conclusion**. Your
context *steers attention and corroborates*; it never overrides what the numbers
say. Anything you skip simply isn't used. Nothing you add can "break" the RCA.

## What you can add

### 1. A focus area or hunch
Where you think the problem is, in your own words.
- ✅ *"Focus on CVR — I think the funnel broke, not traffic."*
- ✅ *"LP2S at the landing-page level looks off — it's been fragile here before."*
- A hunch becomes a **prioritised, falsifiable branch**: opened early, tested,
  and reported as CONFIRMED or RULED OUT. A wrong hunch costs nothing.

### 2. Known dates (deploy / pricing / promo / content change)
Operational facts with a date.
- ✅ *"Pricing changed Apr 8."*  *"Ran a 20%-off promo Apr 12–15."*  *"New
  landing page shipped last week."*
- Each date drops a **marker on the trend charts** and seeds a check at the
  reconciliation step. Dates never move the analysis window you confirmed.

### 3. An MMP doc (GM context doc) — link
The doc GMs keep with CE history, past RCAs, supply notes, known quirks.
- Paste the **Google Drive link**. The RCA reads it and pulls out
  **historical-pattern hypotheses** — things that broke before, recurring
  seasonality, structural quirks — that the generic playbook wouldn't know.
- Best for: "this CE has a history — use it."

### 4. An ad-hoc data pull (Google Sheet) — link
A Sheet where you've already pulled numbers relevant to this CE.
- Paste the **Sheet link**. The RCA reads the relevant figures and uses them as
  **corroboration** at the reconciliation step (not to steer branch selection).
- Keep the sheet reasonably tidy (a clear tab with headers). Very large or
  formula-heavy sheets may need you to point at a BigQuery table or paste the key
  numbers instead — the RCA will tell you if so.

### 5. A Slack channel
A channel where this CE has been discussed (a market channel, an incident thread).
- Name the channel (e.g. *"check #mkt-france"*). It's read **alongside** the
  RCA's automatic Slack discovery, tagged as a user-requested source.

## Tips for high-signal input
- **Be specific and falsifiable** — "S2C dropped after the Apr 8 price change"
  beats "something feels off."
- **Give dates** whenever you can — they're the highest-leverage single input.
- **Link the source** rather than pasting long text — the RCA reads it directly.
- **One or two strong priors** beat a long list — the investigation stays
  proportional to the evidence.

## What it will NOT do
- It won't let your input override the data-driven conclusion.
- It won't silently move your analysis window.
- It won't treat an ad-hoc sheet as ground truth — it's corroboration, weighed
  against the system's own data.
