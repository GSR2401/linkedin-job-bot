/**
 * LinkedIn Job Tracker — Auto-delete rows on status change.
 *
 * Setup (one-time):
 *   1. Open your Google Sheet
 *   2. Extensions → Apps Script
 *   3. Delete any existing code, paste this entire file, click Save
 *   4. Run setupDropdowns() once (Run → Run function → setupDropdowns)
 *      and approve the permissions prompt
 *   5. Done — the onEdit trigger is automatic from here on
 *
 * Behaviour:
 *   - Status column shows a dropdown: New / Applied / Skipped / Interview
 *   - Change any row to "Applied" or "Skipped" → row is deleted immediately
 *   - Change to "Interview" → row is highlighted green (kept for tracking)
 */

var SHEET_NAME   = "Jobs";
var STATUS_COL   = 11;   // Column K
var HEADER_ROWS  = 1;

// ── Auto-delete trigger (fires on every cell edit) ────────────────────────────
function onEdit(e) {
  var sheet = e.source.getActiveSheet();
  if (sheet.getName() !== SHEET_NAME) return;
  if (e.range.getColumn() !== STATUS_COL) return;
  if (e.range.getRow() <= HEADER_ROWS) return;

  var status = (e.value || "").trim();

  if (status === "Applied" || status === "Skipped") {
    sheet.deleteRow(e.range.getRow());
  } else if (status === "Interview") {
    // Highlight the whole row green so it stands out
    sheet.getRange(e.range.getRow(), 1, 1, sheet.getLastColumn())
         .setBackground("#b7e1cd");
  }
}

// ── One-time setup: add dropdown validation to Status column ─────────────────
function setupDropdowns() {
  var ss    = SpreadsheetApp.getActiveSpreadsheet();
  var sheet = ss.getSheetByName(SHEET_NAME);
  if (!sheet) {
    SpreadsheetApp.getUi().alert('Sheet "' + SHEET_NAME + '" not found.');
    return;
  }

  var lastRow  = Math.max(sheet.getLastRow(), 2);
  var range    = sheet.getRange(HEADER_ROWS + 1, STATUS_COL, lastRow - HEADER_ROWS, 1);

  var rule = SpreadsheetApp.newDataValidation()
    .requireValueInList(["New", "Applied", "Skipped", "Interview"], true)
    .setAllowInvalid(false)
    .build();

  range.setDataValidation(rule);

  // Set all blank status cells to "New"
  var values = range.getValues();
  for (var i = 0; i < values.length; i++) {
    if (!values[i][0]) values[i][0] = "New";
  }
  range.setValues(values);

  SpreadsheetApp.getUi().alert("✓ Dropdowns applied to " + (lastRow - HEADER_ROWS) + " rows.");
}
