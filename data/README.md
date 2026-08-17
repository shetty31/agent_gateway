Project data directory for test automation and VRAM outputs.

Layout:

- `quarantine/structural/` — incoming or invalid payloads are written here in Hive-style partitions (year=/month=/day=).
- `approved/` — VRAM-approved payload batches are written here in Hive-style partitions (year=/month=/day=).

Both services in `src/` write to `PROJECT_ROOT / "data"` so this directory must live at the repository root.
Create or seed files under these folders as needed; the services will create dated partition folders automatically.
