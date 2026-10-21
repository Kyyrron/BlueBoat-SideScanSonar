# Distilled Literature — Verified Conclusions and Design Directives
## The papers we use, what they teach, and what we build

> **Superseded in part since 2026-10-20** (dated document, not rewritten): its design directives that assume a detector trained on real beach data (calibration on a "held-out beach split", the beach dataset as critical path), 30 m coverage / 15 m revisit passes, or a "mission swap" are replaced by the owner's decisions of 2026-10-20 — see the revision note of `project_synthesis.md` (detector: YOLO in BlueBoat-Perception trained on simulated datasets, calibrated on held-out simulated worlds; range 20 m per side for every condition; live path update). The literature findings themselves stand.

*Every claim below is checked against the paper's own text. **[full]** = full text read, equations
and result tables checked. **[abs]** = abstract only, and only abstract-level claims are made.
A glossary of every metric and abbreviation used here is at the end (§11); terms are also defined
at first use, so the document can be read straight through.*

---

## 1. Scope and standards — the framing changes

### IHO (2022). S-44, Standards for Hydrographic Surveys, Edition 6.1.0. [full: Chapter 1 and Chapter 3]

The International Hydrographic Organization's S-44 defines survey "orders", each specifying how
small an object the survey system must be able to detect and how much of the area must be searched.
Edition 6 introduced a new **Exclusive Order** above Special Order, and it fits this project far
better than the Special Order we have been citing.

Two terms from the standard, defined:
- **Feature detection** — the smallest object the survey system must be able to find, expressed as
  a *cubic feature*, meaning a symmetric cube with six equal square sides used as a reference shape.
- **Feature search** — the percentage of the survey area that must be systematically searched. 100%
  means the area is covered once; 200% means it is covered twice.

| Order | Feature detection | Feature search | Where it applies |
|---|---|---|---|
| Order 1a | Cubic features > 2 m down to 40 m depth; 10% of depth beyond | 100% | Coastal waters, harbours, berthing areas, fairways, channels |
| Special Order | **Cubic features > 1 m** | 100% | Areas where underkeel clearance is critical: berthing areas, harbours, critical fairways |
| **Exclusive Order** | **Cubic features > 0.5 m** | **200%** (plus 200% bathymetric coverage) | Shallow-water harbours, berthing areas and critical fairways with strict minimum underkeel clearance |

Three consequences.

1. **Our 0.5 m target floor is Exclusive Order, not Special Order.** `project_synthesis.md` §3.1 and
   the thesis plan cite Special Order (> 1 m). The correct citation for a 0.5 m detection floor in
   shallow harbour water is Exclusive Order. Correcting this strengthens the scope claim.
2. **The standard mandates our baseline.** Exclusive Order requires a 200% feature search, and §3.4
   states that a search greater than 100% "may be accomplished by adequately overlapping collection
   or by acquiring more than one independent dataset within a survey". Two-pass coverage at our
   target size and environment is the requirement, not a strawman we built to beat.
3. **The standard concedes the thesis premise.** §3.3: "no single survey system can guarantee
   detection of all features", and the specified detection sizes "are not implicit determinations of
   what constitutes a hazard to navigation" — smaller objects can still be hazards, and where the
   survey system may miss them, "consideration should be given to use an alternative survey system."

**§3.7, charted object confirmation:** to confirm or disprove a reported object, "the search radius
should be at least 3 times the estimated position uncertainty of the reported hazard." This gives a
direct rule for sizing the revisit envelope around a contact: **R ≥ 3σ**, where σ is the contact's
position uncertainty, which our belief grid already stores as `covariance_xy`.

---

## 2. Detector choice (Q1)

*Metrics used throughout this section.* **Precision** = of the objects the detector reported, the
fraction that were real. **Recall** = of the objects actually present, the fraction the detector
reported. **IoU** (Intersection over Union) = overlap between a predicted box and the true box,
divided by their combined area; a detection counts as correct only above an IoU threshold.
**mAP50** (mean Average Precision at IoU 0.5) = detection accuracy averaged over classes, counting a
box correct if it overlaps the truth by at least 50%. **mAP50:95** = the same averaged over IoU
thresholds from 0.5 to 0.95, so it also rewards precise box placement. **FPS** = frames per second,
inference speed. **GFLOPs** = billions of floating-point operations per image, a hardware-independent
measure of compute cost. **Parameters** = the model's learned weights, in millions.

### Liu, Li, Zhu, Peng, Zhai (2026). YOLO Variant Evaluation and Transfer Learning Analysis for Side-Scan Sonar Object Detection. JMSE 14(6), 550. [full]

YOLO ("You Only Look Once") is a family of single-stage object detectors; the "n" suffix denotes the
smallest, "nano" size of each version. This paper compares YOLOv8n, v10n, v11n and v13n on two
public side-scan sonar datasets: SeabedObjects-KLSG (447 images, 86.4% shipwrecks) and SCTD (Sonar
Common Target Detection, 357 images, 74.5% shipwrecks). Identical settings throughout: 640×640 input,
batch size 16, learning rate 0.01, stratified 80/20 train/test split, early stop after 100 epochs
without improvement.

- **No version dominates.** On KLSG with the SGD (stochastic gradient descent) optimiser, v10n leads
  mAP50 / mAP50:95 (0.915 / 0.697); v8n leads recall (0.885); v13n leads precision (0.941). On SCTD,
  v13n leads recall (0.886) and mAP50:95 (0.666).
- **Transfer learning is the largest lever.** Transfer learning means initialising from weights
  already trained on a large general image dataset — here COCO, a 330k-image everyday-object
  benchmark — then fine-tuning on sonar. Result: v13n mAP50:95 rises 0.634 → 0.761 on KLSG (+20%
  relative) and 0.632 → 0.722 on SCTD; v11n 0.674 → 0.731. Pretrained models reach high accuracy
  within roughly 20 epochs versus hundreds from scratch. On a third set of 304 real mine images
  (Marine Sonic dual-frequency sonar on a Gavia AUV), v13n mAP50 rises 0.742 → 0.822.
- **Speed is not our constraint.** v8n runs at 60.98 FPS on an RTX 4060 desktop card and 55.56 FPS
  on a 45-watt T1200 laptop card; v13n at 34.01 / 31.06 FPS. Our waterfall buffer needs roughly
  1–2 detections per second.
- **Their stated limits are ours.** Test sets of only 90 and 72 images; background regions are
  frequently misclassified as shipwrecks on both datasets; shadow, speckle and multipath effects
  were not investigated. Differences of one to three mAP points sit inside partitioning noise.

### Liu D., Chen H., Chen J., Ding Y., Zhu J. (2026). Performance Evaluation of YOLO Models for Target Detection from Ocean Sidescan Sonar Imagery. Frontiers in Marine Science 13, 1883695. [full]

Six models (YOLOv4, v6, v7, v9, v13n, YOLO26n) on two purpose-built datasets: **D1, noisy with
complex sea conditions and no augmentation; D2, high signal-to-noise ratio and clean images**. The
subject is generalisation, which makes it the complement to the paper above.

- **Model size correlates positively with overfitting risk.** Overfitting here means the model
  memorises the training set's particular seabed texture rather than learning target shape.
  YOLOv4 (64 million parameters) scores mAP50 0.664 on noisy D1 but 0.887 on clean D2 — a 22-point
  swing. YOLOv6 overfits the clean data and its recall collapses under noise (0.869 → 0.732).
- **Small networks generalise better because they cannot store the noise.** YOLOv13n (2.448 M
  parameters): mAP50 0.925 and mAP50:95 0.562 on noisy D1, 0.870 / 0.548 on clean D2 — the smallest
  gap in the table. YOLO26n (2.375 M parameters, 5.2 GFLOPs, 526 FPS): 0.892 / 0.550 and
  0.885 / 0.556. Their explanation is that limited capacity forces the model onto general geometric
  features rather than background texture.
- Their recommendation for large-area scanning with small vehicles is YOLOv13n; YOLO26n for
  low-compute continuous deployment.

**Together the two evaluations give one instruction:** use a nano-scale model *and* COCO-pretrained
weights. Nano for stability across sea conditions, pretraining for sample efficiency. Neither result
argues for a large backbone.

### Yang, Li, Wang, Wei, Ren, Zhang, Pei (2025). SS-YOLO: A Lightweight Deep Learning Model Focused on Side-Scan Sonar Target Detection. JMSE 13(1), 66. [full]

Built for our exact deployment case: real-time side-scan detection on an unmanned surface vessel.
Their dataset combines the public SCTD set with data they collected using a USV carrying an SS900F
side-scan sonar. Their modifications to YOLOv8n, in sequence: replacing standard convolutions with
partial and pointwise convolutions (which compute over only part of the feature map, cutting
redundant work) reduces parameters 3.15 M → 2.45 M and compute 8.9 → 7.1 GFLOPs; adding a
multi-scale fusion block recovers the lost accuracy (+1.8 mAP50, +2.5 mAP50:95). Final model:
**2.55 M parameters, 6.4 GFLOPs, mAP50 0.924, mAP50:95 0.647, precision 0.821, recall 0.857** —
4.4 and 3.0 points above stock YOLOv8n with 0.49 M fewer parameters. A candidate second iteration.

### Ma, Jin, Bian, Cui (2024). Multi-Scale Marine Object Detection in Side-Scan Sonar Images Based on BES-YOLO. Sensors 24(14), 4428. [full]

YOLOv8n plus an attention module (which lets the network weight informative regions more heavily),
a bidirectional feature-pyramid neck (which fuses information across scales in both directions) and
a shape-aware box-regression loss, with **two-dimensional discrete wavelet decomposition and
reconstruction used as preprocessing** — a multi-resolution filter that separates image detail from
noise. Result: mAP50 87.1% → 92.4%, mAP50:95 +4.4 points. Two details matter more than the headline.
Per-class results show the gain concentrated on the weakest class (69.5% → 82.6%) while strong
classes move 1–2 points — attention buys recall on the hard class, which is where our threshold
probes sit. And they **used no pretrained weights**, so against the transfer-learning result above
their gains and COCO pretraining are probably additive.

### Guo, Pleiss, Sun, Weinberger (2017). On Calibration of Modern Neural Networks. ICML. [full]

Calibration means a detector's confidence number matches its actual correctness rate — if it reports
0.8 on a hundred objects, about eighty should be right. Formally, perfect calibration is
P(Ŷ = Y | P̂ = p) = p for every p.

- **Cause of miscalibration.** Network depth, width, batch normalisation and *low* weight decay all
  worsen it. The mechanism: **NLL** (negative log likelihood, the standard training loss, which
  penalises confident wrong answers heavily) can still be reduced after the network already
  classifies the training set correctly, simply by making predictions more confident. So the model
  overfits NLL without overfitting classification error — CIFAR-100 test error falls 29% → 27%
  precisely where test NLL is rising.
- **Measurement.** Sort predictions into M equal-width confidence bins Bm. For each bin compute
  accuracy and mean confidence. Then the **ECE** (Expected Calibration Error) is the
  sample-weighted average gap:
  **ECE = Σₘ (|Bm|/n)·|acc(Bm) − conf(Bm)|**, and the **MCE** (Maximum Calibration Error) is the
  worst single bin, maxₘ|acc(Bm) − conf(Bm)|. A **reliability diagram** plots accuracy against
  confidence and should follow the diagonal. They use M = 15 bins.
- **Fix: temperature scaling.** One scalar T > 0 divides the logits (the network's raw pre-softmax
  scores) before the softmax: **q̂ᵢ = maxₖ σ(zᵢ/T)ₖ**. T is fitted by minimising NLL on a held-out
  validation set with the network weights frozen. Because dividing by a constant does not change
  which class scores highest, **accuracy is exactly unchanged**.
- **Evidence.** ECE before → after: CIFAR-100 ResNet-110 16.53% → 1.26%; ResNet-110 with stochastic
  depth 12.67% → 0.96%; Birds ResNet-50 9.19% → 1.85%; ImageNet ResNet-152 5.48% → 1.86%. It beats
  histogram binning, isotonic regression, Bayesian binning, and the strictly more general vector and
  matrix scaling. Matrix scaling collapses when there are many classes (25.49% ECE on CIFAR-100)
  because its parameter count grows with the square of the class count. Binning methods *change
  class predictions* and cost accuracy; temperature scaling cannot.
- **Cost.** A one-dimensional convex optimisation, about ten iterations, a fraction of a second.

### What we do

1. **Baseline = a nano-scale YOLO (v8n or v11n), COCO-pretrained, SGD, stratified split**, selected
   by **recall** — the belief grid absorbs false positives through negative evidence but cannot
   recover a target the detector never reported.
2. **Reproduce the JMSE protocol**: stratified split, identical hyperparameters across candidates,
   report mAP50 / mAP50:95 / recall, and state that differences below partition noise are not
   decisions.
3. **Build our own noisy/clean split** — beach data under good and poor conditions (sea state,
   turbidity, tide-driven altitude change). The Frontiers result says the accuracy *gap between
   conditions*, not the mean, predicts field behaviour.
4. **Calibrate before the grid**: fit T by NLL on a held-out beach split; report a reliability
   diagram and ECE at 15 bins, before and after. Avoid binning calibrators.
5. **Second iteration if needed**: attention plus multi-scale fusion on the nano backbone, keeping
   the pretrained initialisation that SS-YOLO and BES-YOLO under-use.

---

## 3. Building the probability map (Q2)

### Bourgault, Furukawa, Durrant-Whyte (2006). Optimal Search for a Lost Target in a Bayesian World. FSR, STAR vol. 24, 209–222. [full]

The complete recursive-Bayesian search formulation. "Recursive Bayesian" means the probability map
is updated observation by observation, each update using the previous map as its prior.

- **Filter.** Prediction by the Chapman–Kolmogorov equation (the target's probability distribution is
  convolved forward through a motion model, computed on a grid using the fast Fourier transform),
  then update by Bayes' rule, p(xₖ|z₁:ₖ) = K·p(xₖ|z₁:ₖ₋₁)·p(zₖ|xₖ), applied cell by cell. For a
  static seabed the prediction step is the identity, so our grid keeps only the update.
- **The miss update.** With detection likelihood p(Dₖ|xₖ), the probability of *not* detecting a
  target that is present is the complement **p(D̄ₖ|xₖ) = 1 − p(Dₖ|xₖ)** (their Eq. 4). Multiplying
  the map by this complement and renormalising *is* the correct update after an unsuccessful look:
  probability is carved out of the searched region, not zeroed.
- **Accumulation over looks.** qₖ = ∫p(D̄ₖ|xₖ)p(xₖ|z₁:ₖ₋₁)dxₖ is the probability of missing on look
  k; **Qₖ = ∏ᵢ qᵢ** is the probability of having missed on every look so far; **Pₖ = 1 − Qₖ** is the
  cumulative probability the target has been detected by step k. The probability of detecting for
  the *first* time on step k is **pₖ = Qₖ₋₁(1 − qₖ)**, and the mean time to detection is
  MTTD = Σ k·pₖ. Two candidate mission objectives follow: maximise Pₖ within a fixed time, or
  minimise MTTD.
- **Greedy planning is one-step lookahead, and it is not enough.** With a one-step horizon both
  objectives reduce to maximising pₖ. Greedy is cheap and produces sensible paths, but it spirals
  outward and misses payoff beyond sensor range. Static target: greedy reaches cumulative detection
  probability 0.59 after 120 s, versus **0.77 (+29%)** for a twelve-parameter piecewise-constant
  lookahead. Drifting target: 0.71 versus **0.87 (+22%)** for a 30 s lookahead replanned every 10 s,
  at roughly 25× the computation.
- **The scattering effect.** Flying straight over a probability peak spreads the probability mass and
  *raises* the distribution's entropy, devaluing every later look. The optimal path instead circles
  the peak without crossing it, compressing the mass and delaying reward. So a revisit leg driven
  straight through a contact is not automatically the best leg.
- **Caveats.** Their sensor has perfect discrimination — it can miss but never false-alarm — and they
  state that computing Pₖ accurately would require an observation model built from extensive in-situ
  experiments, so a theoretical model is adequate for planning and for comparing strategies but not
  for absolute claims. Both apply to our fitted detection model.

### Paull, Saeedi, Seto, Li (2013). Sensor-Driven Online Coverage Planning for AUVs. IEEE/ASME Trans. Mechatronics 18(6), 1827–1838. [full]

- Each cell holds a confidence c = P(a target would be detected if present), read from a
  lateral-range curve (detection probability as a function of across-track distance). Cell entropy —
  a measure of uncertainty, maximal at c = 0.5 and zero at certainty — is
  **H = −c log c − (1−c) log(1−c)**, which → 0 as c → 1. Maximising confidence therefore minimises
  map entropy, so the coverage objective *is* an entropy objective.
- With target density estimated as p̃ ≈ N/A (number of targets over area), the probability that a
  reported detection is real is **P(M = 1 | m = 1) = c·p̃ / (2c·p̃ − c − p̃ + 1)** (their Eq. 9) — a
  consistency check on what our grid's p_target should imply.
- **Aspect fusion (Eqs. 22–24).** For two looks at the same cell with confidences c¹ ≥ c² and track
  intersection angle α between 0 and 90°: parallel tracks (α = 0) are treated as dependent, so
  c_total = max(c¹, c²) — the second look adds nothing; orthogonal tracks (α = 90°) as independent,
  so c_total = 1 − (1−c¹)(1−c²); and in between, linear interpolation
  **c_total = (2α/π)·c²·(1−c¹) + c¹**. This is an assumed model, justified by citing Fawcett et al.
  2010.
- **Coverage results**, 36 Monte-Carlo runs per condition. Path length needed to reach coverage
  confidence 0.90 / 0.95 / 0.98: lawnmower 1275 / 1545 / 2355 m; information gain alone
  1488 / 2429 / 3307 m — **worse than the lawnmower, with much larger variance**; information gain
  plus a global completion term 1088 / 1458 / 1761 m. In-water trials on an IVER2 vehicle stopped
  when confidence reached 95%.

### Wiig, Krogstad, Midtgaard (2012). Autonomous Identification Planning for Mine Countermeasures. FFI (Norwegian Defence Research Establishment). [full]

The fielded answer to data association — turning many detections into one contact. **Their SITAR
system applies multiple detection filters over the sonar data; each contact receives a confidence
value, and multi-filter contacts corresponding to the same seafloor object are fused using
Dempster–Shafer theory of evidence** (a generalisation of Bayesian fusion that can represent
"unknown" explicitly, so conflicting detectors need not be forced to a single probability). Contacts
above a low fused threshold pass to a classifier that matches templates indexed by target type,
orientation, sonar range and altitude. They report high detection probability at a moderate
false-alarm rate. The detector runs after each survey line and again over the full dataset at survey
end, because the full-set pass performs better.

### What we build

1. **Grid update per insonification of cell i.** No detection → pᵢ⁺ = pᵢ(1−PDᵢ) / (pᵢ(1−PDᵢ) + 1 − pᵢ),
   where PD is our fitted P(detect | range, aspect, class, seabed). Detection with calibrated
   confidence → Bayes with the detector's likelihood ratio; Paull's Eq. 9 is the consistency check.
   Increment `n_observations`; record the heading sector in `aspect_coverage`.
2. **Maintain Qᵢ = ∏ⱼ(1 − PDᵢⱼ) as an explicit channel** — Bourgault's Qₖ localised to a cell. It is
   monotone, and 1 − Q is the coverage statistic the replanner thresholds. Mission-level 1 − Q̄ is
   the reportable coverage figure, and maps directly onto S-44's feature-search percentage.
3. **Adopt Paull's angle-interpolated fusion as the placeholder aspect model**, to be replaced by the
   E3-measured response. This gives a working system before the beach data and a clean before/after
   ablation afterwards.
4. **Data association by Dempster–Shafer fusion of same-object contacts, following SITAR** — fuse
   multi-detection evidence per object, threshold low, classify second, rather than gating on raw
   detector output.
5. **Do not run the replanner greedy.** Bourgault's +29% / +22% margins and Paull's information-gain
   row are two independent demonstrations that one-step-lookahead information maximisation
   underperforms.
6. **Watch the scattering effect** — judge leg geometry by expected posterior sharpening, not by
   proximity. **Size the revisit envelope from S-44 §3.7: R ≥ 3× the contact's position
   uncertainty.**
7. **Keep detection-probability estimates conservative** and report the headline result's sensitivity
   to getting them wrong.

---
## 4. Coverage pattern for a given area (Q3)

A **boustrophedon** or **lawnmower** path is a set of parallel straight lines with turns at the ends
— the standard survey pattern. The **swath** is the strip of seabed a side-scan sonar images on each
pass; **nadir** is the blind strip directly under the sonar where the grazing angle is too steep to
image usefully.

### IHO S-44 6.1.0 §3.4 and NOAA descriptive-report practice (H11640, H12509, H12392, H12559, H13502). [full / primary documents]

S-44 requires a 200% feature search at Exclusive Order and permits it either by overlapping
collection or by acquiring more than one independent dataset. NOAA object-detection surveys
implement exactly that as "200% side scan sonar": two independent 100% mosaics, reviewed separately,
with concurrent multibeam bathymetry. NOAA's second pass is typically offset or parallel; our
orthogonal second pass is the stronger variant, because it adds aspect diversity as well as
redundancy. State this when defending the baseline.

### Yordanova & Gips (2020). Coverage Path Planning with Track Spacing Adaptation for Autonomous Underwater Vehicles. IEEE Robotics and Automation Letters. [full]

- The side-looking swath is an annulus between minimum and maximum usable range. Covering the nadir
  gap using **paired tracks** — where each line's blind strip is imaged by its neighbour — requires
  **r_max ≥ 3·r_min** (their Eq. 1). Check this against Omniscan geometry at our 15 m and 30 m
  settings; if it fails, the nadir strip must either be declared uncovered or be covered by the
  orthogonal pass.
- Data quality varies with range: their measured detection probability peaks mid-range and degrades
  at both ends. Their planner picks the smallest admissible virtual range that still achieves the
  minimum track count, which spreads the extra overlap uniformly onto the weak tail of the swath
  rather than dumping it all on the final leg.
- Multi-look coverage accumulates multiplicatively as **residual risk RR = ∏ᵢ(1 − Pdᵢ)** per grid
  point (their Eq. 2) — the same quantity as Bourgault's Q, computed as a map.
- At sea: recovering from an overestimated range cut missed coverage from 4.4% to 0.18% at the cost
  of one extra track; with a correct range estimate, adaptation lowered residual risk by 4.2% for
  the worst ~30% of the data without changing the track count. They are explicit that the overall
  mean did not improve — the gain is confined to the worst data.

### Wiig, Krogstad, Midtgaard (2012). [full]

Their sea-trial survey was **two lawnmower patterns at an angle to each other, 75 m line spacing**,
planned to cover the deployed targets plus surroundings and to avoid terrain unsafe for the
low-altitude inspection phase. Two-pass-at-an-angle is fielded mine-countermeasures practice, not
only a hydrographic convention. They also name the recurring operational problem: minimum and
maximum sonar range vary with sea state, seabed type, bathymetry, depth and altitude; operators use
heuristics; and range-estimation errors produce either coverage holes or wasted time.

### Cocchi, Muccini, Locritani, Spinelli, Cocco (2024). CORAL — Catamaran for Underwater Exploration. Sensors 24(14), 4544. [full]

The closest published operating envelope to ours, and the foil for our positioning.

- **Platform.** Compact electric catamaran, cruise about 3 knots (maximum 5), 8 hours endurance at
  3 knots; a **452 kHz chirp side-scan sonar mounted 20–40 cm below the sea surface**; inertial
  navigation aided by GPS. Chirp means the transmitted pulse sweeps in frequency, which raises the
  signal-to-noise ratio and hence resolution.
- **Survey settings.** Pozzuoli harbour: water depth 4 m in the central canal to 10–12 m at the
  entrance, and the **swath was changed from 45 m to 25 m** moving from the outer to the inner port.
  Riomaggiore: depths 6–13 m, **fixed 25 m lateral swath**, and areas shallower than 1.5 m not
  surveyed for safety. Mosaics produced at 10 cm and 15 cm per pixel.
- **Detection performance.** The mosaic resolved aligned cubic concrete mooring blocks of
  approximately 1 m per side joined by a mooring chain; the authors state the resolution "allows us
  to easily detect objects with sub-metric dimensions".
- **Autonomy, in their own words.** The harbour survey ran in **assisted mode** — the system holds a
  fixed heading until the operator issues a new directional command — with an operator adjusting
  swath distance and gain in real time during acquisition. No detection loop, no replanning, no
  baseline comparison.

Three uses. It sanity-checks our reserved settings: a 452 kHz surface-mounted sonar at 25–45 m swath
in 4–13 m of water resolves roughly 1 m objects, consistent with our 30 m coverage and 15 m revisit
choices. It confirms the platform-and-regime precedent. And the assisted-mode detail makes the
positioning argument concrete — the closest comparable system keeps a human in the loop on both
heading and sonar gain.

### What we do

1. **Initial pass: boustrophedon at 30 m per side**, line spacing set from the *measured* usable
   swath, with overlap placed on the weak end of the fitted detection-probability curve. Verify
   r_max ≥ 3·r_min; if it fails, declare the nadir strip or cover it with the orthogonal pass.
2. **Baseline for the policy comparison: boustrophedon plus orthogonal boustrophedon**, spacing
   tuned for the target coverage confidence rather than a default. Defend it with S-44 Exclusive
   Order's 200% requirement, NOAA practice, and Wiig's angled double lawnmower.
3. **Revisit legs: straight passes with lead-in and lead-out at fixed length, radius R ≥ 3σ.** The
   replanner chooses which contact and which heading, never a curved path through the contact.
4. **Log the detection-probability-versus-range curve per session**, and expect usable range to drift
   with conditions.

---

## 5. The replanning pipeline (Q4)

### Sethuraman, Baldoni, Skinner, McMahon (2024). Learning Which Side to Scan. ICRA. [full]

- **Framing.** Survey-and-Reacquisition means a 100%-coverage lawnmower to find contacts, then
  per-contact reacquisition from K = 6 discrete headings at fixed pass length 75 m and radius 12 m,
  flown at lower altitude. Adaptive Survey-and-Reacquisition interleaves the two and chooses which
  headings to fly. They state that exhaustive reacquisition **can exceed 30 minutes per object** —
  the source for our motivating figure.
- **Machinery.** Each contact gets an angular view-graph: nodes are convolutional-network embeddings
  of the acquired views, edges weighted by the angular offset between them. A graph neural network
  classifies from the graph, and a deep Q-network — a reinforcement-learning agent that estimates
  the long-run value of each action — selects the next heading or the STOP action. Reward: +10 for a
  correct classification, −10 for incorrect, −1 for each view acquired after the first correct one.
- **Results** (simulation, 1.2 × 1.2 km, 16 targets, 3 random seeds × 100 surveys): single-pass
  lawnmower 0.628 accuracy in 3.87 hours; exhaustive six-view reacquisition 0.919 in 7.38 hours;
  their method 0.952 in 4.86 hours using 1.18 views per target on average.
- **The key ablation:** taking the *same number* of views but choosing them at random drops accuracy
  0.952 → 0.92, and to 0.85 without the angular graph. Which aspect you take matters, not only how
  many.
- **Stated limits.** Simulation only; future work is sim-to-real transfer, clutter, multipath, and
  variable pass length and radius.

### Wiig, Krogstad, Midtgaard (2012). Autonomous Identification Planning for Mine Countermeasures. FFI. [full]

The fielded detect-then-revisit loop.

- **Concept.** Detect, classify and identify mine-like objects within a single dive: side-scan
  survey, automatic target recognition run in-mission after each line, then on survey completion the
  autonomy layer fuses the targets and automatically plans an identification mission. Platform:
  HUGIN 1000 V0 autonomous underwater vehicle with an Edgetech MPX-4300 side-scan sonar (190 m swath
  at 4 knots, 4–8 cm range resolution, 35–60 cm along-track resolution) and an optical camera.
- **Architecture.** A hierarchical autonomy layer: a mission module generating tasks above a
  reactive layer of parallel behaviours. A lawnmower survey is defined as a *task*, which is what
  tells the detector where the survey begins and ends. Survey completion is either marked in the
  plan or decided by the autonomy layer, which allows both immediate interruption to inspect an
  object and full-survey-first operation.
- **Contact filtering.** The planner ignores targets classified as clutter, targets with
  classification confidence below **20%**, and targets outside the area of interest.
- **Revisit planning.** Formulated as a travelling salesman problem — find the shortest route
  visiting every target — solved with a genetic algorithm (a population of candidate routes improved
  by selection, crossover and mutation). Route cost includes distance **plus penalties for sharp
  turns below 90° and rewards for targets visited along a straight line**. Each target carries an
  optional lead-in point, computed 100 m along the line joining consecutive targets, and the
  encoding carries both the visit order and a per-target lead-in on/off bit.
- **Sea trial (Horten, June 2012).** Six exercise mines among other mine-like objects; two angled
  lawnmowers at 75 m spacing; inspection flown at 4–6 m altitude. Every filtered target was covered
  and all were identified as either practice mines or clutter. **Only four of the six exercise mines
  were detected by the automatic target recognition, attributed to low sonar resolution.**
- **Where our contribution sits.** Their revisits go to *all* filtered contacts using a *second
  sensor modality*; heading is not a decision variable, only visit order and lead-in; there is no
  per-cell belief map and no comparison against a fixed-pattern baseline.

### Myers & Williams (2012). Adaptive Multiview Target Classification in Synthetic Aperture Sonar Images Using a POMDP. IEEE J. Oceanic Engineering 37(1), 45–55. [full]

A **POMDP** (Partially Observable Markov Decision Process) is a decision framework for an agent that
cannot see its true state directly and must act on a probability distribution over states, called
the belief.

- **Formulation.** States are object–aspect pairs, |S| = |Γ|×|Θ| + 1 including an absorbing
  end-state, with |Γ| = 4 object types (cylinder, truncated cone, wedge, irregular non-target) and
  |Θ| = 8 aspect sectors of 45° each. Actions: 7 movements to another aspect, plus 4 declarations of
  class. Belief updated by Bayes, policy from the Bellman equation, solved by focused real-time
  dynamic programming with discount factor 0.75.
- **Observation model without training data.** Templates are ray-traced per target type, aspect,
  range and altitude, using Lambert's law for echo amplitude and explicit shadow prediction. The
  observation is the index of the template with maximum similarity, provided it exceeds a threshold;
  otherwise "no peak". Similarity scores are modelled with the **Gumbel distribution** — the
  distribution of the maximum of many samples, appropriate because the template matcher returns a
  peak of cross-correlations — with shape parameter 0.12. The non-target class is handled by a
  logistic function on the threshold rather than an explicit clutter model.
- **Reward.** +1 correct, −1 incorrect, **0 for an additional view** — deliberate, because the paper
  evaluates classification accuracy and does not price acquisition. That gap is what Sethuraman's
  −1-per-view and our budget rule fill.
- **Results on real synthetic-aperture-sonar data** (MUSCLE vehicle, 300 kHz, about 1.5 × 2.5 cm
  resolution, 10 objects with 17–25 views each, bootstrap samples of 200): peak accuracy **0.995**,
  versus **0.845 for a single aspect** and **0.905 for two perpendicular views**. Views required:
  1.849 for the cylinder, 2.567 cone, 2.604 wedge, 3.25 non-target. Non-target accuracy specifically:
  0.31 single view, 0.66 two views, **0.88 with the adaptive policy**.
- **The aspect logic, concretely.** After observing a cone at 45°, all movement actions are nearly
  equal in value with "move +90°" marginally ahead — not because the cone has a preferred aspect (it
  is rotationally symmetric) but because that aspect best discriminates it *against* the
  non-symmetric cylinder. After observing a cylinder at 135°, the best action is "move +135°",
  yielding the broadside view where the cylinder presents its largest signature. Aspect selection is
  **discrimination geometry**, not maximum echo strength.
- **Path geometry.** Range to target fixed at 90 m, Dubins turns (shortest curves respecting a
  minimum turning radius) at 10 m radius, lead-in 100 m and lead-out 20 m.
- **Two caveats they raise.** The Markov property means the vehicle does not track which aspects it
  already holds, so the same aspect can be requested twice; and the belief update assumes
  independent looks, while two looks from the same aspect in imaging sonar are "nearly completely
  dependent". **Our `aspect_coverage` bitmap is precisely the state variable that removes this
  failure mode.**

### Hollinger & Sukhatme (2014). Sampling-Based Robotic Information Gathering Algorithms. IJRR 33(9), 1271–1287. [full]

The formal frame for the budget rule.

- **Problem.** Maximise an information objective subject to a cost budget. Cost is assumed strictly
  positive, monotonically increasing and additive — c(Pa) < c(Pa + Pb) and c(Pab) = c(Pa) + c(Pb) —
  which covers distance, energy and time and guarantees that all budget-satisfying paths are finite.
- **Objective classes.** *Modular*: I(Pab) = I(Pa) + I(Pb), information simply adds. *Time-varying
  modular*: the same but the value depends on when a segment is executed. **Submodular**:
  I(Pab) + I(Pa∩b) ≤ I(Pa) + I(Pb) — diminishing returns, meaning future information depends on the
  path already taken. Our belief grid is submodular by construction, because a revisited cell yields
  less than a fresh one.
- **Hardness and guarantee.** Finding the optimum is NP-hard or worse for nearly all interesting
  objectives, and the space of paths grows with the budget. Their graph variant is asymptotically
  optimal for all three objective classes **provided a conservative pruning strategy is used that
  never discards a node which could still lead to the most informative plan.** The practical warning:
  any heuristic that drops candidate revisits early forfeits the guarantee.

### Qiao et al. (2026). AUVs for Seabed Surveying: A Comprehensive Review of Side-Scan Sonar-Based Target Detection. JMSE 14(2), 145. [full: §4.3 and §5]

Their own future-work item states our premise: *"Traditional seabed target detection involves three
distinct tasks: preliminary survey, detailed survey, and verification. However, due to underwater
positioning inaccuracies, completing these three tasks through separate dive missions for a specific
seabed target is highly inefficient, particularly for small seabed objects. Thus, integrating
preliminary, detailed, and verification surveys into a single dive using automated target detection
algorithms represents a significant future direction."* Cite this as the field-level statement of the
gap. Their §4.3.2 confirms the multi-view planning lineage — Sethuraman's angular view-graph, Lu's
joint POMDP-and-travelling-salesman formulation with confidence-driven adaptive observation, Shin's
generalised travelling-salesman formulation — and characterises the family as compensating for "the
limitations of the traditional lawn mowing path".

### Gap table

| Capability | Status in verified literature |
|---|---|
| Detect → revisit loop, in water | Exists on AUVs: full survey, in-mission detection, route-planned revisit of *all* filtered contacts for *optical* identification (Wiig) |
| Aspect-selective next-view for sonar | Recorded data and simulation only (Myers & Williams; Sethuraman, simulation-only by their own statement) |
| Coverage adaptation from sonar performance, in water | Exists (Paull; Yordanova) — driven by data quality, not by detections |
| Per-cell belief map with an aspect-coverage channel as planner input | Not found. Paull fuses aspect into a scalar; Sethuraman's graph is per contact; Myers & Williams explicitly lack aspect memory and flag it as a weakness |
| Aspect rule fitted from a measured aspect response | Not found. Paull assumes a linear-in-angle model; Myers & Williams use ray-traced templates; Sethuraman learns one inside a simulator |
| Closed-loop policy evaluation against a tuned two-pass baseline | Not found. Sethuraman compares against single-pass lawnmower and other adaptive planners, in simulation |
| Single-mission integration of survey, detailed survey and verification | Named as an open direction by the field's own 2026 review (Qiao §5) |
| Surface-vehicle, shadow-starved regime characterisation | Not found. CORAL is platform-only and operator-assisted, with no autonomy loop |

### What we build

1. **Utility over candidate actions** {continue coverage, revisit contact k from heading θ} =
   w₁·(expected confidence gain from the fitted aspect model) + w₂·(coverage-deficit reduction)
   − w₃·(transit plus leg time), evaluated on the belief grid only. Submodular by construction, so
   Hollinger's framing applies — and pruning must stay conservative if we invoke the guarantee.
2. **Revisit action = a straight leg at fixed length and radius R ≥ 3σ past the contact at heading
   θ, with lead-in and lead-out.** Decide only which contact and which heading. Three independent
   verified precedents build lead-in and lead-out into the leg; Wiig additionally penalises turns
   below 90°.
3. **Filter candidates before planning** (Wiig): drop clutter-classified contacts, contacts below a
   confidence floor, and contacts outside the area of interest.
4. **Order accepted revisits as a turn-penalised travelling salesman problem.** Wiig's genetic
   algorithm with a per-target lead-in bit is directly reusable; our addition is that heading is also
   a decision variable, making it a *generalised* travelling salesman problem over (contact, heading)
   pairs — the same structure Shin used, per Qiao §4.3.2.
5. **Reproduce Sethuraman's evaluation shape** for the policy comparison: randomised scenes, about
   100 surveys per condition per seed, metrics {recall, total time, views per target, coverage rate}
   — plus the two-pass baseline no prior work ran.
6. **Reproduce their key ablation**: informed heading versus random heading at matched view count.
   If it is flat in real water, the aspect claim fails honestly. Schedule it early.
7. **Aspect selection maximises expected confidence gain, not expected echo strength.**

---
## 6. Stopping the recursive survey (Q5)

### Jadidi, Valls Miro, Dissanayake (2017). Sampling-Based Incremental Information Gathering. [full, arXiv preprint dated 26 September 2017]

Two portable stopping constructs.

- **Planner convergence — Relative Information Contribution.** For each node added to the planner's
  search tree, RIC = I_new / I_near − 1, penalised by the sampling effort spent:
  **I_RIC = RIC / n_samples**. Planning stops when a moving average of I_RIC falls below a threshold
  δ. The quantity is dimensionless and independent of the absolute scale of the information measure,
  and δ behaves as an information-theoretic planning horizon — as δ → 0 the horizon grows without
  bound. Portable directly as our **per-contact resolution and abandonment test**.
- **Mission termination — saturation entropy.** Using the fact that the joint entropy of a map is
  bounded by the sum of its cell entropies, the average map entropy is bounded by H(p_sat), so the
  mission can terminate when **(1/n) Σᵢ H(mᵢ) ≤ H(p_sat)** — computable from marginal cell entropies
  alone, with no joint covariance needed. Their experiments show this ends missions earlier than
  exhausting the frontier, with comparable final maps.
- Their motivating observation: human operators stop once the map looks certain, while
  frontier-driven autonomy keeps grinding.

### Paull, Saeedi, Seto, Li (2013). [full]

In-water IVER2 runs were terminated when the coverage-confidence map reached 95%. Threshold-on-belief
stopping for side-scan coverage is therefore published, sea-tested practice; our additions are the
per-contact and budget layers above it.

### Sethuraman, Baldoni, Skinner, McMahon (2024). [full]

Per-contact stopping as an explicit STOP action, priced by the −1-per-view penalty applied after the
first correct classification: 1.18 views per target versus 6 for exhaustive coverage, at equal or
better accuracy. We take the form — stopping is an action priced against marginal gain — and
implement it with the fitted model rather than a learned value function.

### Myers & Williams (2012). [full]

The contrasting design: **zero** reward for an extra view, so stopping is driven purely by the value
of declaring, and the policy still converges to under three looks on average because additional
views stop changing the belief. Two lessons. A per-look cost is not strictly necessary for
termination if the observation model saturates. And their per-class view counts (1.849 for the
cylinder versus 3.25 for the non-target) show the stopping point is **class-dependent** — a single
global "N aspects then stop" rule is the wrong shape.

### The three rules, grounded

| Rule | Adopted mechanism | Source |
|---|---|---|
| Resolution — when is a contact done | Target probability above a high threshold, **or** cost-penalised relative confidence gain of the last look below δ | Jadidi (Relative Information Contribution); Paull (threshold practice) |
| Budget — how much time may go to revisits | Revisit time ≤ a fraction of mission time; each leg priced as expected gain divided by leg cost, under a submodular objective with conservative pruning | Hollinger & Sukhatme; Sethuraman's per-view penalty |
| Abandonment — when to give up | A maximum number of looks without the relative gain exceeding δ, then drop the contact | Jadidi |
| Mission stop | Mean cell entropy, or mean residual risk, below a saturation level, plus a hard time budget | Jadidi (saturation entropy); Paull (95% practice) |

Thresholds were tuned empirically in every source paper, so ours must be set from simulation sweeps —
how much gain does a genuinely informative second look give under our fitted model? — and reported
with a sensitivity check. The resolution rule must be allowed to be class-dependent.

---

## 7. The aspect mechanism (the keystone experiment)

### Fawcett, Myers, Hopkin, Crawford, Couillard, Zerr (2010). Multiaspect Classification of Sidescan Sonar Images: Four Different Approaches to Fusing Single-Aspect Information. IEEE J. Oceanic Engineering 35(4), 863–876. [full]

- **Setup.** Klein 5500 side-scan sonar on the DORADO semi-submersible vehicle, CITADEL trial near
  La Spezia, October 2005; four classes — rock, manta (a truncated-cone-like shape), rockan (a
  smaller wedge shape) and cylinder. Images were acquired in "daisy wheel" patterns centred on each
  target, giving multiaspect looks at **30° increments**; image chips came from detections in the
  20–45 m across-track interval at 10 cm pixel spacing in both directions. Classifier: kernel ridge
  regression on **21 features** — 10 from the shadow region (shadow-profile statistics, fitted-ellipse
  parameters, object height estimated from shadow length, convexity, and lacunarity, which is the
  variance of pixel amplitudes divided by their mean squared), 6 from the highlight region, 5
  combining both. All results averaged over 600 random train/test partitions, with 5th and 95th
  percentiles reported.
- **Four fusion methods.** The Combined-Feature method concatenates the two views' feature vectors
  and retrains with a symmetrised two-look kernel. The three Dempster–Shafer variants instead fuse
  the two single-look classifier *outputs*, differing only in how classifier scores become evidence
  masses: **DSE** derives them from empirical histograms, well fitted by the sigmoid
  **F(α) = 0.5·(tanh((α + 0.25)/0.4) + 1)**; **DSC** derives them from a single-aspect confusion
  matrix; **DSNE** assigns them non-empirically from the sorted, clipped, normalised classifier
  outputs, requiring no prior knowledge of classifier performance.
- **The second look pays.** Site A, single aspect → DSE: rock 0.77 → 0.89, manta 0.89 → 0.97, rockan
  0.92 → 0.98, cylinder 0.89 → 0.97. Combined sites, single → DSE: 0.67 → 0.78, 0.79 → 0.90,
  0.93 → 0.98, 0.86 → 0.96. Combined-Feature, DSE and DSNE perform essentially identically; DSC is
  worse.
- **The failure case matters more.** Training on site A and testing on site B, the site-B rock is
  classified correctly only 0.28 of the time from a single aspect and is mostly called a manta — and
  **a second look does not fix it**: 0.29, 0.28 and 0.24 for the three methods. Their explanation:
  "we are fusing two poor single-aspect results", and the site-A training set is not general enough
  to classify the site-B rock. Multi-aspect fusion multiplies the quality of the single-look
  classifier; it cannot manufacture it.
- **What this paper does not measure.** The combined-feature vectors "do not correspond to any fixed
  change in object aspect but rather contain a mixture of different angles", so the reported
  performances are **an average over aspect increments**. There is no measurement of how the gain
  varies with the angular separation between the two looks. **The dependence of detectability on the
  change in heading — what our keystone experiment measures, and what Paull's angle model assumes —
  is not established here.**
- **Method note.** Dempster–Shafer fusion needs no classifier retraining and extends trivially from
  two looks to N; DSNE additionally needs no prior knowledge of single-aspect performance. Given our
  small dataset, DSNE is the sensible starting fusion rule.

### Sethuraman, Baldoni, Skinner, McMahon (2024). [full]

Side-scan backscatter is approximately Lambertian — brightness depends on the angle between the
surface and the sonar — so return strength depends on object geometry and viewing angle, and sound
can scatter entirely away from the receiver. Slant-range binning additionally creates elevation
ambiguity. Their informed-versus-random ablation at matched view count (0.952 versus 0.92) is the
cleanest evidence that aspect *choice* carries information beyond aspect *count*.

### Myers & Williams (2012). [full]

Real-data evidence that adaptively chosen aspects beat predetermined ones (0.995 versus 0.905 for
two perpendicular views), and the demonstration that the informative aspect is the discriminating
one rather than the brightest.

### What the keystone experiment must do

1. **The design stands** — 4–5 objects, 8–12 systematic headings at fixed ground range, repeated —
   and Fawcett's daisy wheel at 30° increments is the direct precedent for the acquisition pattern.
2. **Its contribution is sharper than assumed.** Fawcett establishes that a second look helps but
   explicitly averages over aspect increments; Myers & Williams and Paull both *assume* a
   relationship between angular separation and information. Measuring detectability as a function of
   heading change, in real shallow water, fills a gap that three verified papers leave open.
3. **Analyse against Paull's angle model.** Does measured look-to-look redundancy decay with angular
   separation, and over what angular width? The fitted curve then replaces both the linear-in-angle
   fusion in the grid and the heuristic in the aspect-selection rule.
4. **Carry Fawcett's warning into the detector plan.** If the beach detector generalises badly, no
   amount of revisit recovers it — which is why the dataset is the critical path and why the
   perfect-detector ablation exists.
5. **Use DSNE as the initial multi-look fusion rule.**
6. **Drop the unsourced "20 dB over less than 10°" target-strength figure** from the synthesis and
   plan. No verified source states it. Describe the mechanism qualitatively — aspect-dependent
   specular return, Lambertian scattering away from the receiver — and let the experiment supply the
   magnitude for our own targets.

---

## 8. Simulation, validation and sim-to-real

### Kamal Basha & Nambiar (2026). ACOUSIM: Physics-Informed Simulation Framework for Realistic Sonar Image Generation and Statistical Validation. arXiv 2605.19712. [full]

Its value to us is the **validation protocol**, not the simulator. Their simulator is deliberately
shallow: a Gazebo scene where sonar-like images are produced from an optical rendering,
I(x,y) = L(x,y)·R(x,y) with L encoding illumination and shadowing and R the surface reflectance,
then degraded with additive Gaussian and multiplicative speckle noise,
I_S = (I + N(0,σ²))·S(x,y). Shadow geometry is controlled by rotating a directional light source;
platform altitude is varied between 10 and 20 m. They state plainly that they do not model acoustic
wave propagation, only "first-order visual effects".

The protocol, which we should adopt for our own appearance validation:

- **Two distributions per image set.** A global intensity histogram, and a **Local Binary Pattern**
  texture histogram — LBP encodes each pixel by thresholding its neighbours against it, producing a
  compact descriptor of local texture that is invariant to overall brightness.
- **Three divergence measures** between the real distribution P and the synthetic distribution Q.
  **Kullback–Leibler divergence**, D_KL(P‖Q) = Σᵢ P(i)·log(P(i)/Q(i)), which measures directional
  information loss and is asymmetric. **Jensen–Shannon divergence**, the symmetric bounded version,
  D_JS = ½D_KL(P‖M) + ½D_KL(Q‖M) with M = ½(P+Q). **Earth Mover's Distance**, the minimum cost of
  transporting one distribution into the other, which is especially sensitive to shifts caused by
  shadow displacement and illumination change.
- **An interpretation scale on KL divergence**: High alignment below 0.2, Moderate 0.2 to 0.7, Low
  at or above 0.7. Plus stratified five-fold resampling, reporting mean ± standard deviation, so the
  numbers come with error bars.
- **Acquisition-consistent subsetting, which is a prerequisite, not a detail.** Synthetic images
  contain large seabed regions and wider scene coverage than real dataset images, where targets are
  cropped around the object. They spatially crop and zoom-adjust the synthetic samples to match the
  object scale, framing and viewing characteristics of the real imagery, convert to greyscale, resize
  to 256×256 and normalise to 8-bit, before any comparison. Without this the comparison is invalid.

**Their results, and why they matter to us.** Local texture aligns strongly across every class and
dataset (KL below 0.07, Earth Mover's Distance below 0.016). Global intensity aligns only moderately
for the plane class (KL 0.1804 and 0.2500) and *poorly* for the ship class (KL 0.5442 and 0.9173;
five-fold 1.019 ± 0.231 on SCTD). Their attribution: the elongated hull geometry and extended shadow
regions of ships "introduce complex intensity variations that are not fully reproduced by the
simulation framework". So the class whose appearance is dominated by shadow geometry is the class
the simulator gets wrong — a direct warning for our shadow-starvation modelling, and a reason to
report per-class rather than pooled agreement.

**How we use it.** Adopt the intensity-plus-LBP, KL/JS/EMD protocol as the concrete implementation of
our appearance-calibration check against the July recordings, with per-class and per-range reporting
and the five-fold error bars. It is cheap, quantitative and now has a citable precedent. But note the
limit that defines our own contribution: ACOUSIM validates *appearance distributions only*, and
states its own scope as "distribution-level statistical comparison". No verified work validates a
sonar simulator on the quantities a policy actually depends on. Our aspect-response check does
exactly that, which is a claimable methodological point rather than housekeeping.

### Sethuraman & Skinner (2023). STARS: Zero-Shot Sim-to-Real Transfer for Segmentation of Shipwrecks in Sonar Imagery. BMVC. [full introduction]

Side-scan image formation is well approximated by ray tracing; limited terrain and environmental
diversity produces a measurable gap between training on synthetic data and testing on real data.
The available realism levers are generative adversarial networks, style transfer, ray tracing, and
image composition. STARS targets zero-shot transfer — no real examples of the target class at all —
via physics-based rendering plus composition.

### Sethuraman, Baldoni, Skinner, McMahon (2024), simulator internals. [full]

A published reference design: OptiX ray tracing, material-specific acoustic reflectance in the
shader, speckle added after rendering, composition onto real terrain, and randomised Perlin-noise
heightmaps. Independent validation of our own simulator architecture, with the authors' caveat that
clutter, artifacts and multipath remain unvalidated — mirror that caveat in our limitations.

### Agrawal, Sikdar, Makam, Sundaram, Besai, Gopi (2024). Syn2Real Domain Generalization for Underwater Mine-like Object Detection Using Side-Scan Sonar. arXiv 2410.12953. [full]

The generative-augmentation route, with the numbers checked. A **diffusion model** generates images
by learning to reverse a gradual noising process; DDPM and DDIM are two samplers for it, DDIM being
the faster deterministic variant.

- **Scale.** 100 real images per mine type to train the generators (200 epochs, linear noise
  schedule); 600 annotated images total (200 DDIM + 200 DDPM + 200 real with augmentation) to train
  a Mask R-CNN segmentation model; verification on a held-out set of 100 real conical-mine images.
- **Results on the real test set.** Metrics are **AP** (Average Precision) at various IoU thresholds,
  plus **AUPC**, the area under the precision-versus-IoU-threshold curve. Real data only: AP50 0.682,
  AP50:95 0.399, AUPC 0.168. **DDPM + DDIM + real: AP50 0.833, AP50:95 0.635, AUPC 0.264** — the
  "about 60% increase" in their abstract is AP50:95 rising 0.399 → 0.635, i.e. +59% relative.
- **The striking row.** **DDIM synthetic data alone (AP50 0.727, AP50:95 0.521) beats real-data-only
  training (0.682 / 0.399)** on a real test set, with only 100 real images behind the generator.
  DDPM alone is far worse (0.434 / 0.263), so the sampler choice dominates. Their stated mechanism:
  residual noise in the sampled images improves generalisation to real data, which is itself noisy
  and highly variable.

Directly relevant to our dataset bottleneck. If the beach set lands at roughly 100 labelled instances
per class, training a diffusion generator on it and mixing the output back into training is an
evidenced route to accuracy we would otherwise need several times the data for — and a cheaper
sim-to-real experiment than full simulator transfer.

### What we do

The simulation plan is confirmed, with two additions. **Adopt ACOUSIM's statistical protocol** for
appearance validation against July data — intensity and LBP histograms, KL/JS/EMD, per class and
per range band, five-fold error bars, with acquisition-consistent cropping first. **Run the
sim-to-real experiment with two arms**: physics-simulator transfer and diffusion augmentation, since
the second is cheap and has a verified effect size on a comparably small real dataset. Keep the
aspect-response check as the go/no-go, because appearance agreement — as ACOUSIM's own ship-class
result shows — does not imply the simulator reproduces shadow-driven behaviour. State multipath and
clutter as unmodelled.

---

## 9. Preprocessing and geocoding — the pipeline we have already built

### Lei, Franchi, Rajani, Gracias, Garcia, Wang (2026). Geometric Correction of Side-Scan Sonar Images with Image-Consistent Attitude Refinement. arXiv 2604.19901. [full]

Geocoding means projecting each sonar sample from its position in the raw waterfall image to a
physical location on the seabed. This paper is the closest published description of our own
preprocessing module, plus a correction stage we do not yet have — and it is written for exactly our
failure mode.

**Why it matters to a surface vehicle.** Side-scan sonar is a line-scan sensor: the waterfall image
is built by stacking one echo profile per ping, so it is *highly sensitive to time-varying platform
motion*. They list the causes — attitude oscillation, speed fluctuation, trajectory perturbation,
timing mismatch between the sonar and navigation systems, and phase lag introduced by filtering —
and the symptoms: inter-ping misalignment, along-track stretching, and local compression. Their
central observation is that navigation data "preserve the coarse motion trend but fail to accurately
represent the ping-scale perturbations that directly affect line-scan image formation". A wave-driven
USV has more of this motion than the towed and autonomous platforms they test on, not less.

**Their geocoding equations, which formalise what our pipeline does** (ping index n, across-track
sample index x, image width W):
- slant range of a sample: ℓ(x,n) = ℓ_max(n)·x/(W−1)
- **effective altitude, corrected for pitch**: a(n) = h(n)/cos θ(n)
- ground range: D(x,n) = √(ℓ(x,n)² − a(n)²)
- cross-track offset: D_ct = σ·D with σ = −1 for port, +1 for starboard
- **along-track offset induced by pitch**: D_at(n) = h(n)·tan θ(n)
- world position: g(x,n) = p(n) + R(ψ(n))·D_loc, i.e. rotate the local offset by the yaw angle and
  translate by the towfish position.

Two of these are refinements our current implementation may not include: pitch enters twice, once
inflating the effective altitude used in the slant-range correction, and once displacing the
footprint along-track.

**Two implementation choices worth copying.**
- **A track-aligned local frame instead of rasterising directly into map coordinates.** Because the
  survey track is generally not aligned with the map projection axes, rasterising in UTM produces an
  awkwardly oriented grid with more empty cells. They define a local frame whose axes follow the
  dominant survey direction, preserving the natural across-track/along-track organisation while
  remaining metrically consistent. They note the assumption: the segment must have a well-defined
  dominant direction, so trajectories with strong turning must be segmented before gridding — which
  matters for us, since our replanner deliberately introduces turns.
- **Normalized convolution for hole filling.** Gridding produces a validity mask marking cells that
  received no samples; those cells are then filled by a convolution that weights only valid
  neighbours (they use a 7×7 kernel). This is a principled alternative to plain interpolation and
  keeps the support of real measurements explicit.

**The attitude-refinement idea, and whether we need it.** They decompose the attitude used for
geocoding into a smooth navigation-derived baseline plus a small image-inferred perturbation,
Θ_ref = Θ̄ + δΘ, where Θ̄ comes from a Savitzky-Golay smoother (a polynomial-fit filter that
suppresses jitter while preserving local trend shape; window 301 pings, polynomial order 1). The
perturbation is inferred from the imagery using **port–starboard symmetry**, which is the elegant
part: a yaw error advances one side along-track while delaying the other, producing *antisymmetric*
distortion, whereas a pitch error stretches both sides the same way, producing *symmetric*
distortion. Speed and position fluctuations produce the same symmetric signature as pitch and are
absorbed into that channel; roll is excluded because it mainly modulates backscatter intensity
through the incidence angle rather than causing along-track misalignment; altitude is held fixed
because it is obtained robustly from bottom tracking.

**Results, and the honest limits.** Against a navigation-derived reference image, correction improves
all four image-quality measures — **PSNR** (peak signal-to-noise ratio, higher is better) 20.03 →
22.27 on dataset I and 18.04 → 20.68 on dataset II; **MS-SSIM** (multi-scale structural similarity,
0 to 1, higher better) 0.617 → 0.751 and 0.561 → 0.702; **NCC** (normalised cross-correlation,
higher better) 0.587 → 0.755 and 0.521 → 0.711; **LPIPS** (learned perceptual image patch similarity,
lower better) 0.227 → 0.211 and 0.250 → 0.230. Under deliberately degraded attitude input, the
method helps substantially when navigation is over-smoothed (PSNR +2.71, MS-SSIM +0.11) or delayed
(+2.74, +0.12), but **under strong random noise it improves PSNR (+1.62) while slightly *degrading*
structural similarity (−0.005) and correlation (−0.031)**. They also state two limitations: the
method depends on several empirically chosen thresholds, and it models stretching only, because
compression is not distinguishable from natural terrain variation by image appearance.

**The incidental finding that matters most.** Their three datasets span two sonar models and three
range settings — Marine Sonic Arc Scout MK II at 900 kHz with 30–60 m and 30–80 m range, and Klein
3000H at 500 kHz with 50–100 m range — and in all three, **acquisition altitude is approximately 10%
of range**. Three independent surveys, two platforms, one convention. This is the cleanest verified
anchor we have for the scientific spine's first step: conventional side-scan practice places the
sonar at roughly a tenth of its range above the seabed, and a surface vehicle in 3 m of water at
30 m range operates at 10% of that altitude ratio. The shadow-starvation argument now rests on a
citable norm rather than an assertion.

### What we do

1. **Check our slant-range correction for the two pitch terms** — pitch inflating effective altitude
   (a = h/cos θ) and pitch displacing the footprint along-track (D_at = h·tan θ). If our
   implementation assumes zero pitch, quantify the error at our altitudes before dismissing it.
2. **Adopt the track-aligned gridding frame and normalized-convolution hole filling** for the mosaic
   product, and **segment the trajectory at turns** before gridding — necessary for us because the
   replanner generates turns by design.
3. **Cite this paper for the altitude convention** (altitude ≈ 10% of range, verified across three
   datasets and two sonars) in the scientific spine, and for the catalogue of surface-motion
   distortion mechanisms in the preprocessing chapter.
4. **Treat attitude refinement as optional future work, not a dependency.** It helps most when
   navigation is over-smoothed or lagged, and least under random noise — and a wave-driven USV's
   attitude error is closer to the noisy case. If our imagery shows systematic stretching, their
   port–starboard symmetry test is the cheap diagnostic to run first: symmetric stretching implicates
   pitch or speed, antisymmetric implicates yaw.

---

## 10. Platform, operations and ground truth

### Mandić, Rendulić, Mišković, Nađ (2016). Underwater Object Tracking Using Sonar and USBL Measurements. Journal of Sensors 2016, 8070286. [abs]

USBL (Ultra-Short BaseLine) is an acoustic positioning method in which a receiver measures the range
and bearing to a pinger. They fuse sonar and USBL measurements in a tracking filter, adapting the
sonar's region of interest from the filter's covariance; on field data the fused estimate outperforms
either sensor alone. The precedent for treating USBL as first-class instrumentation and, if needed,
for gating detections by predicted position uncertainty.

### CORAL (Cocchi et al. 2024) — see §4. [full]

### What we do

Characterise the Water Linked unit's error empirically before using it as ground truth. Log the
detection-probability-versus-range curve per session. Expect usable range to vary with sea state,
seabed type, depth and altitude, as Wiig reports.

---

## 11. Build list

1. **Scope.** Cite **S-44 Exclusive Order** (cubic features > 0.5 m, 200% feature search) for the
   detection floor and the baseline, not Special Order. Size the revisit envelope R ≥ 3σ per §3.7.
   Cite Lei et al. for the altitude ≈ 10% of range convention underpinning the shadow-starvation
   argument.
2. **Detector.** Nano-scale YOLO with COCO-pretrained weights, stratified splits, selected by recall;
   temperature scaling with reliability diagram and ECE at 15 bins before anything enters the grid;
   a noisy/clean generalisation split of our own.
3. **Grid.** Bayes miss update pᵢ⁺ = pᵢ(1−PD)/(pᵢ(1−PD) + 1 − pᵢ); per-cell Qᵢ = ∏(1 − PDᵢⱼ)
   channel; Paull's angle-interpolated fusion as placeholder, replaced by the measured response;
   DSNE for multi-look evidence; Dempster–Shafer contact fusion for data association.
4. **Preprocessing.** Verify both pitch terms in the slant-range correction; track-aligned gridding
   with normalized-convolution hole filling; segment the trajectory at turns.
5. **Coverage.** Boustrophedon at measured-swath spacing, overlap on the weak swath tail,
   paired-track check r_max ≥ 3·r_min; two-pass orthogonal baseline tuned for the target coverage
   confidence.
6. **Replanner.** Three-term submodular utility on the grid; straight legs with lead-in and lead-out;
   decide contact and heading only; filter by class, confidence floor and area of interest; order as
   a turn-penalised generalised travelling salesman problem; conservative pruning; short lookahead,
   not greedy.
7. **Stopping.** Relative-Information-Contribution-style per-contact resolution and abandonment,
   allowed to be class-dependent; a budget fraction; saturation-entropy mission stop; thresholds from
   simulation sweeps with sensitivity reported.
8. **Simulator validation.** Intensity and LBP histograms with KL, JS and EMD divergences, per class
   and per range band, five-fold error bars, acquisition-consistent cropping first; aspect-response
   check as the go/no-go.
9. **Experiments to reproduce.** Sethuraman's informed-versus-random-aspect ablation; Paull's
   adaptive-versus-lawnmower confidence-threshold sweep; the JMSE version-comparison protocol on
   beach data; Fawcett's daisy-wheel geometry for the aspect experiment; Syn2Real's diffusion
   augmentation on the beach dataset.
10. **Claims now sourced.** 30 minutes per contact for exhaustive reacquisition (Sethuraman); the
    200% two-pass requirement (S-44 Exclusive Order §3.4, NOAA practice, Wiig's angled double
    lawnmower); "no single survey system can guarantee detection of all features" (S-44 §3.3);
    altitude ≈ 10% of range as survey convention (Lei et al., three datasets); raw confidence
    overconfidence and its fix (Guo); second-look gains and their limits (Fawcett); the
    single-mission integration gap (Qiao §5).

---

## 12. Glossary

**AP / AP50 / AP50:95** — Average Precision, the area under the precision-recall curve; the suffix
gives the IoU threshold(s) at which a detection counts as correct.
**AUPC** — Area Under the Precision-versus-IoU-threshold Curve.
**AUV** — Autonomous Underwater Vehicle.
**Boustrophedon / lawnmower** — a survey path of parallel straight lines with turns at the ends.
**COCO** — a 330,000-image general-purpose object-detection dataset used for pretraining.
**Cubic feature** — S-44's reference shape for detection size: a cube with six equal square sides.
**Dempster–Shafer theory** — an evidence-combination framework generalising Bayesian fusion, able to
represent "unknown" explicitly rather than forcing a single probability.
**DDPM / DDIM** — Denoising Diffusion Probabilistic Model and its faster deterministic sampler;
generative models that create images by reversing a noising process.
**Dubins turn** — the shortest curve between two poses under a minimum-turning-radius constraint.
**ECE / MCE** — Expected and Maximum Calibration Error; the average and worst-case gap between a
model's confidence and its accuracy, computed over confidence bins.
**EMD** — Earth Mover's Distance; the minimum cost of transforming one distribution into another.
**Entropy** — a measure of uncertainty in a probability distribution; zero when certain.
**Feature detection / feature search** — S-44 terms: the smallest detectable object, and the
percentage of area systematically searched.
**FPS / GFLOPs / parameters** — inference speed in frames per second; billions of floating-point
operations per image; the count of learned weights.
**Geocoding** — projecting sonar samples from image coordinates to physical seabed positions.
**Gumbel distribution** — the distribution of the maximum of many samples; used to model the peak of
a template-matching score.
**IoU** — Intersection over Union, the overlap between a predicted and a true bounding box.
**JS divergence** — Jensen–Shannon divergence, the symmetric bounded form of KL divergence.
**KL divergence** — Kullback–Leibler divergence, an asymmetric measure of how one probability
distribution differs from another.
**Lacunarity** — variance of pixel amplitudes divided by their mean squared; a texture descriptor
used to distinguish man-made from natural objects.
**Lambertian** — a reflection model in which brightness depends on the angle between surface and
sensor.
**LBP** — Local Binary Pattern; a compact local-texture descriptor invariant to overall brightness.
**LPIPS** — Learned Perceptual Image Patch Similarity; a perceptual image-difference measure computed
in a neural network's feature space, lower being more similar.
**mAP50 / mAP50:95** — mean Average Precision at IoU 0.5, and averaged over IoU 0.5 to 0.95.
**MS-SSIM** — Multi-Scale Structural Similarity, an image-similarity measure from 0 to 1.
**MTTD** — Mean Time To Detection.
**Nadir** — the blind strip directly beneath a side-scan sonar.
**NCC** — Normalised Cross-Correlation between two images, closer to 1 being more similar.
**NLL** — Negative Log Likelihood, the standard classification training loss.
**Normalized convolution** — filling missing grid cells using only valid neighbours, weighted by a
validity mask.
**POMDP** — Partially Observable Markov Decision Process; a decision framework where the agent acts
on a probability distribution over states rather than the state itself.
**Precision / recall** — the fraction of reported detections that are real; the fraction of real
objects that were reported.
**PSNR** — Peak Signal-to-Noise Ratio in decibels, higher being closer to the reference image.
**Residual risk** — the accumulated probability of having missed a target after all looks, ∏(1 − Pd).
**RIC** — Relative Information Contribution; a dimensionless measure of how much a new planning step
adds, used as a stopping criterion.
**Savitzky-Golay filter** — a smoothing filter that fits local polynomials, preserving trend shape
better than a moving average.
**Slant range / ground range** — the straight-line distance from sonar to target; its horizontal
projection onto the seabed.
**Submodular** — a diminishing-returns property: additional observations of an already-observed
region yield less information.
**Swath** — the strip of seabed imaged on one sonar pass.
**Temperature scaling** — dividing a network's raw scores by a single fitted constant to calibrate
confidence without changing predictions.
**TSP** — Travelling Salesman Problem; find the shortest route visiting a set of points.
**USBL** — Ultra-Short BaseLine acoustic positioning, measuring range and bearing to a pinger.
**USV** — Unmanned Surface Vessel.
**YOLO** — "You Only Look Once", a family of single-stage object detectors; "n" denotes the smallest
"nano" variant of each version.

*End.*
