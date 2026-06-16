// Baseline permit: Allow all authenticated users to invoke tools on this Gateway.
// This is REQUIRED because AgentCore Policy uses deny-by-default semantics.
// Without this rule, ALL requests would be denied.
// The forbid rules below carve out specific restrictions.
permit(
    principal,
    action,
    resource == AgentCore::Gateway::"${GATEWAY_ARN}"
);
