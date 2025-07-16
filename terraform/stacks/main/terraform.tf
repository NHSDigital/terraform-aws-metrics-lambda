
provider "aws" {
  region  = var.region
  profile = var.profile

  default_tags {
    tags = {
      TagVersion         = "1"
      Programme          = "spinecore"
      Project            = "odin"
      DataClassification = "N/A"
      ServiceCategory    = "N/A"
      Tool               = "terraform"
      Provenance         = "${var.application}/${var.stack}/${var.deployment}"
    }
  }

}

terraform {
  backend "s3" {
    region  = "eu-west-2"
    encrypt = true
  }
}

data "terraform_remote_state" "core" {
  backend   = "s3"
  workspace = "default"

  config = {
    bucket  = "nhse-odin-${var.account}-terraform"
    key     = "core/main/main.tfstate"
    region  = var.region
    profile = var.profile
  }
}

locals {
  # tflint-ignore: terraform_unused_declarations
  account_vpc = data.terraform_remote_state.core.outputs.account_vpc
  # tflint-ignore: terraform_unused_declarations
  resources = data.terraform_remote_state.core.outputs.resources
}
