# Elzar v2 Plan: Conversational Meal Planning & Batch Cook Workflow

This is the revised implementation plan, incorporating decisions from design review.
See `enhancement-request.md` for the original feature descriptions.

---

## Key Design Decisions

These decisions override or refine the original enhancement request:

**Chat is the landing page.** Not just another nav item — Chat replaces the current
Generator as the default view. The Generator stays as a "Quick Recipe" shortcut in the
nav for one-off use. The standalone Meal Planner page is retired; meal planning
(weekly and batch cook) happens through Chat and Prep Cook Sessions.

**Ideas list is a Chat sidebar.** Not a separate nav item. Ideas live in a collapsible
sidebar panel within the Chat page, accessible via tool calls and direct UI interaction.
This keeps navigation lean and ideas contextually close to where they're discussed.

**Freezer inventory is Grocy-only.** No standalone SQLite fallback for inventory tracking.
Users who want freezer/inventory features need Grocy configured. This avoids building a
parallel inventory system and keeps Grocy as the single source of truth for stock.

**No tool-call fallback for non-capable models.** Instead of building a structured-JSON
fallback parser, add a clear disclaimer in Settings (under model configuration) that the
Chat feature requires a model with tool/function call support. The Generator and other
form-driven features continue to work with any model.

**Chat gets collapsible parameter controls.** A collapsible header at the top of the Chat
page with sliders/checkboxes similar to the Generator (cuisine, effort, servings, calorie
target, equipment, etc.). These set defaults for the session — the LLM uses them as
context when generating recipes, but the user can override via conversation.

**Preference document stays lean (~2000 tokens max).** The user preference profile is
injected into every LLM prompt. To avoid eating context window on smaller models, the UI
should guide users toward concise, high-signal descriptions rather than exhaustive lists.

---

## Navigation (Post-v2)

```
Chat (landing page, 💬)
Quick Recipe (Generator, ⚡)
Inventory (Grocy import, 📦) — hidden when Grocy not configured
History (📜)
Profiles (👤)
Settings (⚙️)
```

The Meal Planner nav item is removed. Prep Cook Sessions are accessible from Chat
(via conversation or a dedicated "New Batch Cook" action) and browsable from History.

---

## Implementation Order

Build bottom-up so each feature is fully functional when shipped. Chat is the capstone
that ties everything together — by the time we build it, all the tools have real
services behind them.

### Phase 1: Foundations

**1. User Preference Profile** (enhancement #7) — COMPLETED, SIMPLIFIED
- Merged preferences into the existing per-person profiles (renamed "Preferences & Restrictions")
  instead of a separate document. Each person's profile now covers dietary restrictions AND
  cooking style, likes/dislikes, calorie goals, etc.
- Added a "Household Preferences" field (always-on, injected into every prompt) for shared
  context: where you shop, kitchen quirks, cooking schedule, food philosophy.
- Backend: `user_preferences` table (single-row document) + API at `/api/preferences`
- Frontend: Compact textarea on the Profiles page above person profiles
- Injected into all LLM prompts (recipe, meal plan, advice, regeneration)

**2. Recipe Locking & Saving** (enhancement #12) — COMPLETED
- New DB columns on `recipes`: `is_locked`, `is_saved` (bookmarked), `tags`, `parent_recipe_id`
- Lock/unlock toggle (🔒/🔓) in recipe display and History list
- Locked recipes: disable Regenerate button, show badge in History
- Saved/bookmarked recipes (and locked): exempt from `cleanup_old_recipes`
- Manual recipe entry: "+ Add Recipe" button in History header
- **Tags**: DB column added now (JSON text), but full tag management UI deferred to
  Ideas List (#3) or Chat. Tags and Ideas are closely related — building a tagging UI
  here and then rebuilding it for Ideas would be redundant. For now, tags are stored
  but not exposed in the UI.
- **Variant linking**: `parent_recipe_id` column added now. Simple "Based on: #N" display
  in recipe detail view. Full variant tree UI (parent shows list of variants, etc.)
  deferred to Chat's `copy_and_edit_recipe` tool, which is the primary way variants
  get created. No point building a variant browser before the creation mechanism exists.

**3. Ideas List** (enhancement #3)
- New `ideas` table: id, name, notes, tags (JSON), calorie_estimate_range, status
  (idea/planned/tested/favorite), created_at, updated_at
- API endpoints: full CRUD + search/filter
- UI: Built as a sidebar panel (will live in Chat page later; for now, accessible from
  a temporary standalone route or the Profiles page during development)
- Inline editing, tag toggles, status transitions
- "Promote to recipe" action (pre-fills Generator)

### Phase 2: Inventory & Batch Cooking

**4. Freezer Inventory Tracking** (enhancement #5) — Grocy-only — COMPLETED
- Reads Grocy's freezer locations (any location with `is_freezer` flag)
- Dashboard view within Inventory Manager: product name, quantity, unit, location,
  freeze age, and best-before expiry with color-coded badges
- Quick consume: "-1 portion" and "Use All" buttons per item
- Search/filter freezer contents
- Setup locations automation now creates Freezer alongside Pantry and Fridge
- Backend: `get_freezer_stock()` on GrocyClient aggregates stock entries by freezer location,
  `GET /api/inventory/freezer` and `POST /api/inventory/freezer/consume` endpoints
- Hidden when Grocy is not configured (section loads silently)

**5. Prep Cook Sessions** (enhancement #2) — BACKEND ONLY, UI DEFERRED TO CHAT
- Decision: No standalone Prep Cook page. Batch cook planning is inherently
  conversational — you always want to discuss and iterate before committing.
  The standalone form-driven UI has the same problem as the Meal Planner.
- Backend infrastructure built and ready for Chat tool calls:
  - DB table: `prep_cook_sessions` + `prep_session_id` FK on `recipes`
  - LLM prompt: generates recipes with portions, reheating/storage instructions,
    unified prep day timeline, and aggregated shopping list
  - API: `POST /api/prepcook/generate`, `GET /api/prepcook/`, `GET /api/prepcook/{id}`,
    `DELETE /api/prepcook/{id}`
  - Pydantic models: `PrepCookRequest`, `PrepCookSessionResponse`, etc.
- Frontend API functions wired up, ready for Chat to call
- Chat will expose this via `create_prep_cook_session` tool call

**6. Shopping List Enhancements** (enhancement #8) — DEFERRED TO CHAT
- Shopping list aggregation is built into the prep cook LLM prompt (grouped by
  store section, deduped/summed across recipes)
- Full enhancements (Grocy inventory subtraction, copy-to-clipboard, standalone
  generation from arbitrary recipe sets) will be added as Chat tool calls
- Chat tool call: `generate_shopping_list(recipe_ids[])`

### Phase 3: Conversational Interface

**7. Chat Interface** (enhancement #1) — COMPLETED (non-streaming)
- New DB tables: `chat_sessions`, `chat_messages`
- Full multi-turn chat with persistent message history across sessions
- Session list sidebar: name, browse, resume, rename, delete past sessions
- Collapsible parameter controls at top (cuisine, effort, servings, calories, budget,
  equipment, profiles, Spice Weasel, inventory toggles)
- Full response mode (SSE streaming deferred to future enhancement)
- Spice Weasel personality toggle in compact header
- System prompt includes: user preferences, Grocy inventory summary (if configured),
  session parameters, dietary profiles, behavioral rules
- 13 LLM tool calls implemented:
  **Read/Query:** `get_recipe`, `search_recipes`, `get_ideas_list`, `query_inventory`,
  `query_freezer`, `get_user_preferences`
  **Create:** `create_recipe`, `create_prep_cook_session`, `generate_shopping_list`,
  `add_to_ideas_list`
  **Edit:** `edit_recipe`, `update_idea`, `update_user_preferences`
- Tool call loop: max 5 iterations, server-side execution
- Grocy-dependent tools auto-hidden when Grocy not configured
- Preference prompting: LLM must ASK before calling `update_user_preferences`
- Chat is now the app's landing page at `/`, Generator moved to `/generator` as "Quick Recipe"
- Navigation updated: Chat, Quick Recipe, Inventory, History, Profiles, Settings
- Meal Planner removed from nav (still accessible at `/meal-planner`)

**8. Iterative Recipe Editing** (enhancement #4) — COMPLETED
- `edit_recipe(id, instructions)` tool call — surgical LLM-powered changes preserving the rest
- `copy_and_edit_recipe(id, instructions)` — explicitly fork a recipe as a variant
- `last_edited` timestamp column on recipes, updated on every edit
- Lock-aware: locked recipes auto-fork via `copy_and_edit_recipe` with `parent_recipe_id` set
- Variant linking preserved: new variants reference their parent recipe
- The existing Regenerate button remains for full regeneration on Quick Recipe page

### Phase 4: Polish & Enhancement

**9. Grocy-Free Experience Audit** (enhancement #13) — COMPLETED
- Thorough audit of every page for Grocy-dependent UI
- Generator: Consume, Add Missing, Save to Grocy buttons already hidden (grocyConfigured)
- History: no Grocy-dependent buttons — already clean
- Inventory Manager: added full Grocy-not-configured guard with link to Settings
- Settings: Grocy setup section shows warning banner and disables buttons when unconfigured;
  added model disclaimer about Chat requiring tool/function call support
- Chat: inventory/freezer tools auto-filtered; system prompt notes Grocy unavailability;
  inventory toggles already hidden in collapsible controls
- MealPlanner: Grocy buttons already wrapped in grocyConfigured check
- Goal achieved: clean experience with no dead buttons when Grocy not configured

**10. Post-Session Debrief** (enhancement #10) — COMPLETED
- `debriefs` table: stores what was cooked, what worked, what didn't, what was wasted, notes
- Optional link to prep cook session via `prep_session_id`
- Chat tool calls: `log_debrief` (record feedback), `get_debriefs` (retrieve past feedback)
- System prompt injection: 3 most recent debriefs included in every chat, so the LLM
  learns from past sessions when planning new ones
- Feedback loop: plan → cook → eat → debrief → better plan

**11. Bulk Ingredient Prep Tracking** (enhancement #6)
- Track pre-made base ingredients (garlic blend, caramelized onions, etc.)
- Shopping list generation accounts for bulk prep inventory
- Recipes can reference bulk ingredients
- Low-stock reminders

**12. Opportunistic Batching Suggestions** (enhancement #9)
- Chat behavior: detect equipment use or upcoming cooks, suggest piggybacking
- Factor in ideas list, freezer gaps, available equipment
- Combined prep plans layering opportunistic work into existing cooks

**13. Nutritional Awareness Dashboard** (enhancement #11)
- Per-portion calorie/macro estimates
- Freezer-wide nutritional summary
- Gap flagging (low fiber, heavy sodium, etc.)
- Daily calorie planning across multiple meals

---

## Technical Notes

**Database migrations:** The current approach uses inline ALTER TABLE statements in
`database.py`. New tables (ideas, chat_sessions, chat_messages, prep_cook_sessions,
prep_cook_recipes) follow this pattern. New columns on `recipes` (is_locked, is_saved,
tags, parent_recipe_id) added via ALTER TABLE with defaults.

**Streaming:** Chat requires SSE for good UX. Backend uses FastAPI `StreamingResponse`.
Frontend uses `fetch` with `ReadableStream` reader (not Axios, which doesn't support SSE).

**Tool call execution loop:** When the LLM returns tool calls, the backend executes them,
sends results back to the LLM, and streams the final response. This loop runs server-side
to keep the frontend simple.

**Context management:** The Chat system prompt grows with preferences, inventory, ideas,
and session context. Monitor total token usage and implement summarization or truncation
strategies if context gets too large for smaller models.
