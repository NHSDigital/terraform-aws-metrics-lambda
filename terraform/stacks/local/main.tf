
module "example" {
  source  = "../../modules/example"
  example = "test"
}

module "example_bucket" {
  source = "terraform-aws-modules/s3-bucket/aws"

  version = "4.3.0"

  bucket = "example-bucket"
  acl    = "private"

  control_object_ownership = true
  object_ownership         = "ObjectWriter"

  versioning = {
    enabled = true
  }
}
