import json
from ssh_client import SshClient
import paramiko
import os
from paramiko.ssh_exception import NoValidConnectionsError, AuthenticationException, SSHException
from mooncloud_driver import abstract_probe, atom, result, entrypoint
import joblib
import onnx
import numpy as np
import typing
from sklearn.ensemble import RandomForestClassifier

class ModelParameterProbe(abstract_probe.AbstractProbe):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.ssh_client = None

    def requires_credential(self) -> any:
        return True

    def parse_input(self):
        self.ssh_host = self.config.input.get("config").get('target')
        self.remote_path = self.config.input.get("config").get('remote_model_path')
        self.model_type = self.config.input.get("config").get('model_type')
        self.local_path = '/home/mic/Desktop/model_file' 
        self.ssh_username = self.config.credential.get('username') 
        self.ssh_private_key = self.config.credential.get('private_key')
        self.ssh_private_key_passphrase = self.config.credential.get('private_key_passphrase')

    def setup_ssh_client(self):
        self.ssh_client = SshClient(
            host=self.ssh_host,
            port="22",  
            username=self.ssh_username,
            private_key=self.ssh_private_key,
            private_key_passphrase=self.ssh_private_key_passphrase
        )
        self.ssh_client.connect_ssh()

    def download_model(self):
        assert self.ssh_client is not None, "SSH client not initialized. Call setup_ssh_client before proceeding."
        self.ssh_client.get_file(self.remote_path, self.local_path)

    def analyze_model(self):
        if self.model_type in ['CNN', 'LSTM']:
            model = onnx.load(self.local_path)
            num_params = self.count_onnx_parameters(model)
            self.result.integer_result = result.INTEGER_RESULT_TRUE
            self.result.pretty_result = f"The model has {num_params} parameters."
            self.result.put_extra_data("num_parameters", int(num_params))
        elif self.model_type == 'RandomForest':
            model = joblib.load(self.local_path)
            if isinstance(model, RandomForestClassifier):
                num_trees = len(model.estimators_)
                avg_depth = sum(tree.tree_.max_depth for tree in model.estimators_) / num_trees
                self.result.integer_result = result.INTEGER_RESULT_TRUE
                self.result.pretty_result = f"The model has {num_trees} trees with an average depth of {avg_depth:.2f}."
                self.result.put_extra_data("num_trees", int(num_trees))
                self.result.put_extra_data("avg_depth", float(avg_depth))
            else:
                raise ValueError("The loaded model is not a RandomForestClassifier.")
        else:
            raise ValueError("Unsupported model type.")

    def count_onnx_parameters(self, model):
        param_count = 0
        for initializer in model.graph.initializer:
            param_count += np.prod(initializer.dims).item()  # Convert to native Python int
        return param_count

    def run_analysis(self, inputs: any) -> bool:
        self.download_model()
        self.analyze_model()
        return True

    def atoms(self) -> typing.Sequence[atom.AtomPairWithException]:
        return [
            atom.AtomPairWithException(
                forward=self.parse_input,
                forward_captured_exceptions=[]
            ),
            atom.AtomPairWithException(
                forward=self.setup_ssh_client,
                forward_captured_exceptions=[
                    atom.PunctualExceptionInformationForward(
                        exception_class=AuthenticationException,
                        action=atom.OnExceptionActionForward.STOP,
                        result_producer=lambda e: self.handle_ssh_connection_exception(e, "Authentication Failed")
                    ),
                    atom.PunctualExceptionInformationForward(
                        exception_class=SSHException,
                        action=atom.OnExceptionActionForward.STOP,
                        result_producer=lambda e: self.handle_ssh_connection_exception(e, "SSH connection error")
                    ),
                    atom.PunctualExceptionInformationForward(
                        exception_class=NoValidConnectionsError,
                        action=atom.OnExceptionActionForward.STOP,
                        result_producer=lambda e: self.handle_ssh_connection_exception(e, "Non è possibile stabilire una connessione.")
                    )
                ]
            ),
            atom.AtomPairWithException(
                forward=self.download_model,
                forward_captured_exceptions=[
                    atom.PunctualExceptionInformationForward(
                        exception_class=FileNotFoundError,
                        action=atom.OnExceptionActionForward.STOP,
                        result_producer=lambda e: self.handle_remote_dataset_exception(e, "Model file not found")
                    ),
                    atom.PunctualExceptionInformationForward(
                        exception_class=PermissionError,
                        action=atom.OnExceptionActionForward.STOP,
                        result_producer=lambda e: self.handle_remote_dataset_exception(e, "Access Denied")
                    ),
                ]
            ),
            atom.AtomPairWithException(
                forward=self.run_analysis,
                forward_captured_exceptions=[
                    atom.PunctualExceptionInformationForward(
                        exception_class=ValueError,
                        action=atom.OnExceptionActionForward.STOP,
                        result_producer=lambda e: self.handle_model_read_exception(e)
                    )
                ]
            )
        ]

    def handle_ssh_connection_exception(self, e, message):
        pretty_result = f"SSH Error: {message}."
        error_details = str(e)

        return result.Result(
            integer_result=result.INTEGER_RESULT_TARGET_CONNECTION_ERROR,
            pretty_result=pretty_result,
            base_extra_data={"Error": error_details}
        )
    
    def handle_remote_dataset_exception(self, e, message):
        pretty_result = f"Error: {message}"
        error_details = str(e)

        return result.Result(
            integer_result=result.INTEGER_RESULT_INPUT_ERROR,
            pretty_result=pretty_result,
            base_extra_data={"Error": error_details}
        )

    def handle_model_read_exception(self, e):
        pretty_result = f"Model Read Error: {str(e)}"
        error_details = str(e)

        return result.Result(
            integer_result=result.INTEGER_RESULT_INPUT_ERROR,
            pretty_result=pretty_result,
            base_extra_data={"Error": error_details}
        )

if __name__ == '__main__':
    entrypoint.start_execution(ModelParameterProbe)
