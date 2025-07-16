
module "example" {
  source = "../../modules/example"

  shared      = local.shared
  account_vpc = local.account_vpc
  resources   = local.resources

  example = "test"

}
