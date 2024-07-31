from flask import Flask, request, session
import boto3
import uuid

config = {
    "AWS_ACCESS_KEY_ID": "your-access-key-id",
    "AWS_SECRET_ACCESS_KEY": "your-secret-access-key",
    "IN_BUCKET_NAME": "your-input-bucket",
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
app = Flask(__name__)
app.config['TIMEOUT'] = 3600
map_webtier = {}

def upload_file_to_s3(img_file, bucket_name, img_filename):
    try:
        s3.upload_fileobj(Fileobj = img_file, Bucket = bucket_name, Key = img_filename)
        return True
    except Exception as e:
        print("Upload to S3 failed with err: ", e)
        exit()

def send_message_to_queue(queue_url, queue_message, queue_key):
    try:
        sqs.send_message(QueueUrl = queue_url, MessageAttributes={ 'key': { 'DataType': 'String', 'StringValue': str(queue_key)} }, MessageBody = queue_message)
        return True
    except Exception as e:
        print("Could not send message to queue, err: ", e)
   
def receive_message_from_queue(unique_queue_key, queue_url):
    response_queue_msg = sqs.receive_message(QueueUrl=queue_url, MessageAttributeNames=['All'])
    if unique_queue_key in map_webtier.keys():
        resp_queue_img_val = map_webtier[unique_queue_key]
        map_webtier.pop(unique_queue_key)
        return resp_queue_img_val
    if 'Messages' in response_queue_msg:
        for i in range(0, len(response_queue_msg["Messages"])):
            msg_received_unique_key = response_queue_msg["Messages"][i]["MessageAttributes"]["key"]["StringValue"]
            msg_body = response_queue_msg["Messages"][i]["Body"]
            msg_receipt_handle = response_queue_msg["Messages"][i]["ReceiptHandle"]

            sqs.delete_message(QueueUrl = queue_url, ReceiptHandle = msg_receipt_handle)

            msg_values = msg_body.strip("()").split(", ")
            img_key = str(msg_values[0].strip("'"))
            img_message =str(msg_values[1].strip("'"))
            map_webtier[msg_received_unique_key] = str(img_key) + ':' + str(img_message)
    else:
        return False


@app.route("/", methods=["POST"])
def post_data():
    session.permanent = True
    if "inputFile" not in request.files:
        return "No file found"
    req_img_file = request.files["inputFile"]
    req_img_filename = req_img_file.filename
    if upload_file_to_s3(req_img_file, config["IN_BUCKET_NAME"], req_img_filename):
        request_queue_url = sqs.get_queue_url(QueueName = config["REQ_QUEUE_URL"])["QueueUrl"]
        unique_queue_key = str(uuid.uuid4())

        if send_message_to_queue(request_queue_url, req_img_filename, unique_queue_key):
            response_queue_url = sqs.get_queue_url(QueueName = config["RESP_QUEUE_URL"])["QueueUrl"]

            while True:
                resp_queue_img_val = receive_message_from_queue(unique_queue_key, response_queue_url)
                if resp_queue_img_val:
                    return resp_queue_img_val
    
    return None


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, threaded=True, debug=True)
