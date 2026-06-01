# Weekly Progress Log

Update this file every week.

## Week 1
### Completed
- Repository created
- Initial planning completed
- Raspberry connected 
- Branches created ('docs/proposal', 'feature/cloud-logic', 'feature/infrastructure', 'feature/pi-node')

### In Progress
- Architecture draft
- Task assignment


### Problems / Risks
- Example: hardware delay
- Figure out how to connect the flow control sensor


### Next Steps
- Finalize architecture
- Create first Issues

### Team Contribution
- Student 1: Created and setup the repository
- Student 2: Configured connections

## Week 2
### Completed
- Completed the setup and connected hose to flow sensor and humidity sensor on a pot 
- Tested the sensors using test_sensor.py
- Completed Lab5 and tried grafana and influxDB
- Added Twingate to access pi remotely

### In Progress
- Sensor Calibration: i) Humidity Sensor: DRY_VALUE = 25350, WEB_VALUE = 8000 those values are approximate averages after some tests
- Add a Zero Trust Network Access(using Twingate) to PI for remote access.
- Sensor Calibration: i) Humidity Sensor: DRY_VALUE = 25350, WET_VALUE = 8000 those values are approximate averages after some tests



### Problems / Risks
- The flow sensor leaks when water comes through.

- Write a python script to connect the pi with influx db and send data from sensors (percentage for the humidity sensor and litters for the flow sensor)

### Team Contribution
- Student 1: 
- Student 2:

## Week 3 
### Completed 
- Succesfully added weather api script to fetch current temp, 12hour rain probability in percentage, sunset and sunrise hours
- Added a vps to run weather_api and brain 24/7 to be able to collect data.

### In Progress
- Writing main script brain.py, the main script making the decision making.
- Still callibrating to get watering stats right.

### Problems / Risks
- 
