// Line-scope enforcement: Line supervisors can only access their assigned lines.
// The interceptor injects the user's line_scope into the JWT claims.
// This rule denies access when the requested line is NOT in the user's scope.
//
// Applies to tools that accept a 'line' parameter:
//   - get_equipment_status, detect_anomaly, get_oee_trends, get_quality_metrics
//
// Plant managers bypass this rule (they don't have the line_supervisor group tag).
forbid(
    principal is AgentCore::OAuthUser,
    action in [
        AgentCore::Action::"EquipmentTarget___get_equipment_status",
        AgentCore::Action::"EquipmentTarget___get_shared_infrastructure",
        AgentCore::Action::"IoTTarget___detect_anomaly",
        AgentCore::Action::"AnalyticsTarget___get_oee_trends",
        AgentCore::Action::"AnalyticsTarget___get_quality_metrics"
    ],
    resource == AgentCore::Gateway::"${GATEWAY_ARN}"
) when {
    context.input has line &&
    principal.hasTag("cognito:groups") &&
    principal.getTag("cognito:groups") like "*line_supervisors*" &&
    principal.hasTag("custom:line_scope") &&
    !(principal.getTag("custom:line_scope") like ("*" + context.input.line + "*"))
};
