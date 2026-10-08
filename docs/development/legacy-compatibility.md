# Historical archive compatibility

Tanggal: 9 Oktober 2026. Profile yang didukung: `legacy-2660222-archive-1`. Audit statis menggunakan `git show 6e7bd3f^:backend/storage.py`, `backend/session.py`, `backend/models.py`, dan `backend/app.py`. Parent reset adalah commit `2660222`; source lama tidak dipasang kembali sebagai runtime.

## Archive conversion

Archive lama adalah SQLite tanpa migration ledger dengan tabel `sessions(id,metadata,status)`, `events(session_id,ordinal,data)`, `frames(session_id,sim_ms,sequence,public,private)`, dan `commands(session_id,command_id,request,response)`. Format lain tidak diasumsikan kompatibel. Host normal tetap menolak unversioned archive; konversi adalah maintenance action eksplisit ke **file berbeda**:

```sh
.venv/bin/python -m flowlens.cli.migrate_archive \
  --source /absolute/private/archive.sqlite3 \
  --target /absolute/private/converted.sqlite3
```

Command mengambil snapshot source melalui read-only SQLite transaction, termasuk committed WAL content, lalu menulis ke target melalui API-owned Database/UOW. Source tidak dibuka sebagai writer dan tidak dijalankan dengan constructor Archive lama yang mengubah status. Target baru memakai private permissions dan owner lock; semua import rows committed atomik. CLI mengeluarkan profile/digest/counts saja; failure tidak mencetak paths/JSON/SQL/credential.

Logical digest SHA-256 mencakup profile dan ordered rows beserta original JSON text, bukan hash main DB file yang dapat melewatkan WAL. Identical retry tidak menggandakan rows. Perubahan archive yang menggunakan legacy session ID yang sudah imported ditolak sebagai conflict; import tidak menimpa histori.

## ID dan data mapping

| Historis | Target | Disposition |
| --- | --- | --- |
| Session string ID | `platform_legacy_sessions.legacy_id` | Dipertahankan persis; mapped ke canonical platform UUID via UUIDv5 namespace tetap |
| Metadata/status | `platform_legacy_sessions` | Original JSON text/status tetap; READY/RUNNING/PAUSED mempunyai runtime_status INTERRUPTED tanpa auto-resume |
| Event ordinal/data | `platform_legacy_events` | Original ordinal dan JSON text tetap |
| Frame time/sequence/public | `platform_legacy_frames` | Original sim_ms/sequence/public text tetap |
| Frame private checkpoint | `platform_legacy_private_frames` | Terpisah, bukan bagian DTO/observer/provider/source ports |
| Command ID/request/response | `platform_legacy_commands` | Original ID/text tetap sebagai historical record, tidak dieksekusi |
| Import receipt | `platform_legacy_imports` | Profile/digest/counts; idempotent retry |

UUID namespace: `f9526f99-15d3-4f62-b8c5-22f48a7b3400`; name UUIDv5 adalah original session ID. String ID lama bukan UUID wire v1; alias mapping harus dipakai eksplisit pada compatibility readers A07, bukan silent coercion pada shared DTO.

Payload lama berada dalam quarantine tables. Import tidak menulis observed `platform_records`/stream events, tidak membuat account/grant, dan tidak mengirim provider payload. Metadata/public frame historis masih bisa mempunyai seed, nested metadata, assessments atau scenario hints; jangan memakai label "public" lama sebagai bukti aman untuk observer/AI. Eligibility/redaction/clock/unit adapters harus diterapkan sebelum compatibility reads pada A07. Availability historis tidak diciptakan; AS_KNOWN belum dapat diklaim dari archive ini. Private checkpoint/truth membutuhkan evaluator-only policy saat reader tersedia.

Validation memeriksa table/column inventory, integrity/FKs, unique row keys, valid finite JSON objects tanpa duplicate keys, supported status, metadata ID, event ordinal/time, frame time/sequence, command response ID dan session references. Limits awal: 1 juta rows total/128 MiB text; profile tambahan atau archive lebih besar membutuhkan implementation/measurement tersendiri. Original text disimpan tanpa reserialization.

## Auth dan routes lama

- `FLOWLENS_OPERATOR_KEY` serta file `runtime/operator-key.txt` tidak menjadi individual accounts/passwords; config baru menolak setting operator key lama.
- Seat/operator bearer tokens lama adalah in-memory hashed-token entries dengan expiry 8 jam; archive SQLite tidak menyimpan token/account credentials. Tidak ada token conversion atau grandfathered grants.
- `/api/v1/auth/operator`, seat minting dan mutating `/commands` lama tidak diaktifkan kembali. Host sekarang membalas 404. Individual bootstrap/login/logout/reset/deactivation berikutnya A02, grants/CSRF A03.
- Session/scenario/events/snapshot/report/stream serializers lama belum dipulihkan. Mapping read-only history/casing dan training-route compatibility merupakan A07; training commands bukan tool AI dan bukan scope live ATC.
- Simulator branch restoration menggunakan private checkpoint tidak dijalankan oleh migrator. Branch/what-if tetap optional dengan disposition sendiri.

Tidak melakukan migrasi terhadap data nyata/developer selama task ini. Penggunaan CLI terhadap archive milik operator tetap mengikuti source rights/retention/privacy. [Evidence A01.3](../testing/a013-evidence.md) membuktikan sintetik dan batasnya.
