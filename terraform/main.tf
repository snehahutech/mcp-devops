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


resource "docker_container" "mcp" {
  name  = "mcp-server"
  image = docker_image.mcp.image_id

  ports {
    internal = 8000
    external = 8000
  }

  # Mount .env inside container for idempotency
  volumes = [
    "/opt/mcp/.env:/app/.env"
  ]

  restart = "always"

  # Runtime health check (state management)
  healthcheck {
    test     = ["CMD", "curl", "-f", "http://localhost:8000/health"]
    interval = "30s"
    timeout  = "5s"
    retries  = 3
  }
}
