# 🧬 AgentGuard Bio-Manufacturing Data Dictionary & Contract

**Document Version:** 1.0.0

**Compliance Standard:** FAIR (Findable, Accessible, Interoperable, Reusable) / 21 CFR Part 11 Audit Ready

**Target Domain:** Autonomous Synthetic Insulin Fermentation (Bioreactor Level-2 Telemetry)

---

## Overview & Purpose

This document defines the semantic data contracts and operational thresholds governing raw telemetry ingestion from decentralized bioreactor hardware. External AI agents (via the Anthropic Model Context Protocol server) and internal BI reporting tools utilize these definitions to autonomously interpret sensor streams without manual data engineering translation.

---

## 📊 Core Custom Metrics & Parameter Significance

### 1. Biological Temperature (`temperature_c`)

* **Data Type:** `Float`
* **Unit:** Degrees Celsius (°C)
* **Optimal Range:** $36.5^{\circ}\text{C}$ to $38.5^{\circ}\text{C}$
* **Critical Threshold:** $> 39.0^{\circ}\text{C}$ (Hard Failure / Batch Denaturation)
* **Biological Significance:**
Producing synthetic insulin relies on genetically engineered host organisms (such as *E. coli* or yeast) expressing recombinant insulin proteins. These cellular machinery components are extremely sensitive to thermal energy. If internal vessel temperatures spike beyond $39.0^{\circ}\text{C}$, the protein structures undergo irreversible thermal denaturing, destroying the active pharmaceutical ingredients and instantly ruining a multi-million-dollar production batch.

### 2. Bioreactor Mechanical Agitation (`bioreactor_rpm`)

* **Data Type:** `Integer`
* **Unit:** Revolutions Per Minute (RPM)
* **Optimal Range:** $150\text{ RPM}$ to $350\text{ RPM}$
* **Critical Thresholds:** $< 100\text{ RPM}$ (Hypoxia risk) or $> 450\text{ RPM}$ (Shear stress cell lysis)
* **Biological Significance:**
Bioreactors are massive liquid culture vats requiring continuous mechanical mixing. The rotating impellers ensure uniform nutrient distribution and maintain dissolved oxygen levels essential for cellular respiration and reproduction. If the RPM drops too low, bacterial cells experience oxygen starvation (hypoxia) and cease insulin synthesis. Conversely, excessive RPM creates high shear stress that physically tears cell walls apart (lysis), contaminating the broth.

### 3. Vessel Internal Pressure (`pressure_psi`)

* **Data Type:** `Float`
* **Unit:** Pounds per Square Inch (PSI)
* **Optimal Range:** $5.0\text{ PSI}$ to $15.0\text{ PSI}$
* **Critical Threshold:** $< 2.0\text{ PSI}$ (Loss of positive containment / Contamination risk)
* **Biological Significance:**
Maintaining positive internal pressure is vital to preserve absolute biological sterility. A pressurized vessel acts as an impenetrable barrier against airborne microbial contaminants (wild bacteria, fungi) entering through micro-fissures or seals. A sudden pressure drop compromises the sterile envelope, risking total biological contamination of the culture broth.

### 4. Culture Acidity / Alkalinity (`ph_level`)

* **Data Type:** `Float`
* **Unit:** pH Scale ($0 - 14$)
* **Optimal Range:** $6.8$ to $7.4$ (Physiological Neutrality)
* **Critical Thresholds:** $< 6.5$ or $> 7.6$ (Enzymatic inactivation)
* **Biological Significance:**
Cellular metabolism generates acidic byproducts over time. Unchecked accumulation shifts the chemical balance of the growth media outside the narrow physiological band required by expression hosts. Maintaining strict pH homeostasis ensures that intracellular enzymatic pathways remain active and capable of high-yield recombinant protein production.

