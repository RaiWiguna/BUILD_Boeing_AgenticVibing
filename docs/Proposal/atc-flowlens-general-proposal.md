# ATC FlowLens General Proposal

## Project Overview

**ATC FlowLens** is a runway safety and decision-support dashboard for air traffic control operations. It helps controllers, airport safety teams, and training centers see runway movement, aircraft sequencing, vehicle activity, communication status, and workload risk in one clear operational view.

The system does not replace air traffic controllers. It supports their decisions by bringing scattered operational information together and turning it into earlier, clearer, and easier-to-understand alerts.

## Primary Innovation Focus Area

**Selected Focus Area: Advanced Technology and Innovation**

ATC FlowLens fits this focus area because it applies digital aviation technology to a real safety-critical problem in aerospace operations. The idea combines simulated surveillance data, runway status modeling, communication parsing, time-to-conflict calculation, workload scoring, and explainable alerting. These capabilities support innovation in controller decision support and airport operation safety.

The solution can also create social impact through improved aviation safety and support sustainability by reducing avoidable go-arounds and delays. However, its main innovation is technological: helping controllers detect and understand risk faster through an integrated digital assistant.

## Alignment with BUILD Indonesia Focus Area

ATC FlowLens aligns with the **Aerospace & Defense** theme by addressing runway safety, air traffic control workload, and airport operational readiness. These are core issues in aviation safety and critical infrastructure operations.

The project also supports the **Advanced Technology and Innovation** focus area because it uses digital decision support, simulated aircraft and vehicle tracking, rule-based conflict detection, workload scoring, and explainable alerts. For the BUILD Indonesia context, this makes the solution relevant as a practical aviation safety prototype that can be demonstrated without accessing sensitive live ATC data.

The solution has secondary alignment with **Social Impact** and **Sustainability**. Safer runway operations protect passengers, crews, ground teams, and airport emergency units. Better runway flow can also help reduce unnecessary go-arounds, delays, and fuel burn in future operational use.

## Problem Statement

Air traffic control is one of the most demanding environments in aviation. Controllers must monitor aircraft, runway status, airport vehicles, weather, radio communication, flight strips, and coordination with other units while making decisions in a matter of seconds.

The problem is not only the number of aircraft in the airspace. A controller's workload can rise quickly when several conditions happen at the same time: low visibility, active runway crossings, emergency vehicles, dense radio traffic, arrival sequencing, or a sudden change in runway use. In these moments, critical information may be spread across multiple systems and radio exchanges. This makes it harder to maintain complete situational awareness.

Runway safety is especially sensitive. A landing or departing aircraft can come into conflict with a ground vehicle if clearance status, vehicle movement, and aircraft timing are not understood together. Real incidents involving runway incursions and aircraft-vehicle conflicts show that the accident chain often comes from a mix of workload, communication gaps, timing pressure, and incomplete operational visibility.

Current air traffic technologies already provide important safety nets, such as radar, ADS-B, surface surveillance, electronic flight strips, A-SMGCS, RIMCAS, STCA, and data communication systems. However, not every airport has the same level of equipment, and many systems still require controllers to connect information from separate displays and voice communication. There is a need for a practical support layer that helps identify runway conflict risk and workload escalation before the situation becomes unsafe.

## Proposed Solution / Idea

ATC FlowLens is a dashboard-based decision-support and training tool. It brings runway movement, aircraft sequence, ground vehicle activity, communication events, and workload indicators into one operational timeline.

The system can be developed as a hackathon MVP using simulated airport data instead of live ATC systems. It would model a runway environment with inbound aircraft, departure traffic, airport vehicles such as fire trucks or inspection vehicles, clearance logs, and changing weather or visibility conditions.

Core capabilities include:

- **Runway Occupancy Monitoring**  
  Shows whether a runway is clear, occupied, being crossed, used for takeoff, or receiving an inbound aircraft.

- **Aircraft and Vehicle Tracking**  
  Displays simulated aircraft and airport vehicle positions on a simple airport map.

- **Clearance State Engine**  
  Tracks operational states such as cleared to land, cleared for takeoff, hold short, line up and wait, cleared to cross, and go around.

- **Time-to-Conflict Calculation**  
  Compares estimated aircraft touchdown or runway entry time with vehicle runway crossing or clearance time.

- **Explainable Conflict Alert**  
  Provides a short reason behind each alert, such as: "Vehicle clear time is later than aircraft touchdown time."

- **Communication Timeline**  
  Organizes ATC, pilot, and vehicle messages into a readable event history. This can later be expanded with speech-to-text or readback mismatch detection.

- **Controller Workload Indicator**  
  Estimates workload based on traffic count, radio calls, active clearances, vehicle movements, weather conditions, and active alerts.

- **Replay Mode for Training**  
  Allows users to review the timeline of a conflict scenario and understand what happened, when it happened, and why the system issued an alert.

The main value of ATC FlowLens is explainability. In a safety-critical environment, an alert is more useful when it clearly explains the operational reason behind it. The system is not meant to act like an autonomous controller. Its role is to support faster awareness, better training, and clearer decision-making while keeping the human controller in command.

## Target Users / Market

ATC FlowLens is intended for organizations and teams involved in airport operations, air traffic management, runway safety, and aviation training.

The primary users are:

- **Tower Controllers**  
  They manage takeoff, landing, runway occupancy, and runway crossing decisions.

- **Ground Controllers**  
  They coordinate aircraft taxi routes, vehicle movement, runway crossing requests, and surface safety.

- **Approach Controllers**  
  They sequence inbound aircraft and coordinate handoff to tower control.

- **Airport Operation Centers**  
  They monitor runway conditions, emergency response activity, and operational disruptions.

- **Airport Rescue and Firefighting Units**  
  They operate vehicles that may need to move near or across active runways, especially during drills or emergencies.

- **ATC Training Centers**  
  They can use the system to teach workload awareness, runway incursion prevention, communication accuracy, and conflict recognition.

- **Aviation Safety Investigators**  
  They can use replay-style views to study event timelines, communication sequence, and operational decision points.

The initial market is best positioned as a training, simulation, and safety-awareness platform for airports, aviation schools, air navigation service providers, and airport operation teams. This positioning is realistic because real operational ATC systems require strict certification, validation, cybersecurity review, and regulatory approval. A simulation-first product can still deliver strong value by improving training quality, safety analysis, and readiness for complex runway scenarios.

## Expected Impact

ATC FlowLens is expected to improve how runway safety risks are identified, explained, and reviewed in simulation or training environments. By showing aircraft movement, vehicle activity, clearance status, and time-to-conflict in one view, the system can help users recognize potential runway conflicts earlier.

The solution can also reduce training complexity by giving controllers and safety teams a clear event timeline, not only an alert. This makes it easier to understand why a conflict is happening, what operational factors contributed to it, and what action should be considered.

In the longer term, the concept can support safer runway operations, better workload awareness, and more effective post-event learning. It may also provide indirect sustainability benefits by helping reduce avoidable go-arounds, holding, taxi delays, and unnecessary fuel burn in future operational versions.

## MVP Scope

For the first prototype, ATC FlowLens can be built with:

- one simulated airport layout with a runway and taxiway
- three to five simulated aircraft
- one or two airport vehicles
- clearance and communication logs
- weather or visibility status
- rule-based conflict detection
- time-to-conflict alerting
- workload scoring
- replay mode

This scope is achievable without using sensitive real ATC data while still demonstrating a credible aerospace and defense innovation concept.

## One-Line Summary

ATC FlowLens is an explainable decision-support dashboard that helps air traffic teams detect runway conflict risk, understand controller workload, and train for safer airport operations.
