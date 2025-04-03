import os
import boto3
import time
import torch
from PIL import Image
from facenet_pytorch import MTCNN, InceptionResnetV1
from ec2_metadata import ec2_metadata

config ={
    "AWS_ACCESS_KEY_ID": "your-access-key-id",
    "AWS_SECRET_ACCESS_KEY": "your-secret-access-key",
    "IN_BUCKET_NAME": "your-input-bucket",
    "OUT_BUCKET_NAME": "your-output-bucket",
    "REQ_QUEUE_URL": "your-request-queue-url",
    "RESP_QUEUE_URL": "your-response-queue-url"
}
session = boto3.Session(
    region_name="us-east-1",
    aws_access_key_id=config["AWS_ACCESS_KEY_ID"],
    aws_secret_access_key=config["AWS_SECRET_ACCESS_KEY"]
)
s3 = session.client("s3")
sqs = session.client("sqs")
ec2 = session.client('ec2', region_name='us-east-1')

def push_result_to_s3(img_filename, img_val, bucket_name):
    try:
        s3.put_object(Key = img_filename, Body = img_val, Bucket = bucket_name)
        return True
    except Exception as e:
        print("Upload to S3 failed with err: ", e)
        exit()

def send_message_to_queue(queue_url, queue_key, queue_message):
    try:
        sqs.send_message(QueueUrl = queue_url, MessageAttributes={ 'key': { 'DataType': 'String', 'StringValue': str(queue_key)} }, MessageBody = queue_message)
    except Exception as e:
        print("Could not send message to queue, err: ", e)

def receive_message_from_queue(queue_url):
    message = sqs.receive_message(QueueUrl = queue_url, MessageAttributeNames = ['All'], VisibilityTimeout = 1)
    if 'Messages' in message:
        message_body = message["Messages"][0]["Body"]
        receipt_handle = message["Messages"][0]["ReceiptHandle"]
        key = message["Messages"][0]["MessageAttributes"]["key"]["StringValue"]
        sqs.delete_message( QueueUrl=queue_url, ReceiptHandle=receipt_handle )
        return (key, message_body)
    else:
        print("No message received.")
        time.sleep(5) 

    return None

mtcnn = MTCNN(image_size=240, margin=0, min_face_size=20) # initializing mtcnn for face detection
resnet = InceptionResnetV1(pretrained='vggface2').eval() # initializing resnet for face img to embeding conversion

def face_match(img_path, data_path): # img_path= location of photo, data_path= location of data.pt
    # getting embedding matrix of the given img
    img = Image.open(img_path)
    face, prob = mtcnn(img, return_prob=True) # returns cropped face and probability
    emb = resnet(face.unsqueeze(0)).detach() # detech is to make required gradient false

    saved_data = torch.load(data_path) # loading data.pt file
    embedding_list = saved_data[0] # getting embedding data
    name_list = saved_data[1] # getting list of names
    dist_list = [] # list of matched distances, minimum distance is used to identify the person

    for idx, emb_db in enumerate(embedding_list):
        dist = torch.dist(emb, emb_db).item()
        dist_list.append(dist)

    idx_min = dist_list.index(min(dist_list))
    return (name_list[idx_min], min(dist_list))

def listen():
    request_queue_url = sqs.get_queue_url(QueueName = config["REQ_QUEUE_URL"])["QueueUrl"]
    while True:
        req_queue_img_object = receive_message_from_queue(request_queue_url)
        if req_queue_img_object:
            req_queue_img_key, req_queue_img_file = req_queue_img_object
            req_queue_img_filename = req_queue_img_file.split('.')[0]
            
            relative_download_img_path = "./temp_downloaded_images"
            os.makedirs(relative_download_img_path, exist_ok=True)
            actual_img_path = os.path.join(relative_download_img_path, req_queue_img_file)
            s3.download_file(config["IN_BUCKET_NAME"], req_queue_img_file, actual_img_path)
            face_match_result_object = face_match(actual_img_path, 'data.pt')
            os.remove(actual_img_path)

            face_match_result_value, _ = face_match_result_object
            response_queue_img_val = str((req_queue_img_filename, face_match_result_value))

            response_queue_url = sqs.get_queue_url(QueueName = config["RESP_QUEUE_URL"])["QueueUrl"]
            send_message_to_queue(response_queue_url, req_queue_img_key, response_queue_img_val)
            push_result_to_s3(req_queue_img_filename, face_match_result_value, config["OUT_BUCKET_NAME"])
        response = sqs.get_queue_attributes(QueueUrl=config["REQ_QUEUE_URL"], AttributeNames=['ApproximateNumberOfMessages'])
        num_messages = int(response['Attributes']['ApproximateNumberOfMessages'])
        if num_messages == 0:
            instance_id = ec2_metadata.instance_id
            ec2.terminate_instances(InstanceIds=[instance_id])


if __name__ == "__main__":
    listen()
