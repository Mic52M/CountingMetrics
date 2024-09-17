# CountingMetrics
This probe connects to a remote AWS server via SSH to download machine learning models and analyze their parameters. It supports different model types, counting parameters for ONNX models and tree structures for Random Forest models, ensuring insights into model complexity and architecture.



 ModelParameterProbe (SSH-based Model Analysis)

## Overview

The `ModelParameterProbe` is a specialized tool for remotely analyzing machine learning models hosted on AWS servers. Using SSH for secure communication, the probe downloads models and analyzes their structure to count parameters and provide insights into the model's complexity. This probe supports different model architectures, including Random Forest classifiers and ONNX models (such as CNN and LSTM). The probe is designed for environments requiring automated model inspection, helping ensure that models used in production are well-understood.

## Core Functionality

### 1. **SSH Connection Setup**
The probe first establishes an SSH connection to a remote server (e.g., an AWS instance) using the provided credentials. This secure connection allows the probe to interact with the server to download the machine learning model. The following configuration details are needed:
- **Host**: The target server’s address (usually an AWS EC2 instance).
- **Username**: The SSH user account for connecting to the server.
- **Private Key**: A private SSH key used to authenticate the connection.
- **Remote Path**: The file path to the model on the remote server.

### 2. **Downloading the Model**
After successfully connecting to the server, the probe downloads the model from the specified remote path. The file is securely transferred to a local directory, ensuring that the model is accessible for further analysis. If the file is not found or there are permission issues, detailed error messages are provided.

### 3. **Model Analysis**
The probe supports two main model types:
- **ONNX Models (CNN, LSTM, etc.)**: 
  - For models in the ONNX format (often used for neural networks), the probe loads the model and counts the total number of parameters.
  - The number of parameters provides insight into the model's complexity and size.
  
- **Random Forest Models**: 
  - For Random Forest classifiers, the probe loads the model and extracts key metrics, such as the **number of trees** in the forest and the **average depth** of each tree.
  - These metrics help assess the complexity of the decision trees and the overall model structure.

### 4. **Parameter Counting**
For ONNX models, the probe counts the total number of parameters by iterating through the model’s graph and summing up all the dimensions of each parameter tensor. This allows for a precise measure of the model’s size, which is important for evaluating its scalability and performance.

For Random Forest models, the probe calculates the number of decision trees and the average depth of each tree. A greater number of trees or deeper trees typically indicate a more complex model, which might affect performance or interpretability.

### 5. **Result Reporting**
The probe outputs the following results based on the model type:
- For **ONNX models**: It reports the total number of parameters.
- For **Random Forest models**: It reports the number of trees and the average depth of the trees.

These results are displayed in a human-readable format and are also made available for integration with CI/CD systems via the MoonCloud platform, ensuring seamless integration into automated machine learning workflows.

## Error Handling

The probe includes robust error handling for the following scenarios:
- **SSH Connection Failures**: If the SSH credentials are invalid or the connection cannot be established, the probe provides detailed error messages, including authentication failures and unreachable servers.
- **File Access Issues**: If the model file cannot be found or there are permission issues, the probe will raise appropriate errors, indicating whether the file is missing or access is denied.
- **Model Type Validation**: If the downloaded model is not of the expected type (e.g., a Random Forest model is expected but something else is provided), the probe raises a descriptive error.

## Use Case in MLOps

This probe is designed for MLOps pipelines, where automated analysis and validation of models are critical before deployment. It provides insights into the complexity and structure of machine learning models hosted on remote servers, making it ideal for continuous integration (CI) environments where models are updated or reviewed regularly. By automating model parameter counting and complexity evaluation, the probe helps ensure models are well-understood and suitable for production use.

