# Face Recognition Service

Thw project is a scalable face recognition service deployed on AWS. It uses a microservices architecture with a web tier, application tier, and a controller tier. The service performs face recognition tasks by leveraging AWS S3 for storage, SQS for messaging, and EC2 for scalable compute resources.

## Project Components

### 1. `webtier.py`
This is a Flask-based web service that handles file uploads and communicates with the AWS SQS queues to manage face recognition requests and responses.

### 2. `apptier.py`
The application tier is responsible for processing the face recognition tasks. It retrieves images from S3, performs face recognition using a pre-trained model, and stores results back in S3.

### 3. `controller.py`
This script manages the scaling of EC2 instances based on the number of messages in the SQS request queue. It ensures that there are enough instances running to handle incoming requests.

## Getting Started

### Prerequisites

- Python 3.x
- AWS CLI configured with appropriate access
- AWS account with S3, SQS, and EC2 services

### Installation

1. **Clone the repository**

    ```bash
    git clone https://github.com/AkhilVKhatode/aws_face_recognition.git
    cd aws_face_recognition
    ```

2. **Install dependencies**

    Create a virtual environment and install the required packages.

    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows use `venv\Scripts\activate`
    pip install -r requirements.txt
    ```

### Configuration

Update the `config` dictionary in each of the scripts (`webtier.py`, `apptier.py`, `controller.py`) with your AWS credentials, bucket names, and queue URLs.

```python
config = {
    "AWS_ACCESS_KEY_ID": "your-access-key-id",
    "AWS_SECRET_ACCESS_KEY": "your-secret-access-key",
    "IN_BUCKET_NAME": "your-input-bucket",
    "OUT_BUCKET_NAME": "your-output-bucket",
    "REQ_QUEUE_URL": "your-request-queue-url",
    "RESP_QUEUE_URL": "your-response-queue-url",
    "AMI_ID": "your-ami-id"
}
```
### Running the Service
  1. Start the web service
  ```
  python webtier.py
  ```
2. Start the application tier
  ```
  python apptier.py
  ```
3. Start the controller
  ```
  python controller.py
  ```

### Usage
  - Upload an image: Send a POST request with an image file to the web service running at http://localhost:8000/.
  - Face recognition: The application tier processes the image, performs face recognition, and stores the result in the output S3 bucket.
