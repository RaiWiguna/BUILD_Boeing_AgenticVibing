# Local backup, restore dan maintenance

A09.3 menggunakan SQLite backup API dan private source-referenced assets. Hentikan API/worker sebelum maintenance: exclusive owner locks menolak pemilik aktif. Tidak ada provider call. Semua command memakai `.venv/bin/python -m flowlens.cli.maintenance`.

| Command | Argumen wajib | Hasil |
| --- | --- | --- |
| check | --database --raw --artifacts --imports --journal | Integrity/FK/schema, recovery retention dan inventory counts |
| backup | argumen check + --destination | Bundle baru dan receipt manifest_hash |
| verify | --backup --manifest-hash | Hash semua bytes, supported schema/catalog dan exact tree |
| restore | argumen verify + --journal --target | Target baru terisolasi; sumber tidak ditimpa |
| prune | argumen verify + --journal | Hapus bundle ketika copied expiry/current tombstone mewajibkan |
| cleanup | --parent | Hapus kandidat crash bertanda lease; skip kandidat aktif |

Argumen path menunjuk root privat yang sudah diinisialisasi host. Journal **current** harus memiliki ledger/head valid dan berada di luar backup/restore; jangan memakai salinan journal lama. Simpan receipt hash di tempat terpercaya terpisah. Hash memberikan integritas relatif terhadap receipt, bukan signature atau encryption. Parent tujuan milik OS user dan private; target harus baru. CLI hanya mencetak status/count/ID/hash dan error generik.

Backup menyalin committed WAL melalui SQLite API, raw package/inventory, live pending/accepted artifacts dan staged imports yang direferensikan. Manifest mencatat SHA/size, session/revision references, migration checksums, curated release dan expiry. Credential files/environment/ADC/keyfile tidak disalin. Database tetap mencakup account password hashes dan grants: bundle sensitif, **LOCAL_PRIVATE_UNENCRYPTED**. Encryption/off-host delivery dan jadwal operator VM belum diimplementasikan.

Restore memverifikasi sebelum publikasi, menjalankan current tombstones/expiry sebelum membuka sumber, menolak inventory SQL/namespace tak terdaftar, lalu membatalkan auth/context/worker credentials dan queued/retry/running jobs. Active reservations dikenai conservative charge dan dilepas; completed history, transcript/evidence, exports, revisions, grants dan replay checkpoint/cursor dipertahankan. Login/provisioning baru diperlukan. Grant/account state adalah snapshot point-in-time: perubahan permission/password setelah snapshot tidak seluruhnya direkonsiliasi. Review operator diperlukan sebelum promotion; restore bukan production promotion.

Frozen purge callbacks dapat didaftarkan melalui Python Maintenance/Snapshots.restore oleh composition owner; standalone CLI tidak memuat B. Namespace/tables yang belum dikenali ditolak. Test memakai fake analysis registration.

Publikasi memakai fsync file dan seluruh directory tree, rename atomik serta parent lock/fsync. Failure sebelum publish membersihkan staging; crash meninggalkan kandidat bertanda external lease yang dapat di-cleanup setelah lock dilepas. Cleanup tidak menghapus direktori tanpa marker. Jika audit backup gagal sesudah bytes durable, status BACKUP_DURABLE_AUDIT_PENDING menandai kebutuhan rekonsiliasi audit; bundle tetap valid.

Retirement memakai fsynced external PREPARED envelope sebelum rename/erase, sehingga retry bekerja meski manifest internal telah hilang. Bundle immutable dihapus seluruhnya ketika expiry terpendek/current session deletion mewajibkan. Jalankan prune sesuai removal_due_ms pada receipt dan setelah purge; tidak ada scheduler/daemon otomatis dan tidak ada klaim erasure salinan off-host. Marker REMOVED minimal tetap di parent untuk retry/audit. [Evidence](../testing/a093-evidence.md).
