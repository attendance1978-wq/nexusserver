# Release and LTS policy

NexusServer uses calendar versioning: `YY.MINOR.PATCH` (`26.3.0` is the third
minor line of 2026; `PATCH` is bumped for fixes).

| Release | Channel | Status |
| --- | --- | --- |
| 26.4.x | Stable | Latest feature release (adds nexuspy) |
| **26.3.x** | **LTS** | Current LTS line, released 2026-10-28; fixes only |
| 26.2.x | Stable | Superseded by 26.3; upgrade recommended |

## What "LTS" means for 26.3.x

- **Supported for 24 months** after the 26.3.0 release (until **2028-10-28**).
- **Only fixes:** security fixes, bug fixes and documentation corrections ship as
  `26.3.1`, `26.3.2`, ... No new features.
- **No breaking changes.** Public API (everything importable from `nexusserver`,
  `nexusserver.middleware`, `nexusserver.database` and `nexusserver.security`),
  the CLI flags, `Config` fields and documented behaviour stay compatible for the
  whole line. Anything deprecated is announced in the changelog and keeps working.
- **Python support:** 3.9 and newer are supported for the whole line, even
  after upstream end-of-life of an old Python version.
- **Security reports** go through the process in [SECURITY.md](../SECURITY.md);
  fixes are released as a patch version on the LTS line first.

## Non-LTS releases

Feature releases (`26.4`, `26.5`, `27.1`, ...) may add features and change behaviour,
following the changelog. Use them if you want the newest features; stay on the LTS
line if you want stability.

New features land in regular releases, never on the LTS line: nexuspy shipped in
26.4.0, so 26.3.x does not contain it. Security fixes are applied to both lines.

## Checking the version at runtime

```python
import nexusserver
nexusserver.__version__       # "26.4.0"
nexusserver.__version_info__  # (26, 4, 0)
nexusserver.LTS               # True only on the LTS line (26.3.x)
```

```bash
nexusserver --version         # nexusserver 26.4.0   (26.3.x prints "(LTS)")
```

## Upgrading from 26.2

26.3 is a drop-in upgrade, with these behaviour notes:

- **Keep-alive is now on** (`Config.keep_alive=True`). Each open connection occupies
  a worker thread while idle (up to `keep_alive_timeout`, default 5 s). Raise
  `max_workers` for many concurrent clients, or set `keep_alive=False` for the 26.2 behaviour.
- Chunked request bodies are accepted instead of rejected with 501.
- `--reload` now works.
