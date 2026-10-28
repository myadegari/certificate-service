"""Test package marker.

No infrastructure stubs are needed at import time: the Mongo/S3/Redis
clients constructed at module scope in core.storage and worker are lazy
(no network I/O until the first command), and pytest's pythonpath setting
(repo root, configured in pyproject.toml) makes `import worker` work.
"""
