## 1.1.31

#### Enhancements made

* Handles random special characters in notebook names
* Handles hidden folders in notebook submission zip

## 1.1.29

#### Enhancements made

* PVC is now 250 GB
* Updated messages to say fds instead of sp22

## 1.1.28

#### Enhancements made

* Removed More Problematic Characters from Download Code

## 1.1.27

#### Enhancements made

* Removed Problematic Characters from Download Code
* Fixed Version Checking to be anything over 6.0.4

## 1.1.25

#### Enhancements made

* Increased(Doubled) Resources to Production Pod
* Improved the name of the download code and downloaded file

## 1.1.23

#### Enhancements made

* Actual Version Check!

## 1.1.22

#### Enhancements made

* Updated Version warning

## 1.1.21

#### Enhancements made

* Increased Docker image storage

## 1.1.20

#### Enhancements made

* Named Docker Image the same as autograder.zip

## 1.1.19

#### Enhancements made

* Docker Caches Images

## 1.1.18

#### Enhancements made

* Captures otter-grader version format changes in otter-grader version 6

## 1.1.14

#### Enhancements made

* Updated version message
* Fixed Scrolling Div
* Added Memory to pod
* Increased Timeout


## 1.1.10

#### Enhancements made

* Otter Grade: fixed otter-grader version check

## 1.1.9

#### Enhancements made

* Otter Grade: checks autograder.zip


## 1.1.8

#### Enhancements made

* Remove Button for Submission Progress
* Submission Progress in UI
* Otter Grade: prints each notebooks summary
* Otter Grade: checks autograder.zip

## 1.1.2

#### Enhancements made

* Receiving updates while grading from Otter Grader
* Otter Grade CSV to indicate which notebooks timeout

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
