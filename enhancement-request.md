# Enhancement Request: Conversational Meal Planning & Batch Cook Workflow

## Context

Elzar currently excels at single-recipe generation, meal plan grids, and Grocy inventory
integration. This request adds a conversational planning interface and batch-cook workflow
that supports an iterative, discussion-driven approach to meal prep — the way planning
actually happens in practice.

The workflow looks like: brainstorm ideas → discuss modifications → generate recipes →
build a prep cook plan → create an aggregated shopping list → iterate on everything
through conversation → cook → debrief.

### How This Fits the Existing App

The current app has a strong form-driven flow: Generator for single recipes, Meal Planner
for day/meal grids, Inventory Manager for Grocy import, History for browsing, Profiles
for dietary restrictions, and Settings for configuration. These all stay as-is. The new
features add a Chat page as a new nav item (💬 between Meal Planner and Inventory), expand
the Meal Planner with a Batch Cook mode, enhance History with recipe locking and saving,
and evolve Profiles into a richer preference system.

---

## 1. Conversational Chat Interface

**What:** A multi-turn chat view where the user can discuss meal ideas, request changes,
and trigger tool-call actions (create recipe, edit recipe, generate shopping list, etc.)
through natural conversation.

**Why:** The current UI is form-driven — you fill in parameters and hit generate. Real
meal planning is iterative: "what if we added mushrooms to three of these recipes?" or
"swap the chicken for the leftover chuck roast." That back-and-forth doesn't fit a form.

**Where it fits:** New nav item: 💬 Chat, between Meal Planner and Inventory. This is
its own page, not a replacement for the existing Generator. The Generator remains the
quick "I just want one recipe" tool; Chat is for planning sessions.

**Details:**
- Full chat interface with persistent message history (retained across sessions, stored
  in the database — not ephemeral)
- Chat sessions can be named, browsed, and resumed from a session list sidebar
- LLM has access to tool calls / function calls:
  **Read / Query tools:**
  - `get_recipe(id)` — retrieve a specific recipe by ID
  - `search_recipes(query, filters)` — search recipe history by text, cuisine, tags, etc.
  - `get_ideas_list(filters?)` — retrieve the current ideas list, optionally filtered
  - `query_inventory` — check Grocy stock ("what do I have on hand?")
  - `query_freezer` — check freezer meal inventory (see #5)
  - `get_user_preferences` — read the current preference profile
  - `get_prep_cook_session(id)` — retrieve a past batch cook session and its recipes
  - `get_debriefs(recent?)` — retrieve past debrief notes for planning context

  **Create / Write tools:**
  - `create_recipe` — generate a new recipe and save it
  - `create_prep_cook_session` — build a batch cook plan (see #2)
  - `generate_shopping_list(recipe_ids[])` — aggregate shopping list from multiple recipes
  - `add_to_ideas_list` — add an idea to the brainstorm board (see #3)
  - `log_debrief` — save a post-session debrief (see #10)

  **Edit / Update tools:**
  - `edit_recipe(id, instructions)` — surgical edit to an existing recipe (see #4)
  - `copy_and_edit_recipe(id, instructions)` — fork a locked recipe into an editable variant (see #12)
  - `update_ideas_list(id, changes)` — edit an existing idea
  - `update_user_preferences(changes)` — update the preference profile (see #7)
- Chat context automatically includes: user preference profile, current Grocy inventory
  summary, freezer inventory summary, ideas list, and any recipes/plans created in the
  current session
- The Spice Weasel toggle should be available in Chat to control Elzar's personality

**Preference prompting behavior:** The LLM system prompt should instruct the model to
watch for opportunities to learn user preferences during conversation. When it detects
one (e.g., user says "I actually don't like corn much"), it should ASK the user before
calling `update_user_preferences` — never silently update. Example: "Want me to add that
to your preferences so I remember next time?"

---

## 2. Prep Cook Sessions (Batch Cook Planning)

**What:** A planning mode built around batch cooking — "I'm going to cook on Sunday and
produce N portions of M different meals for the freezer."

**Why:** The current Meal Planner organizes around days and meal types (Monday lunch,
Tuesday dinner) using sliders for days (1-14), people (1-12), meal type toggles, budget
buttons, cooking time preferences, and a variety slider. That's great for weekly meal
planning. Batch cooking is fundamentally different — it organizes around a single cook
session that produces freezer inventory.

**Where it fits:** New tab or mode within the Meal Planner page. The existing Meal Planner
becomes "Weekly Plan" tab; this becomes "Batch Cook" tab. Same page, shared nav item,
different UI for different planning models.

**Details:**
- Define a prep cook session: date, target meals, portions per meal
- Each session produces multiple recipes with portion counts
- Generates a unified prep day timeline (what to start first, what can run in parallel,
  when assembly happens — similar to the timeline in our current prep cook plans)
- Aggregated shopping list across all recipes in the session (deduped, quantities summed)
- Tracks total yield: portions, calories per portion, total cost estimate
- Supports a shared protein anchor across recipes (e.g., one 5 lb chuck roast split
  across shepherd's pie, sliders, and frittata cups — with the LLM allocating portions)
- Session history — browse past prep cooks
- Reheating instructions per recipe (temperature, time from frozen)
- Controls that make sense for batch cooking:
  - Number of different meals to generate
  - Portions per meal
  - Portion size (8-12 oz cup, etc.)
  - Shared protein anchor (optional — specify a protein to build around)
  - Calorie target per portion
  - Equipment available (reuse existing equipment checklist from Generator)

---

## 3. Ideas List / Brainstorm Board

**What:** A persistent, running list of meal ideas with notes, tags, and status.

**Why:** Ideas come up during conversation ("what about egg roll in a bowl?") and need
somewhere to live between planning sessions. Currently this is a markdown file maintained
manually.

**Where it fits:** New nav item: 💡 Ideas, between Chat and Inventory. Lightweight page —
a searchable/filterable list with inline editing. Also accessible from Chat via tool calls.

**Details:**
- Add ideas from chat (`add_to_ideas_list` tool call) or from the dedicated UI
- Each idea has: name, notes/description, tags (e.g., "freezer-friendly", "cheat-day",
  "low-cal"), calorie estimate range, status (idea / planned / tested / favorite)
- Ideas can be promoted to full recipes (button → opens Generator pre-filled, or
  triggers `create_recipe` in Chat)
- Searchable and filterable by tags and status
- Chat can reference and modify the ideas list via tool calls
- Simple inline editing — click to edit notes, click tags to toggle

---

## 4. Iterative Recipe Editing via Chat

**What:** Modify existing recipes through conversation rather than regenerating from scratch.

**Why:** "Add mushrooms to the shepherd's pie, enchilada bowls, and frittata cups" should
update three recipes in one request. Currently you'd regenerate each one and hope the LLM
doesn't change everything else. The existing Regenerate button (🔄, yellow) on recipes
does a full regeneration with higher temperature (0.9) — useful for "give me something
totally different," but not for surgical edits.

**Where it fits:** This is a Chat tool call (`edit_recipe`), not a new UI page. The
existing Regenerate button stays for full regeneration. Surgical edits happen through
conversation.

**Details:**
- Chat tool call: `edit_recipe(id, instructions)` — LLM applies targeted changes to the
  recipe text while preserving everything else
- Supports bulk edits across multiple recipes ("add mushrooms to all three")
- Preserves the rest of the recipe (surgical edits, not full regeneration)
- Edit history / version tracking so you can see what changed — show a "last edited"
  timestamp and optionally a diff view
- Respects recipe lock status (see #12) — if locked, must use `copy_and_edit_recipe`

---

## 5. Freezer Inventory Tracking

**What:** Track what's in the freezer — meal type, portions remaining, date frozen.

**Why:** The batch cook rotation strategy depends on knowing what's in stock. "I have
4 shepherd's pies and 2 sliders left, time to cook another batch of sliders and something
new." Could integrate with Grocy or be standalone.

**Where it fits:** Could be a section within the Inventory Manager page (which currently
handles Grocy paste/scan import), or a dashboard widget on the Chat page. The Inventory
Manager already has Purchase/Consume action types — freezer tracking extends this concept
to prepped meals rather than raw ingredients.

**Details:**
- Log portions when a prep cook session is complete (button on batch cook results)
- Decrement as portions are consumed (manual button, or Grocy-integrated)
- Dashboard showing what's in the freezer, how old it is, what's running low
- Chat can query this: "what do I have in the freezer?" / "what's running low?"
- Suggestions for next prep cook based on what's depleted
- Simple table view: meal name, portions remaining, date frozen, cal/portion

---

## 6. Bulk Ingredient Prep Tracking

**What:** Track pre-made base ingredients that are kept frozen and used across recipes.

**Why:** Things like blended garlic-oil frozen in butter moulds, caramelized onions in
portions, etc. These are always on hand and should be factored into shopping lists
(don't buy garlic if you have 8 sticks of garlic blend in the freezer).

**Where it fits:** Section within Inventory Manager or a sub-tab alongside freezer
tracking. These are essentially freezer inventory items that are ingredients rather
than finished meals.

**Details:**
- Inventory of bulk-prepped ingredients with approximate quantity remaining
- Recipes can reference bulk ingredients (e.g., "garlic blend, 1 stick")
- Shopping list generation skips items covered by bulk prep inventory
- Reminders when bulk ingredients are running low
- Recipes for the bulk ingredients themselves (how to make the garlic blend, etc.)

---

## 7. User Preference Profile

**What:** A single, rich preference document that captures who the user is as a cook and
eater — fed into every LLM prompt as context.

**Why:** The current Profiles page manages dietary restriction profiles (name + restrictions
text, toggleable per recipe). That's useful for household members with allergies. But
planning decisions depend on much more: "loves assembly-style eating," "dislikes corn
except where it belongs," "experienced chef but lazy." These aren't dietary restrictions —
they're the user's identity as a cook.

**Where it fits:** Expand the existing Profiles page. Keep the current dietary restriction
profiles as-is (they're per-person toggles, great for households). Add a new section above
or below them: "Your Preferences" — a single document covering the user's cooking identity.

**Important scoping notes:**
- This is ONE document (think: a single markdown file fed into LLM context), not a
  complex multi-field database schema. It should read like a natural description, not a
  form with 50 fields.
- **Do NOT include** equipment or budget here — those are already handled by the Generator
  page's equipment checkboxes (12 items) and the Meal Planner's budget level buttons
  (6 levels from "I'm Broke" to "Luxury"). Those are per-generation parameters, not
  permanent preferences.
- **Do include:** cooking style and experience level, effort tolerance, food loves and
  dislikes (with nuance — "corn is fine in shepherd's pie but annoying everywhere else"),
  favorite cuisines, meal format preferences (assembly-style, dip meals, sandwiches),
  planning approach (batch cook rotation, protein anchors), calorie/macro goals, store
  preferences, and anything else that helps the LLM understand this specific person.

**Details:**
- Editable in the Profiles page UI as a rich text area or structured markdown editor
- Fed into all LLM prompts (recipe generation, meal planning, chat) as system context
- Chat tool call: `update_user_preferences(changes)` — allows the LLM to propose updates
  during conversation
- **Critical behavior:** The LLM must ASK before updating preferences, never silently
  modify. System prompt instructs: "If you notice a user preference or opinion that would
  be useful to remember, ask the user if they'd like to save it before calling
  update_user_preferences."
- Viewable from Chat context so the LLM can reference it naturally

---

## 8. Shopping List Enhancements

**What:** Aggregated shopping lists from batch cook sessions, formatted for text message
sharing, with a copy button right in the UI.

**Why:** The shopping list gets texted to a spouse. It needs to be plain text, grouped
by store section, with quantities. Currently Grocy's "Add Missing to Shopping List"
(🛒, cyan button) works per-recipe. Batch cooks need aggregation across multiple recipes.

**Where it fits:** The existing 🛒 button on individual recipes stays. Add a new
"Generate Shopping List" action on batch cook sessions that aggregates across all recipes.
The output panel (wherever it displays) gets a prominent **📋 Copy to Clipboard** button
for easy text-message sharing.

**Details:**
- Aggregate ingredients across all recipes in a prep cook session
- Deduplicate and sum quantities (3 onions from recipe A + 2 from recipe B = 5 onions)
- Subtract what's already on hand (Grocy inventory + bulk prep inventory)
- Group by store section: PRODUCE & REFRIGERATED, PROTEINS, PANTRY, FROZEN, ALREADY HAVE
- Plain text output optimized for copy/paste into a text message (no markdown tables,
  no complex formatting)
- **📋 Copy to Clipboard button** — prominent, one-click, copies the plain text shopping
  list. Should also be available on individual recipe shopping lists anywhere they appear.
- "ALREADY HAVE" section so the shopper knows what was intentionally excluded
- Notes on quantities where helpful, brand preferences where relevant
- Chat tool call: `generate_shopping_list(recipe_ids[])` — can be triggered conversationally

---

## 9. Opportunistic Batching Suggestions

**What:** When the user mentions an upcoming cook (dinner party, holiday meal, etc.),
suggest ways to piggyback prep work using the same equipment or heat source.

**Why:** Running a sous vide for a ribeye? Throw a chuck roast in too. Oven on for a
casserole? Roast a sheet pan of veg. The marginal effort is near zero.

**Where it fits:** Chat behavior — the LLM detects mentions of equipment use or upcoming
cooks and proactively suggests additions. Could also surface as a suggestion in the Batch
Cook tab when equipment is selected.

**Details:**
- Chat-aware: detect mentions of upcoming cooks, equipment in use
- Suggest additions based on ideas list, freezer inventory gaps, and available equipment
- Factor in what proteins/ingredients the user is already buying
- Generate a combined prep plan that layers the opportunistic work into the existing cook

---

## 10. Post-Session Debrief

**What:** A structured debrief after each planning/cooking cycle that feeds back into
future sessions.

**Why:** "The burritos were great but I ate nothing else for a week and never want to
see a tortilla again" is critical planning data. Without capturing it, the same mistakes
repeat.

**Where it fits:** Could be a section within Chat (natural place to have a debrief
conversation), or a button/prompt on completed batch cook sessions in the Meal Planner.
The LLM can prompt for a debrief in Chat after a configurable period.

**Details:**
- Prompted debrief after a configurable period (end of week, after a prep cook, etc.)
- Questions: What did I eat vs. plan? What got skipped/wasted? What worked? How did I feel?
- Debrief data is stored and surfaced to the LLM in future planning sessions
- Tracks the "weekly nudge" — what small improvement was tried this cycle?
- Over time, builds a feedback loop: plan → cook → eat → debrief → better plan
- Chat tool call: `log_debrief` to save structured notes

---

## 11. Nutritional Awareness Dashboard

**What:** Per-portion and per-day calorie/macro estimates with gap analysis.

**Why:** The goal is awareness and pattern recognition, not obsessive tracking. After a
batch cook, it's useful to see: "your freezer averages 380 cal/portion, protein is good,
fiber is low — consider adding a bean-heavy option next round."

**Where it fits:** Summary panel on batch cook results, and an optional view in the
freezer inventory dashboard. The Generator already shows 🔥 calories per serving in recipe
metadata — this extends that concept across the whole freezer.

**Details:**
- Calorie and macro estimates per portion for each recipe
- Freezer-wide nutritional summary (average cal, protein, fiber across all stocked meals)
- Flag obvious gaps (low fiber week, heavy sodium, etc.)
- Suggest easy improvements without overhauling the plan
- Daily calorie planning: "if I eat a shepherd's pie for lunch and sliders for dinner,
  that's ~750 cal, leaving room for snacks"

---

## 12. Recipe Locking & Saving Enhancements

**What:** Expand recipe management with a lock/unlock toggle, manual recipe entry, and
enhanced save functionality — all within the existing recipe UI.

**Why:** Some recipes are personal or family recipes that should never be overwritten by
AI regeneration. Others are AI-generated but finalized and shouldn't be accidentally
changed. The current recipe actions (Regenerate, Consume, Shopping List, Save to Grocy)
are all outbound — there's no way to manually create, lock, or carefully manage recipes
within Elzar itself.

**Where it fits:** These enhancements live in the existing History page and recipe display
components. No new pages needed. The History page already shows recipes with Download (📥)
and Delete (🗑️) buttons — add Lock (🔒) alongside them. Manual recipe entry could be a
"+ Add Recipe" button in History's header, similar to "+ Add Profile" on the Profiles page.

**Details:**

**Recipe Locking:**
- Toggle lock/unlock on any recipe (🔒/🔓 button in recipe header, next to existing
  Download and Delete buttons)
- Locked recipes cannot be edited or regenerated through the normal UI
- The existing Regenerate button (🔄) should be disabled/hidden on locked recipes
- In Chat, if the LLM tries to `edit_recipe` on a locked recipe, it must instead use
  `copy_and_edit_recipe(id, instructions)` — which creates a new unlocked variant linked
  to the original
- Visual indicator: locked recipes show a 🔒 badge in History list items
- Family recipes, finalized recipes, or any recipe the user wants to protect

**Manual Recipe Entry:**
- "+ Add Recipe" button in History page header
- Opens a form: title, recipe text (large textarea or markdown editor), optional metadata
  (cuisine, calories, time, effort)
- Saved as a regular recipe in the database — appears in History, searchable, usable in
  meal plans
- Can be locked immediately on creation

**Enhanced Saving:**
- Currently "Save to Grocy" (💾) pushes to external system. Add "Save to Elzar" as a
  first-class action — explicitly save/bookmark a recipe so it persists beyond history
  cleanup (current max history is configurable, default 1000, managed by the database's
  cleanup_old_recipes method)
- Saved/bookmarked recipes exempt from history cleanup
- Tag/categorize saved recipes (family, weeknight, batch cook, etc.)

**Variant Linking:**
- When `copy_and_edit_recipe` creates a variant, store the parent recipe ID
- Show "Based on: [Parent Recipe Name]" link in the variant's display
- Parent recipe shows "Variants: [list]" section
- Allows tracking recipe evolution: Mom's Shepherd's Pie → Freezer Cup Version →
  Low-Cal Version

---

## Priority Suggestion

**High (enables the core workflow):**
1. Conversational Chat Interface (#1) — the backbone; everything else plugs into this
2. Prep Cook Sessions (#2) — the primary planning model for batch cooking
3. Shopping List Enhancements (#8) — aggregation + copy button for text sharing
4. Iterative Recipe Editing (#4) — surgical edits via chat, not full regeneration

**Medium (makes the workflow much better):**
5. User Preference Profile (#7) — single preference doc fed into all prompts
6. Recipe Locking & Saving (#12) — lock, manual entry, variants, save/bookmark
7. Ideas List (#3) — persistent brainstorm board
8. Freezer Inventory Tracking (#5) — know what's in stock, what to cook next

**Lower (nice-to-have, build over time):**
9. Post-Session Debrief (#10) — feedback loop for future planning
10. Bulk Ingredient Prep Tracking (#6) — garlic blend, caramelized onions, etc.
11. Opportunistic Batching Suggestions (#9) — "you're running the sous vide anyway..."
12. Nutritional Awareness Dashboard (#11) — per-portion macros, freezer-wide gap analysis
13. Grocy-Free Demo Mode (#13) — standalone mode for users without Grocy

---

## 13. Complete Grocy-Free Experience

**What:** Audit and enhance the existing no-Grocy behavior so that every Grocy-dependent
UI element is cleanly hidden when no Grocy API is configured — making the app feel like
a polished standalone tool, not a half-configured one.

**Why:** The app already degrades gracefully in several places: nav hides the Inventory
page when Grocy isn't configured, Generator switches "Use ingredients not in inventory"
to "Allow any ingredients," and recipe generation works fine without stock data. But the
coverage isn't complete — some Grocy-dependent elements still show up as vestigial UI
(action buttons, configuration prompts, connection test sections) that make the app feel
like it's waiting to be set up rather than fully functional on its own.

**Where it fits:** Not a new toggle — just a thorough pass through every page to ensure
the existing `grocyConfigured` check from ServiceStatusContext covers everything.

**Details:**
- Audit every page for Grocy-dependent UI that still renders when unconfigured:
  - **Generator:** Grocy action buttons (🍽️ Consume, 🛒 Add Missing, 💾 Save to Grocy)
    and the RecipeIngredientReview modal flow — hide fully when no Grocy
  - **Meal Planner:** Per-recipe Grocy action buttons (Consume, Add Missing, Save) and
    the "Use Grocy inventory" / "Prioritize expiring" checkboxes — hide fully
  - **History:** Any Grocy action buttons on the recipe viewer — hide fully
  - **Settings:** Grocy configuration fields (URL, API key), connection test section,
    unit conversion setup, and storage location setup should collapse into a single
    "Connect Grocy" prompt or be hidden behind an expandable section — not dominate the
    page when irrelevant
  - **RecipeIngredientReview / GrocyActionModal components:** Should never render when
    Grocy is unconfigured
- Chat integration (new feature #1): when Grocy is not configured, the `query_inventory`
  tool call should be unavailable and the LLM system prompt should note that inventory
  tracking is not active — don't offer to check stock if there's no stock system
- Shopping list generation (#8) still works without Grocy — just aggregates ingredients
  and formats them, skipping the "subtract what's on hand" step
- All non-Grocy features work fully: recipe generation, chat, batch cook planning,
  ideas list, preference profiles, recipe locking/saving, debriefs, nutritional awareness
- The goal is that a user who never sets up Grocy has a clean, complete experience with
  no dead buttons, no "configure Grocy to use this feature" messages, and no sense that
  they're missing the "real" version of the app
