
Aim: Deploy a model to Lambda/Kinesis


# Create IAMRole for Lambda

 Create a Role. Choose Lambda as the service.
 - Add the policy 'AWSLambdaKinesisExecutionRole'
 - To write the output to another data stream, you need to add another policy.
 - Name it 'mlops-dtc-lambda-role' 
	
	
# Create Lambda function
- Option: Author from scratch
- Name: mlops-dtc-lambda
- Runtime: Python 3.9
- Execution Role: mlops-dtc-lambda-role


# Modify the code
	
Edit the lambda_function.py file shown in the editor.


# Create Kinesis Data Stream
- Name: mlops-dtc-kinesis
- Capacity: Provisioned
- Shards: 1

# Read Data from Kinesis in Lambda

Add Trigger
- Trigger Configuration: Kinesis
- Stream: mlops-dtc-kinesis


# Send Data to Kinesis

```bash

KINESIS_STREAM_INPUT=mlops-dtc-kinesis 

aws kinesis put-record \
    --stream-name ${KINESIS_STREAM_INPUT} \
    --partition-key 1 \
    --region us-east-1 \
    --data '{
        "ride": {
            "PULocationID": 10,
            "DOLocationID": 10,
            "trip_distance": 40
        }, 
        "ride_id": 1234
    }'
```


# To See Output

Go to Lambda -> Monitor -> Logs -> View Logs in CloudWatch.
You will see that the output (generated from Kinesis) is in a dictionary starting with `Records`. The data (originally sent) is in base64 format, which needs to be decoded.

# Re-directing Output
We can print our results and read them in CloudWatch. In practice, we might want to re-direct them to **another** Kinesis stream.

## Creating Stream
To do this we create another Kinesis stream

- Name: mlops-dtc-ride-predictions
- Capacity: Provisioned
- Shards: 1

## Modifying Permissions
We only have read-only permission for Kinesis (from Lambda). To allow writing to this new stream, modify the permissions.

Go to IAM -> Role -> mlops-dtc-lambda-role ->Add Permission -> Attach Policy -> Create Policy
- Service: Kinesis
- Action -> Write -> PutRecord, PutRecords
- Resources: (Add Kinesis Stream ARN here) (arn:aws:kinesis:{REGION}:{ACCOUNT_ID}:stream/mlops-dtc-ride-predictions)
- Name: mlops-dtc-lambda-role-write-policy

Don't forget to attach this policy.

# Reading from this Stream

```bash
KINESIS_STREAM_OUTPUT='mlops-dtc-ride-predictions'
SHARD='shardId-000000000000'


SHARD_ITERATOR=$(aws kinesis \
    get-shard-iterator \
        --shard-id ${SHARD} \
        --shard-iterator-type TRIM_HORIZON \
        --stream-name ${KINESIS_STREAM_OUTPUT} \
        --query 'ShardIterator' \
        --region us-east-1 \
)

RESULT=$(aws kinesis get-records --shard-iterator $SHARD_ITERATOR --region us-east-1)

echo ${RESULT} | jq -r '.Records[-1].Data' | base64 --decode | jq
```

# Building Docker Image for our Model

- Attach the model and a lambda_handler.py file
- create a test file for the lambda_handler.py file
- create a Dockerfile (make sure it starts from an AWS base image e.g. public.ecr.aws/lambda/python:3.9)
- build the docker image
```
docker build -t ride-stream-ride-duration:v1 .
```
- run the image

```
# needed on local machine
export AWS_ACCESS_KEY_ID=...
export AWS_SECRET_ACCESS_KEY=...

docker run -it --rm \
    -p 8080:8080 \
    -e PREDICTIONS_STREAM_NAME="mlops-dtc-ride-predictions" \
    -e AWS_DEFAULT_REGION="us-east-1" \
    -e AWS_ACCESS_KEY_ID="${AWS_ACCESS_KEY_ID}" \
    -e AWS_SECRET_ACCESS_KEY="${AWS_SECRET_ACCESS_KEY}" \
    ride-stream-ride-duration:v1
```

- create a test file for the docker image

# Upload image to ECR

```
export ACCOUNT_ID=410330524497
export REGION=us-east-1
export REPOSITORY_NAME=mlops-dtc-ride-duration-ecr

aws ecr get-login-password --region ${REGION} | docker login --username AWS --password-stdin ${ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com
aws ecr create-repository --repository-name $REPOSITORY_NAME --region ${REGION}
REMOTE_URI=${ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com/${REPOSITORY_NAME}
REMOTE_TAG="v1"
REMOTE_IMAGE=${REMOTE_URI}:${REMOTE_TAG}

LOCAL_IMAGE="ride-stream-ride-duration:v1"
docker tag ${LOCAL_IMAGE} ${REMOTE_IMAGE}
docker push ${REMOTE_IMAGE}
```

# Lambda Function for ECR

Our previous lambda function was a test code where we were updating the code in the IDE in the browser.

We will now create another function that reads from 

- Option: Container Image
- Name: mlops-dtc-docker-lambda
- Image URI: (copy from above) = ${REMOTE_IMAGE}
- Execution Role: mlops-dtc-lambda-role

Go to Configuration -> General Configuration -> Edit
(edit Memory and Timeout depending on your model)

Go to Configuration -> Environment Variables -> Add

- PREDICTIONS_STREAM_NAME: mlops-dtc-ride-predictions
(no need to specify region/access key etc.)


(Like before...)
Add Trigger
- Trigger Configuration: Kinesis
- Stream: mlops-dtc-kinesis


# Send Data to Kinesis to trigger Docker-based Lambda Function

```
aws kinesis put-record \
    --stream-name ${KINESIS_STREAM_INPUT} \
    --partition-key 1 \
    --region us-east-1 \
    --cli-binary-format raw-in-base64-out \
    --data '{
        "ride": {
            "PULocationID": 10,
            "DOLocationID": 10,
            "trip_distance": 40
        }, 
        "ride_id": 12345
    }'
```

(you can watch logs in CloudWatch)

# Read Data from Kinesis written by the Docker-based Lambda Function

```
KINESIS_STREAM_OUTPUT='mlops-dtc-ride-predictions'
SHARD='shardId-000000000000'

SHARD_ITERATOR=$(aws kinesis \
    get-shard-iterator \
        --shard-id ${SHARD} \
        --shard-iterator-type TRIM_HORIZON \
        --stream-name ${KINESIS_STREAM_OUTPUT} \
        --query 'ShardIterator' \
        --region us-east-1 \
)

RESULT=$(aws kinesis get-records --shard-iterator $SHARD_ITERATOR --region us-east-1)

echo ${RESULT} | jq -r '.Records[-1].Data' | base64 --decode | jq
```