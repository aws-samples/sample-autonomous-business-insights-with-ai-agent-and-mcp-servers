// Cost governance: Block tool calls when user's daily token budget is exhausted.
//
// This policy is evaluated at the Gateway BEFORE every tool call.
// The REQUEST interceptor reads the user's current token count from DynamoDB
// and injects it into context.budget.daily_token_count.
//
// Graduated enforcement:
//   80% → Log warning (handled by interceptor, not Cedar)
//   90% → Throttle (handled by interceptor delay)
//  100% → FORBID (this policy)
//
// Cedar evaluates deterministically: same budget state → same decision.
// The agent cannot bypass this through prompt manipulation.

forbid(
    principal is AgentCore::OAuthUser,
    action,
    resource == AgentCore::Gateway::"${GATEWAY_ARN}"
) when {
    context.input has _budget_context &&
    context.input._budget_context has daily_token_count &&
    context.input._budget_context has daily_token_limit &&
    context.input._budget_context.daily_token_count >= context.input._budget_context.daily_token_limit
};
