✅ README FULL DOC - Draft v4.8
Linear LightSpec Optimiser v4.8
Fast, Accurate, Build-Ready Photometric Files
Powered by Evolt – So much more than light.

📖 Overview
Linear LightSpec Optimiser is a highly configurable photometric normalisation and optimisation tool designed for Lighting Designers, Engineers, and BDMs. It enables rapid generation and validation of luminaire photometric files (IES), delivering mm-accurate lengths, optimised LED power loads, and ensuring system uniformity for real-world buildability.

✅ What It Does
Parses and analyses IES photometric data
Normalises LED Board & Chip Load Calculations
Scales Luminaire Lengths dynamically
Reverse lookup of LumCAT Codes
Exports AGI32 / DIALux compliant IES files (planned for v5.x)
🔨 Key Features
Feature	Description
Live Length Validation	Ensures luminaire lengths are buildable & accurate
LED Pitch & Series/Parallel Configurations	Calculate accurate LED loads across varying designs
Optimise for Target Lux / Efficiency	Achieve desired light levels & balance efficacy
Scalable Length & Power Calculations	Scale luminaire lengths without compromising load uniformity
Live Efficacy & Wattage Feedback	Visual feedback on energy efficiency
LumCAT Reverse Lookup	Parse and validate product codes
Tier-Based Component Selection	Core / Pro / Advanced tiers, tied to Chip & Board configs
🛠️ How It Works
Upload IES file
Tool auto-loads Default Board / LED Pitch based on configuration
Derived calculations include:
Total Lumens, lm/W, Lumens/meter
Actual mA per LED & per mm
User can:
Change LED Board / Chip / ECG
Scale Luminaire Length
Adjust LED Pitch or Max Load
Normalisation recalculates load sharing automatically
Data displayed in Parameters / Derived Values / LumCAT Lookup panes
Future v5.x: Export normalised IES & CSV
📦 Data Models & Spreadsheets
Table	Description
LED_Chip_Config	Defines chips: CRI, CCT, Vf, lm/W, Nominal & Max mA
LED_and_Board_Config	Defines boards: Pitch, Series/Parallel design, Chip Reference
ECG_Config	Driver models: Power outputs, tiers
LumCAT_Config	Product code mapping for reverse lookup
📐 Design Philosophy
Normalisation by LED Pitch
Uniform load sharing across LEDs
36V SELV system consistency
Scalable & modular data models
Human-friendly defaults & future-proofing
🏆 Product Tiers
Tier	Description
Core	Basic performance, entry-level cost
Advanced	Mid-range, improved efficacy, CRI 90+
Professional	High-end, CRI 95+, advanced optics
Bespoke	Fully customised luminaires
🚀 BDM Strategy Guidance
Start High, Stay High
Lead with Pro / Bespoke specs
Downgrade only when VE requires
Track reductions in the Product Tier Matrix
Communicate performance impact clearly
🌱 Roadmap
v4.9+:
Luminaire Scaling Logic
ECG Output Balancing
Export IES + CSV
v5.x:
AGI32 / DIALux exports
ERP / CRM API Integration
BDM Margin Tracker
Visualisation Tools (Lux Levels, Beam Angles)
📂 Version History
Version	Changes
4.7	Base system, IES parsing, derived values, LumCAT lookup
4.8	Modular Chip/Board/ECG configs, Scaling Prep, mA normalisation
4.9 (Planned)	Length Scaling Logic, ECG Balancing
