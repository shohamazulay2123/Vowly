# Vowly Wedding Planning Logic — Israel-Focused Roadmap

## Purpose

This document defines the core wedding-planning logic that should be implemented in Vowly after the couple completes the initial onboarding flow.

The goal is for the app to behave like a real wedding planner, not just a static checklist.  
After collecting the couple’s basic wedding profile, the system should guide them through the correct planning order for a wedding in Israel.

---

## Planning Logic Overview

The app should guide the couple through the following phases:

1. Venue first
2. Core vendors
3. Legal / documents / ceremony
4. Guest management
5. Budget management
6. Wedding month execution checklist

Each phase should generate relevant tasks, dashboard widgets, reminders, and “next best action” recommendations.

---

# Phase 2 — Venue First

## Why this phase comes first

In Israel, the venue usually comes before most other vendors because it determines:

- Wedding date availability
- Catering model
- Location and travel distance
- Guest capacity
- Minimum guest commitment
- Kashrut level
- Design style
- Indoor / outdoor setup
- Production rules and restrictions
- Parking and accessibility

Because of this, the app should guide couples to close a venue before focusing heavily on other vendors.

## Venue Tasks

| Task | Priority |
|---|---|
| Search venues by region and guest count | Very high |
| Compare price per guest / minimum guests | Very high |
| Check parking and accessibility | High |
| Check indoor/outdoor backup plan | High |
| Check kashrut and catering options | High |
| Book venue and sign contract | Very high |

## Recommended Next Best Action

If the couple does not have a booked venue, the system should push this message:

> Your next best action: choose 3–5 venues to visit.

## Suggested App Behavior

If `venue_booked = false`, then:

- Show venue planning as the main dashboard priority.
- Highlight venue search in the home page.
- Recommend 3–5 venue visits.
- Show venue-related tasks before other vendor tasks.
- Disable or visually de-prioritize later planning phases until a venue/date is selected.

## Suggested Statuses

| Status | Meaning |
|---|---|
| Not started | No venue search started |
| Searching | Couple is viewing or saving venues |
| Visits scheduled | Couple selected venues to visit |
| Comparing offers | Couple is comparing price and terms |
| Booked | Venue contract signed |

---

# Phase 3 — Core Vendors

## When this phase starts

This phase should begin after the couple has selected a wedding date and venue.

After the venue/date is closed, the couple should book the vendors that are usually taken quickly.

## Core Vendor Priorities

| Vendor | Why early |
|---|---|
| Photographer / video | Good teams are booked months ahead |
| DJ / music | Very date-dependent |
| Makeup and hair | Limited availability per date |
| Rabbi / ceremony provider | Needed early if using Rabbinate/private ceremony |
| Wedding dress / suit | Needs fittings and time |
| Design / flowers | Depends on venue style and budget |

## Supplier Journey Concept

In the app, this phase should become a “Supplier Journey” that includes:

- Supplier discovery
- Swiping / like / skip
- Favorites
- Shortlist comparison
- Meeting scheduling
- Notes per supplier
- Selected supplier status
- Vendor booking progress

## Suggested Vendor Statuses

| Status | Meaning |
|---|---|
| Not started | Couple has not started searching |
| Browsing | Couple is viewing suppliers |
| Favorited | Couple saved supplier to favorites |
| Contacted | Couple contacted supplier |
| Meeting scheduled | Couple scheduled a meeting |
| Offer received | Supplier sent price/offer |
| Booked | Supplier selected and confirmed |
| Skipped | Supplier rejected or not relevant |

## Suggested Dashboard Logic

Once venue/date is booked:

- Replace venue-first CTA with supplier recommendations.
- Show the highest-priority missing vendor as the next action.
- Example: `Your next best action: choose a DJ / music supplier.`
- Show supplier progress as a percentage.

---

# Phase 4 — Legal / Documents / Ceremony

## Purpose

The app should create a ceremony checklist based on the couple’s selected marriage route.

The app should not assume all couples are using the same legal or religious path.

## Required Onboarding Field

Add or use a field such as:

```text
ceremony_route
```

Suggested values:

```text
rabbinate
private_rabbi
civil_abroad
utah_online
symbolic_ceremony
other
unknown
```

---

## Rabbinate Route Checklist

For couples marrying through the Rabbinate, Vowly should create reminders for:

| Task |
|---|
| Open marriage file |
| Prepare IDs and required documents |
| Choose rabbi / officiant |
| Schedule kallah guidance if relevant |
| Confirm ketubah / ceremony details |
| Save marriage certificate after the wedding |

## Non-Rabbinate Route Logic

For couples not using the Rabbinate, the app should ask what route they chose and create a different checklist.

Examples:

- Civil marriage abroad
- Utah / online civil marriage process
- Symbolic ceremony in Israel
- Private rabbi / alternative ceremony
- Other custom route

## Suggested App Behavior

If `ceremony_route = rabbinate`, show Rabbinate-related reminders.

If `ceremony_route != rabbinate`, show a custom checklist based on the selected route.

If `ceremony_route = unknown`, show this prompt:

> Choose your ceremony route so Vowly can build the correct legal and ceremony checklist for you.

## Important Israel-Specific Reminder

After the wedding, couples may need to update their marital status in the population registry, depending on the selected route and documentation.

The app should add a post-wedding reminder:

> Update marital status and save official marriage documents.

---

# Phase 5 — Guest Management

## Purpose

Guest management should become a major part of the system.

This should feel like a smart planning tool, not just a table.

## Guest Management Features

| Feature | Purpose |
|---|---|
| Guest list | Names, phone numbers, side, group |
| RSVP tracking | Coming / not coming / maybe |
| Table planning | Seating arrangements |
| Gifts tracking | Optional after wedding |
| WhatsApp invite export | Very useful in Israel |
| Dietary notes | Vegan, kosher level, allergies, children |

## Suggested Guest Fields

| Field | Type | Notes |
|---|---|---|
| full_name | text | Guest name |
| phone | text | Needed for WhatsApp / RSVP |
| side | enum | Bride / groom / shared / family / work / friends |
| group_name | text | Family, army, work, school, etc. |
| rsvp_status | enum | Unknown / coming / not coming / maybe |
| table_number | text/number | For seating plan |
| meal_notes | text | Vegan, vegetarian, allergies, kids, kosher notes |
| gift_amount | number | Optional after wedding |
| invitation_sent | boolean | Whether invite was sent |
| notes | text | Free text |

## Suggested RSVP Statuses

```text
unknown
invited
coming
not_coming
maybe
needs_follow_up
```

## Suggested Dashboard Widgets

- Total guests
- Confirmed coming
- Not answered yet
- Tables completed
- Guests with dietary notes
- WhatsApp invites sent

## Suggested Smart Logic

The app should detect useful situations:

- If many guests are still `unknown`, show:  
  `Your next best action: follow up with guests who have not answered yet.`

- If wedding is close and seating is incomplete, show:  
  `Your next best action: finish the seating plan.`

- If guest count changed significantly, show:  
  `Review venue minimum guest commitment and final number submission.`

---

# Phase 6 — Budget Management

## Purpose

The app should immediately create a budget structure after onboarding.

For Israel, the budget should be calculated mainly from:

```text
guest count × estimated price per guest + fixed vendors + extras
```

This is more useful than a generic wedding budget because the venue/food cost is usually the largest variable.

## Budget Categories

| Category |
|---|
| Venue / food |
| DJ |
| Photography |
| Dress |
| Suit |
| Makeup and hair |
| Rings |
| Rabbi / ceremony |
| Design / flowers |
| Invitations |
| Alcohol upgrades |
| Extras / surprises |
| Honeymoon |
| Emergency buffer |

## Suggested Budget Fields

| Field | Type | Notes |
|---|---|---|
| category | text/enum | Budget category |
| estimated_amount | number | Planned cost |
| actual_amount | number | Real cost |
| paid_amount | number | Amount already paid |
| remaining_amount | number | Calculated |
| vendor_id | optional foreign key | Link to supplier if relevant |
| due_date | date | Payment deadline |
| payment_status | enum | Not paid / deposit paid / partially paid / paid |
| notes | text | Free text |

## Suggested Formula

```text
estimated_total_budget =
  (estimated_guest_count × estimated_price_per_guest)
  + fixed_vendor_costs
  + extras
  + emergency_buffer
```

## Suggested Dashboard Widgets

- Estimated total budget
- Actual committed cost
- Paid so far
- Remaining payments
- Over/under budget
- Next payment due

## Suggested Smart Logic

If actual costs exceed budget, show:

> You are above the planned budget. Review optional extras or update your budget.

If payment due date is near, show:

> Upcoming payment: check supplier payment schedule.

If venue/food price is missing, show:

> Add estimated price per guest to calculate a realistic Israeli wedding budget.

---

# Phase 7 — Wedding Month Checklist

## Purpose

Near the wedding, the system should change from planning mode to execution mode.

This means the dashboard should focus less on discovery and more on:

- Confirmations
- Final numbers
- Supplier coordination
- Seating
- Payments
- Timeline
- Documents
- Wedding-day readiness

## Wedding Month Tasks

| Timing | Tasks |
|---|---|
| 30 days before | Final guest confirmations, seating plan, supplier payments |
| 14 days before | Final numbers to venue, timeline with vendors |
| 7 days before | Beauty appointments, rings, documents, emergency kit |
| 1 day before | Pack items, confirm transportation, sleep |
| Wedding day | Timeline, contacts, supplier checklist |

## Suggested Date-Based Logic

If `days_until_wedding <= 30`, activate wedding month mode.

If `days_until_wedding <= 14`, prioritize final venue numbers and supplier timeline.

If `days_until_wedding <= 7`, prioritize documents, rings, beauty appointments, and emergency kit.

If `days_until_wedding <= 1`, show a calm final checklist and emergency contacts.

On wedding day, show:

> Today is your wedding day. Focus only on the timeline, contacts, and final supplier checklist.

## Suggested Dashboard Behavior

When wedding month mode is active:

- Replace general planning CTA with execution checklist.
- Show urgent tasks first.
- Show supplier contact list.
- Show timeline for the wedding day.
- Show final guest count.
- Show unpaid balances.
- Show emergency checklist.

---

# Global Next Best Action Logic

The app should calculate one primary recommendation for the couple at any time.

## Suggested Priority Order

1. If no wedding date: choose date or date range.
2. If no guest count: estimate guest count.
3. If no budget: set budget range.
4. If no venue: choose 3–5 venues to visit.
5. If venue booked but no core vendors: book highest-priority missing vendor.
6. If ceremony route unknown: choose ceremony route.
7. If Rabbinate route and legal tasks missing: complete legal checklist.
8. If guest list is empty: create guest list.
9. If RSVP deadline is close: follow up with guests.
10. If wedding is within 30 days: switch to wedding month checklist.
11. If wedding is today: show wedding-day timeline.

## Example Output

```text
next_best_action = {
  "title": "Choose 3–5 venues to visit",
  "phase": "venue",
  "priority": "very_high",
  "reason": "The venue determines your wedding date, guest capacity, catering model, and core vendor availability.",
  "cta_label": "Start venue search",
  "route": "/venues"
}
```

---

# Suggested Implementation Notes

## Backend

Consider adding or updating models/tables for:

- Wedding profile
- Planning phases
- Tasks
- Vendors
- Vendor favorites
- Vendor meetings
- Ceremony route
- Guests
- RSVP statuses
- Budget categories
- Payments
- Wedding-day timeline

## Frontend

The home dashboard should show:

- Wedding countdown
- Planning progress
- Current phase
- Next best action
- Upcoming tasks
- Vendor journey progress
- Guest management summary
- Budget summary
- Wedding month checklist when relevant

## Task Generation

Tasks should be generated based on:

- Wedding date
- Region
- Guest count
- Budget
- Venue status
- Ceremony route
- Vendor booking status
- Days until wedding

## Do Not Hardcode Everything

Use structured task templates where possible.

Example:

```text
task_template = {
  "phase": "venue",
  "title": "Search venues by region and guest count",
  "priority": "very_high",
  "trigger": "venue_booked == false",
  "route": "/venues"
}
```

---

# Acceptance Criteria

The implementation is complete when:

- The couple receives venue-first guidance when no venue is booked.
- The system recommends choosing 3–5 venues to visit.
- Core vendors become the main focus only after venue/date is selected.
- Ceremony checklist changes based on ceremony route.
- Rabbinate-specific reminders are generated when relevant.
- Guest management includes RSVP, table planning, dietary notes, and WhatsApp export logic.
- Budget is calculated using guest count, price per guest, fixed vendors, extras, and emergency buffer.
- Wedding month mode activates automatically within 30 days of the wedding.
- Dashboard displays a clear next best action at all times.
- Existing routes, authentication, and backend behavior are not broken.

---

# Manual Testing Checklist

Test the following user scenarios:

## Scenario 1 — New couple with no venue

Expected:

- Venue is the main priority.
- CTA says: `Choose 3–5 venues to visit`.
- Venue tasks appear before supplier tasks.

## Scenario 2 — Venue booked, vendors missing

Expected:

- Supplier Journey becomes the main focus.
- App recommends missing core vendor, such as DJ or photographer.

## Scenario 3 — Rabbinate ceremony route

Expected:

- Rabbinate checklist appears.
- Marriage file and document reminders are created.

## Scenario 4 — Non-Rabbinate ceremony route

Expected:

- App asks for selected route.
- Different legal/ceremony checklist is shown.

## Scenario 5 — Wedding within 30 days

Expected:

- Wedding month mode activates.
- Dashboard prioritizes RSVP, seating, payments, and supplier confirmations.

## Scenario 6 — Wedding day

Expected:

- Dashboard shows wedding-day timeline, supplier contacts, and final checklist.
