# Docker Deployment

Deploy TaskMajor in a container with Docker.

## Build the Image

```bash
docker build -t taskmajor:latest .
```

The Dockerfile uses a multi-stage build:
1. **Builder stage** — Compiles TaskWarrior from source
2. **Runtime stage** — Minimal Python image with TaskWarrior

## Run the Container

### Basic

```bash
docker run -p 8888:8888 taskmajor:latest
```

### With Environment Variables

```bash
docker run -p 8888:8888 \
  -e TASKMAJOR_LOG_LEVEL=DEBUG \
  -e TASKMAJOR_LOG_FORMAT=text \
  taskmajor:latest
```

### With Volume Mounts

```bash
docker run -p 8888:8888 \
  -v ~/.taskrc:/config/taskrc \
  -v ~/.local/share/task:/data/task \
  -e TASKMAJOR_TASKRC=/config/taskrc \
  -e TASKMAJOR_TASKDATA=/data/task \
  taskmajor:latest
```

## Docker Compose

The repository ships a ready-to-use compose file at `docker/docker-compose.yaml`:

```yaml
services:
  taskmajor:
    image: taskmajor:latest
    volumes:
      - ./app/config:/app/config:ro   # mount your config.yaml here
      - taskmajor_data:/data/task     # persistent task data

volumes:
  taskmajor_data:
```

Place your `config.yaml` in `./app/config/config.yaml` before starting. Run with:

```bash
docker compose -f docker/docker-compose.yaml up -d
```

## Production Setup

### With Observability

```bash
docker run -p 8888:8888 \
  -e TASKMAJOR_OTEL_ENABLED=true \
  -e TASKMAJOR_OTEL_EXPORTER_ENDPOINT=http://otel-collector:4317 \
  -e TASKMAJOR_OTEL_SERVICE_NAME=taskmajor-prod \
  taskmajor:latest
```

### With Reverse Proxy

Use Nginx to expose TaskMajor on port 80:

```nginx
upstream taskmajor {
    server taskmajor:8888;
}

server {
    listen 80;
    server_name taskmajor.example.com;
    
    location / {
        proxy_pass http://taskmajor;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

## Troubleshooting

### "TaskWarrior command not found"
The Dockerfile builds TaskWarrior from source. If this fails, check the build logs.

### "Config file not found"
Ensure volume mounts are correct and paths exist on the host.

### Permission errors
Check volume mount permissions:

```bash
ls -la ~/.taskrc ~/.local/share/task
```
