// Plant-scope enforcement: Users can only access data from their authorized plants.
// This applies to all non-plant-manager users.
//
// Applies to tools that accept a 'plant' parameter:
//   - get_equipment_status, detect_anomaly, get_oee_trends, get_quality_metrics
forbid(
    principal is AgentCore::OAuthUser,
    action in [
        AgentCore::Action::"EquipmentTarget___get_equipment_status",
        AgentCore::Action::"IoTTarget___detect_anomaly",
        AgentCore::Action::"AnalyticsTarget___get_oee_trends",
        AgentCore::Action::"AnalyticsTarget___get_quality_metrics"
    ],
    resource == AgentCore::Gateway::"${GATEWAY_ARN}"
) when {
    context.input has plant &&
    principal.hasTag("custom:plant_scope") &&
    !(principal.getTag("custom:plant_scope") like ("*" + context.input.plant + "*"))
};
