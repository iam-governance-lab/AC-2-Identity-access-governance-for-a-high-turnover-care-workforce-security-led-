from unittest.mock import patch

from src.saif_graph_transport import send_b2b_invitation


def test_send_b2b_invitation():
    fake_json = (
        '{"invitationId":"test-invitation-id",'
        '"entraUserId":"test-entra-user-id"}'
    )

    with patch("src.saif_graph_transport.subprocess.run") as mock_run:
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = fake_json

        result = send_b2b_invitation(
            "test@example.com",
            "Test Worker",
            "test-script.ps1"
        )

        assert result["invitationId"] == "test-invitation-id"
        assert result["entraUserId"] == "test-entra-user-id"
        
def test_send_b2b_invitation_failure():
    with patch("src.saif_graph_transport.subprocess.run") as mock_run:
        mock_run.return_value.returncode = 1
        mock_run.return_value.stdout = ""
        mock_run.return_value.stderr = "Graph invitation failed"

        try:
            send_b2b_invitation(
                "test@example.com",
                "Test Worker",
                "test-script.ps1"
            )

            assert False

        except RuntimeError as error:
            assert str(error) == "B2B invitation failed"