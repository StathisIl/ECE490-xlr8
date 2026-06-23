# ECE490 Team Project Repository

## Team Information
- Team name: XLR8
- Team members:
  - Iliadis Efstathios - 03829
  - Antoniadis Ioannis - 03805

## Project Title
Smart Irrigation System (API)

## Project Summary
This project implements an end-to-end IoT Decision Support System for smart agriculture.
It utilizes a Raspberry Pi as an edge gateway to collect real-time soil moisture and water 
flow metrics using analog and digital sensors (ADS1015, YF-S201). Data is modeled using the 
NGSI-LD standard and transmitted via the lightweight MQTT protocol to a centralized Private Cloud Server (Ubuntu/Docker). 
A custom logic engine processes the time-series data stored in InfluxDB, integrates external weather forecasts via a Weather API, 
and provides actionable irrigation alerts and real-time visualization through a Grafana dashboard. 
The system also features a bidirectional communication loop for dynamic duty cycling to optimize energy consumption.

## Objectives
- Objective 1: Establish a reliable, fault-tolerant Edge-to-Cloud telemetry pipeline using MQTT (QoS 1) and NGSI-LD data modeling.
- Objective 2: Implement a data-driven logic engine that integrates local sensor readings with external Weather API forecasts to generate smart irrigation advisories (Rain Delay policy).
- Objective 3: Design an enterprise-grade, scalable backend infrastructure utilizing Docker containers for Time-Series storage (InfluxDB) and real-time visualization (Grafana), while enabling remote device configuration (Adaptive Sampling Rate).

## Repository Structure
- `src/` → source code
- `docs/` → architecture, setup, extra documentation
- `data/` → datasets, logs, exported measurements
- `tests/` → tests
- `progress.md` → weekly progress log
- `milestones.md` → milestone evidence map
- `demo-evidence/` → screenshots, output snapshots, demo proof

## Required Workflow
1. Create an Issue before starting a task
2. Work in a branch
3. Commit regularly with meaningful messages
4. Open a Pull Request
5. Merge into `main`
6. Update `progress.md`

## Deliverables to maintain
- complete `README.md`
- weekly `progress.md`
- `docs/architecture.md`
- `milestones.md`
- demo evidence in `demo-evidence/`

## Current Status
Pi code is in feature/pi-node/src
The rest of the code is on a vps in feature/cloud-logic. Files are brain.py weather.py and test_injector.py
