## Project TODOs — clarified and detailed

1) Fix upload custom fields
- Summary: Ensure `scripts/5_upload_to_cms.py` includes product settings fields currently missing in uploads: `customField1`, `customField2`, `customField17`, `customField18`, and `customField20` (map from your `final_products` CSV/JSON).
- Why: These fields are part of product site settings and must be present for correct product display and metadata on the Dandomain site.
- Implementation notes:
  - Use the settings patch endpoint pattern: `/products/{productNumber}/sites/{siteId}/settings` (see `Dandomain_API_docs/productdata_patch_example.md`).
  - Update `settings.items[0]` for the target `languageId`. Only patch the missing fields (preserve existing values).
  - Validate by fetching the product GET and verifying `settings.items[0]` contains the new `customFieldX` values.
- Acceptance criteria:
  - API returns 2xx for the settings patch.
  - A subsequent GET shows the fields set exactly as input.

2) Send `unitNumber` in upload
- Summary: Include `unitNumber` (stored as `ACTIVE_UNIT_ID` in `final_products`) in the `settings.items[0]` payload when creating or updating products.
- Why: `unitNumber` is used by the store to identify product units and affects presentation and ordering.
- Implementation notes:
  - Add `unitNumber` to the same `settings` payload used for custom fields.
  - Confirm mapping between `ACTIVE_UNIT_ID` and the API `unitNumber` value.
- Acceptance criteria:
  - After upload, a GET for the product returns the expected `unitNumber` inside `settings.items[0]`.

3) Refactor offer management
- Summary: Rework offer (tilbud) logic so the process is deterministic and easy to test: prepare operations, then execute them in strict sequence (DELETE → POST → PUT, etc.).
- Why: Current flow sometimes reuses deleted price IDs or mixes operations and causes 404s / inconsistent state.
- Implementation notes:
  - Build a small operation model: each operation is one of `{ delete, create, update }` with the exact payload to send.
  - For deletes include identifiers when available (`id`, `periodId`, `specialOfferPeriodId`) to ensure server matches the intended row; treat DELETE 404 as non-fatal (row already removed).
  - For creates do not include an `id` (let the API create the new row); include `b2bGroupId`=`1` or `-2` as needed.
  - For updates use PUT and include only fields to change (e.g., `specialOfferPrice`, `specialOfferPeriodId`).
  - Refer to `Dandomain_API_docs/ProductDataPrice_delete.md`, `ProductDataPrice_post.md`, `ProductDataPrice_put.md` for payload examples.
- Acceptance criteria:
  - 404s are handled gracefully for deletes; the system still creates the replacement tier and updates the offer row.
  - The logs show clear sequences: DELETE (optional 404) → POST (new tier) → PUT (single-unit offer update).

4) Split offer workflow scripts
- Summary: Separate preparation and execution steps into two scripts for clarity and safety: `scripts/offers_prepare.py` and `scripts/offers_apply.py`.
- Why: Preparation-only mode allows review and dry-run without calling production APIs; execution can be gated behind confirmation.
- Implementation notes:
  - `offers_prepare.py` reads inputs (category/product selection or file), inspects current product prices and settings, and writes a JSON file listing operations.
  - `offers_apply.py` reads the operations JSON and executes operations in order; add `--dry-run` and `--yes` flags.
  - Add logging, per-product result summary and optional `--limit N` concurrency option.
- Acceptance criteria:
  - Prepare step runs without performing API changes and writes an operations JSON.
  - Apply step reads the file and performs the operations when `--dry-run` is not set.

5) Improve table UI interactions
- Summary: Make the Streamlit table less chatty and more explicit: lock non-editable columns, only allow editing `Ny Tilbudspris`, and add a single “Recalculate” button for margins/savings. Keep bulk select/drag options for adding items to the queue.
- Why: Current UI recalculates on every edit and tries to perform many operations at once, which is confusing and performance-heavy.
- Implementation notes:
  - Use `st.data_editor` column configuration to disable editing for all but `Ny Tilbudspris`.
  - Add a `Beregn priser ud fra margin` style control to compute `Ny Tilbudspris` for all rows, and a separate `Recalculate` button to refresh `Ny Margin %` and `Besparelse %` for the whole set.
  - Keep `Mark all` / `Unmark all` controls; optionally add a multi-select for categories + “Add to queue” button (drag/drop is optional, multi-select is simpler to implement).
  - Hide `Tilbud Label` from the editor; set it automatically on create.
- Acceptance criteria:
  - Edits to `Ny Tilbudspris` are stored but do not trigger global recalculation until user explicitly presses `Recalculate`.

6) Implement offer CREATE flow (explicit API sequence)
- Summary: Implement and document the exact sequence for creating a new offer on a product.
- Steps (canonical):
  1. PATCH `/products/{productNumber}/sites/{siteId}/settings` → set `customField3 = "Tilbud"` (see `productdata_patch_example.md`).
  2. PATCH `/products/{productNumber}` → add `OFFER_CATEGORY_NUMBER` to the product categories array.
  3. GET `/products/{productNumber}?include=prices` → fetch current prices (collect `id`, `period`, `quantity`, `b2bGroupId`, `unitPrice`).
  4. DELETE `/products/{productNumber}/prices` → delete the tier row where `b2bGroupId = -2` and `quantity > 1`. Include `id`/`periodId` in delete payload if present.
  5. POST `/products/{productNumber}/prices` → create the same tier row but with `b2bGroupId = 1`. Do not include `id` (let API create a new row).
  6. PUT `/products/{productNumber}/prices` → update the single-unit row to set `specialOfferPrice` and `specialOfferPeriodId = 1`.
- Notes:
  - See `Dandomain_API_docs/ProductDataPrice_post.md` and `ProductDataPrice_put.md` for sample payload shapes and required fields.
- Acceptance criteria:
  - After the flow, `customField3 == "Tilbud"`, the offer category is present, the volume tier exists under `b2bGroupId = 1`, and the single-unit price has `specialOfferPrice` and `specialOfferPeriodId = 1`.

7) Implement offer REMOVE flow (explicit API sequence)
- Summary: Implement and document the reverse sequence for removing an offer.
- Steps (canonical):
  1. PATCH `/products/{productNumber}/sites/{siteId}/settings` → set `customField3 = ""`.
  2. PATCH `/products/{productNumber}` → remove `OFFER_CATEGORY_NUMBER` from categories.
  3. GET `/products/{productNumber}?include=prices` → fetch current prices.
  4. DELETE `/products/{productNumber}/prices` → delete the tier row where `b2bGroupId = 1` and `quantity > 1`.
  5. POST `/products/{productNumber}/prices` → recreate the tier row with `b2bGroupId = -2`.
  6. PUT `/products/{productNumber}/prices` → update the single-unit row to clear `specialOfferPeriodId` (and `specialOfferPrice` if required).
- Acceptance criteria:
  - After the flow, `customField3` is empty, offer category removed, the volume tier exists under `b2bGroupId = -2`, and `specialOfferPeriodId` is cleared.

8) Add API docs references
- Summary: Link code and README steps to specific files in `Dandomain_API_docs/` so that implementers and automated tests have canonical examples.
- Implementation notes:
  - For each offer step above, add a short reference to the matching file in `Dandomain_API_docs/`.
- Acceptance criteria:
  - README and/or `docs/OFFER_WORKFLOW.md` contains direct links to the example files.

9) Add tests for price flow
- Summary: Create unit or integration tests that mock the API to validate the CREATE and REMOVE flows and the edge case where DELETE returns 404.
- Implementation notes:
  - Mock `APIManager._make_api_request` or use a small HTTP mock server.
  - Test cases: normal create flow, create when DELETE returns 404, remove flow, idempotency tests.
- Acceptance criteria:
  - Tests run locally without contacting production and reproduce the previously observed failure modes (404 after delete) to verify fixes.
