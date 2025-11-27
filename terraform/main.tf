terraform {
  required_providers {
    docker = {
      source  = "kreuzwerker/docker"
      version = "~> 3.0"
    }
  }
}

provider "docker" {}

# Build Docker image from ../mcpp-main (where Dockerfile is)
resource "docker_image" "mcp" {
  name = "mcp-server:latest"

  build {
    context = "../mcpp-main"
  }
}

# Run container from that image
resource "docker_container" "mcp" {
  name  = "mcp-server"
  image = docker_image.mcp.image_id

  ports {
    internal = 8000  # inside container (Dockerfile EXPOSE)
    external = 8000  # on your laptop (localhost:8000)
  }

  restart = "always"
}
