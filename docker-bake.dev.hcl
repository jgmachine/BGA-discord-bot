# docker-bake.dev.hcl
group "default" {
  targets = ["bga-discord-bot"]
}

target "bga-discord-bot" {
  dockerfile = "Dockerfile"
  tags = ["docker.io/johrad/bga-discord-bot"]
  platforms = ["linux/arm64", "linux/amd64"]
}
