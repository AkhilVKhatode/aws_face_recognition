import boto3
import time

config ={
    "AWS_ACCESS_KEY_ID": "your-access-key-id",
    "AWS_SECRET_ACCESS_KEY": "your-secret-access-key",
    "REQ_QUEUE_URL": "your-request-queue-url",
    "AMI_ID": "your-ami-id"
}
session = boto3.Session(
    region_name="us-east-1",
    aws_access_key_id=config["AWS_ACCESS_KEY_ID"],
    aws_secret_access_key=config["AWS_SECRET_ACCESS_KEY"]
)
sqs = session.client('sqs', region_name='us-east-1')
ec2 = session.client('ec2', region_name='us-east-1')

MAX_INSTANCES = 19

def main():
    while True:
        response = sqs.get_queue_attributes(QueueUrl=config["REQ_QUEUE_URL"], AttributeNames=['ApproximateNumberOfMessages'])
        num_messages = int(response['Attributes']['ApproximateNumberOfMessages'])

        response = ec2.describe_instances(Filters=[{
            'Name': 'image-id',
            'Values': [config["AMI_ID"]]
        }, {
            'Name': 'instance-state-name',
            'Values': ['running', 'pending']
        }])
        count_app_tier = sum(len(reservations['Instances']) for reservations in response['Reservations'])
        if num_messages > count_app_tier:
            temp1 = MAX_INSTANCES - count_app_tier
            temp2 = num_messages - count_app_tier
            num_instances = min(temp1, temp2)

            for i in range(num_instances):
                instance_name = f"app-tier-instance-{i+1}"
                instance = ec2.run_instances(
                    ImageId=config["AMI_ID"],
                    InstanceType='t2.micro',
                    MinCount=1,
                    MaxCount=1
                )
                instance_id = instance['Instances'][0]['InstanceId']
                ec2.create_tags(Resources=[instance_id], Tags=[{'Key': 'Name', 'Value': instance_name}])
        time.sleep(2)

if __name__ == "__main__":
    main()
