# AGENTS.md

Rebuild *Battle for Middle-earth II* (`game.dat` 1.06) as clean, readable C++ compiling 1-to-1 with Visual C++ 7.1 (`cl.exe 13.10.3077`).
Swarm prompts & playbooks: [docs/swarm.md](docs/swarm.md) · [docs/agents.md](docs/agents.md) · [tools/README.md](tools/README.md) · [RULES.md](RULES.md).

## Repo map

| Path | Role |
|---|---|
| `src/` | Game TUs (`src/unk/O<addr>.cpp` = unconfirmed filename; **`src/Code/Tools/` is exporter code, banned by G1**) |
| `include/` | Shared headers (`include/Draft/` = temporary layouts awaiting promotion); unified names: `Matrix4x4` (`WWMath/Matrix4.h`), `DXWrapper` (`WW3D2/dxwrapper.h`), `BitChannelClass` (`WW3D2/motchan.h`) |
| `baseline/game.dat` | Retail 1.06 binary (**ground truth**, `VA = RVA + 0x400000`) |
| `reference/` | Zero Hour source (names/structure reference only; never compiled; follow `baseline/game.dat` on any conflict) |
| `worklist/` | Priority queues: `unwritten_with_zero_hour_counterpart.tsv`, `files.tsv`, `draft_headers_in_use.tsv` |
| `config/`, `expected/`, `tools/`, `ci/` | Ledger (`config/map.json`), check records, local gate (`tools/gates/gate.py`), local judge (`tools/judge/bin/judge.py`), CI — **never edit in contributor PRs** |

## Zero-human auto-landing lanes (Ready fork PRs, non-owner token only)

- **Narrow (`src/` only, fastest):** 1–8 files (`<= 3` substantive per G6), `<= 8` affected TUs, `250/author` & `1,200/day` (`BFME_ADMISSION_DAILY_*`, same-day per-commit dedup). Auto-merges on `source rules` + `Boat` pass (`Inline virtual` pending can land; fresh failure blocks).
- **Wide (`include/`):** up to 60 `src/`+`include/` paths, `30/author` & `120/day` (`BFME_ADMISSION_WIDE_DAILY_*`, H10). Auto-merges on `Boat` + `Header rules` (H1–H10) pass: H2 ledger-matched methods, access updates, H5 plain non-inline/non-pure virtual overrides (no default args/private-base errors), non-virtual-base abstract classes, and H5 typed-access member witnesses. Anything outside H5's subset (`> 4` classes, unproved layout/base edits, virtual-base abstract, H9 ledger requests) holds safely for a maintainer.
- **Never touch canary PRs** (`#3`, `#4`, `#21`, `#27`, `#29` — intentional permanent refusal controls).

## Workflow (local tools allowed & encouraged)

1. **Clone & isolate:** `git clone` (or fork & clone) freely; branch off fresh `upstream/main` (one `git worktree` per subagent).
2. **Check claims first:** `gh pr list -R Open-BFME/BFME2-Rebuild --state open --search "<RVA|file>"` + `git grep` `src/`/`include/`. Claim before coding in a Draft PR (`Claim: <RVA|path>`).
3. **Verify against retail:** disassemble `baseline/game.dat` and run local math/offset/layout scripts in `/tmp` freely.
4. **Write clean C++:** directly under the owning `// FUNCTION:` line with real types/shared headers and zero regressions. Add `NOTICE` attribution if adapting Zero Hour code; cite the retail vtable slot in the commit/PR for virtuals; add `Removed-Declaration: <Qualified::Name>` trailer when removing a declaration.
5. **Local compile pre-checks (recommended, saves Boat quota):** bootstrap the exact VC7.1 (`13.10.3077`) compiler + STLport/SDK headers outside Git with `python3 tools/setup_local_toolchain.py` ([tools/README.md](tools/README.md)), then compile/diff locally with `cl.exe` or `tools/judge/bin/judge.py` before pushing. Keep all scratch files/objects outside Git; never paste raw disassembly dumps. Hosted Boat is the sole authoritative proof (include `head_sha` + `gate.py` `policy_digest` in subagent handoffs for pre-flight audit).
6. **Mandatory local gate on committed `HEAD` BEFORE pushing:**
   ```sh
   python3 tools/gates/gate.py . <upstream-main-ref> HEAD --json /tmp/gate-<slug>.json
   ```
   Must exit `0` with `"status": "pass"`. Never spend a Boat slot on a G1–G8 failure.
7. **Push & mark Ready:** enable `Allow edits by maintainers`; put claim + concise evidence in the PR body (auto-admission ignores Drafts).
8. **Iterate cleanly (max 3 Boat rounds):** wait on `Held: daily limit` / `checking the source rules` / `runners unavailable` (auto-retried); on green `Landing: Held: merge-forbidden` (HTTP 403 after workflow edits on `main`), merge `upstream/main` and push once. If still refused after 3 rounds, log findings in `docs/hard_rows.md` or an issue and close the PR.

## Hard rules (G1–G8 & H1–H10)

- **G1 Paths:** existing `src/` (never `src/Code/Tools/`) & eligible `include/` only; no new `.cpp`; UTF-8 regular files.
- **G2 Annotations:** never edit `// FUNCTION:` / `// DATA:` / `// cl*` / `// stlport*` / `// psdk`; only `// dxsdk` or `// platformsdk` additions allowed at top of existing non-vendored `.c`/`.cpp` (LF, no duplicates/trailing space).
- **G3 Forbidden:** no `__asm`, `__emit`, `#pragma optimize`, or banned casts/pragmas.
- **G4 Types:** no `void *` or raw integer stand-ins where real engine types exist.
- **G5 Comments:** no hex addresses (`0x...`), dates, or author/model tags in new source comments (evidence belongs in commits/PRs).
- **G6 Scope:** one logical item per PR (`<= 3` substantive source files, except Draft promotions).
- **G7 One definition:** never duplicate a class/struct/global already defined in `include/`.
- **G8 Names:** no address-derived identifiers (`rva...`, `sub_...`, `g_00...`).
- **H1–H10 Headers:** wide Boat parity (H1), compiled symbol-to-ledger match (H2), qualified identities (H3), complete declaration diff (H4), layout & virtual-slot proof (H5), inline bodies (H6), Draft hygiene (H7), inlining/macros (H8), ledger-request hold (H9), wide budget (H10).
