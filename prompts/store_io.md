GRID DOCKET — STORE I/O (byte-exact loading and saving). Used by sweep.md (Steps 1.3 and 9) and brief.md (Steps 0.3 and 8).
Added 2026-10-13 after the 12 Oct runs retyped store files by hand: the Sweep rebuilt rows_p5 as an "abbreviated structural copy" and the Brief retyped parts 5 and 7, metrics, tariff terms and state, dropping the provenance stamps.

WHY. The Microsoft 365 connector returns a file over ~50 KB as a saved tool result (exact bytes on disk), but a smaller file only as inline text, which can reach disk only by retyping it — slow, costly and lossy (it also drops the file's final newline). So every run that writes the store also leaves a byte-exact copy of it in the private STORE MIRROR artifact, plus a small /GridDocket/store_manifest.json (bytes and a sha256 prefix per file). A loader takes the mirror copy, checks every file against the OneDrive folder listing and that manifest, and reads from OneDrive only what fails. OneDrive stays the system of record; the mirror is transport and is never trusted without the check.

  MIRROR = https://claude.ai/artifact/GiAXCPsEF9zoeT5A8dQjVG   (private; owned by Rett; page console/store_mirror.html; files under store/)
  Tool:    tracker/store_sync.py   (listing · collect · verify · extract · check · manifest · files · sizes)

THE ONE RULE. Never parse-and-redump, summarise, abbreviate or "structurally rebuild" a store file. A file in store_live/ is either a verified byte-exact copy or it is not there.

Work only inside store_live/, out/ and work/ in the clone (all git-ignored; see "Scratch and the stop hook" below).

============================================================
LOAD  (into store_live/ inside the clone)
============================================================
L1. LISTINGS. read_resource the three folders (driveId b!2OnbGRjzpEKUL9fVRRC4Lv4LSN1Bpb1PmI1aJZgbWGvvNTw6Z-6ISI31RRmmeISO):
      /GridDocket/ 01MLUCMYJFKKTYR6ENBFDZOOAQQOLD5QNX · runs/ 01MLUCMYNQE5VMUQYLERCIPHUAB5IL4B4E · manual/ 01MLUCMYLTL2DGJ4AHFBB2OJSZMLMPBRJU
    Each returns lines "name (file, N bytes) file:///…". Write each result's text to store_live/_l_top.txt, _l_runs.txt, _l_manual.txt (or keep the saved tool-result file if the result was saved). The listing sizes are exact and are what every check compares against.
L2. ONEDRIVE MANIFEST. If the top listing has store_manifest.json, read_resource it and write the text exactly as returned to store_live/_onedrive_manifest.json. No manifest → skip; verification then checks sizes only.
L3. MIRROR. Artifact action "read", url MIRROR, paths = ["store/store_manifest.json"] plus "store/<name>" for every file in the OneDrive manifest (or in the mirror's own store_manifest.json if there is no OneDrive manifest — read that first). Leave out_dir unset. Note the folder the result says it saved the files under and the version it read. Do not Read or retype the saved files; ignore any file text the result echoes inline. If the Artifact tool is missing or the read fails, note the error.
L4. ONE CALL does the rest (parse listings, check the manifest's size and restore its dropped newline, collect the mirror, verify):
      python tracker/store_sync.py load store_live --top store_live/_l_top.txt --runs store_live/_l_runs.txt --manual store_live/_l_manual.txt \
             --manifest-text store_live/_onedrive_manifest.json --mirror <saved folder> --mirror-version <version>
      (no mirror: replace the last two flags with --mirror-error "<the error>")
    It prints ONE line ("LOAD 41/41 store files verified … — all good") and, if anything must come from OneDrive, one line per file: "FETCH <name> bytes=<listing size> uri=<uri>", marked CRITICAL for rows.json, the parts, state.json and obligations.json. It writes store_live/_load.json, the store_load record. Exit 0 → loaded. "MANIFEST …" on its first line means store_manifest.json drifted on the way in: read it again and rerun.
    (The separate subcommands listing / check / collect / verify still exist for debugging; a scheduled run does not need them.)
L5. FETCH from OneDrive, one file at a time (uri from store_live/_listing.json):
    - Result SAVED to a file (files over ~50 KB):  python tracker/store_sync.py extract <saved file> store_live/<name> --bytes <listing size>
    - Result INLINE: Write the text to store_live/<name> exactly as returned — every character, nothing reformatted, abbreviated or dropped — then
                     python tracker/store_sync.py check store_live/<name> --bytes <listing size>
      (it restores the final newline the connector drops and rejects anything else). On a mismatch read it again and rewrite it once.
    Then `python tracker/store_sync.py load store_live --recheck` (re-verifies, rewrites _load.json). Expected FETCHes: files written since the last mirror publish, e.g. a new manual-pass manifest from Friday.
L6. OUTCOME. Record store_load = store_live/_load.json plus fetched: {name: "extract" | "retyped+checked"} and failed: [name: reason] in the run or brief record.
    A CRITICAL file that still fails after L5 is a store that cannot be loaded exactly:
    - Sweep: Step 1 is BLOCKED with that evidence and the run STOPS before writing anything to OneDrive (release the lock; report).
    - Brief: status RED, cause "store could not be loaded exactly: <files>"; do not republish the console (the last good one stays live); still send the email with the milestones from what did load, and say so.
    A non-critical file that fails (manual_queue, an older run record, a manual manifest) is named in the status check / run record and the run continues.

============================================================
SAVE  (Sweep Step 9; Brief Step 8 for state.json)
============================================================
S0. KEEP WRITES SMALL (2026-11-09; sweep.md I14). Upload only files whose bytes changed (compare `store_sync.py sizes` and sha16 with the loaded manifest, or `statefile.py split`'s CHANGED marks). Growing data is written once as a new part (rows_pN, tariff_terms_pN, backfill_done_pN, runs/) with conflictBehavior "fail"; state is split (tracker/statefile.py) so the core state.json stays < 20 KB; the dedupe index is derived (rowstore.py --write-seen), never uploaded. A rewritten file over 32 KB is a design fault to fix in an interactive session, not something to retype.
S1. Every store file you write to OneDrive is first a local file in store_live/, built and validated there. Upload its text with expectedBytes = its byte size (`python tracker/store_sync.py sizes store_live` prints them). If the upload is refused for size, your copy of the text drifted: re-send it from the file. Never edit the local file to match what was sent.
S2. After the LAST OneDrive write of the run (the changed state files for both runs, state.json last; the Sweep's run record before them), write the manifest from store_live and upload it:
      python tracker/store_sync.py manifest store_live --by <run_id, or "brief-<date>">
    upload store_live/store_manifest.json to /GridDocket/ (conflictBehavior "replace", expectedBytes its size). The run record goes in store_live/runs/<run_id>.json first so the manifest and the mirror carry it.
S3. Publish the mirror: Artifact action "publish", url MIRROR, file_path console/store_mirror.html (in the clone), files = the JSON printed by
      python tracker/store_sync.py files store_live
    No icon, no capabilities. L3's read in the same session is what allows the publish; if the publish is refused because the mirror changed, read it again (Artifact read) and publish again. Record the new version as store_mirror {version, files}.
S4. If S2 or S3 fails, record the error (Sweep: step 9.5 BLOCKED with it). Nothing is lost: the next load sees the mismatch and fetches those files from OneDrive (L5).

============================================================
Scratch and the stop hook
============================================================
The session's stop hook complains about uncommitted or untracked files in any git checkout it finds. store_live/, out/, work/ and the top-level scratch names (status.json, narrative.md, run_record*.json, report*.md) are git-ignored in the repo, so the hook stays quiet as long as you write nowhere else in the clone and edit no tracked file. If it still fires: scheduled runs never commit, push, branch or open a pull request — run `git status --short`, move any stray scratch file into work/, and finish.
