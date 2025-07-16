
data "terraform_remote_state" "shared" {
  backend   = "s3"
  workspace = "default"

  config = {
    bucket  = "nhse-odin-${var.account}-terraform"
    key     = "shared/main/main.tfstate"
    region  = var.region
    profile = var.profile
  }
}

locals {
  shared = data.terraform_remote_state.shared.outputs
}
