"""
Test docker backend functionality.
"""

import json
import subprocess
from unittest.mock import Mock, patch

import pytest

from mcp_platform.backends.docker import DockerDeploymentService


@pytest.mark.unit
@pytest.mark.docker
class TestDockerDeploymentService:
    """Test Docker deployment service."""

    def test_init(self):
        """Test Docker service initialization."""
        with patch(
            "mcp_platform.backends.docker.DockerDeploymentService._ensure_docker_available"
        ):
            service = DockerDeploymentService()
            assert service is not None

    @patch(
        "mcp_platform.backends.docker.DockerDeploymentService._ensure_docker_available"
    )
    @patch("mcp_platform.backends.docker.DockerDeploymentService._run_command")
    def test_deploy_template_success(self, mock_run_command, mock_ensure_docker):
        """Test successful template deployment."""

        # Setup mocks
        def run_cmd(cmd, check=True, **kwargs):
            # Simulate network inspect existing
            if cmd[:4] == ["docker", "network", "inspect", "mcp-platform"]:
                return Mock(returncode=0)
            # Simulate image inspect raising to indicate missing image
            if len(cmd) >= 3 and cmd[1] == "image" and cmd[2] == "inspect":
                raise subprocess.CalledProcessError(1, cmd, "image not found")
            if len(cmd) >= 2 and cmd[1] == "pull":
                return Mock(stdout="pulled", stderr="")
            if "run" in cmd:
                return Mock(stdout="container123", stderr="")
            return Mock(stdout="")

        mock_run_command.side_effect = run_cmd

        service = DockerDeploymentService()
        template_data = {
            "image": "test-image:latest",
            "ports": {"8080": 8080},
            "env_vars": {"TEST_VAR": "test_value"},
        }
        config = {"param1": "value1"}

        result = service.deploy_template("test", config, template_data, {})

        assert result["template_id"] == "test"
        assert result["status"] == "deployed"
        assert "deployment_name" in result
        assert "container_id" in result

    @patch(
        "mcp_platform.backends.docker.DockerDeploymentService._ensure_docker_available"
    )
    @patch("mcp_platform.backends.docker.DockerDeploymentService._run_command")
    def test_deploy_template_with_pull(self, mock_run_command, mock_ensure_docker):
        """Test deployment with image pulling."""

        def run_cmd_pull(cmd, check=True, **kwargs):
            if cmd[:4] == ["docker", "network", "inspect", "mcp-platform"]:
                return Mock(returncode=0)
            if len(cmd) >= 3 and cmd[1] == "image" and cmd[2] == "inspect":
                raise subprocess.CalledProcessError(1, cmd, "image not found")
            if len(cmd) >= 2 and cmd[1] == "pull":
                return Mock(stdout="pulled", stderr="")
            if "run" in cmd:
                return Mock(stdout="container123", stderr="")
            return Mock(stdout="")

        mock_run_command.side_effect = run_cmd_pull

        service = DockerDeploymentService()
        template_data = {"image": "test-image:latest"}

        service.deploy_template("test", {}, template_data, {}, pull_image=True)

        # Verify a pull was attempted (inspect then pull should occur somewhere)
        called_cmds = [c[0][0] for c in mock_run_command.call_args_list if c and c[0]]
        assert any((len(cmd) >= 2 and cmd[1] == "pull") for cmd in called_cmds), (
            "Expected a docker pull to be attempted"
        )

    @patch(
        "mcp_platform.backends.docker.DockerDeploymentService._ensure_docker_available"
    )
    @patch("mcp_platform.backends.docker.DockerDeploymentService._run_command")
    def test_deploy_template_docker_error(self, mock_run_command, mock_ensure_docker):
        """Test deployment failure handling."""
        mock_run_command.side_effect = Exception("Docker error")

        service = DockerDeploymentService()
        template_data = {"image": "test-image:latest"}

        with pytest.raises(Exception) as exc_info:
            service.deploy_template("test", {}, template_data, {})

        assert str(exc_info.value) == "Docker error"

    # CREATE_NETWORK TESTS - Core focus of this task
    @patch(
        "mcp_platform.backends.docker.DockerDeploymentService._ensure_docker_available"
    )
    @patch("mcp_platform.backends.docker.DockerDeploymentService._run_command")
    def test_create_network_already_exists(self, mock_run_command, mock_ensure_docker):
        """Test create_network when network already exists - should no-op."""
        # Simulate docker network inspect mcp-platform returning success
        mock_run_command.return_value = Mock(returncode=0)

        service = DockerDeploymentService()
        service.create_network()

        # Only the initial inspect should have been called
        assert mock_run_command.call_count == 1
        mock_run_command.assert_called_with(
            ["docker", "network", "inspect", "mcp-platform"], check=False
        )

    @patch(
        "mcp_platform.backends.docker.DockerDeploymentService._ensure_docker_available"
    )
    @patch("mcp_platform.backends.docker.DockerDeploymentService._run_command")
    def test_create_network_ipam_success(self, mock_run_command, mock_ensure_docker):
        """Test create_network successfully creates with IPAM when candidate is available."""
        # Sequence of calls inside create_network:
        # 1) inspect mcp-platform -> not found (returncode != 0)
        # 2) docker network ls -> returns list of networks
        # 3) docker network inspect <net> for each listed network
        # 4) docker network create ... --subnet <chosen> -> succeeds

        mock_run_command.side_effect = [
            Mock(returncode=1),  # inspect mcp-platform (not found)
            Mock(stdout="bridge\nhost\n"),  # docker network ls
            Mock(
                stdout=json.dumps(
                    [
                        {
                            "IPAM": {
                                "Config": [
                                    {"Subnet": "172.17.0.0/16", "Gateway": "172.17.0.1"}
                                ]
                            }
                        }
                    ]
                )
            ),  # inspect bridge
            Mock(stdout="[]"),  # inspect host
            Mock(stdout="network_created_id", returncode=0),  # create with IPAM
        ]

        service = DockerDeploymentService()
        service.create_network()

        # Ensure we attempted a create with an explicit subnet (IPAM)
        called_cmds = [" ".join(call[0][0]) for call in mock_run_command.call_args_list]
        assert any("--subnet" in c for c in called_cmds), (
            "Expected an IPAM create attempt with --subnet"
        )
        assert any(
            "10.100.0.0/24" in c or "10.101.0.0/24" in c or "10.102.0.0/24" in c
            for c in called_cmds
        ), "Expected one of the candidate subnets"

    @patch(
        "mcp_platform.backends.docker.DockerDeploymentService._ensure_docker_available"
    )
    @patch("mcp_platform.backends.docker.DockerDeploymentService._run_command")
    def test_create_network_ipam_fail_fallback(
        self, mock_run_command, mock_ensure_docker
    ):
        """Test create_network falls back to basic create when IPAM creation fails."""
        # Prepare side effects to simulate IPAM create raising CalledProcessError
        mock_run_command.side_effect = [
            Mock(returncode=1),  # inspect mcp-platform (not found)
            Mock(stdout="bridge\n"),  # docker network ls
            Mock(
                stdout=json.dumps(
                    [
                        {
                            "IPAM": {
                                "Config": [
                                    {"Subnet": "172.17.0.0/16", "Gateway": "172.17.0.1"}
                                ]
                            }
                        }
                    ]
                )
            ),  # inspect bridge
            subprocess.CalledProcessError(
                1, "docker", "numerical result out of range"
            ),  # create with IPAM fails
            Mock(
                stdout="network_created_basic", returncode=0
            ),  # fallback basic create succeeds
        ]

        service = DockerDeploymentService()
        service.create_network()

        # Verify we attempted an IPAM create (with --subnet) and then a fallback create
        called_cmds = [
            " ".join(call[0][0]) if call and call[0] else ""
            for call in mock_run_command.call_args_list
        ]
        assert any("--subnet" in c for c in called_cmds), (
            "Expected an IPAM create attempt"
        )
        # Look for the fallback create (without --subnet but basic docker network create)
        fallback_creates = [
            c
            for c in called_cmds
            if "network create" in c and "--subnet" not in c and "mcp-platform" in c
        ]
        assert len(fallback_creates) > 0, "Expected fallback basic create call"

    @patch(
        "mcp_platform.backends.docker.DockerDeploymentService._ensure_docker_available"
    )
    @patch("mcp_platform.backends.docker.DockerDeploymentService._run_command")
    def test_create_network_no_candidates_fallback(
        self, mock_run_command, mock_ensure_docker
    ):
        """Test create_network falls back to basic create when all candidate subnets conflict."""
        # Build ls output with several networks. Each inspect will report an IPAM config
        networks = "n1\nn2\nn3\nn4\nn5\n"
        # Provide inspect responses that include all candidate subnets so no candidate is free
        inspect_responses = []
        candidate_subnets = [
            "10.100.0.0/24",
            "10.101.0.0/24",
            "10.102.0.0/24",
            "10.103.0.0/24",
            "10.104.0.0/24",
        ]
        for s in candidate_subnets:
            inspect_responses.append(
                Mock(
                    stdout=json.dumps(
                        [
                            {
                                "IPAM": {
                                    "Config": [{"Subnet": s, "Gateway": s.split("/")[0]}]
                                }
                            }
                        ]
                    )
                )
            )

        # Sequence: inspect mcp -> not found, ls, then 5 inspects, then fallback create
        mock_run_command.side_effect = [
            Mock(returncode=1),  # inspect mcp-platform (not found)
            Mock(stdout=networks),  # docker network ls
            *inspect_responses,
            Mock(
                stdout="network_created_fallback", returncode=0
            ),  # fallback create succeeds
        ]

        service = DockerDeploymentService()
        service.create_network()

        called_cmds = [
            " ".join(call[0][0]) if call and call[0] else ""
            for call in mock_run_command.call_args_list
        ]
        # No IPAM create should have been attempted (no --subnet in any call)
        assert not any("--subnet" in c for c in called_cmds), (
            "Did not expect an IPAM create when no candidate available"
        )
        # Fallback create should exist (basic docker network create)
        fallback_creates = [
            c for c in called_cmds if "network create" in c and "mcp-platform" in c
        ]
        assert len(fallback_creates) > 0, "Expected fallback create"

    @patch(
        "mcp_platform.backends.docker.DockerDeploymentService._ensure_docker_available"
    )
    @patch("mcp_platform.backends.docker.DockerDeploymentService._run_command")
    def test_create_network_inspect_errors_handled(
        self, mock_run_command, mock_ensure_docker
    ):
        """Test create_network handles errors gracefully when network inspection fails."""
        # Simulate various failures during network discovery
        mock_run_command.side_effect = [
            Mock(returncode=1),  # inspect mcp-platform (not found)
            Exception("docker daemon error"),  # docker network ls fails
            Mock(stdout="network_created_safe", returncode=0),  # fallback create succeeds
        ]

        service = DockerDeploymentService()
        service.create_network()

        # Should fall back to basic create when discovery fails
        called_cmds = [
            " ".join(call[0][0]) if call and call[0] else ""
            for call in mock_run_command.call_args_list
        ]
        fallback_creates = [
            c for c in called_cmds if "network create" in c and "mcp-platform" in c
        ]
        assert len(fallback_creates) > 0, "Expected fallback create when discovery fails"

    @patch(
        "mcp_platform.backends.docker.DockerDeploymentService._ensure_docker_available"
    )
    @patch("mcp_platform.backends.docker.DockerDeploymentService._run_command")
    def test_create_network_all_creation_fails(
        self, mock_run_command, mock_ensure_docker
    ):
        """Test create_network handles complete failure gracefully."""
        # Simulate all network creation attempts failing
        mock_run_command.side_effect = [
            Mock(returncode=1),  # inspect mcp-platform (not found)
            Mock(stdout="bridge\n"),  # docker network ls
            Mock(
                stdout=json.dumps([{"IPAM": {"Config": [{"Subnet": "172.17.0.0/16"}]}}])
            ),  # inspect bridge
            subprocess.CalledProcessError(
                1, "docker", "numerical result out of range"
            ),  # IPAM create fails
            subprocess.CalledProcessError(
                1, "docker", "unknown error"
            ),  # fallback create also fails
        ]

        service = DockerDeploymentService()
        # Should not raise exception - method handles errors gracefully
        service.create_network()

        # Verify both creation attempts were made
        called_cmds = [
            " ".join(call[0][0]) if call and call[0] else ""
            for call in mock_run_command.call_args_list
        ]
        assert any("--subnet" in c for c in called_cmds), "Expected IPAM create attempt"
        fallback_creates = [
            c
            for c in called_cmds
            if "network create" in c and "--subnet" not in c and "mcp-platform" in c
        ]
        assert len(fallback_creates) > 0, "Expected fallback create attempt"

    # EXISTING TESTS CONTINUE...
    @patch(
        "mcp_platform.backends.docker.DockerDeploymentService._ensure_docker_available"
    )
    @patch("mcp_platform.backends.docker.DockerDeploymentService._run_command")
    def test_list_deployments(self, mock_run_command, mock_ensure_docker):
        """Test listing deployments."""
        mock_response = """{"ID": "abc123def456", "Names": "mcp-test-123", "State": "running", "CreatedAt": "2024-01-01", "RunningFor": "2 hours ago", "Image": "test:latest", "Labels": "template=test,managed-by=mcp-template", "Ports": "0.0.0.0:8080->8080/tcp"}"""
        mock_run_command.return_value = Mock(stdout=mock_response)
        service = DockerDeploymentService()
        deployments = service.list_deployments()

        assert len(deployments) == 1
        assert deployments[0]["id"] == "abc123def456"
        assert deployments[0]["name"] == "mcp-test-123"
        assert deployments[0]["template"] == "test"

    @patch(
        "mcp_platform.backends.docker.DockerDeploymentService._ensure_docker_available"
    )
    @patch("mcp_platform.backends.docker.DockerDeploymentService._run_command")
    def test_delete_deployment_success(self, mock_run_command, mock_ensure_docker):
        """Test successful deployment deletion."""
        mock_run_command.return_value = Mock(stdout="", stderr="")

        service = DockerDeploymentService()
        result = service.delete_deployment("test-container")

        assert result is True
        assert mock_run_command.called

    @patch(
        "mcp_platform.backends.docker.DockerDeploymentService._ensure_docker_available"
    )
    @patch("mcp_platform.backends.docker.DockerDeploymentService._run_command")
    def test_delete_deployment_not_found(self, mock_run_command, mock_ensure_docker):
        """Test deletion of non-existent deployment."""
        from subprocess import CalledProcessError

        mock_run_command.side_effect = CalledProcessError(
            1, "docker", "No such container"
        )

        service = DockerDeploymentService()
        result = service.delete_deployment("nonexistent")

        assert result is False

    @patch(
        "mcp_platform.backends.docker.DockerDeploymentService._ensure_docker_available"
    )
    @patch("mcp_platform.backends.docker.DockerDeploymentService._run_command")
    def test_get_deployment_status(self, mock_run_command, mock_ensure_docker):
        """Test getting deployment status with logs via unified get_deployment_info method."""
        mock_response = """[{"Name": "/test-container", "State": {"Status": "running", "Running": true}, "Created": "2024-01-01", "Config": {"Image": "test:latest", "Labels": {"template": "test"}}}]"""

        # Simple approach: make a mock that returns the JSON string
        mock_run_command.return_value = Mock(stdout=mock_response)

        service = DockerDeploymentService()
        status = service.get_deployment_info(
            "test-container", include_logs=False
        )  # Don't include logs to avoid second call
        assert status is not None, "Status should not be None"
        assert status["status"] == "running"
        assert status["name"] == "test-container"
        assert status["running"] is True
        assert "created" in status
        # No logs since include_logs=False

    def test_prepare_environment_variables(self):
        """Test environment variable preparation."""
        with patch(
            "mcp_platform.backends.docker.DockerDeploymentService._ensure_docker_available"
        ):
            service = DockerDeploymentService()
            config = {"param1": "value1", "param2": "value2"}
            template_data = {"env_vars": {"TEMPLATE_VAR": "template_value"}}

            env_vars = service._prepare_environment_variables(config, template_data)

            assert "--env" in env_vars
            assert "param1=value1" in env_vars
            assert "param2=value2" in env_vars
            assert "TEMPLATE_VAR=template_value" in env_vars

    def test_prepare_port_mappings(self):
        """Test port mapping preparation."""
        with patch(
            "mcp_platform.backends.docker.DockerDeploymentService._ensure_docker_available"
        ):
            service = DockerDeploymentService()
            template_data = {"ports": {"8080": 8080, "9000": 9001}}

            port_mappings = service._prepare_port_mappings(template_data)

            assert "-p" in port_mappings
            # Check that there are two port mappings (even if ports are remapped)
            port_args = [
                port_mappings[i + 1] for i, arg in enumerate(port_mappings) if arg == "-p"
            ]
            assert len(port_args) == 2

            # Check that container ports are correctly mapped (host ports may be remapped)
            assert any(":8080" in port for port in port_args)  # Container port 8080
            assert any(":9001" in port for port in port_args)  # Container port 9001

    def test_prepare_volume_mounts(self):
        """Test volume mount preparation."""
        with patch(
            "mcp_platform.backends.docker.DockerDeploymentService._ensure_docker_available"
        ):
            service = DockerDeploymentService()
            template_data = {"volumes": {"/host/path": "/container/path"}}

            with patch("os.makedirs"):
                volumes = service._prepare_volume_mounts(template_data)

                assert "--volume" in volumes
                assert "/host/path:/container/path" in volumes

    @patch(
        "mcp_platform.backends.docker.DockerDeploymentService._ensure_docker_available"
    )
    @patch("mcp_platform.backends.docker.DockerDeploymentService._run_command")
    def test_get_deployment_logs_success(self, mock_run_command, mock_ensure_docker):
        """Test successful retrieval of deployment logs."""
        # Setup mock for docker logs command
        mock_log_output = "Log line 1\nLog line 2\nLog line 3"
        mock_run_command.return_value = Mock(
            stdout=mock_log_output, stderr="", returncode=0
        )

        service = DockerDeploymentService()

        # Test basic logs retrieval (uses default 100 lines)
        result = service.get_deployment_logs("container123")

        assert result["success"] is True
        assert mock_log_output in result["logs"]

        # Verify docker logs command was called correctly with default --tail 100
        mock_run_command.assert_called_once_with(
            ["docker", "logs", "--tail", "100", "container123"]
        )

    @patch(
        "mcp_platform.backends.docker.DockerDeploymentService._ensure_docker_available"
    )
    @patch("mcp_platform.backends.docker.DockerDeploymentService._run_command")
    def test_get_deployment_logs_with_parameters(
        self, mock_run_command, mock_ensure_docker
    ):
        """Test logs retrieval with lines, since, and until parameters."""
        mock_log_output = "Recent log line"
        mock_run_command.return_value = Mock(
            stdout=mock_log_output, stderr="", returncode=0
        )

        service = DockerDeploymentService()

        # Test with lines parameter
        result = service.get_deployment_logs(
            "container123", lines=50, since="2023-01-01", until="2023-12-31"
        )

        assert result["success"] is True
        assert mock_log_output in result["logs"]

        # Verify docker logs command was called with parameters
        mock_run_command.assert_called_once_with(
            [
                "docker",
                "logs",
                "--tail",
                "50",
                "--since",
                "2023-01-01",
                "--until",
                "2023-12-31",
                "container123",
            ]
        )

    @patch(
        "mcp_platform.backends.docker.DockerDeploymentService._ensure_docker_available"
    )
    @patch("mcp_platform.backends.docker.DockerDeploymentService._run_command")
    def test_get_deployment_logs_failure(self, mock_run_command, mock_ensure_docker):
        """Test logs retrieval failure handling."""
        # Setup mock for failed docker logs command
        mock_run_command.return_value = Mock(
            stdout="", stderr="Error: No such container", returncode=1
        )

        service = DockerDeploymentService()

        # Test logs retrieval failure
        result = service.get_deployment_logs("nonexistent-container")

        assert result["success"] is False
        assert result["error"] == "Error: No such container"

        # Verify docker logs command was called
        mock_run_command.assert_called_once_with(
            ["docker", "logs", "--tail", "100", "nonexistent-container"]
        )

    @patch(
        "mcp_platform.backends.docker.DockerDeploymentService._ensure_docker_available"
    )
    @patch("mcp_platform.backends.docker.DockerDeploymentService._run_command")
    def test_get_deployment_logs_default_lines(
        self, mock_run_command, mock_ensure_docker
    ):
        """Test logs retrieval uses default lines when only lines specified."""
        mock_log_output = "Default lines log"
        mock_run_command.return_value = Mock(
            stdout=mock_log_output, stderr="", returncode=0
        )

        service = DockerDeploymentService()

        # Test with only lines parameter
        result = service.get_deployment_logs("container123", lines=100)

        assert result["success"] is True
        assert result["logs"] == "\n" + mock_log_output

        # Verify docker logs command was called with lines only
        mock_run_command.assert_called_once_with(
            ["docker", "logs", "--tail", "100", "container123"]
        )
