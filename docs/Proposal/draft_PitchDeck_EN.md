# ATC FlowLens Pitch Deck Draft

Document purpose: This draft defines the full content structure for a maximum 10-slide pitch deck for BUILD Indonesia. It is written as a proposal deck, not only a product presentation. The deck should explain the problem, evidence, solution, MVP, impact, business relevance, and why the idea fits BUILD Indonesia.

Recommended deck length: **10 slides maximum**  
Project: **ATC FlowLens**  
Theme: **Aerospace & Defense**  
Primary focus area: **Advanced Technology and Innovation**  
Secondary relevance: **Social Impact and Sustainability**

---

## Should the Deck Include More Data?

Yes. The pitch deck should include enough data and references to show that ATC FlowLens is based on real aviation safety problems, not only assumption or speculation. However, the deck should not become a research paper. The main slides should use short, high-signal evidence, while detailed references can be placed in appendix notes or backup slides.

The deck should include four types of evidence:

1. **Real incident evidence**  
   Examples of runway incursion, aircraft-vehicle conflict, low visibility, and controller workload cases.

2. **Operational evidence**  
   Explanation of why ATC workload becomes difficult: traffic, runway crossing, communication, weather, vehicle movement, and multiple display monitoring.

3. **Technology landscape evidence**  
   Current ATC/ATM systems already exist, such as radar, ADS-B, A-SMGCS, RIMCAS, STCA, electronic flight strips, CPDLC, and SWIM. This helps position ATC FlowLens as a support and training layer, not a replacement for certified ATC systems.

4. **Business and operational impact evidence**  
   The solution can support training efficiency, safety awareness, post-event review, runway flow, and future reduction of avoidable delays or go-arounds.

Business impact should be included because BUILD Indonesia is a hackathon and innovation program. Judges will likely evaluate not only technical creativity, but also practical value, feasibility, adoption path, and impact. The business angle does not need to be complex, but it should clearly answer:

- Who would use this?
- Why would they care?
- What value does it create?
- Why is the MVP feasible?
- How can it grow after the hackathon?

---

# Slide-by-Slide Deck Structure

## Slide 1 - Cover

### Slide Title
**ATC FlowLens**

### Subtitle
**Explainable Runway Safety and ATC Decision-Support Dashboard**

### Content to Show
- BUILD Indonesia Hackathon
- Theme: Aerospace & Defense
- Focus Area: Advanced Technology and Innovation
- Team name
- Team members

### Speaker Notes
ATC FlowLens is a proposed runway safety and decision-support dashboard for air traffic control operations. It helps air traffic teams see aircraft movement, ground vehicle activity, clearance status, communication timeline, and workload risk in one operational view.

### Visual Direction
Use a clean airport runway or tower-control inspired visual. Avoid overly futuristic graphics. The deck should feel credible, aviation-focused, and operational.

---

## Slide 2 - Problem: Runway Operations Are Time-Critical

### Slide Message
Air traffic controllers must make fast decisions while monitoring many moving parts at once.

### Content to Show
Controllers need to monitor:

- aircraft approaching, landing, departing, or taxiing
- active runway status
- airport vehicles and runway crossing requests
- weather and visibility
- radio communication and readbacks
- flight strips and clearance state
- coordination with ground, tower, approach, airport operations, and emergency units

### Key Statement
**When information is scattered across displays, voice communication, and human memory, runway conflict risk becomes harder to detect early.**

### Speaker Notes
The problem is not only the number of aircraft. Workload can increase quickly when low visibility, emergency vehicles, radio congestion, runway crossings, and arrival sequencing happen at the same time. In that environment, the controller must connect aircraft timing, vehicle movement, and clearance status within seconds.

### Suggested Visual
A simplified diagram showing multiple information sources flowing into one controller:

- aircraft track
- vehicle track
- radio call
- flight strip
- weather
- runway status

---

## Slide 3 - Evidence: Runway Conflict Is a Real Safety Issue

### Slide Message
Runway conflicts and workload-related incidents have happened in real operations.

### Content to Show
Use 3 short case examples:

| Case | What Happened | Relevance to ATC FlowLens |
|---|---|---|
| LATAM Peru Flight 2213, Lima, 2022 | Aircraft collided with a fire truck on the runway during takeoff roll. | Shows the risk of aircraft-vehicle conflict and emergency vehicle movement near active runway. |
| Austin-Bergstrom, 2023 | A departure aircraft was cleared on the runway while another aircraft was on final approach in dense fog. | Shows how low visibility and runway status awareness can reduce safety margin. |
| LaGuardia, 2026 preliminary report/news | A fire truck runway crossing occurred close to a landing aircraft in a high-workload environment. | Shows why time-to-conflict and workload awareness matter. |

### Important Note
For cases still under investigation, avoid claiming final cause. Use careful wording such as "preliminary information" or "reported as a high-workload environment."

### Speaker Notes
These cases show a common pattern: runway safety issues rarely come from one factor alone. They often involve timing pressure, communication, vehicle movement, visibility, workload, and incomplete shared awareness.

### Suggested Visual
Timeline-style visual:

Aircraft on final/takeoff + vehicle entering/crossing runway = conflict window.

---

## Slide 4 - Gap: Current Systems Help, but Information Can Still Be Fragmented

### Slide Message
ATC already has important technologies, but the challenge is connecting information into one clear operational picture.

### Content to Show
Existing technologies:

- Radar / ADS-B / MLAT
- Surface surveillance
- Electronic flight strips
- A-SMGCS / RIMCAS / ASDE-X
- STCA / MTCD
- CPDLC / Data Comm
- SWIM and flight data systems

### Gap to Highlight
- Not every airport has the same level of surface surveillance and conflict alerting.
- Voice communication is still widely used, especially in tower and ground operations.
- Controllers may need to connect runway status, clearance, aircraft timing, and vehicle movement from separate sources.
- Alerts are more useful when they are explainable and connected to an event timeline.

### Key Statement
**ATC FlowLens is not designed to replace certified ATC systems. It is a practical support, simulation, and training layer that makes runway risk easier to understand.**

### Speaker Notes
The idea is realistic because it does not claim to automate ATC or take authority away from controllers. It focuses on supporting awareness, training, and post-event review.

### Suggested Visual
Two-column layout:

Left: Existing systems  
Right: Remaining gap  
Bottom: ATC FlowLens as an explainable support layer

---

## Slide 5 - Solution: ATC FlowLens

### Slide Message
ATC FlowLens brings runway movement, clearance status, vehicle activity, communication, and workload risk into one dashboard.

### Main Definition
**ATC FlowLens is a runway safety and decision-support dashboard that helps air traffic teams detect runway conflict risk, understand controller workload, and review events through an explainable timeline.**

### Core Capabilities
- Runway occupancy monitoring
- Aircraft and vehicle tracking
- Clearance state engine
- Time-to-conflict calculation
- Explainable conflict alert
- Communication timeline
- Workload indicator
- Replay mode for training and review

### Speaker Notes
The core value is clarity. Instead of only showing an alert, the system explains why the alert appears: which aircraft, which vehicle, what clearance state, what estimated time, and what runway overlap risk.

### Suggested Visual
Dashboard mockup concept:

- left: airport map
- center: arrival/runway sequence
- right: alerts and communication timeline
- top: workload score

---

## Slide 6 - How It Works

### Slide Message
The system converts simulated operational data into clear runway risk insight.

### Input
- aircraft position, speed, phase, runway
- vehicle position, speed, status, route
- runway and taxiway layout
- clearance status
- communication log
- weather and visibility status

### Processing
- runway occupancy model
- clearance state engine
- time-to-conflict calculation
- workload scoring
- severity classification
- alert explanation generator

### Output
- runway map dashboard
- conflict alert
- reason behind alert
- recommended action category
- workload indicator
- replay timeline

### Example Rule
```text
IF aircraft.status = "cleared_to_land"
AND aircraft.distance_to_threshold < 2 NM
AND vehicle.status = "cleared_to_cross"
AND vehicle.runway = aircraft.runway
AND vehicle_clear_time > aircraft_touchdown_time
THEN trigger HIGH runway conflict alert
```

### Speaker Notes
For the hackathon MVP, the system can use simulated JSON data. This makes it feasible without using sensitive real ATC data, while still demonstrating the logic and operational value.

### Suggested Visual
Simple flow diagram:

Inputs -> Processing Engine -> Dashboard and Alerts

---

## Slide 7 - MVP Scope and Demo Plan

### Slide Message
The MVP is feasible for a hackathon because it uses simulation, rule-based logic, and a focused runway scenario.

### MVP Components
- one simulated airport layout with runway and taxiway
- three to five simulated aircraft
- one or two airport vehicles
- clearance and communication logs
- weather or visibility status
- rule-based conflict detection
- time-to-conflict alerting
- workload scoring
- replay mode

### Demo Scenario
Example scenario:

1. Aircraft BAW123 is on final approach and cleared to land.
2. Vehicle ARFF-2 requests or receives runway crossing clearance.
3. The system estimates aircraft touchdown time and vehicle runway clear time.
4. A conflict is detected because the vehicle may still occupy the runway when the aircraft arrives.
5. ATC FlowLens shows an alert, explanation, workload state, and replay timeline.

### Hackathon Build Priority
Build in this order:

1. simulation data model
2. runway map visualization
3. clearance state engine
4. conflict detection and time-to-conflict
5. alert explanation
6. workload score
7. replay mode

### Speaker Notes
This scope is strong because it is narrow enough to build but complete enough to demonstrate the idea. It avoids dependency on live aviation data and focuses on a clear safety story.

---

## Slide 8 - Target Users and Business Impact

### Slide Message
The first adoption path is training, simulation, and safety awareness before real operational integration.

### Target Users
- tower controllers
- ground controllers
- approach controllers
- airport operation centers
- airport rescue and firefighting units
- ATC training centers
- aviation safety investigators

### Initial Market Positioning
**Simulation, training, and runway safety awareness platform for airports, aviation schools, Air Navigation Service Providers, and airport operation teams.**

### Business / Operational Value
- improves training quality for runway conflict scenarios
- reduces time needed to explain complex incident timelines
- supports safety briefings and after-action review
- helps airport teams understand aircraft-vehicle risk
- can become a low-risk entry point before certified operational systems
- creates a path toward advanced modules such as speech-to-text, readback mismatch detection, and richer workload analytics

### Why Business Impact Matters
Even if the MVP is a simulation tool, it can create value for aviation education, safety training, and operational readiness. This makes the solution more realistic than a tool that tries to directly replace certified ATC infrastructure.

### Speaker Notes
The realistic first market is not live ATC operations. Certification for operational ATC systems is strict and complex. A training and simulation product has a more practical adoption path while still addressing a real safety need.

---

## Slide 9 - Expected Impact and BUILD Indonesia Alignment

### Slide Message
ATC FlowLens aligns with BUILD Indonesia by applying advanced technology to a real aerospace safety challenge.

### Expected Impact
- helps users recognize runway conflict risk earlier
- improves understanding of aircraft-vehicle interaction
- supports controller workload awareness
- makes training scenarios easier to explain and replay
- helps safety teams review near-miss or simulated incidents
- may reduce avoidable go-arounds, taxi delay, holding, and fuel burn in future operational versions

### BUILD Indonesia Alignment
**Theme: Aerospace & Defense**  
The solution addresses runway safety, air traffic control workload, and airport operational readiness.

**Primary Focus Area: Advanced Technology and Innovation**  
The solution uses digital decision support, simulated tracking, conflict prediction, workload scoring, and explainable alerting.

**Secondary Relevance: Social Impact and Sustainability**  
Safer runway operations protect passengers, crews, ground staff, and emergency units. Better flow can also support lower delay and fuel waste.

### Speaker Notes
This slide should connect the product idea to the hackathon criteria. It shows that the idea is not only technically interesting, but also relevant to Indonesia's aviation ecosystem and BUILD's innovation direction.

---

## Slide 10 - Roadmap and Closing

### Slide Message
ATC FlowLens starts as a feasible hackathon MVP and can grow into a broader aviation safety training platform.

### Roadmap

**Phase 1 - Hackathon MVP**
- simulated runway map
- aircraft and vehicle movement
- clearance log
- time-to-conflict alert
- workload indicator
- replay timeline

**Phase 2 - Enhanced Prototype**
- speech-to-text for ATC-style communication
- readback mismatch detection
- better scenario generator
- improved workload model
- multi-runway support

**Phase 3 - Future Vision**
- integration with airport operation datasets
- training simulator for tower/ground coordination
- safety analytics dashboard
- research pathway toward certified decision-support use

### Closing Line
**ATC FlowLens helps air traffic teams see runway risk before it becomes a runway incident.**

### Speaker Notes
End with a confident but careful message: the solution is not replacing controllers; it helps them train, review, and understand runway risk faster.

---

# Appendix Data and Supporting Material

The appendix can be used as backup material for Q&A, not necessarily included in the 10 main slides.

## Appendix A - Real Incident References

| Incident | Date | Summary | Why It Matters |
|---|---:|---|---|
| LATAM Peru Flight 2213 | 18 Nov 2022 | Airbus A320neo collided with fire truck on runway during takeoff roll in Lima. | Strong aircraft-vehicle runway conflict example. |
| Austin-Bergstrom runway incursion | 4 Feb 2023 | Southwest aircraft was cleared for takeoff while FedEx aircraft was on final approach in dense fog; FedEx went around. | Shows low visibility and runway status awareness problem. |
| Linate Airport disaster | 8 Oct 2001 | Runway incursion in fog led to collision between Cessna and SAS MD-87. | Shows systemic runway safety risk involving visibility, procedure, and surveillance. |
| Uberlingen mid-air collision | 1 Jul 2002 | Collision involving workload, system maintenance, and conflict alert issues. | Shows importance of workload, safety nets, and human-machine interface. |
| LaGuardia fire truck runway conflict | 22 Mar 2026 | Preliminary reports described a fire truck crossing close to landing aircraft in a high-workload environment. | Recent example of runway crossing, workload, and time pressure. |

Suggested wording in deck: "These cases are used as safety context, not as claims that ATC FlowLens would have prevented them."

## Appendix B - ATC Workload Factors

| Workload Factor | Example | Relevance |
|---|---|---|
| Traffic density | multiple arrivals and departures | increases monitoring and communication load |
| Weather | fog, thunderstorm, wind shift | reduces visibility and changes runway flow |
| Radio congestion | blocked transmission, repeated readback | increases communication workload |
| Runway crossing | aircraft or vehicle crossing active runway | creates time-sensitive risk |
| Emergency vehicle movement | fire truck, inspection vehicle | may require urgent coordination |
| Multiple displays | radar, surface map, strip, weather | increases visual and cognitive load |
| Staffing/fatigue | short staffing, night shift | affects attention and response time |

## Appendix C - Existing Technology Landscape

| Technology | Function | Relationship to ATC FlowLens |
|---|---|---|
| Radar | aircraft detection and tracking | possible future data source |
| ADS-B | aircraft position broadcast | possible simulation or public-data source |
| MLAT | position estimation from transponder signals | supports surveillance context |
| Surface surveillance | monitors runway/taxiway movement | core concept reference |
| Electronic flight strip | tracks flight and clearance information | related to clearance state engine |
| A-SMGCS | surface movement guidance and control | existing advanced surface safety system |
| RIMCAS/RMCA | runway incursion/conflict alert | existing safety net reference |
| STCA/MTCD | short/medium-term aircraft conflict detection | conflict prediction reference |
| CPDLC/Data Comm | digital ATC communication | future communication input |
| SWIM | aviation data sharing framework | future integration reference |

## Appendix D - Example Simulation Dataset

```json
{
  "aircraft": [
    {
      "callsign": "BAW123",
      "phase": "final",
      "runway": "27",
      "distance_nm": 1.8,
      "speed_kt": 145,
      "clearance": "cleared_to_land",
      "estimated_touchdown_sec": 42
    },
    {
      "callsign": "SIA456",
      "phase": "downwind",
      "runway": "27",
      "distance_nm": 9.8,
      "speed_kt": 180,
      "clearance": "continue_approach",
      "estimated_touchdown_sec": 260
    }
  ],
  "vehicles": [
    {
      "id": "ARFF2",
      "type": "fire_truck",
      "status": "cleared_to_cross",
      "runway": "27",
      "estimated_clear_time_sec": 58
    }
  ],
  "communications": [
    {
      "time": "18:42:11",
      "speaker": "Tower",
      "target": "BAW123",
      "message": "Cleared to land runway 27"
    },
    {
      "time": "18:42:18",
      "speaker": "Tower",
      "target": "ARFF2",
      "message": "Cross runway 27"
    }
  ],
  "weather": {
    "visibility": "low",
    "wind": "270/12",
    "condition": "fog"
  }
}
```

## Appendix E - Example Alert Output

```text
HIGH RUNWAY CONFLICT RISK

Aircraft: BAW123
Status: Cleared to land RWY 27
Estimated touchdown: 42 seconds

Vehicle: ARFF2
Status: Cleared to cross RWY 27
Estimated runway clear time: 58 seconds

Reason:
Vehicle clear time is later than aircraft touchdown time.
Predicted runway occupancy overlap: 16 seconds.

Suggested action category:
Hold vehicle / cancel crossing / consider go-around advisory if crossing has already started.
```

## Appendix F - Workload Score Variables

Possible workload scoring inputs:

- active aircraft count
- active vehicle count
- radio calls in the last 5 minutes
- number of active clearances
- runway crossing requests
- low visibility or weather disruption
- active alerts
- emergency state
- runway configuration change

Simple scoring idea:

```text
workload_score =
  aircraft_count_weight
  + vehicle_count_weight
  + communication_load_weight
  + weather_risk_weight
  + active_alert_weight
  + emergency_weight
```

Workload levels:

- Low: normal operation
- Medium: increased monitoring required
- High: multiple risk factors active
- Critical: conflict or emergency with limited reaction time

## Appendix G - Business Impact Framing

### Problem Owner
- airport operators
- ANSPs
- ATC training centers
- aviation academies
- airport safety teams

### Value Created
- faster understanding of complex runway scenarios
- better training for aircraft-vehicle conflict
- easier incident replay and explanation
- safer coordination between tower, ground, and emergency units
- lower barrier for early aviation safety innovation through simulation

### Adoption Path
1. training and simulation tool
2. safety briefing and scenario replay product
3. airport operation support prototype
4. research collaboration with ANSPs or aviation schools
5. future certified decision-support exploration

### Possible Differentiation
ATC FlowLens focuses on explainability and runway event timeline, not only alerting. This makes it useful for training, review, and human understanding.

## Appendix H - Recommended Design Tone

The deck should feel:

- professional
- aviation-specific
- clear and calm
- operational, not overly futuristic
- confident but not exaggerated

Avoid claims such as:

- "automates ATC"
- "prevents all runway accidents"
- "replaces controllers"
- "real-time certified ATC system"

Use safer wording:

- "decision-support"
- "simulation-first"
- "training and safety awareness"
- "human-in-the-loop"
- "helps identify risk earlier"
- "supports clearer post-event review"

