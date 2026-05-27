# System Architecture

## Overview
The project is a Smart Irrigation System designed to optimize agricultural water usage through real-time monitoring and predictive logic. It utilizes an Edge Computing approach to collect environmental data (soil moisture) and water consumption metrics (water flow). Instead of relying on a naive threshold, the system incorporates a decoupled "Brain" logic that cross-references local soil conditions with external weather forecasts (probability of rain) to make intelligent, water-saving alerting decisions.   

## Components
- sensors / input devices :Analog Soil Moisture Sensor connected via an ADS1015 I2C ADC.

- processing node :Processing Node:A Raspberry Pi acting as an Edge Node (edge12). It runs Python scripts inside an isolated virtual environment (venv) and operates persistently in the background using tmux.

- communication :Dual-path transmission: MQTT protocol (Port 1883) for telemetry broadcasting (to satisfy standard project constraints).

- storage :InfluxDB time-series database (edge12_db) hosted on the central university server.

- dashboard / app :Grafana dashboard featuring customized Data Visualizations

- actuators / notifications :A software-based Smart Alerting System. Instead of a physical relay, a dedicated "Brain" script generates system notifications when intervention is required.

## Data Flow
Describe how data moves through the system.

## Decisions and Tradeoffs
Explain key design choices.

## Validation Plan
Describe how you will test the system.
