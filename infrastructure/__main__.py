"""An AliCloud Python Pulumi program"""

import pulumi
import pulumi_alicloud as alicloud

with open('role_document.json', 'r') as f:
    role_document = f.read()
role = alicloud.ram.Role(
    "fc-role", 
    name=f"fc-{ pulumi.get_project() }-{ pulumi.get_stack() }",
    document=role_document,
    description=f"serverless running role, project: { pulumi.get_project() }, stack: { pulumi.get_stack() }"
)

with open('role_policy.json', 'r') as f:
    role_policy = f.read()
policy = alicloud.ram.Policy(
    "fc-role-policy",
    force=True,
    rotate_strategy='DeleteOldestNonDefaultVersionWhenLimitExceeded',
    policy_name=f"fc-policy-{ pulumi.get_project() }-{ pulumi.get_stack() }",
    policy_document=role_policy,
    description=f"policy for serverless running role, project: { pulumi.get_project() }, stack: { pulumi.get_stack() }"    
)

alicloud.ram.RolePolicyAttachment("fc-role-policy-attach",
    policy_name=policy.policy_name,
    policy_type=policy.type,
    role_name=role.name)

pulumi.export('role_arn: ', role.arn)
