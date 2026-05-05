Mounting a custom profile into the TaskMajor container

Overview

This document explains how to mount a custom TaskMajor profile into the container image so it coexists with the built-in profiles and can be selected with the --profile flag. This approach does not overwrite the built-in profiles and keeps host-provided profiles read-only inside the container.

Recommended approach

- Prepare a profile directory on the host with the required structure (manifest.yaml and optional subfolders):

  myprofile/
  ├─ manifest.yaml
  ├─ prompts/
  ├─ resources/
  └─ instructions/

- Mount the host directory into the container under the built-in profiles tree so it does not hide existing package profiles:

  /app/taskmajor/profiles/myprofile

- Start the container with --profile myprofile so TaskMajor resolves it using the built-in search path.

Docker run example

```bash
docker run --rm \
  -v /host/path/myprofile:/app/taskmajor/profiles/myprofile:ro \
  -p 8888:8888 \
  myorg/taskmajor:latest \
  --profile myprofile
```

Docker Compose excerpt

```yaml
services:
  taskmajor:
    image: myorg/taskmajor:latest
    ports:
      - "8888:8888"
    volumes:
      - /host/path/myprofile:/app/taskmajor/profiles/myprofile:ro
    command: ["--profile","myprofile"]
```

Notes and tips

- Use :ro in the volume mount to avoid accidental overwrites from inside the container.
- If the container runs as a non-root user, ensure the mounted files are readable by that user (adjust UID/GID or permissions on host).
- Verify the profile inside the container before starting TaskMajor if needed:

  docker run --rm -it \
    -v /host/path/myprofile:/app/taskmajor/profiles/myprofile:ro \
    myorg/taskmajor:latest \
    sh -c "ls -la /app/taskmajor/profiles && cat /app/taskmajor/profiles/myprofile/manifest.yaml"

- TaskMajor resolves profiles in the following order:
  1. Absolute path (if passed as --profile and exists)
  2. User config: ~/.config/taskmajor/profiles/<name>/
  3. Built-in package: /app/taskmajor/profiles/<name>/

- You can either mount the profile and pass the name (recommended) or pass an absolute path to the mounted profile with --profile /app/taskmajor/profiles/myprofile.

Related docs

- Profiles and composition: docs/profiles.md
