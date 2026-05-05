# Building TaskMajor from Source

> **Alternative to Docker:** Build and run TaskMajor directly on your machine or server using Python and uv.

## When to Use This Guide

- You prefer not to use Docker
- You want to develop or contribute to TaskMajor
- You have a heterogeneous infrastructure without Docker
- You want more control over the Python environment

## Prerequisites

### System Requirements

- **Python 3.12 or higher**
  ```bash
  python3 --version
  ```
  
  If you need to install Python, see [python.org](https://www.python.org/downloads/)

- **TaskWarrior CLI**
  ```bash
  which task
  ```
  
  If not installed, see [TaskWarrior Installation](https://taskwarrior.org/download/build/)

- **Git**
  ```bash
  git --version
  ```

### Optional Dependencies

- **uv** (faster package manager, recommended)
  ```bash
  curl -LsSf https://astral.sh/uv/install.sh | sh
  ```
  
  Or with pip:
  ```bash
  pip install uv
  ```

---

## Installation Steps

### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/taskmajor.git
cd taskmajor
```

### 2. Install Dependencies

#### Option A: Using uv (Recommended)

```bash
uv sync
```

This creates a virtual environment and installs all dependencies.

#### Option B: Using pip

```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

pip install -e .
```

### 3. Configure TaskMajor

Edit `taskmajor/config/config.yaml` to set your TaskWarrior paths and server settings. Defaults work for most setups.

See [Configuration](../getting-started/configuration.md) for available options.

### 4. Test the Installation

```bash
uv run -m taskmajor.bootstrap.server
```

**Expected output:**
```
INFO:    Starting MCP server on stdio
INFO:    TaskMajor MCP Server ready
```

Press `Ctrl+C` to stop.

---

## Running the Server

### Development Mode (Interactive)

```bash
cd /path/to/taskmajor
uv run -m taskmajor.bootstrap.server
```

Runs the MCP server in the foreground. Useful for testing and debugging.

### Background Mode (systemd)

Create a systemd service to run TaskMajor as a daemon:

**File:** `/etc/systemd/system/taskmajor.service`

```ini
[Unit]
Description=TaskMajor MCP Server
After=network.target

[Service]
Type=simple
User=YOUR_USERNAME
WorkingDirectory=/path/to/taskmajor
ExecStart=/usr/local/bin/python -m taskmajor.bootstrap.server
Restart=on-failure
RestartSec=5

# Optional: environment variables
Environment="TASKMAJOR_LOG_LEVEL=INFO"
Environment="TASKMAJOR_TASKDATA=/home/YOUR_USERNAME/.task"

[Install]
WantedBy=multi-user.target
```

Replace `YOUR_USERNAME` and `/path/to/taskmajor` with actual values.

**Enable and start:**

```bash
sudo systemctl enable taskmajor
sudo systemctl start taskmajor
sudo systemctl status taskmajor
```

**View logs:**

```bash
sudo journalctl -u taskmajor -f
```

### Background Mode (Supervisor)

Using `supervisor` (for systems without systemd):

**File:** `/etc/supervisor/conf.d/taskmajor.conf`

```ini
[program:taskmajor]
command=/usr/local/bin/python -m taskmajor.bootstrap.server
directory=/path/to/taskmajor
user=YOUR_USERNAME
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=/var/log/taskmajor.log
```

**Start:**

```bash
sudo supervisorctl reread
sudo supervisorctl update
sudo supervisorctl start taskmajor
```

---

## Updating

To update TaskMajor to the latest version:

```bash
cd /path/to/taskmajor
git pull
uv sync
```

Then restart the service:

```bash
sudo systemctl restart taskmajor
# or
sudo supervisorctl restart taskmajor
```

---

## Troubleshooting

### "Python 3.12+ required"

Install a newer Python version:

```bash
# macOS
brew install python@3.12

# Ubuntu/Debian
sudo apt-get install python3.12

# Fedora
sudo dnf install python3.12
```

### "task command not found"

Install TaskWarrior:

```bash
# macOS
brew install task

# Ubuntu/Debian
sudo apt-get install task

# From source
https://taskwarrior.org/download/build/
```

### "ModuleNotFoundError"

Reinstall dependencies:

```bash
uv sync --refresh
# or
pip install --upgrade --force-reinstall -e .
```

### "Permission denied"

Ensure the user running TaskMajor can access TaskWarrior data:

```bash
chmod 755 ~/.task
chmod 644 ~/.task/*.json
chmod 644 ~/.taskrc
```

Or configure a custom TaskWarrior path:

```bash
export TASKMAJOR_TASKDATA=/path/to/shared/task
export TASKMAJOR_TASKRC=/path/to/shared/taskrc
uv run -m taskmajor.bootstrap.server
```

---

## Performance Considerations

### Resource Usage

TaskMajor is lightweight:
- **Memory**: ~50-100 MB (baseline)
- **CPU**: Minimal (I/O-bound)
- **Disk**: ~10 MB for code + TaskWarrior data

### Optimizations

1. **Use `uv` instead of `pip`** — Faster dependency resolution
2. **Enable connection pooling** — If deploying with reverse proxy
3. **Monitor TaskWarrior performance** — `task diagnostics`

---

## Advanced Configuration

### Custom Python Executable

If you have multiple Python versions:

```bash
/usr/local/bin/python3.12 -m venv venv
source venv/bin/activate
pip install -e .
uv run -m taskmajor.bootstrap.server
```

### Using Poetry

If you prefer Poetry over uv/pip:

```bash
poetry install
poetry run python -m taskmajor.bootstrap.server
```

### Running Behind a Reverse Proxy

If using nginx/Apache to proxy TaskMajor:

```nginx
server {
    listen 80;
    server_name taskmajor.example.com;

    location / {
        proxy_pass http://127.0.0.1:8888;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

---

## Next Steps

- [Configuration](../getting-started/configuration.md) — Customize with environment variables
- [Observability](../developer/observability.md) — Enable tracing and monitoring
- [Docker Alternative](docker.md) — If you change your mind about containers
- [Troubleshooting](https://github.com/yourusername/taskmajor/issues) — Common issues

---

## Support

- **Issue with build?** [Report it](https://github.com/yourusername/taskmajor/issues)
- **Want to contribute?** See [Contributing](../developer/contributing.md)
