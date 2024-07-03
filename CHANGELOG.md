## 0.1.27

#### Enhancements made

- Upgraded to otter-grader 5.6.0(unreleased)

## 0.1.25

#### Enhancements made

- Added 18 minuted timeout -- the log downloaded to user shows the offending notebook


## 0.1.24

#### Enhancements made

- Removed log on first step of authorization -- it was happening for every robot, etc
- http errors get own log

## 0.1.23

#### Enhancements made

- Set timezone on instances
- updated cron job to delete and log all folders and files

## 0.1.22

#### Enhancements made

- Cleaned up Auth


## 0.1.21

#### Enhancements made

- Added Routes for Health Check from GCP Load Balancer
- Configured K8 LB health check

## 0.1.20

#### Enhancements made

- Grader DNS values for environment were not SSL

## 0.1.19

#### Enhancements made

- Added GitHub OAuth
- Cron Job now deletes notebooks and results from day before
- Added Logging of number of notebooks graded
