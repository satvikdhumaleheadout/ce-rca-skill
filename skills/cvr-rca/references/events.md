# Headout Component Events — Funnel Event Reference

Running document mapping GTM/Mixpanel events to funnel steps for CVR-RCA analysis.
Each event is listed with the properties to pull alongside it and the analytical purpose.

**How to use:** When a locus is fixed (e.g. language, device, TG ID, page URL), query these
events filtered to that locus and compare `pct_of_sessions` pre vs post. A drop in an event's
rate tells you where in the user journey behaviour changed.

**Session join key:** `h-sid` on LP (thevaticantickets.com). `HSID` on select/checkout pages
(book.thevaticantickets.com). Same value, different casing — align when joining across domains.

**Time on page (computed):** `MAX(event_time) - MIN(event_time)` per session ID, filtered to
the relevant page's events. More reliable than timer-based proxies.

**Before writing to this file:** discuss and get approval on events first, then write.

---

## LP Events (Landing Page → Select)

The LP is the collection page (e.g. thevaticantickets.com). LP2S is computed as:
`Select Page Viewed sessions ÷ Microsite Page Viewed sessions` — no explicit click event
was observed firing for the "Check Availability" button before page navigation.

### Structured events (sequential — in order of execution)

| # | Event | Properties to pull | Purpose |
|---|---|---|---|
| 1 | `Microsite Page Viewed` | `h-sid`, `Language`, `Platform Name`, `Collection ID`, `Is Landing Page`, `Currency` | Page load — session denominator for LP2S. All dimension filters live here |
| 2 | `Page Load Time` | `h-sid`, `LoadTime` (ms) | Load complete. Observed range: 2,300–3,600ms. Spike = performance regression |
| 3 | `Experience Card Visible` | `h-sid`, `Tour Group ID`, `Position` | Cards scrolled into viewport — confirms user reached the product list |
| 4 | `Product Card Image Viewed` | `h-sid`, `Tour Group ID`, `Ranking` | Card image loaded and rendered |
| 5 | `gtm.scrollDepth` | `h-sid`, `gtm.scrollThreshold` (10/25/40/50/75%) | How far down the page the user scrolled |
| 6 | `Microsite Page Section Viewed` | `h-sid`, `Section` | Content sections entered viewport (Trust Markers, Reviews, FAQ etc.) |
| 7 | `More Details Clicked` | `h-sid`, `Tour Group ID`, `Position`, `Action` (Open/Close) | User opened inclusions drawer on a card — strong engagement signal |
| 8 | `More Details Viewed` | `h-sid`, `Tour Group ID`, `Position` | Drawer confirmed rendered |
| 9 | `More Details Section Viewed` | `h-sid`, `Tour Group ID`, `Rank`, `Tab Name` | Which tab user read inside drawer (Pinned Reviews, Inclusions etc.) |
| 10 | `Page Section Viewed` | `h-sid`, `Tour Group ID`, `Section` | Content sections scrolled within drawer (Aggregate Countries, Highlights etc.) |
| 11 | `Review Card Clicked` | `h-sid`, `Tour Group ID`, `Section`, `Rating` | User expanded a full review — trust-seeking signal |
| 12 | `Reviews Carousel Scrolled` | `h-sid`, `Tour Group ID`, `Section` | User browsed multiple reviews |
| 13 | `Image Gallery Opened` | `h-sid`, `Tour Group ID`, `Position` | User opened photo gallery — strong purchase consideration signal |
| 14 | `Image Viewed` | `h-sid`, `Tour Group ID`, `Ranking`, `Section` | Individual images viewed — depth of visual engagement |
| 15 | `More Details Swipesheet Closed` | `h-sid`, `Tour Group ID`, `action` (Close Button / backdrop) | Drawer closed. If no click-through follows = "considered but didn't convert" cohort |

### Unstructured events (can fire at any point during LP session)

| Event | Properties to pull | Purpose |
|---|---|---|
| `Locale Selector Clicked` | `h-sid`, `Page Type` | User opened locale selector — currency or language doesn't match their preference |
| `Locale Popup Viewed` | `h-sid`, `Option Type` (Language / Currency) | Which tab they viewed |
| `Locale Option Selected` | `h-sid`, `Option Type`, `Option Name` | What they switched to (e.g. Currency: USD from EUR) — spike = currency mismatch in incoming traffic |
| `MB Currency Changed` | `h-sid`, `Currency` | Microbrand-specific currency switch confirmation |

### Excluded (noise)
`Free Cancellation Tooltip Viewed` (hover on tiny secondary element, not population-level signal),
`Header Dropdown Shown` (hover artefact), `MB Banner Visible` (structural render),
`gtm.timer` / `gtm.dom` / `gtm.load` / `gtm.js` (infrastructure),
`Web Vitals Captured` (performance RCA track, not CVR),
`Image Gallery Component Present` / `Image Gallery Section Viewed` (render events, no user action),
raw `gtm.click` entries (no semantic meaning).

---

## S2C Events (Select Page → Checkout)

The select page lives on `book.thevaticantickets.com/book/<tgid>/select/`. The dataLayer resets
on navigation from LP. S2C = sessions that reached checkout ÷ sessions that viewed the select page.

### Structured events (sequential — in order of execution)

| # | Event | Properties to pull | Purpose |
|---|---|---|---|
| 1 | `Select Page Viewed` | `HSID`, `Tour Group ID`, `Language`, `Platform Name`, `Currency`, `Flow Type` | Page load — S2C denominator. Split by `Flow Type` (multi-tour etc.) as different flows have meaningfully different conversion rates |
| 2 | `Page Load Time` | `HSID`, `LoadTime` (ms) | Select page load complete. Observed: 2,785–5,949ms across sessions. Spike = performance regression on booking flow |
| 3 | `Calendar Opened` | `HSID`, `Tour Group ID`, `Calendar Type` | User opened the date picker. Drop in rate = users not engaging with the date step at all — could indicate calendar not loading or date strip satisfying intent |
| 4 | `Calendar Date Selected` | `HSID`, `Tour Group ID`, `Selected Date`, `Table Type` | User clicked a specific date inside the calendar. This is the intentional date selection — cleaner signal than `Experience Date Selected` which also fires on auto-load |
| 5 | `Calendar Closed` | `HSID`, `Tour Group ID`, `Calendar Type` | Calendar dismissed after date selection. Confirms date step completed |
| 6 | `Experience Date Selected` | `HSID`, `Tour Group ID`, `Experience Date` | Date state pushed to page. Fires on both auto-load (URL param) and manual selection — `Ranking` and `No of Tours` are null in both cases. Keep alongside `Calendar Date Selected`; reconcile once LP-date-select flow is tested |
| 7 | `Error Viewed` | `HSID`, `Error Message` | Validation error shown to user. Observed: 'Please select a date to continue' fires when user attempts to proceed without selecting a date. Spike = step sequence confusion or UX change |
| 8 | `Tour Card Visible` | `HSID`, `Tour Group ID`, `Tour ID`, `Variant ID`, `Ranking`, `Inventory Type`, `Is BNPL`, `Is Cancellable`, `Cancellable Up To` | Variant cards rendered after date selection. Each fired event = one variant shown. `Ranking` tells you position. Drop in a specific variant's rate = it was removed or became unavailable. Changes in `Is BNPL`, `Is Cancellable`, `Inventory Type` across the variant set = product attribute changes that could drive S2C shifts |
| 9 | `Variant Card Clicked` | `HSID`, `Tour ID`, `Variant ID`, `Ranking`, `Is Scarce`, `Is BNPL`, `Is Cancellable`, `Cancellable Up To`, `Inventory Type`, `Tour Entry Time` | User clicked Select on a variant card. `Tour Entry Time` (Single Time vs Fixed Time) determines whether a time selection step follows. If a popular variant changes from Single Time to Fixed Time, users face an extra step that drives abandonment |
| 10 | `Experience Tour Selected` | `HSID`, `Tour Group ID`, `Tour ID`, `Variant ID`, `Triggered By`, `MB Name`, `Seats Left` | Variant confirmed selected by user. Filter `Triggered By = 'User'` to exclude system-triggered fires. `Seats Left` surfaces precise scarcity when populated — combine with `Is Scarce` from Variant Card Clicked |
| 11 | `Experience Time Dropdown Clicked` | `HSID`, `Tour Group ID`, `Tour ID`, `Flow Type` | User opened the time slot selector — only fires for `Tour Entry Time = Fixed Time` variants. Drop in rate = users not completing the time step after selecting the variant |
| 12 | `Experience Time Selected` | `HSID`, `Tour Group ID`, `Experience Time`, `Triggered By`, `Is Scarce`, `Ranking` | Time slot selected. The first fire per session is the user's choice; subsequent fires with `Triggered By = 'Automatic'` are GTM multi-trigger artefacts — deduplicate on session. `Is Scarce = true` on the selected time = low inventory at that slot |
| 13 | `Select Page CTA Clicked` (label: Next) | `HSID`, `label`, `Is Scarce`, `Is XTL`, `from` | **S2C numerator** — user clicked Next to proceed to checkout. `from` distinguishes the two entry points: `Tour Selection Bar` (bottom bar) vs `Booking Itinerary Card` (right panel sticky card). Both count toward S2C. `Is XTL = true` marks cross-destination booking variants |
| 14 | `gtm.scrollDepth` | `HSID`, `gtm.scrollThreshold` | Scroll depth on select page. Note: only a single 90% threshold is configured here, unlike LP's five thresholds — "reached bottom" signal only, not granular engagement depth |

### Unstructured events (can fire at any point during S2C session)

| Event | Properties to pull | Purpose |
|---|---|---|
| `Select Page Section Viewed` | `HSID`, `Tour Group ID`, `Section`, `Ranking` | Content sections entered viewport while scrolling (Highlights, Gallery, Need to know, Cancellation Policy, My tickets, Ratings & Reviews). Drop in a section's rate = users not scrolling far enough to reach it. Note: `Gallery` and `Cancellation Policy` appear with duplicate Rankings — GTM instrumentation quirk, deduplicate |
| `Experience Page Section Viewed` | `HSID`, `Tour Group ID`, `Section`, `Display Price` | Deeper content sections (Aggregate Countries etc.) — separate event from `Select Page Section Viewed`, fires for traveller origin data section |
| `Select Page CTA Clicked` (non-Next labels) | `HSID`, `label` | Content engagement clicks (e.g. 'highlights read more', 'faq read more'). Measures how deeply users read product content before selecting. Distinguish from S2C numerator by filtering `label != 'Next'` |

### Excluded (noise)
`Experiment Viewed` (A/B experiment tracking, not for continuous RCA),
`Javascript Error` (cross-origin third-party script errors — ~24 per page load, harmless pattern),
`SDK Loaded` (payment SDK technical readiness — relevant to C2O, not S2C),
`LocalStorage Time Added` (browser storage write, no user action),
`Experience Pax Updated` (fires automatically on date selection from URL param defaults, not an explicit user action on the select page — captured at checkout level instead),
`gtm.dom` / `gtm.load` / `gtm.js` / `gtm.timer` / `gtm.historyChange` (infrastructure),
`HSID Load Time` push, `Page Url` push, `Web Vitals Captured`.

---

## C2O Events (Checkout → Order)

The checkout page lives on `book.thevaticantickets.com/book/<tgid>/checkout/`. C2O = completed
orders ÷ sessions that viewed the checkout page. Decomposes into C2A (attempt rate) and A2O
(attempt-to-order success rate) — see summary.json for pre-computed split.

### Structured events (sequential — in order of execution)

| # | Event | Properties to pull | Purpose |
|---|---|---|---|
| 1 | `Checkout Page Viewed` | `HSID`, `Tour Group ID`, `Is Group`, `Lead Time Days`, `Flow Type`, `Experience Name` | Page load — C2O denominator. `Lead Time Days` is critical: BNPL requires ≥4 days, scarcity messaging changes at low lead time. Segment by lead time bucket for availability-related hypotheses |
| 2 | `Page Load Time` | `HSID`, `LoadTime` (ms) | Checkout page load complete. Observed: 5,532ms. Spike = performance regression on checkout |
| 3 | `BNPL Status Toggled` | `HSID`, `Status` (Available / Unavailable), `Is Lead Time Condition Met` | BNPL payment option availability on checkout load. `Status = Unavailable` despite variant being BNPL-eligible = lead time too short (observed threshold: <4 days). If BNPL flips from Available → Unavailable in post-period, users lose a deferred payment option — C2A drop. Fires 2–3 times per checkout load due to GTM race condition; use the final fire after `Checkout Started` as the authoritative state |
| 4 | `Payment Currency Changed` | `HSID`, `Original Price`, `Original Currency`, `New Price`, `New Currency` | Price auto-converted to user's local currency on checkout load and on pax adjustment. Large price shift (e.g. USD → EUR) = trust friction if the displayed price is significantly different from what the user saw on the select page. Fires twice per trigger (GTM multi-trigger) — deduplicate on session |
| 5 | `Checkout Started` | `HSID`, `Tour Group ID`, `Is Group`, `Lead Time Days`, `Is Hardcoded Combo Variant` | Checkout funnel confirmed started — fires after page load completes and payment SDKs are ready. Can fire more than once per session if user edits and returns via pencil icon — deduplicate by counting distinct sessions with at least one fire |
| 6 | `Checkout Page Section Viewed` | `HSID`, `Section` | Checkout page sections visible to user (e.g. 'BNPL Option Selection'). Drop in BNPL section view rate = BNPL option not rendering for eligible users |
| 7 | `Experience Pax Updated` | `HSID`, `Tour Group ID`, `Flow Type`, `Is Group`, `Pax Type` | Pax count adjusted on the checkout page via +/- controls. Fires separately per pax type changed (e.g. ADULT then CHILD). Each fire triggers a price recalculation (`Payment Currency Changed` follows immediately). Rise = users arriving at checkout with the wrong group composition — could indicate select page pax defaults are misleading |
| 8 | `Error Viewed` | `HSID`, `Error Message` | Validation error shown on checkout. Observed: `'Only 1 ticket left'` fires when pax adjustment exceeds available inventory; `'Error : please enter a valid full name'` fires on incomplete form submission. Fires multiple times per interaction (GTM multi-trigger) — deduplicate on session |
| 9 | `Itinerary Card Edit Button Clicked` | `HSID`, `Tour Group ID`, `Type` | User clicked pencil icon on the booking summary to edit their selection. `Type = 'Datetime'` = editing time slot; other values (e.g. `'Variant'`) indicate a different edit. Always fires immediately before `Back Button Clicked On Checkout Page` when the pencil is used. Rise = users not satisfied with their selection after reaching checkout |
| 10 | `Back Button Clicked On Checkout Page` | `HSID`, `Tour Group ID` | User navigated back from checkout to select page. Fires for **both** browser back button AND pencil icon edits. To isolate abandonment (browser back only): filter sessions where `Itinerary Card Edit Button Clicked` did NOT precede it in the same session. Rise in rate = checkout friction — combine with `Lead Time Days`, `BNPL Status`, and `Error Viewed` to diagnose cause |
| 11 | `Checkout Customer Field Added` | `HSID`, `Field Name`, `Triggered By` | Form field completed by the user. Fires once per field on blur. Track completion rate per `Field Name` to find where the form loses users — a drop at 'Date of Birth' or 'Ticket Type' = that field is causing friction. For multi-pax bookings fires once per guest per field — use distinct sessions per `Field Name`, not raw count. Do not pull `Field Value` — contains PII (name, phone, email, DOB) |
| 12 | `Checkout Customer All Details Added` | `HSID`, `Tour Group ID`, `Flow Type`, `Cart Value`, `Is Primary Guest Only` | All required guest fields completed. Fires once per guest — deduplicate on session (GTM multi-trigger). `Is Primary Guest Only: true` = single guest booking. Drop in session rate = users abandoning the form before completion. Use alongside `Checkout Customer Field Added` to distinguish partial vs full form completion |
| 13 | `Checkout Payment Details Added` | `HSID`, `Tour Group ID`, `Flow Type`, `Cart Value`, `Payment Type`, `Selected Payment Time`, `Triggered By` | User engaged with a payment method. For PayPal: fires on PayPal selection. For card: fires on valid card entry (invalid cards do not trigger it — SDK validates first). `Payment Type` = `'CARD'` or `'PAYPAL_CHECKOUT'`. `Selected Payment Time` = `'Pay now'` or `'BNPL'` at the moment of engagement. Re-fires on each payment configuration change within the session — deduplicate by first fire per `Payment Type` per session |
| 14 | `Confirm & Pay Clicked` | `HSID`, `Tour Group ID`, `Flow Type`, `Details Valid`, `User Subscribed` | User clicked the payment CTA. `Details Valid: true` = **C2A numerator** — valid attempt forwarded to payment gateway. `Details Valid: false` = incomplete form click, validation errors follow. Split by `Details Valid` to separate real attempts from friction clicks |
| 15 | `Order Completed` | `HSID`, `Order ID`, `Order Value`, `Itinerary Id` | **C2O numerator** — fires on the confirmation page after successful payment. `Order Value` = cart value at time of purchase (0 for fully discounted orders) |

### Unstructured events (can fire at any point during C2O session)

| Event | Properties to pull | Purpose |
|---|---|---|
| `Tooltip Viewed` | `HSID`, `Tooltip Type` | User opened an informational tooltip. `Tooltip Type: 'billable currency'` = user checking the USD→EUR conversion on the price summary. Spike = currency display is creating confusion or unexpected price surprises at checkout |
| `BNPL Option Selected` | `HSID`, `Option` | User explicitly toggled the payment timing selector. `Option: 'BNPL'` = chose book now, pay later; `Option: 'Pay Now'` = chose immediate payment. Distinct from `BNPL Status Toggled` which fires on load to signal availability — this event only fires on explicit user action |
| `Payment Option Selected` | `HSID`, `Payment Type`, `Payment Gateway Type`, `Payment Gateway`, `Ranking` | Payment gateway confirmed active for the session. `Ranking: 1` = card, `Ranking: 2` = PayPal. Changes in `Payment Gateway` across periods signal an infrastructure change (e.g. gateway migration) — relevant if C2A drops coincide with a gateway switch |
| `Listing Price Mismatch Found` | `HSID`, `Currency`, `Tour Group ID`, `Tour Id`, `Variant Id` | Fires when the cart value doesn't match the expected listing price for the selected variant. A small discrepancy (e.g. $0.01) is a rounding artefact; a spike in session rate = a pricing bug creating trust friction at checkout |
| `Save Card Checkbox Clicked` | `HSID`, `Action` | User clicked the save card for future payments checkbox. `Action: 'Selected'` = opted in; `Action: 'Deselected'` = opted out. The sign-in dialog (Google/Apple) that follows has no corresponding GTM event. Drop in rate = save card feature removed or sign-in flow broken |
| `Checkout Have Promo Code Clicked` | `HSID`, `Tour Group ID`, `Flow Type` | User clicked the "Have a promo code?" link. Rise = price sensitivity or an active promo campaign driving coupon intent |
| `Coupon Failed` | `HSID`, `Tour Group ID`, `Coupon Code`, `Flow Type`, `Error Code` | Coupon application failed. `Error Code: 'CAL-0408'` = user not signed in; other codes = invalid or expired coupon. Can fire multiple times per session if user retries. Rise = promo code friction or a campaign driving traffic with codes that don't work |
| `Coupon Applied` | `HSID`, `Tour Group ID`, `Coupon Code`, `Flow Type`, `Discount Value` | Coupon successfully applied. `Discount Value` = discount amount in cart currency. A spike in session rate = active promo campaign — flag when comparing C2O pre/post as coupon sessions have structurally higher conversion and can distort the comparison |

### Excluded (noise)
`SDK Loaded` (Riskified Beacon, Checkout Flow Cards — fraud/payment infrastructure),
`Page Transition Complete` (navigation timing, not user action),
`gtm.historyChange` variants (URL state management),
`gtm.dom` / `gtm.load` / `gtm.js` (infrastructure).

---

## Notes

- All event names match GTM dataLayer names, forwarded 1:1 to Mixpanel and stored in
  `mixpanel_events_partitioned` in BigQuery.
- CE 189 = Vatican Museums (thevaticantickets.com). Events captured via F12 dataLayer
  inspection on 2026-05-03.
- TG ID = Tour Group ID = Experience ID at the collection level (interchangeable in LP queries).
  At the select page level, variants within a TG are distinct.
- `Book now, pay later` as a feature (appearing/disappearing) is relevant to C2A analysis
  but has no reliable event — track as a product change query, not an event.
