# Griffle-Guard member-account role

This Terraform configuration creates the read-only IAM role that the central Griffle-Guard Lambda assumes in a member AWS account.

It creates:

- IAM role: `GriffleGuardReadOnlyRole`
- trust policy allowing only the configured central Griffle-Guard Lambda execution role to assume it
- read permissions required by the current S3 and EC2 Security Group scanners

## Usage

Run this configuration against each AWS member account that Griffle-Guard should scan.

Example:

```bash
cd terraform/member-role

terraform init

terraform plan \
  -var='central_griffleguard_role_arn=arn:aws:iam::CENTRAL_ACCOUNT_ID:role/GriffleGuard-Sentry-Role-v2'

terraform apply \
  -var='central_griffleguard_role_arn=arn:aws:iam::CENTRAL_ACCOUNT_ID:role/GriffleGuard-Sentry-Role-v2'
```

For a large AWS Organization, do not deploy this manually account by account. Use your organization's existing Terraform account-vending/deployment pipeline, or another centrally managed rollout mechanism, so every intended member account receives the same role consistently.

The role is intentionally read-only. Add permissions only when Griffle-Guard adds a scanner that requires them.
