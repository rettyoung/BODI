/* Grid Docket master workbook, built in the browser with ExcelJS.
   A line-for-line port of tracker/build_tracker.py; parity is tested in CI
   (.github/workflows/xlsx-parity.yml) against the Python build. Keep them in step. */
(function (root) {
  const COLUMNS = ["Date","Event ID","Utility","Jurisdiction","Subject","Venue","Instrument","Document","Headline",
    "Takeaway","Status","Next Milestone","Next Date","Materiality","Confidence","Appeal","Superseded","Upfront Costs",
    "Rates","Term","Speed","Curtailment","Deliverability","Supply/Demand","Market Participation","Source URL"];
  const LEVERS = COLUMNS.slice(17, 25);
  const SUBJECTS = ["Large Load Customer Terms","Generation Supply","Rates & Cost Allocation","Law & Governance",
    "Interconnection Queue","Commercial Activity","Transmission & Delivery","Self-Supply & Colocation","Market Structure","Technology"];
  const VENUES = ["State Commission","Utility","Legislature","Market Operator","Court","Other State/Federal Agency","FERC",
    "Executive","Company / Industry Group","Misc"];
  const MATERIALITY = ["High / near-term","Medium / long-term"];
  const CONFIDENCE = ["Verified","Reported","Unverified"];
  const JURISDICTIONS = ["FERC","AL","AZ","GA","IL","KS","LA","MO","NC","NM","NV","OH","OK","PA","SC","TX","VA","WV","US-Federal"];
  const WIDTHS = [11,16,16,12,22,21,16,36,44,66,20,24,12,16,12,9,11,11,11,11,11,11,11,11,11,38];
  const NAVY = "FF1F3243", BAND = "FFF7F5F1", GRID = "FFD9D9D9", GREY = "FF6B7280";
  const MAT_FONT = {"High / near-term": ["FF9A2F2F", true], "Medium / long-term": ["FF8A6414", false]};
  const CONF_FILL = {"Verified": "FFE3F0E8", "Reported": "FFF8EED6", "Unverified": "FFF6E2E0"};
  const thin = {style: "thin", color: {argb: GRID}};
  const BORDER = {left: thin, right: thin, top: thin, bottom: thin};
  const CENTER = {horizontal: "center", vertical: "middle", wrapText: true};
  const fill = rgb => ({type: "pattern", pattern: "solid", fgColor: {argb: rgb}});

  function sortRows(rows) {
    // (Date, Event ID) descending; stable, so rows of one event keep their stored order
    return rows.map((r, i) => [r, i]).sort((a, b) =>
      a[0][0] < b[0][0] ? 1 : a[0][0] > b[0][0] ? -1 :
      a[0][1] < b[0][1] ? 1 : a[0][1] > b[0][1] ? -1 : a[1] - b[1]).map(x => x[0]);
  }
  function mostCommon(rows, idx) {
    const m = new Map();
    rows.forEach(r => m.set(r[idx], (m.get(r[idx]) || 0) + 1));
    return [...m.entries()].map((e, i) => [e[0], e[1], i]).sort((a, b) => b[1] - a[1] || a[2] - b[2]).map(e => e[0]);
  }

  function build(ExcelJS, inputRows, asof) {
    const rows = sortRows(inputRows);
    const n = rows.length + 1;
    const wb = new ExcelJS.Workbook();
    const ws = wb.addWorksheet("Tracker", {views: [{state: "frozen", xSplit: 2, ySplit: 1}]});
    ws.addRow(COLUMNS);
    ws.getRow(1).height = 34;
    ws.getRow(1).eachCell({includeEmpty: true}, c => {
      c.font = {name: "Arial", size: 9, bold: true, color: {argb: "FFFFFFFF"}};
      c.fill = fill(NAVY); c.alignment = CENTER; c.border = BORDER;
    });
    let band = false, last = null;
    rows.forEach(r => {
      if (r[1] !== last) { band = last !== null ? !band : false; last = r[1]; }
      const vals = r.slice(0, 26).map((v, i) => (i >= 17 && i < 25) ? ((v === 1 || v === "1") ? 1 : null)
                                                 : (v === undefined || v === "" ? null : v));
      const row = ws.addRow(vals);
      row.height = 76;
      for (let ci = 1; ci <= 26; ci++) {
        const c = row.getCell(ci);
        c.font = {name: "Arial", size: 9}; c.alignment = CENTER; c.border = BORDER;
        if (band) c.fill = fill(BAND);
      }
      const m = row.getCell(14), mf = MAT_FONT[m.value];
      m.font = mf ? {name: "Arial", size: 9, bold: mf[1], color: {argb: mf[0]}} : {name: "Arial", size: 9};
      const cc = row.getCell(15);
      if (CONF_FILL[cc.value]) cc.fill = fill(CONF_FILL[cc.value]);
    });
    // ExcelJS treats width 9 as "default" and omits it; 9.001 is written and renders identically.
    WIDTHS.forEach((w, i) => { ws.getColumn(i + 1).width = w === 9 ? 9.001 : w; });
    ws.autoFilter = `A1:Z${n}`;

    const s = wb.addWorksheet("Summary");
    s.getColumn(1).width = 44; s.getColumn(2).width = 12;
    const A = col => `Tracker!$${col}$2:$${col}$${n}`;
    let r = 1;
    const put = (a, b, o = {}) => {
      const size = o.size || 10;
      const ca = s.getCell(r, 1); ca.value = a;
      ca.font = Object.assign({name: "Arial", size, bold: !!o.bold, italic: !!o.italic}, o.color ? {color: {argb: o.color}} : {});
      if (b !== undefined && b !== null) {
        const cb = s.getCell(r, 2);
        cb.value = (typeof b === "string" && b.startsWith("=")) ? {formula: b.slice(1)} : b;
        cb.font = {name: "Arial", size, bold: !!o.bold};
      }
      return r++;
    };
    const blank = () => { s.getCell(r, 1).font = {name: "Arial", size: 11}; r++; };
    const distinct = new Set(rows.map(x => x[1])).size;
    const baseline = rows.filter(x => String(x[1]).startsWith("E-20260918")).length;
    put("GRID DOCKET — MASTER TRACKER", null, {bold: true, size: 13});
    put(`Row store through ${asof || rows[0][0]}: ${distinct} events / ${rows.length} rows. ` +
        `Baseline 7 Nov 2025 to 18 Sep 2026 (${baseline} rows), all three phases plus the gap-closing second pass; ` +
        `weekly sweeps thereafter. Materiality floor High and Medium only.`, null, {size: 9, italic: true, color: GREY});
    put("Event ID prefix E-20260918 = loaded as baseline, not observed in flight. Later prefixes are the discovery " +
        "date of the sweep that found the item. Rows sharing an Event ID are ONE event exploded across entities and " +
        "jurisdictions — count events, not rows.", null, {size: 9, italic: true, color: GREY});
    blank();
    put("Scale", "Count", {bold: true});
    const rRows = put("Rows (entity exposures)", `=COUNTA(${A("A")})`, {bold: true});
    const rEv = put("Distinct events", `=SUMPRODUCT((${A("B")}<>"")/COUNTIF(${A("B")},${A("B")}&""))`, {bold: true});
    put("Avg rows per event", `=IFERROR(B${rRows}/B${rEv},0)`);
    const block = (title, col, values) => {
      blank(); put(title, "Count", {bold: true});
      const first = r;
      values.forEach(v => put(v, `=COUNTIF(${A(col)},A${r})`));
      put("TOTAL", `=SUM(B${first}:B${r - 1})`, {bold: true});
    };
    const withVocab = (order, vocab) => order.concat(vocab.filter(v => !order.includes(v)));
    block("Materiality (rows)", "N", MATERIALITY);
    block("Confidence (rows)", "O", CONFIDENCE);
    block("Subject (rows)", "E", withVocab(mostCommon(rows, 4), SUBJECTS));
    block("Venue (rows)", "F", withVocab(mostCommon(rows, 5), VENUES));
    blank(); put("Lever (rows)", "Count", {bold: true});
    LEVERS.forEach((lv, i) => put(lv, `=COUNTIF(${A(String.fromCharCode(65 + 17 + i))},1)`));
    blank(); put("(multi-select — exceeds row count)", null, {size: 8, italic: true, color: GREY});
    block("Jurisdiction (rows)", "D", withVocab(mostCommon(rows, 3), JURISDICTIONS));
    blank(); put("Flags (rows)", "Count", {bold: true});
    put("On appeal", `=COUNTIF(${A("P")},"Yes")`);
    put("Superseded", `=COUNTIF(${A("Q")},"Yes")`);
    wb.calcProperties.fullCalcOnLoad = true;
    return wb;
  }
  const api = {build, COLUMNS};
  if (typeof module !== "undefined" && module.exports) module.exports = api; else root.GridDocketXlsx = api;
})(typeof window !== "undefined" ? window : globalThis);
