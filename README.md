# HyP3 Event Monitoring

A software stack that allows automatic submission of jobs to hyp3 over a specified area to easily monitor areas of interest.

## Table of contents
- [Usage](#usage)
- [Deployment](#deployment)
  - [Prerequisites](#prerequisites)
  - [Stack Parameters](#stack-parameters)
  - [Deploy with CloudFormation](#deploy-with-cloudformation)
- [Testing](#testing)

## Usage
Events represent an area of interest and a timeframe for which RTC and InSAR products will be generated. Events are
managed (manually) as records in a DynamoDB table:
```json
{
  "event_id": "myEvent",
  "wkt": "POINT (0 0)",
  "processing_timeframe": {
    "start": "2021-02-01T00:00:00+00:00",
    "end": "2021-03-01T00:00:00+00:00"
  }
}
```

The `processing_timeframe.end` attribute is optional, and can extend into the future. Any additional attributes required
by a client application can be included in an event record.

Event monitoring routinely searches ASF's inventory for Sentinel-1 IW SLC granules matching any registered events. For
each such granule, one RTC job two InSAR jobs (for nearest and next-nearest neighbors) is automatically submitted to
HyP3. Output products of HyP3 jobs are automatically migrated to an S3 bucket with public read permissions for long term
archival and distribution.

A public REST API is provided to query events and products:
- `/events` returns all registered events
- `/events/<event_id>` returns the requested event with a list of its products
- `/recent_products` returns all products processed in the last week

## Deployment

### Prerequisites
These resources are required for a successful deployment, but managed separately:

- HyP3 target deployment (e.g. https://hyp3-api.asf.alaska.edu)
- S3 bucket for CloudFormation deployment artifacts
- Earthdata Login account authorized to download data from ASF (For submitting jobs to HyP3)
  - If submitting more jobs that the defualt hyp3 quota allows you may need to have an incresed quota
- IAM user and roles for automated CloudFormation deployments (if desired)

### Stack Parameters
Review the parameters in [cloudformation.yml](cloudformation.yml) for deploy time configuration options.

### Deploy with CloudFormation

- Install dependencies for each component (requires pip for python 3.8)

```sh
python -m pip install -r find_new/requirements.txt -t find_new/src
python -m pip install -r api/requirements.txt -t api/src
python -m pip install -r harvest_products/requirements.txt -t harvest_products/src
```

- Package the CloudFormation template
```sh
aws cloudformation package \
            --template-file cloudformation.yml \
            --s3-bucket <CloudFormation artifact bucket> \
            --output-template-file packaged.yml
```

- Deploy to AWS with CloudFormation
```sh
aws cloudformation deploy \
            --stack-name <name of your HyP3 Event Monitoring Stack> \
            --template-file packaged.yml \
            --role-arn <arn for your deployment user/role> \
            --capabilities CAPABILITY_IAM \
            --parameter-overrides \
                "EDLUsername=<EDL Username to submit jobs to HyP3>" \
                "EDLPassword=<EDL Password to submit jobs to HyP3>" \
                "HyP3URL=<URL to a HyP3 deployment for the stack to use"

```


## Testing
The HyP3 Event Monitoring source contains test files in `tests/`. To run them you need to do a bit of setup first.

- Add components to python path
```sh
export PYTHONPATH="${PYTHONPATH}:`pwd`/find_new/src:`pwd`/api/src:`pwd`/harvest_products/src"
```
- Setup environment variables
```sh
export $(cat tests/cfg.env | xargs)
```
- Install test requirements
```sh
pip install -r requirements-all.txt
```

- Run tests
```sh
pytest tests/
```
