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
    Each returns lines "name (file, N bytes) file:///…". Write each result's text to store_live/_l_top.txt, _l_runs.txt, _l_manual.txt (or pass the saved tool-result file if the result was saved) and run:
      python tracker/store_sync.py listing store_live/_l_top.txt               --out store_live/_listing.json
      python tracker/store_sync.py listing store_live/_l_runs.txt   --prefix runs/   --out store_live/_listing.json
      python tracker/store_sync.py listing store_live/_l_manual.txt --prefix manual/ --out store_live/_listing.json
    The listing sizes are exact and are what every check below compares against.
L2. ONEDRIVE MANIFEST. If the listing has store_manifest.json, read_resource it, write the text exactly as returned to store_live/_onedrive_manifest.json and run
      python tracker/store_sync.py check store_live/_onedrive_manifest.json --bytes <its listing size>
    (re-read once on a mismatch). No manifest in the listing → skip; verification then checks sizes only.
L3. MIRROR. Artifact action "read", url MIRROR, paths = ["store/store_manifest.json"] plus "store/<name>" for every file in _onedrive_manifest.json (or in the mirror's own store_manifest.json if there is no OneDrive manifest — read that first). Leave out_dir unset. The result says which folder it saved the files under; then
      python tracker/store_sync.py collect <that folder> store_live
    Do not Read or retype the saved files; ignore any file text the result echoes inline. If the Artifact tool is missing or the read fails, record the error (store_load.mirror) and treat every file as a FETCH in L5.
L4. VERIFY.
      python tracker/store_sync.py verify store_live --listing store_live/_listing.json --manifest store_live/_onedrive_manifest.json
    It checks every store file OneDrive lists (rows.json, every rows_p*.json, state, metrics, tariff_terms and its deltas, obligations, seen_index, manual_queue, the newest four run records, the manual-pass manifests): present, bytes equal to the listing, and sha16 equal to the manifest. Exit 0 → loaded. Otherwise it prints one FETCH line per file to read from OneDrive, marked CRITICAL for rows.json, the parts, state.json and obligations.json.
L5. FETCH from OneDrive, one file at a time (uri from store_live/_listing.json):
    - Result SAVED to a file (files over ~50 KB):  python tracker/store_sync.py extract <saved file> store_live/<name> --bytes <listing size>
    - Result INLINE: Write the text to store_live/<name> exactly as returned — every character, nothing reformatted, abbreviated or dropped — then
                     python tracker/store_sync.py check store_live/<name> --bytes <listing size>
      (it restores the final newline the connector drops and rejects anything else). On a mismatch read it again and rewrite it once.
    Then run L4 again. Expected FETCHes: files written since the last mirror publish, e.g. a new manual-pass manifest from Friday.
L6. OUTCOME. Record store_load {mirror_version, verified, fetched: {name: "extract" | "retyped+checked"}, failed: [name: reason]} in the run or brief record.
    A CRITICAL file that still fails after L5 is a store that cannot be loaded exactly:
    - Sweep: Step 1 is BLOCKED with that evidence and the run STOPS before writing anything to OneDrive (release the lock; report).
    - Brief: status RED, cause "store could not be loaded exactly: <files>"; do not republish the console (the last good one stays live); still send the email with the milestones from what did load, and say so.
    A non-critical file that fails (seen_index, manual_queue, an older run record, a manual manifest) is named in the status check / run record and the run continues.

============================================================
SAVE  (Sweep Step 9; Brief Step 8 for state.json)
============================================================
S1. Every store file you write to OneDrive is first a local file in store_live/, built and validated there. Upload its text with expectedBytes = its byte size (`python tracker/store_sync.py sizes store_live` prints them). If the upload is refused for size, your copy of the text drifted: re-send it from the file. Never edit the local file to match what was sent.
S2. After the LAST OneDrive write of the run (state.json for both runs; the Sweep's run record before it), write the manifest from store_live and upload it:
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
