# Version bumping

This repository contains a small helper script to increment the add-on version recorded in `config.yaml`.

Usage:

```powershell
python scripts\bump_version.py        # increments patch (e.g. 1.4.2 -> 1.4.3)
python scripts\bump_version.py patch  # same as above
python scripts\bump_version.py minor  # increments minor (e.g. 1.4.2 -> 1.5.0)
python scripts\bump_version.py major  # increments major (e.g. 1.4.2 -> 2.0.0)
python scripts\bump_version.py --set 2.0.0  # set an explicit version
```

Recommended workflow

- Before committing or releasing changes, run the bump script to increase the version.
- The script edits `config.yaml` in place. Commit that change together with your code changes.

Notes

- The script uses a simple regex to update the `version` field in `config.yaml`. Keep the `version` line in the common format, e.g. `version: "1.4.2"` or `version: 1.4.2`.
