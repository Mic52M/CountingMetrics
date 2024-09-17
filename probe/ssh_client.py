import io
import socket
import errno
from fabric import Connection
import paramiko
from paramiko.ssh_exception import NoValidConnectionsError, AuthenticationException, SSHException
from dataclasses import dataclass

class SshClient:
    @dataclass
    class OnNotZeroExitCodeAction:
        GO_ON: int = 0
        STOP: int = 1

    def __init__(self, *args, **kwargs):
        self._host: str = kwargs.pop("host")
        self._port: str = kwargs.pop("port")
        self._username: str = kwargs.pop("username")
        self._password: str = kwargs.pop("password", None)  # Set None as default if "password" is not provided
        self._private_key: str = kwargs.pop("private_key")
        self._private_key_passphrase: str = kwargs.pop("private_key_passphrase", None)  # Same here
        self._client: Connection = None

    def connect_ssh(self) -> Connection:
        if self._client is None:
            assert self._host is not None and self._host != "", "[input] host input field not valid"
            assert self._port is not None and self._port != "", "[input] port input field not valid"
            assert self._username is not None and self._username != "", "[input] username input field not valid"
            
            connect_kwargs = {}
            if self._password:
                connect_kwargs["password"] = self._password
            if self._private_key:
                private_key = paramiko.RSAKey.from_private_key(io.StringIO(self._private_key), password=self._private_key_passphrase if self._private_key_passphrase else None) 
                connect_kwargs["pkey"] = private_key
            
            try:
                self._client = Connection(
                    host=self._host, 
                    port=self._port,
                    user=self._username,
                    connect_kwargs=connect_kwargs
                )
                self._client.open()
            except AuthenticationException:
                raise AuthenticationException("The provided authentication data is incorrect.")
            except SSHException as e:
                raise SSHException(f"SSH connection error: {str(e)}")
            except NoValidConnectionsError as e:
                raise NoValidConnectionsError("Unable to establish a connection.")
            except socket.error as e:

                if e.errno == errno.ENOENT:
                    error_message = "The SSH server address is not valid."
                elif e.errno == errno.ECONNREFUSED:
                    error_message = "The connection was refused by the server. Check if the SSH service is running."
                elif e.errno == errno.EHOSTUNREACH:
                    error_message = "The SSH server is unreachable."
                else:
                    error_message = "An unknown socket connection error occurred."
                raise SSHException(f"Socket connection error: {error_message}")

    def send_command(self, command: str, on_not_zero_exit_code):
        assert isinstance(command, str), f"Command expected str but got {type(command)}"
        assert self._client is not None, "Client connection error -- client is None"
        res = self._client.run(command, hide=True, warn=False if on_not_zero_exit_code == self.OnNotZeroExitCodeAction.STOP else True)
        out_parse = {
            "stdout": res.stdout.rstrip("\n"),
            "stderr": res.stderr.rstrip("\n"),
            "exit_code": res.exited
        }
        return out_parse

    def send_file(self, dst, src):
        assert self._client is not None, "Client connection error -- client is None"
        self._client.put(local=src, remote=dst)

    def get_file(self, src, dst):
        assert self._client is not None, "Client connection error -- client is None"
        try:
            self._client.get(local=dst, remote=src)
        except Exception as e:
            if 'denied' in str(e).lower():
                raise PermissionError(f"Permission denied when accessing the file at remote path: {src}")
            else:
                raise FileNotFoundError(f"File not found at remote path: {src}")
