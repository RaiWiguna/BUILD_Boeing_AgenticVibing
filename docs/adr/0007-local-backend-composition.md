# 0007 — API-owned local A/B composition

Status: accepted untuk local engineering; provider/release acceptance pending.
Tanggal: 10 Oktober 2026.

## Context dan decision

Source coexistence tidak menghubungkan private B repositories, reducer dan worker
ke scoped A transactions. Frozen1.0.0 tidak membawa rich private intent/audio
provenance; AS_KNOWN worker context juga menyembunyikan unknown availability pada
batch offline. Maintenance/retention A-only menolak B tables dengan benar.

Composition root memasang code-owned A/B catalog, guarded repository extensions,
server-bound DEBRIEF StagePolicy, frozen projections dan private versioned intent
submission. API tetap satu SQLite writer. B audio executor memakai HTTP ports dan
canonical accepted-payload hash bersama. AUDIO hanya memerlukan local rights;
cloud stages tetap disabled di development tanpa binding provider. Snapshot/purge
serta maintenance memakai exact registered catalog; migration analysis.0005
additive tanpa menulis ulang history. Provider/key tidak disediakan composition.

## Rationale, alternatives dan impact

Memperluas frozen DTO diam-diam, memberi worker akses SQLite, atau menyelundupkan
private payload ke text fields merusak authority/compatibility. Private codec dan
public projection menjaga frozen surface; data asal tetap lengkap dan scoped.
DEBRIEF dipilih server dan masuk policy fingerprint; client tidak memperoleh truth
atau admin authority. Default AS_KNOWN policy lama tetap memiliki fingerprint lama.
Exact table inventory mempertahankan fail-closed terhadap unknown storage.

Konsekuensi: normalized analysis local acceptance bukan raw SDK acceptance; current
composition belum menyediakan semua query/option/signal/correction workflows.
AS_KNOWN tetap menolak unknown availability; coverage/role yang belum authoritative
UNKNOWN. Report rendering ephemeral memerlukan live export rights. Maintenance
harus offline, journal current, roots privat dan account/grant review setelah restore.

## Validation, risks dan follow-up

Real API/SQLite/FFmpeg integration, review/export permissions/idempotency,
nonempty backup/restore serta purge/current-tombstone replay diuji dengan disposable
synthetic fixtures. Forged audio provenance ditolak tanpa artifact promotion.
Frozen contracts/schema drift serta standalone A/B checks terpisah. Lihat
[engineering evidence](../testing/integration-local-evidence.md) dan
[run guide/limitations](../development/backend-integration.md).

Provider transport/account/model/region/rights/quality, full scenarios/capacity,
public client freeze dan G-BE tetap follow-up; automated local checks tidak
membuktikan provider, domain atau operational validation.
