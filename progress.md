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




### Problems / Risks
- The flow sensor leaks when water comes through.

- Write a python script to connect the pi with influx db and send data from sensors (percentage for the humidity sensor and litters for the flow sensor)


## Week 3
### Completed
- Established a  data ingestion pipeline to our team's InfluxDB database, allowing us to visualize our telemetry in real-time on the Grafana dashboard.
- The raw pulses from the water flow sensor were calibrated and converted into Liters, using a calculated factor of 613.3 pulses per liter.
- The raw analog readings from the soil moisture sensor were mapped to a meaningful 0% to 100% percentage scale, based on empirical calibration tests (Dry value: 25350, Wet value: 8000).

### In Progress


### Problems / Risks
- The script crasses after some minutes.


### Team Contribution
- Student 1: 
- Student 2:

## Week 
### Completed 
- Succesfully added weather api script to fetch current temp, 12hour rain probability in percentage, sunset and sunrise hours
- Added a vps to run weather_api and brain 24/7 to be able to collect data.

### In Progress
- Writing main script brain.py, the main script making the decision making.
- Still callibrating to get watering stats right.

### Problems / Risks
- 


## Week 
-Advanced Decision Engine: Upgraded the logic hub (brain.py) to a 7-rule engine, adding a fail-safe rule that checks for actual past rain using the Open-Meteo API.

-Testing Infrastructure: Developed an advanced spoofing tool (test_injector.py) to inject mock data and validate all 7 irrigation rules independently.

-Decision Logging: Created a decision_log measurement in InfluxDB to display the active rule and system status directly on the Grafana dashboard using Stat panels.

-Real-Time Alerting: Integrated Grafana with Discord Webhooks to send real-time push notifications (FIRING/RESOLVED) whenever irrigation starts or stops.

-Standardized Payloads: Adopted the NGSI-LD European standard format for telemetry data transmission.

-Dynamic Duty Cycling: Implemented a dynamic sleep mechanism where the Brain node commands the Edge node (SET_SLEEP) on how long to sleep based on current weather/soil conditions, optimizing energy consumption.



###In Progress
-System monitoring in a continuous real-world run.

-Finalizing the code documentation and preparing for the final presentation.


### Problems / Risks
- **Sensor Degradation**: The soil moisture sensor's readings were significantly affected (measurement drift) after being continuously powered for many hours and exposed to constant moisture.

- **[Resolved] Hardware Malfunctions**: The capacitive soil moisture sensor experienced floating pin behavior and overheating (short-circuit risk). 

- **[Resolved] Grafana Visualization**: Handled null values and timezone discrepancies in Grafana to ensure the UI updates cleanly without empty time buckets.

