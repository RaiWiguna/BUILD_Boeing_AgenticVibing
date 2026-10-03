# FE — Frontend replay/review

**Owner-role:** Frontend. **Status:** `CURRENT_SOURCE` statis dan `TARGET/PROPOSED_CONTRACT`, 3 Oktober 2026. [Master](../README.md) · [Shared contracts](../shared-contracts.md).

## Objective dan output

Membangun UI replay offline terhadap typed adapter dengan fixture terlebih dahulu: context map/runway, timeline, raw/corrected transcript, deterministic evidence, highlights dan opsi evaluator. Output: `ReplayReviewAdapter`/read models, fixture dan API adapters yang kompatibel, components/pages/styles, review controls dan mekanisme explicit loading/error/degraded/auth states. BE menerima request bertipe; QA dapat menjalankan UI mock tanpa backend/inference.

## CURRENT/TARGET dan scope

| Label | Kondisi |
|---|---|
| CURRENT_SOURCE | React entry mengimpor `App` dan `styles.css` yang belum ditemukan; type TS/api helper/Vite config ada |
| CURRENT_SOURCE | `api<T>` cast response, tidak validasi runtime; Track TS kehilangan `received_ms/source/route`, Snapshot tidak mendeklarasikan layout |
| TARGET | Typed UI port dengan fixture/API adapter, map/timeline/evidence/reviewer states, scope-safe transcript/options playback |
| UNKNOWN | Layout/interface mitra, model/hardware readiness, evaluator capability UX final dan audio browser compatibility pada perangkat pengguna |

Included: synthetic/authorized source label, setup offline, review controls, SVG local-meter map, event/alert/transcript/reviewer lanes, evidence resolver, correct/confirm/dismiss/unresolved, debrief/export access. Existing synthetic training views bila dipakai mengikuti role/token current; options hanya pada replay evaluator. Excluded: fetching storage files dari page, recalculation detector, direct provider integration, production/live feed/audio capture, commands dari option text, domain UI seolah tervalidasi.

## Context packet

- [main.tsx](../../../frontend/src/main.tsx), [types.ts](../../../frontend/src/types.ts), [api.ts](../../../frontend/src/api.ts): actual entry/types/transport helper.
- [package.json](../../../frontend/package.json), [vite.config.ts](../../../frontend/vite.config.ts), [tsconfig.json](../../../frontend/tsconfig.json), [index.html](../../../frontend/index.html): available scaffold/build/proxy configuration.
- [app.py](../../../backend/app.py), [review.py](../../../backend/review.py), [session.py](../../../backend/session.py): actual snapshot/redaction/auth/seek/source IDs; baca saja untuk wire parity.
- [Plan](../../Knowledge-Review/ATC_FlowLens_Rencana_Teknis_MVP.md) §7.3/time, §12–13, §14.2: units/UI/empty-degraded/reconnect/historical frame.
- [AI addendum](../../Knowledge-Review/ATC_FlowLens_AI_Assist_Buddy_MVP_Prompt.md) §4–5: four work states, evidence/option review, confidence/badges dan mechanic acceptance.

Tidak ada FE tests/dashboard source yang ditemukan. Scripts build/typecheck ada, tetapi belum dijalankan.

## Modul/file ownership

FE sendiri mengubah `frontend/src/`, package/lock/tsconfig/Vite/index.html jika diperlukan. Struktur baru usulan, belum ada:

```text
frontend/src/
  App.tsx, styles.css
  contracts/replayReview.ts        # UI port, read models dan states
  adapters/fixtureReplayReview.ts # mock against SC-07
  adapters/apiReplayReview.ts     # wire decode/auth/paging/reconnect
  features/replay/                # timeline, controls, source context
  features/runway/                # SVG map dan observed/predicted evidence
  features/assist/                # transcript/candidate/evidence/reviewer panels
```

File port FE bukan duplicate backend schema authority; wire DTO mirror mengikuti SC-01–06 dan QA parity fixtures. FE mengadaptasi wire ke read model SC-07. Page/component tidak mengimpor backend/storage/provider, membuat headers atau membaca file fixture secara langsung. Existing `api.ts` tetap di adapter; perbaikan validate/error handling ditangani FE tanpa mengubah server responses.

## Inputs, outputs, kontrak dan consumer

| Boundary | Input | Output / consumer |
|---|---|---|
| SC-07 ReplayReviewAdapter | Source session/review ID, time/cursor, credentials/capability | Typed source/frame/timeline/evidence/candidates/UI states untuk pages |
| Source subscription | SC-02 direct full snapshots current | Read model sequence/revision/sim_ms/connection; tidak delta-merge data tak diketahui |
| Assist subscription | SC-06 versioned typed message | Job/transcript/highlight/option/review panel; separate assist sequence |
| Review control | START/PAUSE/SET_SPEED/SEEK current command | Server accepted revision/status; convert UI ms seek ke command value detik |
| Reviewer actions | SC-06 correction/decision + expected revision/request ID | Append-only revision/annotation; source state tidak berubah |
| Evidence click | Typed refs/source scope + analysis/time | Transcript/audio/event/alert detail dengan unresolved/privacy state bila inaccessible |

`FixtureReplayReviewAdapter` dan `ApiReplayReviewAdapter` implementasi port yang sama. Pilihan fixture/API explicit configuration; API outage tidak switch ke contoh synthetic diam-diam. Historical frame `sim_ms` tampil sebagai waktu data; requested/playback time terpisah. Metadata source ID tidak diganti Review ID. Review source-read token/capability terpisah dari existing review control token sebagaimana SC-06.

## Mock/stub/fixture mandiri

- Source synthetic dengan metadata/config/layout/tracks/clearances, frame before/after observations, deterministic alert/evidence IDs dan missing/stale variants.
- Timeline complete lewat mock `listEvents`, termasuk TRACK absent dari snapshot tail; same-time ordinals dan seek antara frames.
- Raw ASR/corrected segment pair, alternatives/null confidence/unknown speaker, highlight linked versus possible_link dan valid evaluator option.
- Adapter states loading/empty/ready/degraded/disconnected/unauthorized/conflict/error; AI unavailable tanpa kehilangan map/replay, source unavailable tanpa dummy fallback.
- Auth instructor evaluator replay, tower/ground/observer training, expired/cross-source denied, baseline stripped explanations.
- Audio synthetic sample bila tersedia kelak; transcript-only mock menampilkan audio unavailable, tidak berpura-pura playback audio berhasil.

Fixture port dapat berjalan seluruhnya tanpa BE/SD/AI. QA kelak memasok canonical bundle; FE memakai referensi/semantik SC fixture untuk mulai tanpa menunggu implementasi lain.

## Alur utama dan UI states

1. Setup memperlihatkan source kind/label, timebase/coverage/quality, source versions dan model/job availability yang tersedia. Hanya synthetic baseline atau authorized offline replay; tidak ada capture/live-connect action.
2. Pilih review/source; adapter mengautentikasi dan mendapatkan frame. Map SVG menggunakan public layout LOCAL_METRES/direction mapping; full footprint dan observed/last-known/prediction styles berbeda dengan label teks.
3. Timeline mengurutkan session receive time + ordinal, menampilkan sample/audio offset bila diperiksa. Lanes source communication, transcript, structured clearance, track, deterministic alert dan reviewer annotations berbeda. Raw ASR hypothesis, corrected revision dan unknown tidak disamakan.
4. Playback/seek memakai server review controls ketika API mode; mock punya clock sesuai kontrak. Source time/historical frames tidak dicampur dengan latency/UTC wall time. Audio seek berdasarkan mapping asset; unknown alignment membatasi sync dan menampilkan label.
5. Highlight yang terkait alert muncul di evidence panel alert yang sama; possible_link jelas sebagai kandidat. Opsi evaluator membuka rationale/evidence/preconditions/unknowns; tidak ada execute/send-clearance action.
6. Reviewer mengirim correction/decision setelah evidence inspection. Pending request state mencegah double submit; accepted server annotation menjadi revision baru. Conflict meminta refresh/reconcile, tidak menampilkan success buatan.
7. Debrief memperlihatkan source/model/rule/version, raw/corrected status dan limits. Export request sesuai scope BE; jangan mengambil instructor truth report untuk participant page atau model context.

| State / trigger | UI behavior |
|---|---|
| Loading / first load | Context skeleton/label; tidak memilih data pertama tanpa ID |
| Empty / source sukses zero events atau no speech | Jelaskan data kosong; berbeda dari failed job atau missing coverage |
| Degraded / stale/missing/alignment unknown | Badge source/last-known/unknown; tidak menulis runway clear |
| Disconnected / source WS loss | Last committed frame diberi disconnected/time label, reconnect resync; no fresh extrapolation |
| Assist unavailable/failed | Transcript/options panel failure/retry yang scoped; map/replay tetap usable |
| Unauthorized/expired | Hentikan subscriptions, clear restricted projection, access/session-expired state; role dropdown tidak memberi privilege |
| Conflict / stale revision | Preserve unsent correction, refresh revision, explicit retry baru; duplicate request tidak dimaknai review kedua |
| Evidence missing/inaccessible | Unresolved reference state, bukan event yang dibuat dari teks rationale |
| Unsupported schema/version | Adapter error; jangan unsafe cast/render |

## Verification teknis / readiness-to-integrate

1. Port adapter contract tests dengan canonical payloads memeriksa field/unit/version, current snapshot extra fields, null confidence, source vs Review ID, same-time events dan full history/evidence lookup.
2. FE typecheck/build kelak berhasil setelah scaffold dilengkapi; dependency tooling yang tidak terlihat dalam `package.json` diselesaikan sebagai kebutuhan FE, tanpa mengklaim instalasi/build sudah ada.
3. Native Python Playwright QA memakai mock mode untuk setup→seek→evidence→correction/review dan negative option-command path; keyboard/focus, visible labels/unknowns, layout clipping dan no unexpected console/network errors.
4. API adapter tests memeriksa first-message WS auth, repeated/out-of-order/gap sequences, reconnect full snapshot, cursor dedup, 401/403/409/422 detail errors, time conversion SEEK/branch.
5. UI/server integration menolak wrong source/token/capability, baseline private explanation leak, future transcript/event pada earlier frame dan candidate option pada training seats.
6. Evidence/raw versus corrected annotations tetap traceable setelah refresh/restart; AI outage tidak menghentikan source review. Fixture mode dan API mode terlihat berbeda agar contoh data tidak dianggap hasil backend.

Readiness-to-integrate berarti UI bekerja terhadap port dan mocks dengan semantics yang sama, lalu API runtime dihubungkan/diuji. Screenshot dan build bukan oracle domain atau bukti operational validation. Semua checks tersebut masih target implementasi.

## Asumsi dan unknown

**ASSUMPTION:** React/TypeScript/Vite dan SVG map sesuai plan; source/review labels selalu terlihat, motion/alarm tidak memberi authority ke candidate AI. Format wire existing dipertahankan di adapter sampai versi tambahan benar-benar tersedia.

**UNKNOWN:** audio codec/browser/hardware riil, finalized evaluator capability delivery dan proxy/internet restrictions mitra, exact imported layout. Dapat mulai dengan mock tanpa mengarang live runtime readiness.
