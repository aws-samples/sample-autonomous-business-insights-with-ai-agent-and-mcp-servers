// Equipment-scope enforcement: Maintenance technicians can only access assigned machines.
// Technicians have a custom:equipment_scope attribute listing their machine IDs.
// This rule denies access when machine_id is NOT in their scope.
//
// Applies to tools that accept a 'machine_id' parameter:
//   - get_equipment_status, get_maintenance_history, get_sensor_readings
//
// Line supervisors and plant managers bypass this (different group).
forbid(
    principal is AgentCore::OAuthUser,
    action in [
        AgentCore::Action::"EquipmentTarget___get_equipment_status",
        AgentCore::Action::"EquipmentTarget___get_maintenance_history",
        AgentCore::Action::"IoTTarget___get_sensor_readings"
    ],
    resource == AgentCore::Gateway::"${GATEWAY_ARN}"
) when {
    context.input has machine_id &&
    principal.hasTag("cognito:groups") &&
    principal.getTag("cognito:groups") like "*maintenance_technicians*" &&
    principal.hasTag("custom:equipment_scope") &&
    !(principal.getTag("custom:equipment_scope") like ("*" + context.input.machine_id + "*"))
};
