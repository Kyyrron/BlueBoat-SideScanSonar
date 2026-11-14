# Harbour seabed objects of interest — target set, evidence and simulation specification

*Version 2, 2026-11-14. Supersedes version 1 ("Target Families and Orderable Surrogates", August 2026), which
was written for a field campaign that will not take place. Version 1 stays on the owner's machine; its shopping
list is summarised in Appendix B.*

**What this document fixes**
- **What the thesis means by "objects of interest".** Harbour seabed litter and obstructions of at least 0.5 m, in
  the families that harbour operators actually meet (§1–§2).
- **The simulator's object set.** It goes from 29 classes to 12 active classes, and the 22 others become legacy
  (§3).
- **Each class, precisely enough to build.** Geometry, materials, states, poses, burial, sizes and metadata (§4).
- **How the litter is placed in a simulated harbour.** Densities, family mix, spatial pattern and burial (§5).
- **Implementation instructions** for the code sessions (§6).
- **Text and caveats** for the thesis (§7).

**Evidence tags used throughout**

| Tag | Meaning |
|---|---|
| **[REF n]** | Read in source n of §9 |
| **[PROJ]** | A project fact: our own recordings or reviews |
| **[DERIVED]** | Computed here from referenced values; the computation is shown |
| **[DESIGN]** | A modelling choice, with its reason. It is a parameter with a bracket, never a measurement |
| **[UNCERTAIN]** | Not verified; check before relying on it |

---

## 1. Scope in one paragraph (for the thesis introduction)

**The detection task.** The thesis detects man-made objects of at least about 0.5 m lying on the seabed of harbour
basins 4.5–11 m deep, imaged by a hull-mounted 450 kHz side-scan sonar on a small USV.

**Why this target set.** It is the overlap of three needs.
1. **Port maintenance and hydrography.** Harbours and berths must be surveyed so that cubic features above 0.5 m
   (IHO Exclusive Order) or above 1 m (Special Order) are detected [REF 1]. Side-scan sonar is the standard tool
   for finding debris before dredging and port works [REF 2].
2. **Environmental clean-up.** Harbour seabed clean-ups repeatedly lift a small, stable set of large items: tyres,
   crates, shopping trolleys, metal scrap, nets and ropes, and derelict traps [REF 17–21]. Side-scan sonar is
   already used operationally to find derelict traps and nets [REF 11–13] and dumped drums [REF 14].
3. **Our sensor's physics.** At 20 m range the beam footprint along the track is about 0.17 m [DERIVED: 20 m ×
   0.5°]. An object of 0.5 m spans about three footprints and about thirty range bins, which is the smallest size
   with a usable signature.

**What is excluded.** Small litter (bottles, cans, bags) dominates the item counts in most surveys [REF 6, 8, 22],
but it is below this threshold. It enters the simulator as seabed clutter, not as a target.

---

## 2. Evidence review — who looks for what on harbour seabeds

### 2.1 Port maintenance and hydrography

- **IHO S-44, Edition 6.2.0 (October 2024)** [REF 1]:
  - The **Exclusive Order** is meant for "harbours, berthing areas and critical areas of fairways and channels".
    Its feature-detection requirement is "cubic features > 0.5 m".
  - The **Special Order** is meant for areas "where underkeel clearance is critical". It requires "cubic features
    > 1 m".
  - **Order 1a** requires "cubic features > 2 m, in depths down to 40 m".
  - A *significant feature* is a "feature that poses a potential danger to navigation".
  - **Consequence:** in a harbour, an object of 0.5–1 m is by definition a feature a survey must detect. That is
    the size floor of the thesis's targets.
- **Dredging contractors** use side-scan sonar for the "detection and identification of underwater objects", such
  as "debris, rocks, pipelines" [REF 2].
- **Multibeam mapping of the Venice lagoon** [REF 3] (360 kHz, grids of 0.05–0.5 m, about 40 km² of channels).
  - **Litter found:** wrecks, containers, rubber fenders and tyres, rip-rap debris and dock piles.
  - **Density:** macro-litter averaged 7.5 items/km² over the channels, with a peak of 1,161 items/km² in the
    urban Grand Canal.
  - **Other footprints in the same survey:** keel and propeller grooves, propeller scour holes up to 120 × 80 ×
    3.5 m in the cruise harbour, and dredging marks. These matter to session 02 as seabed texture.
- **Side-scan mapping of Mangalia harbour, Romania** [REF 4] found debris, wrecks, metal frames, and a rock mound
  near the main channel judged a risk to large ships.

### 2.2 Environmental clean-up and derelict fishing gear

**Derelict fishing gear (ALDFG)**
- **Loss rates.** A global meta-analysis estimates that 8.6 % of all traps (19 % of pots and traps specifically),
  5.8 % of gillnets and 29 % of lines are lost every year [REF 10].
- **Derelict traps are found with side-scan sonar, routinely and at scale.**
  - **Lower York River** [REF 11]: a 600 kHz hull-mounted side-scan sonar, run as 100 m swaths with 20 % overlap,
    flagged 676 trap targets; 16 of 17 checked were traps (94 %). 82 % of the derelict traps removed were still
    fishing.
  - **Chesapeake programmes** [REF 12]: more than 28,000 pots were removed in Virginia over three years, and 5,700
    in Maryland in one year. The pots are about 0.6 m cubes of galvanised or vinyl-coated wire, with two chambers.
- **Derelict nets are harder** [REF 13].
  - With a 300 kHz side-scan sonar, all 9 net targets checked by camera were nets or lines.
  - But nets on sand "may be buried", leaving only the lead line visible.
  - Crevices in rock walls produced false targets.
  - Nets are a real target with a low expected detection rate and a high false-alarm risk.
- **By count, ropes and lines dominate.**
  - Ropes and textiles were about 42 % of the seafloor items in German sport-boat marinas [REF 6].
  - Lines and ropes were 57.5 % of the items over 822,704 m² of Italian seabed filmed by ROV [REF 7].

**Hazardous containers**
- At a deep-sea dump site off Los Angeles, a wide-area side-scan survey by two AUVs over 150 km² identified more
  than 74,000 debris targets [REF 14]. Drums and barrels are a documented side-scan target class.
- Drums are rare in harbours but carry the highest hazard per item. They are kept for that reason.

**Tyres**
- **Toxicity.** Car-tyre rubber leaches zinc and organic additives (benzothiazole) into seawater. At high
  concentrations the leachate killed marine copepods within 48 h [REF 15].
- **Where harbour tyres come from.** Fender tyres fall in: 180 tyres were lifted from one small Cypriot fishing
  shelter where "anglers use them as boat bumpers" [REF 18]. Tyres are also dumped.
- **They show on side-scan.** Tyres "show clearly on flat, smooth seabed" on side-scan in Plymouth Sound, next to
  lost anchors, cables, dumped fishing gear and ghost pots [REF 17].
- **Our own data.** The July 2026 Shiraishi-jima harbour recordings contain a tyre that was barely visible
  [PROJ]. The cause is confounded: altitude, aspect, and how strongly rubber and steel belts reflect.

**Classification standard**
- EU monitoring uses a joint list of litter categories [REF 9]. It lets our classes be mapped to a monitoring
  category when the thesis reports results.

### 2.3 What harbour seabed clean-ups and surveys actually find

| Site and source | Method | Large items reported |
|---|---|---|
| Port of Thessaloniki [REF 5] | **USV + 455/800 kHz side-scan**, ROV ground truth | 56 targets in 120 × 160 m (≈ 29 per ha [DERIVED]); sizes peak at 0.6 and 1.5 m, 59 % between 0.5 and 0.7 m, 12.5 % over 1 m; metal pieces, **car tyres**, wires, colonised by biota |
| Venice lagoon channels [REF 3] | Multibeam, 360 kHz | Wrecks, containers, **tyres and rubber fenders**, rip-rap debris, piles |
| Plymouth Sound [REF 17] | Side-scan sonar | **Tyres** (car, truck, tractor), lost anchors, cables, dumped fishing gear, **ghost pots** |
| Cherbourg harbour, 2023 [REF 20] | Divers | 86 items: **tyres**, glass, metal, plastic, **abandoned crates**, shopping trolleys, motorbikes |
| Pomos fishing shelter, Cyprus, 2022 [REF 18] | Divers | About 1,500 kg, including **180 tyres** (used as fenders), old **nets**, metal, cans |
| Marina Port de Mallorca, 2025 [REF 19] | Divers | 1,140 kg: supermarket trolleys, **tyres** |
| Port of Arbatax, Sardinia, 2026 [REF 21] | Divers | About 600 kg: **tyres**, plastic |
| 14 marinas and city ports, Germany and North Africa [REF 6] | Camera on a pole | 0.04–3.7 items/m² (mostly small); ropes and textiles about 42 % in sport-boat marinas |
| Kagawa coast, Seto Inland Sea [REF 22] | Divers | Mostly household waste (bags, cans); **tyres** and appliances "occasionally"; much litter buried under sand and mud |
| Shizuura fishing port, Numazu, 2024 [REF 23] | Divers | Much of the litter "buried in sludge" |

**What the table shows**
- **Tyres are the large item most consistently reported in harbours**, in every method.
- **Crates, metal scrap, nets and ropes, and traps** recur.
- **Shopping trolleys, bicycles and motorbikes** belong to city harbours and marinas rather than fishing harbours.
- **Burial in harbour mud** is reported repeatedly.

### 2.4 Japan

- **The law.** The Act on the Promotion of Marine Debris Treatment (海岸漂着物処理推進法, 2009) was amended in June
  2018 to cover **drifting and seabed litter** that hinders daily life or economic activity [REF 25].
- **Who removes seabed litter.** In Okayama — the prefecture of our harbour data — the Ushimado fisheries
  cooperative collects seabed litter while fishing, and reports that the amount is not falling [REF 24].
- **Ghost gear.** WWF Japan, a town and its fishing cooperative ran a diver survey of ghost gear (nets, ropes,
  buoys) off Nishi-Izu in 2023 [REF 26].
- **Persistence.** Offshore trawl surveys around Japan found 81–2,926 items/km². Seafloor litter "retains its
  condition for a long time (over 30 years)" [REF 8]. Litter therefore accumulates rather than turning over.
- **Low-density plastics still sink.** About 70 % of the seabed litter recovered offshore was plastic lighter than
  water (HDPE, LDPE, PP) [REF 29]. Fouling and trapped sediment sink low-density plastics; a polypropylene crate on
  the seabed is not an anomaly.

### 2.5 Synthesis: ranking the candidate objects

Criteria, one per column:

| Column | Question |
|---|---|
| Freq | Reported repeatedly in harbour surveys or clean-ups? |
| Hazard | Environmental or navigation hazard? |
| ≥ 0.5 m | Above the IHO Exclusive Order floor? |
| SSS | Is there a side-scan precedent for finding it? |
| Family | The acoustic family it covers |

| Candidate | Freq | Hazard | ≥ 0.5 m | SSS | Family | Decision |
|---|---|---|---|---|---|---|
| Car or light-truck tyre | **High** [3, 5, 17–21] | Leachate [15] | Yes | Yes [5, 17] | F7 toroid | **Target T6** |
| Wire trap or pot (derelict) | High in fishing areas [11, 12] | Ghost fishing [11] | Yes (0.6 m) | **Yes, at scale** [11, 12] | F4 open frame | **Target T4** |
| Net or rope bundle | **Highest by count** [6, 7] | Ghost fishing; propellers | Often | Partial [13] | F8 compliant | **Target T7** |
| Plastic crate or box | Medium [20] | Low | Yes | Our field box [PROJ] | F1 flat shell | **Target T1** (physics validated) |
| 200 L drum | Low | **High** (contents) | Yes | Yes [14] | F2 cylinder | **Target T2** |
| Concrete block, sinker, rubble | Medium [3, 4] | Navigation | Yes | Yes [4] | F3 dense block | **Target T3** |
| Pipe, tube, metal bar | Medium (metal pieces, wires [5], cables [17]) | Navigation, fouling | Yes | Yes [5] | F5 elongated | **Target T5** |
| Shopping trolley, bicycle, e-scooter, motorbike | Medium in city harbours [19, 20] | Low | Yes | — | F4 (like the trap) | Not a class: covered acoustically by T4; optional variant |
| Lost anchor and chain | Medium [17] | Navigation | Yes | Yes [17] | F3/F5 compound | Legacy; chains kept as structure tethers |
| Sunken boat or wreck | Low | Navigation | ≫ 1 m | Yes [3, 4] | Large hull | Out of scope: any survey finds it, so no replanning question |
| Traffic cone | Low in harbours | Low | 0.7 m tall | — | F6 taper | Dropped (legacy) |
| Bottle, can, PET, battery, 18 L tin, pail | **High** (small) [6, 8, 22] | Batteries | **No** | — | F9 / small F1–F2 | Clutter only (C2) or legacy |
| Pallet, timber | Low on the seabed (wood floats) | Low | Yes | — | F4/F5 | Legacy |

**The resulting set** has seven target classes, one per acoustic family. Together they span the axis the thesis
tests:
- **Strongly aspect-dependent:** T1 flat faces, T5 the pipe.
- **Partly aspect-dependent:** T4 the lattice, T2 lying on its side.
- **Nearly aspect-independent:** T2 upright, T3, T6, T7.

The adaptive pipeline should gain most on the first group and least on the last. That is a testable prediction of
E4.

---

## 3. The object set v2

| Role | Class (code name) | Family | Replaces (current CATALOG) | Why |
|---|---|---|---|---|
| **Validation** | `plastic_box`, fixed NAFCO instance | F1 | `plastic_box` | The only object measured in the field (beach, 2026-09-07); used by test B4 |
| **Target T1** | `plastic_box`, size distribution | F1 flat shell | `plastic_box`, `crate_plastic`, `polytank` | Crates and containers [20]; same validated shell physics as the field box |
| **Target T2** | `drum_200l` | F2 cylinder | `drum_200l`, `pail_20l`, `fire_extinguisher` | Hazard; side-scan precedent [14] |
| **Target T3** | `concrete_block` (resized) | F3 dense block | `concrete_block`, `brick`, `tent_weight` | Rubble and sinkers; the "easy" reference |
| **Target T4** | `trap_pot` (**new**) | F4 open frame | `mesh_crate`, `shopping_trolley`, `bicycle` | Derelict traps: frequent, harmful, found by side-scan at scale [11, 12] |
| **Target T5** | `pipe_steel` (from `cylinder_metal`) | F5 elongated | `cylinder_metal`, `pipe_pvc`, `pallet_wood` | Metal pieces and pipes [5]; the narrowest aspect window |
| **Target T6** | `tire_car` | F7 toroid | `tire_car`, `tire_bicycle` | The most consistently reported large item [3, 5, 17–21] |
| **Target T7** | `net_bundle` (from `net_ball`) | F8 compliant | `net_ball`, `rope_coil`, `rope` | Most frequent by count [6, 7]; derelict gear |
| **Structure S1** | `mooring_block` (**new**, session 02) | — | (terrain today) | Real blocks A1/A2; test B3 |
| **Structure S2** | `chain` | — | `chain` | Tethers of blocks and buoys |
| **Structure S3** | `mooring_pile` | — | `mooring_pile` | Pontoon and berth furniture |
| **Clutter C1** | `debris` | — | `debris`, `anchor` | Metal scrap and rubble, the "metal pieces" of [5] |
| **Clutter C2** | `small_litter` (**new**: bottles, cans, PET) | — | `bottle_glass`, `bottle_plastic`, `can` | Sub-threshold litter, as seabed texture and false-alarm source |
| *Conditional* | `panel_upright`, `corner_reflector` | — | — | Only if a beach day happens (Appendix A) |

**Legacy classes** (22), kept loadable but excluded from new worlds: `tin_18l`, `crate_plastic`, `polytank`,
`pail_20l`, `fire_extinguisher`, `brick`, `tent_weight`, `anchor`, `bicycle`, `shopping_trolley`, `mesh_crate`,
`pipe_pvc`, `cylinder_metal` (its geometry code is reused by `pipe_steel`), `pallet_wood`, `traffic_cone`,
`tire_bicycle`, `rope_coil`, `net_ball` (reused by `net_bundle`), `rope`, `bottle_glass`, `bottle_plastic`, `can`.
Old world folders reference these names, so they stay valid (NC #10). Active by their current name: `plastic_box`,
`drum_200l`, `concrete_block`, `tire_car`, `chain`, `mooring_pile`, `debris`. New names: `trap_pot`, `pipe_steel`,
`net_bundle`, `mooring_block`, `small_litter`.

**Dropped families**
- **F6, the cone.** Rare in harbours. It is not needed for the aspect axis.
- **F9, small hard objects, as targets.** They are below the IHO floor and the resolution limit; they survive as
  clutter class C2.

**The matched material pairs of version 1** (steel against plastic pail, solid against mesh crate, and so on) were
designed for a field campaign that will not happen. They are not needed for the headline. If a material contrast
is wanted later, it can be a parameter sweep of one class.

---

## 4. Class specification cards (for the code sessions)

**Conventions for every card**
- Sizes in metres; U(a, b) = uniform between a and b.
- **Burial** is the fraction of the object's height (or diameter, for lying cylinders) below the seabed.
- **Yaw** is uniform over [0, 360°) unless stated.
- **Acoustic constants** (density, sound speeds, absorption, reflection, layer transmission) come from session
  01's materials and its `parameter_registry.md`. They are not repeated here.
- **Fouling** is the ray-cast's 0–1 setting. Old litter is colonised by biota [5], so the default is
  **U(0.2, 1)**, with U(0, 0.2) for "fresh" litter [DESIGN].
- **Every instance writes ground truth:** family, class, material, state, dimensions, position, yaw, rest pose,
  burial, fouling, the azimuths of every flat-face normal and cylinder axis, and `nominal_target: true|false`.

### T1 / Validation — `plastic_box` (flat-faced plastic shell)

| Item | Specification |
|---|---|
| Real objects | Fish crates, plastic storage containers, "abandoned crates" [20]; our NAFCO 68 L box [PROJ] |
| Geometry | Open-top rectangular shell: four walls and a floor of thickness t; a rim lip of 10–20 mm; walls tapered outwards by a draft angle of 1–3° [DESIGN, an I3 input]; optional lid (P2) |
| Validation instance | 0.716 × 0.425 × 0.323, t = 2.0 mm, flooded, upright [PROJ, measured] |
| Target sizes | L ~ U(0.50, 0.75); W = L × U(0.55, 0.70); H ~ U(0.22, 0.35); t ~ U(2, 4) mm [DESIGN, spans fish crates and 40–70 L containers] |
| Material | PP shell, elastic-layer physics from session 01 (V5) |
| States | Flooded (default, 0.7); partly sediment-filled, 0–30 % of height (0.3) [DESIGN] |
| Rest poses | Upright, open side up (0.5); inverted (0.3); on a side (0.2) [DESIGN] |
| Burial | Sand U(0, 0.15); mud U(0, 0.4) [DESIGN] |
| Face normals | Four walls; also the floor when on a side or inverted |
| Expected behaviour | The sharpest aspect dependence (wall flashes), with a partly transparent shadow |

### T2 — `drum_200l` (steel cylinder)

| Item | Specification |
|---|---|
| Real objects | Oil and chemical drums; dumped barrels found by side-scan [14] |
| Geometry | Cylinder of body diameter about 0.57 m, 0.585 m over two raised rolling hoops at about one third and two thirds of the height; height 0.89 m; rolled rims (chimes) at both ends; flat ends, one optionally open or holed. **These dimensions are [UNCERTAIN]**: read off a garbled vendor table [28]; check before freezing |
| Wall | Steel 1.0–1.6 mm, "widely used" thicknesses per the foreword of JIS Z 1600:2017 [28] |
| States | **Flooded** (default) or filled with sediment or product. **Not air-filled:** 200 L of air gives about 2 kN of buoyancy against roughly 0.2 kN of steel weight, so a sealed empty drum floats [DERIVED] |
| Rest poses | Lying on its side (0.6) or upright (0.4) [DESIGN; bracket 0.3–0.9 lying] |
| Burial | Lying: sand U(0, 0.2), mud U(0, 0.5) of the diameter. Upright: sand U(0, 0.1), mud U(0, 0.3) of the height [DESIGN] |
| Axis metadata | Axis azimuth when lying; "vertical" when upright |
| Expected behaviour | Upright: nearly aspect-independent, brightened by the object–seabed corner path (session 01, V4). Lying: a broadside glint, like a short pipe |

### T3 — `concrete_block` (dense rough block)

| Item | Specification |
|---|---|
| Real objects | Rubble, abandoned mooring sinkers, construction blocks [3, 4] |
| Geometry | Rough rectangular block with chipped edges (random edge bevels of 0–30 mm) |
| Sizes | L ~ U(0.5, 1.0); W ~ U(0.4, 0.8); H ~ U(0.2, 0.6) [DESIGN: at or above the IHO floor; today's range 0.3–0.8 is shifted up] |
| Material | Concrete; roughness 2 mm, so diffuse |
| Rest poses | Largest face down (0.8); otherwise (0.2) |
| Burial | Sand U(0, 0.1); mud U(0, 0.3) [DESIGN] |
| Expected behaviour | The "if we cannot see this, the run is bad" reference: little aspect dependence, a clear shadow |

### T4 — `trap_pot` (wire-mesh trap; new class)

| Item | Specification |
|---|---|
| Real objects | Derelict crab, fish and eel traps [11, 12] |
| Geometry | Rectangular frame of 0.61 × 0.61 × 0.48 m (the 24 × 24 × 19 in Maryland-style pot [27]). Walls of hexagonal wire mesh with 1.5 in (38 mm) openings [27]. A horizontal divider makes two chambers [12]. Four entrance funnels (cones) on the lower chamber's sides. Ballast bars (rebar, about 10 mm) along the bottom edges. A zinc anode bar |
| Japanese variants | 0.6–1.0 × 0.45–0.6 × 0.25–0.45 m [UNCERTAIN; check against local gear before use] |
| Wire | Galvanised or vinyl-coated steel [12, 27]; wire diameter 1.5–2.0 mm [UNCERTAIN]. Mesh open area about 90 %, so a fill fraction of about 0.05–0.15 per panel [DERIVED from 38 mm hexagons and 2 mm wire] |
| Material | Steel wire; vinyl coating acoustically negligible at 450 kHz [UNCERTAIN; session 01 to confirm] |
| Rest poses | Upright (0.8); on a side (0.2) [DESIGN] |
| Burial | Sand U(0, 0.2); mud U(0, 0.4), with sediment inside the lower chamber [DESIGN] |
| Fouling | Default U(0.3, 1): old traps are heavily fouled [DESIGN] |
| Face normals | The four side panels |
| Expected behaviour | Thin-member glints that change with aspect; a weak, diluted shadow; complex texture. The family where a second look should help after the flat faces |
| Optional variant | A shopping-trolley lattice for city-harbour worlds, as a geometry variant of the same class |

### T5 — `pipe_steel` (elongated rigid)

| Item | Specification |
|---|---|
| Real objects | Pipe sections, scaffold tubes, steel bars, "metal pieces, wires" [5]; cables [17] |
| Geometry | Hollow cylinder, open at both ends and flooded |
| Sizes | Diameter ~ U(0.10, 0.30); length ~ U(1.0, 3.0); wall 3–8 mm [DESIGN] |
| Material | Steel |
| Rest pose | Lying only |
| Burial | Sand U(0, 0.3); mud U(0, 0.6) of the diameter [DESIGN] |
| Axis metadata | Axis azimuth |
| Expected behaviour | The narrowest specular window: bright at broadside, near-invisible a few degrees off. The cleanest test of the aspect argument |

### T6 — `tire_car` (toroid, rubber over steel)

| Item | Specification |
|---|---|
| Real objects | Car and light-truck tyres, used as fenders or dumped [17–21] |
| Construction [16] | "Two steel belts … on top of the body plies, under the tread area". Steel bead bundles at both beads. Polyester body plies. Rubber everywhere else |
| Sizes | Section width W ~ U(0.16, 0.25); outer diameter ~ U(0.55, 0.80). Worked examples [DERIVED]: outer diameter = rim + 2 × W × aspect ratio. A 165/65R14 gives 0.356 + 2 × 0.165 × 0.65 = 0.570 m; a 205/70R15 gives 0.381 + 2 × 0.205 × 0.70 = 0.668 m |
| Material | Rubber over steel belts: session 01 brackets steel-belted against pure rubber |
| States | Flooded, or partly filled with sediment |
| Rest poses | Flat (0.85); on edge or leaning (0.15) [DESIGN] |
| Burial | Sand U(0, 0.3); mud U(0, 0.6) of the section height [DESIGN] |
| Expected behaviour | Low aspect dependence (no flat face). Its strength depends on the steel belts; the July harbour tyre was barely visible [PROJ] |
| Optional variant (P2) | Tyre on a steel rim: a strong reflector inside the same outline |

### T7 — `net_bundle` (tangled compliant mass)

| Item | Specification |
|---|---|
| Real objects | Ghost nets, rope coils, mooring lines [6, 7, 13] |
| Geometry | An irregular mass: a flattened random envelope of size L ~ U(0.5, 2.0), W ~ U(0.4, 1.5), H ~ U(0.1, 0.5). Inside it, a fibre volume fraction of 0.05–0.3 [DESIGN]. Optional lead line along one edge. A rope-coil variant: a torus of rope 12–16 mm thick, 0.3–0.8 m across |
| Material | Sinking synthetic fibre (nylon, polyester) [UNCERTAIN on mix]; a lead line where present. Floating fibres (PP, PE) reach the seabed only when weighted or fouled. Acoustic parameters come from session 01, measured or bracketed |
| Rest pose | Flattened; draping over other objects and structures is P2 |
| Burial | Partial: on sand only the lead line may stay visible [13]. Sand U(0, 0.5); mud U(0, 0.7) [DESIGN] |
| Expected behaviour | Weak, diffuse, aspect-independent; the most likely to be missed and to be confused with seabed texture |

### S1–S3 — Structures (not litter; never counted as targets)

| Class | Specification |
|---|---|
| `mooring_block` | Concrete, as surveyed in the real harbour: A1 about 4 m square and 2.8 m tall, A2 about 1.6 m tall [PROJ, review §B5.5]. A chain tether to its buoy |
| `chain` | Studless steel links as discrete parts at the 450 kHz scale |
| `mooring_pile` | As today: diameter 0.3–0.6 m, protruding 1.2–3.0 m above the seabed, concrete |

### C1–C2 — Clutter (non-targets)

| Class | Specification |
|---|---|
| `debris` | Metal scrap and rubble pieces of 0.2–1.2 m, rough. Mostly steel or concrete. It is "other litter": a detection on it is reported separately, not as a false positive (§5.6) |
| `small_litter` | Bottles, cans and PET, 0.1–0.4 m (the old F9 geometries). **Recommended:** implement as a seabed layer of hard point-like scatterers rather than as individual objects, for rendering cost |

---

## 5. Harbour population model (for session 02)

### 5.1 Density of sonar-size litter (targets plus `debris`)

| Preset | Density | Anchor |
|---|---|---|
| Sparse | 2 per ha | Open basin; the Venice lagoon-wide mean is 0.075 per ha [REF 3] |
| **Nominal** | **10 per ha** | Venice urban peak, 11.6 per ha [REF 3, DERIVED from 1,161 per km²] |
| Dense | 30 per ha | Off the Thessaloniki port breakwater, about 29 per ha [REF 5, DERIVED] |

- **Share of targets** among these: 0.5 [DESIGN; bracket 0.3–0.7].
- **Size check.** Thessaloniki's detected targets are mostly 0.5–0.7 m, which matches the target sizes of §4.
- **Scale check.** An E4 world of 0.6–1 ha at the nominal density holds 6–10 objects, the order the policy
  comparison was planned around (about ten objects per run).

### 5.2 Family mix — two modes

**Realistic mode**: count weights for harbour worlds [DESIGN, informed by §2.3]:

| Target | Weight | Reason |
|---|---|---|
| T6 tyre | 0.30 | Most consistently reported |
| T4 trap | 0.15 | Fishing harbours |
| T7 net or rope bundle | 0.15 | Most frequent by count, but often under 0.5 m |
| T1 plastic box | 0.15 | Crates |
| T3 concrete block | 0.10 | Rubble and sinkers |
| T5 pipe | 0.10 | Metal pieces and pipes |
| T2 drum | 0.05 | Rare, hazardous |

No study gives the composition of sonar-size harbour litter by count. These weights are a stated assumption, swept
in E5.

**Balanced mode**: equal counts per target class. Use it for per-family results, so that each family has enough
detection opportunities.

### 5.3 Spatial pattern

- **Mechanism.** Sinking litter "mostly stays near its emission point", while storms can move it up to about
  4 km [REF 6]. Litter peaks near urban quays and harbour inlets [REF 3], slightly near a breakwater [REF 5], and
  at river-mouth drop-offs [REF 22].
- **Model** [DESIGN]: an inhomogeneous Poisson process,

  λ(x) = λ_bg + Σ_k A_k · exp(−d_k(x) / L_k)

  over the hotspot features k, with d_k the distance to the feature.
  - **Hotspot features:** quay walls and fender lines; pontoons; mooring blocks and buoys; fishing berths;
    slipways; drain and river outlets; breakwater toe.
  - **Decay length:** L_k = 15 m [bracket 5–40 m].
  - **Share within 30 m of a hotspot:** 0.7 [bracket 0.5–0.9].
- **Class affinities** [DESIGN]:

  | Class | Where it concentrates |
  |---|---|
  | Tyres | Along quay walls and fender lines (cf. tyres beside a harbour wall [17]; fender tyres [18]) |
  | Traps, nets, crates | Fishing berths and mooring areas |
  | Nets | Additionally snagged near structures |
  | Drums, blocks, pipes | Working quays |
  | `debris` | Everywhere, with extra weight near breakwaters and rip-rap |
- **Spacing.** At least 3 m between targets, so that their echoes do not merge [DESIGN]. All objects inside the
  depth domain; none on land (NC #13).

### 5.4 Burial and sediment

- **Evidence:** litter buried under sand and mud [REF 22], buried in sludge in a fishing port [REF 23], nets buried
  on sand with only the lead line visible [REF 13].
- **Model:** per-class ranges as in §4 [DESIGN]; mud gives deeper burial than sand. A burial preset scales all
  ranges: low ×0.5, nominal ×1, high ×1.5, capped at 0.9.
- **Burial above 0.7** marks the instance `effectively_buried: true`. It stays in the ground truth, but is excluded
  from the detectable-target denominator and reported separately ("missed by any survey").

### 5.5 Persistence

Seafloor litter keeps its condition for decades [REF 8], so worlds model accumulated stock: there is no ageing
process within a mission. Fouling (§4) stands for age.

### 5.6 What counts as a detection, for E4 metrics

| Detection matched to | Counted as |
|---|---|
| A T-class instance with `nominal_target: true` that is not effectively buried | True positive |
| `debris` | "Other litter": real litter, reported separately, not a false positive |
| `small_litter` or nothing | False positive |
| A structure or the seabed | False positive (structures also reported separately) |

---

## 6. Implementation instructions (code sessions)

### 6.1 Catalogue (`worldgen/objects.py` CATALOG)

1. **Deprecate, never delete.** Add `legacy: true` to the 22 legacy classes of §3.
   - Legacy classes are excluded from new-world generation, from the default composition, and from the World
     Builder's default lists.
   - Old world folders must still load and render identically. Add a smoke-test check.
2. **New classes:**
   - `trap_pot`: a compound of mesh panels, divider, funnels, ballast bars and anode;
   - `net_bundle`: from `net_ball`, plus the rope-coil variant;
   - `pipe_steel`: from `cylinder_metal`, hollow, lengths 1–3 m;
   - `small_litter`: preferably a seabed scatterer layer;
   - `mooring_block`: a structure, built by session 02.
3. **Changed classes:**
   - `plastic_box`: a size distribution, draft angle, states and poses; the NAFCO fixed instance kept as a preset
     (`variant: nafco_68l`);
   - `drum_200l`: rolling hoops, chimes, states, poses;
   - `concrete_block`: new size range;
   - `tire_car`: size from the tyre-code formula; steel belts and beads per session 01;
   - all classes: poses and burial per §4.
4. **`DEFAULT_COMPOSITION`** stays for legacy worlds. New worlds use the v2 composition: realistic or balanced mode
   (§5.2).
5. **Acoustics stay in session 01's material model.** This document only fixes geometry, states and placement.
   There is no brightness setting anywhere (NC #17).

### 6.2 World metadata (`metadata.yaml`, additive, schema v2)

Per object, the ground-truth fields of §4, plus:
- `effectively_buried`;
- the hotspot feature it was drawn from, if any;
- the composition mode.

Per world: the density preset, the target share, the composition mode, the burial preset, the hotspot parameters.

### 6.3 Campaign specification (example)

```yaml
objects:
  set: v2                       # v2 classes only; legacy excluded
  composition: realistic        # realistic | balanced
  density_per_ha: 10            # 2 | 10 | 30 presets, or a value
  target_share: 0.5
  burial: nominal               # low | nominal | high
  fouling: [0.2, 1.0]
  hotspots: {decay_m: 15, share_within_30m: 0.7}
  min_target_spacing_m: 3.0
validation_instances:
  - {class: plastic_box, variant: nafco_68l}   # beach and validation worlds only
```

### 6.4 Tests to add

- Every v2 class builds at the extremes of its size range.
- The pose and state frequencies match their specification within sampling error.
- Burial is applied per sediment class.
- Face-normal and axis metadata are correct for known yaws.
- Legacy worlds load and render bit-identically.
- For a seed, the campaign's composition and density come out as specified.

### 6.5 Where this is used

- **Session 02** implements §5–§6.
- **Session 01's atlas** should use the v2 representatives: `plastic_box` (NAFCO), `pipe_steel`, `drum_200l`
  upright and lying, `concrete_block`. Add `tire_car` and `trap_pot` once they exist.
- **Session 05** reports test results per v2 class.

---

## 7. For the thesis

### 7.1 Scope sentence

> The detection targets are man-made objects of at least 0.5 m on harbour seabeds — the feature size the IHO
> Exclusive Order requires harbour surveys to detect — drawn from the seven acoustic families that harbour surveys
> and clean-ups most consistently report: tyres, derelict traps, net and rope bundles, plastic crates, drums,
> concrete blocks and pipes.

### 7.2 Arguments it supports

- **Usefulness.** Port authorities need obstruction surveys [REF 1, 2]. Fisheries cooperatives and municipalities
  remove seabed litter and derelict gear, in Japan under the 2018 amendment of the marine debris act [REF 24–26].
- **Feasibility of the method.** Side-scan sonar already finds traps, tyres and drums operationally
  [REF 5, 11, 14, 17]. A survey from a USV with a 455 kHz side-scan sonar in a port has been demonstrated
  [REF 5].
- **Why replanning matters.** The families differ in aspect dependence (§2.5), which is exactly what the replanner
  exploits.

### 7.3 Limitations to state

1. **The family mix and densities are assumptions anchored on two sites** (Venice and Thessaloniki) and on
   qualitative clean-up reports. They are swept, not claimed.
2. **Objects are product-shaped.** Real litter is dented, fouled and partly filled with sediment. Fouling and
   burial are modelled only as parameters; acoustic changes from fouling are bracketed, not measured.
3. **Japanese harbour composition is undocumented** at sonar size; Japanese evidence is qualitative [REF 22–26].
4. **Derelict-trap dimensions follow a US standard pot** [REF 12, 27]. Japanese trap geometry is unverified.
5. **Drum dimensions are unverified** [REF 28].

---

## 8. Version 1 → version 2, in brief

- **Purpose:** a shopping list for a field campaign, replaced by an evidence-based target set for simulation.
- **Families:** F1–F9 become seven targets (F6 dropped; F9 becomes clutter).
- **Classes:** 29 classes become 12 active ones (22 legacy), plus 2 conditional ones (§3).
- **New:**
  - harbour evidence (§2);
  - the population model (§5);
  - detection accounting (§5.6);
  - implementation instructions (§6).

---

## 9. References

How each was read: **[full]** = full text extracted; **[page]** = web page or abstract record only; **[draft]** = an
official pre-publication file.

1. IHO (2024). *S-44 Standards for Hydrographic Surveys*, Edition 6.2.0, October 2024. IHO-hosted file
   https://iho.int/uploads/user/pubs/Drafts/S-44_Edition_6.2.0_Proposed.pdf [draft — check the final text before
   quoting].
2. IADC (2015). *Facts About: Underwater Surveys*. International Association of Dredging Companies.
   https://www.iadc-dredging.com/wp-content/uploads/2016/07/facts-about-underwater-surveys.pdf [full].
3. Madricardo, F., Foglini, F., Campiani, E., Grande, V., Catenacci, E., Petrizzo, A., Kruss, A., Toso, C., &
   Trincardi, F. (2019). Assessing the human footprint on the sea-floor of coastal systems: the case of the Venice
   Lagoon, Italy. *Scientific Reports* 9:6615. doi:10.1038/s41598-019-43027-7 [full].
4. Lazăr, A. V., Bugheanu, A. D., Ungureanu, G. V., & Ionescu, A. D. (2013). Side-scan sonar mapping of
   anthropogenically influenced seafloor: a case-study of Mangalia Harbor, Romania. *Geo-Eco-Marina* 19, 59–64.
   https://journal.geoecomar.ro/geo-eco-marina/article/view/04_2013 [page].
5. Papatheodorou, G., Kosmopoulou, A., Fakiris, E., Geraga, M., Dimas, X., Maurommatis, N., Christodoulou, D.,
   Kouvara, K., & Xirotagarou, P. (2021). Benthic megalitter detection using unmanned surface vehicle (USV) and
   Automatic Target Detection: a case study in the Port of Thessaloniki, Thermaikos Gulf. *CEST2021*, paper
   CEST2021_00599.
   https://cms.gnest.org/sites/default/files/Proceedings/cest2021_00599/cest2021_00599.pdf [full].
6. Schernewski, G., Escobar Sánchez, G., Wandersee, P., Lange, X., Haseler, M., & Nassour, A. (2023). Marine
   macro-litter (plastic) pollution of German and North African marina and city-port sea floors. *Applied Sciences*
   13(20), 11424. doi:10.3390/app132011424 [full].
7. Angiolillo, M., Di Lorenzo, B., Bo, M., Fortibuoni, T., Canese, S., Cau, A., Bavestrello, G., Tunesi, L., &
   Toma, M. (2026). From shallow to deep water: a large-scale assessment of seafloor marine macrolitter in the
   Italian seas by ROV-imaging. *Marine Pollution Bulletin* 230, 119809. doi:10.1016/j.marpolbul.2026.119809
   [full]. Offshore, 40–2,129 m: used for composition only.
8. Kuroda, M., Uchida, K., Tokai, T., Miyamoto, Y., Mukai, T., Imai, K., Shimizu, K., Yagi, M., Yamanaka, Y., &
   Mituhashi, T. (2020). The current state of marine debris on the seafloor in offshore area around Japan.
   *Marine Pollution Bulletin* 161, 111670. doi:10.1016/j.marpolbul.2020.111670 [full].
9. Fleet, D., Vlachogianni, T., & Hanke, G. (2021). *A Joint List of Litter Categories for Marine Macrolitter
   Monitoring*. EUR 30348 EN, JRC. doi:10.2760/127473 [page].
10. Richardson, K., Hardesty, B. D., & Wilcox, C. (2019). Estimates of fishing gear loss rates at a global scale:
    a literature review and meta-analysis. *Fish and Fisheries* 20(6), 1218–1231. doi:10.1111/faf.12407 [full].
11. Havens, K. J., Bilkovic, D. M., Stanhope, D., Angstadt, K., & Hershner, C. (2008). The effects of derelict blue
    crab traps on marine organisms in the lower York River, Virginia. *North American Journal of Fisheries
    Management* 28, 1194–1200. doi:10.1577/M07-014.1 [full].
12. VIMS Center for Coastal Resources Management. *Marine Debris Location & Removal — Fact Sheet* (undated web
    page). https://ccrm.vims.edu/marine_debris_removal/fact_sheet.html [page].
13. Natural Resources Consultants (2011). *Deepwater Sidescan Sonar and Camera Surveys for Derelict Fishing Nets
    and Rockfish Habitat*. Report to the Northwest Straits Foundation.
    https://Fisheries.noaa.gov/s3/dam-migration/deepwater_nets_surveys_dnr.pdf [full].
14. Merrifield, S. T., Celona, S., McCarthy, R. A., Pietruszka, A., Batchelor, H., Hess, R., Nager, A., Young, R.,
    Sadorf, K., Levin, L. A., Valentine, D. L., Conrad, J. E., & Terrill, E. J. (2023). Wide-area debris field and
    seabed characterization of a deep ocean dump site surveyed by autonomous underwater vehicles. *Environmental
    Science & Technology* 57(46), 18162–18171. doi:10.1021/acs.est.3c01256 [page].
15. Halsband, C., Sørensen, L., Booth, A. M., & Herzke, D. (2020). Car tire crumb rubber: does leaching produce a
    toxic chemical cocktail in coastal marine systems? *Frontiers in Environmental Science* 8.
    doi:10.3389/fenvs.2020.00125 [full].
16. Gent, A. N., & Walter, J. D. (eds.) (2006). *The Pneumatic Tire*. NHTSA, report DOT HS 810 561 (chapter 1 by
    B. E. Lindenmuth) [full, chapter 1].
17. The SHIPS Project. *1000 Tyres Project* — survey pages. https://1000tyres.org.3hconsulting.com/search.html
    [page].
18. Cyprus Mail (2022-11-01). Over 1,500 kilos of rubbish removed from Pomos harbour [page].
19. Afloat.ie (2025-11-15). Mallorca marina lifts 1.1 tonnes of rubbish from seabed [page].
20. EMSA. *Clean Harbour Cherbourg Project (France)* (2023 edition) [page].
21. L'Unione Sarda (2026-05-16). Arbatax: tires and plastic among the 600 kg of waste recovered from the port's
    seabed [page].
22. Kagawa Prefecture, Environment Management Division. *潜水士調査* (diver survey of seabed litter), year not
    stated. https://www.pref.kagawa.lg.jp/documents/10760/sensuido_1.pdf [full].
23. PADI Japan blog (2024). Shizuura fishing port underwater clean-up, 3 June 2024.
    https://blog.padi.com/jp/?p=540380 [page].
24. Okayama Prefecture Marine Litter Countermeasures Promotion Council (2026-08). *今日からできる海ごみゼロアクション*.
    https://www.pref.okayama.lg.jp/uploaded/attachment/419760.pdf [full].
25. EIC Net, environmental glossary: 海岸漂着物処理推進法 (2009; amended June 2018).
    https://eic.or.jp/ecoterm/?act=view&serial=4569 [page].
26. Ryukyu Shimpo / Kyodo (2023-08-28). WWF Japan ghost-gear survey off Nishi-Izu [page].
27. Lee Fisher Fishing. *Blue Crab Trap 24″ × 24″ × 19″H*, product page (1.5″ hex mesh, galvanised or vinyl-coated
    wire) [page].
28. Nippon Steel Drum Co. Open-head drum specification page (en-A2.pdf; table garbled) [page, UNCERTAIN]. JSA,
    *JIS Z 1600:2017 Open head steel drums*, preview (foreword: 1.0–1.6 mm plate widely used) [page].
29. Ministry of the Environment / Tokyo University of Marine Science and Technology (March 2025). FY2024 survey of
    floating and seabed litter in offshore waters, summary report. https://www.env.go.jp/content/000415172.pdf
    [full].

**Project sources:** the simulator review of 2026-11-12 (`simulator_analysis.md`); the July 2026 Shiraishi-jima
harbour recordings; the 2026-09-07 beach box; version 1 of this document (August 2026); `project_synthesis.md`.

---

## Appendix A — Conditional beach-day kit (only if a beach day happens)

Its purpose is to narrow the flash bracket (R1 of the frozen acceptance criteria) by measuring it.

| Item | Use |
|---|---|
| The NAFCO boxes we already own | Validation class |
| `panel_upright` | A flat board standing vertical (for example plywood or a steel sheet of about 0.9 × 0.6 m, braced), at a known heading. Passes every 2° within ±10° of broadside, at fixed gain and range, two passes per heading |
| `corner_reflector` | A trihedral of 0.2–0.3 m, to measure the beam pattern directly |

- Add both classes to the simulator only if the day is confirmed.
- Before the day, write an amendment to the frozen acceptance criteria defining the new test.

## Appendix B — Version 1's shopping list, condensed

Version 1 listed orderable surrogates for all nine families: the 18 L tin, PP containers solid and mesh, steel and
plastic pails, JIS concrete blocks, PVC and steel tubes, cones, used tyres, rope, bottles. It also listed matched
material pairs, rigging and ballast rules, and permissions advice for fishing harbours. The full version stays on
the owner's machine. Of that list, only the NAFCO boxes (owned) and the Appendix A kit are relevant now.
