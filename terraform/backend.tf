terraform {
  backend "remote" {
    hostname = "app.terraform.io"
    organization = "YOUR_ORG_NAME"

    workspaces {
      name = "mcp-devops-state"
    }
  }
}
