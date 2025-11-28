terraform {
  required_providers {
    docker = {
      source  = "kreuzwerker/docker"
      version = "~> 3.0"
    }
  }
}

provider "docker" {}

resource "docker_image" "mcp" {
  name = "mcp-server:latest"

  build {
    context = "../mcpp-main"
  }

  lifecycle {
    ignore_changes = [
      build
    ]
  }
}

resource "local_file" "mcp_env_file" {
  filename = "/opt/mcp/.env"
  content  = "ENVIRONMENT=production\nLOG_LEVEL=info\nPORT=8000\n"
}



resource "docker_container" "mcp" {
  name  = "mcp-server"
  image = docker_image.mcp.image_id

  ports {
    internal = 8000
    external = 8000
  }

  # Correct bind mount block
  mounts {
    target = "/app/.env"
    source = "/opt/mcp/.env"
    type   = "bind"
  }

  restart = "always"

  # Runtime health check
  healthcheck {
    test     = ["CMD", "curl", "-f", "http://localhost:8000/health"]
    interval = "30s"
    timeout  = "5s"
    retries  = 3
  }
}
