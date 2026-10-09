from src.saif_agency_validation import validate_worker
from src.saif_b2b_invitation import prepare_invitation
from src.saif_identity_mapping import create_identity_mapping
from src.saif_graph_transport import send_b2b_invitation
from src.saif_iam_handover import create_iam_handover

def process_external_worker(worker, agencies, redirect_url, script_path, invitation_sender=send_b2b_invitation):
    validation_result = validate_worker(worker, agencies)

    if validation_result != "APPROVED":
        return validation_result

    prepare_invitation(worker, redirect_url)

    graph_result = invitation_sender(worker["email"], worker["displayName"], script_path)

    mapping = create_identity_mapping( worker, graph_result["entraUserId"])

    handover = create_iam_handover(mapping)

    return {
    "status": "APPROVED",
    "invitationId": graph_result["invitationId"],
    "identityMapping": mapping,
    "iamHandover": handover
}