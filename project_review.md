# Project review — side-scan sonar sensor pipeline: literature versus implementation

*First-pass review, 2026-09-14. Review only: no code was changed. Every repository claim
carries a `path:line` (paths relative to this superproject root); every literature claim
carries a numbered reference from the list below; every measured number names the log and
the script that produced it. Scripts and raw outputs are in the session scratchpad
(`scratchpad/review/`, see Appendix).*

**Markers.** VERIFIED = read in the named file or paper. MEASURED = computed by a named
script on a named log or image. UNCERTAIN = contested, undocumented, or not establishable
from this machine.

**Evidence base on this machine.** 19 `.svlog` files under `~/ros2_ws/data/SSS_data/`.
Reading each file's session header and packet census (MEASURED, `side_identity.py`) shows
**16 were recorded by SonarLink 1.14.50-dev on the boat's BlueOS** (they carry id-12 view
config and id-2194 status packets; the whole `beach_sept/` set of 2026-09-07, plus
`diffDepthCompensation`, `fullHarbourCleanExample`, `OneLineHarbourClean70m`,
`toOptimize-harbourScan`) and **3 by our own `sss_processor_node`** (the July harbour
logs `DiffSV-US_whenDepthCompensation`, `MainReflectionEvidence+misspingsWaterfall`,
`reflectionEvidenceFullharbour`). There is therefore **no field recording made by our stack
after the September 2026 side-identity patch on this machine**; the corpus mount named in
`BlueBoat-SSS/.claude/CLAUDE.md` is absent. The screenshot
`~/Desktop/us_vs_sonarview_noise.png` (right = our GCS, left = SonarView, per the user) is
from a deleted simulator session, so it supports relative measurements only.

---

## References

Only sources whose full text was read are cited in Parts 1–5. Access route and the
sections read are given so the claim trail is auditable.

**Peer-reviewed, standards, preprints — read in full text**

- [R1] Burguera, A., Oliver, G. (2016). High-resolution underwater mapping using side-scan sonar. *PLOS ONE* 11(1): e0146396. https://doi.org/10.1371/journal.pone.0146396 — full HTML.
- [R2] Xu, W., Ling, L., Xie, Y., Zhang, J., Folkesson, J. (2023). Evaluation of a canonical image representation for sidescan sonar. *OCEANS 2023 – Limerick*; arXiv:2304.09243. https://doi.org/10.1109/OCEANSLimerick52467.2023.10244293 — arXiv PDF, whole paper.
- [R3] Zhao, J., Yan, J., Zhang, H., Meng, J. (2017). A new radiometric correction method for side-scan sonar images in consideration of seabed sediment variation. *Remote Sensing* 9(6): 575. https://doi.org/10.3390/rs9060575 — PDF, §2–3 and §5.
- [R4] Zheng, G., Zhang, H., Li, Y., Zhao, J. (2021). A universal automatic bottom tracking method of side scan sonar data based on semantic segmentation. *Remote Sensing* 13(10): 1945. https://doi.org/10.3390/rs13101945 — PDF, §1, §2.1.2, §3.2.1.
- [R5] Yan, J., Meng, J., Zhao, J. (2021). Bottom detection from backscatter data of conventional side scan sonars through 1D-UNet. *Remote Sensing* 13(5): 1024. https://doi.org/10.3390/rs13051024 — PDF, §2.1, §3.2.1, §4.
- [R6] Grabek, J., Cyganek, B. (2019). Speckle noise filtering in side-scan sonar images based on the Tucker tensor decomposition. *Sensors* 19(13): 2903. https://doi.org/10.3390/s19132903 — PDF, §3 and §6.
- [R7] Grządziel, A. (2023). The impact of side-scan sonar resolution and acoustic shadow phenomenon on the quality of sonar imagery and data interpretation capabilities. *Remote Sensing* 15(23): 5599. https://doi.org/10.3390/rs15235599 — PDF, §2–5.
- [R8] Kim, Y., Ryou, J. (2020). A study of sonar image stabilization of unmanned surface vehicle based on motion sensor for inspection of underwater infrastructure. *Remote Sensing* 12(21): 3481. https://doi.org/10.3390/rs12213481 — PDF, §1, §3.2, §4.2.
- [R9] Zhang, Z., Wu, R., Li, D., Lin, M., Xiao, S., Lin, R. (2024). Image stitching and target perception for Autonomous Underwater Vehicle-collected side-scan sonar images. *Frontiers in Marine Science* 11: 1418113. https://doi.org/10.3389/fmars.2024.1418113 — full HTML.
- [R10] Lei, C., Franchi, V., Rajani, H., Gracias, N., Garcia, R., Wang, H. (2026). Geometric correction of side-scan sonar images with image-consistent attitude refinement. arXiv:2604.19901. https://doi.org/10.48550/arXiv.2604.19901 — local PDF, §I–II, §V.
- [R11] Lurton, X., Lamarche, G. (eds.) (2015). *Backscatter measurements by seafloor-mapping sonars — Guidelines and Recommendations*. GeoHab Backscatter Working Group, 200 pp. https://doi.org/10.5281/zenodo.10089260 — PDF, §2.3–2.6, §4.2.2 (stage 2), §5.3.1, §5.5.2.
- [R12] NOAA Office of Coast Survey (2021). *Hydrographic Surveys Specifications and Deliverables*. https://nauticalcharts.noaa.gov/publications/docs/standards-and-requirements/specs/HSSD_2021.pdf — PDF, §5.2.2, §6.1.2–6.1.3.
- [R13] International Hydrographic Organization (2022). *S-44 Standards for Hydrographic Surveys*, Edition 6.1.0. https://iho.int/uploads/user/pubs/standards/s-44/S-44_Edition_6.1.0.pdf — PDF, §3.3–3.5 and Table 1.
- [R14] Steiniger, Y., Kraus, D., Meisen, T. (2022). Survey on deep learning based computer vision for sonar imagery. *Engineering Applications of Artificial Intelligence* 114: 105157. https://doi.org/10.1016/j.engappai.2022.105157 — author-deposited PDF (DLR elib), §1, §6, §7.
- [R15] Qiao, J., Yu, J., Huang, Y., Feng, H., Jia, D., Wang, Z., Wang, B. (2026). AUVs for seabed surveying: a comprehensive review of side-scan sonar-based target detection. *Journal of Marine Science and Engineering* 14(2): 145. https://doi.org/10.3390/jmse14020145 — PDF, §2, §4.3.2, §5.
- [R16] Sethuraman, A. V., Sheppard, A., Bagoren, O., Pinnow, C., Anderson, J., Havens, T. C., Skinner, K. A. (2025). Machine learning for shipwreck segmentation from side scan sonar imagery: dataset and benchmark. *International Journal of Robotics Research* 44(3): 341–354. https://doi.org/10.1177/02783649241266853 — arXiv 2401.14546v2 full text.
- [R17] Sethuraman, A. V., Baldoni, J., Skinner, K. A., McMahon, J. (2024). Learning which side to scan: multi-view informed active perception with side scan sonar for autonomous underwater vehicles. arXiv:2402.01106. https://doi.org/10.48550/arXiv.2402.01106 — full HTML.
- [R18] Huo, G., Wu, Z., Li, J. (2020). Underwater object classification in sidescan sonar images using deep transfer learning and semisynthetic training data. *IEEE Access* 8: 47407–47418. https://doi.org/10.1109/ACCESS.2020.2978880 — open-access PDF, §II–III.
- [R19] Wei, C., Bai, Y., Liu, C., Zhu, Y., Wang, C., Li, X. (2024). Unsupervised underwater shipwreck detection in side-scan sonar images based on domain-adaptive techniques. *Scientific Reports* 14: 12687. https://doi.org/10.1038/s41598-024-63501-1 — PMC full text.
- [R20] Gomes, L. S., Almeida, G. P., Moreira, B. U., Quiroz, M., Xavier, B., Soares, L., Brião, S. L., Oliveira, F. G., Drews-Jr, P. L. J. (2025). Sonar image datasets: a comprehensive survey of resources, challenges, and applications. SIBGRAPI 2025; arXiv:2510.03353. https://doi.org/10.48550/arXiv.2510.03353 — full HTML.
- [R21] Zhang, P. (2026). SCTD 3.0: Sonar Common Target Detection in the wild — a large-scale, multi-scene dataset from real marine surveys. arXiv:2608.08106. https://doi.org/10.48550/arXiv.2608.08106 — full HTML.
- [R22] Basha, S. K., Nambiar, A. (2024). S3Simulator: a benchmarking side scan sonar simulator dataset for underwater image analysis. *ICPR 2024*, Springer LNCS; arXiv:2408.12833. https://doi.org/10.1007/978-3-031-78444-6_15 — arXiv full HTML.
- [R23] Sethuraman, A. V., Skinner, K. A. (2023). STARS: zero-shot sim-to-real transfer for segmentation of shipwrecks in sonar imagery. arXiv:2310.01667. https://doi.org/10.48550/arXiv.2310.01667 — full HTML.
- [R24] Basha, S. K., Nambiar, A. (2026). Physics-informed simulation framework for realistic sonar image generation and statistical validation (ACOUSIM). arXiv:2605.19712. https://doi.org/10.48550/arXiv.2605.19712 — local PDF, whole paper.
- [R25] Cocchi, L., Muccini, F., Locritani, M., Spinelli, F., Cocco, M. (2024). CORAL — Catamaran for Underwater Exploration: development of a multipurpose unmanned surface vessel for environmental studies. *Sensors* 24(14): 4544. https://doi.org/10.3390/s24144544 — PMC full text.
- [R26] Yu, B., Lin, R., Zhou, H., Zhang, J., Zhang, X. (2026). Physics-informed side-scan sonar perception: tackling weak targets and sparse debris via geometric and frequency decoupling. *Sensors* 26(6): 1938. https://doi.org/10.3390/s26061938 — PDF, §1, §4.1, §6.
- [R27] Liu, L., Li, H., Zhu, J., Peng, Y., Zhai, G. (2026). YOLO variant evaluation and transfer learning analysis for side-scan sonar object detection. *Journal of Marine Science and Engineering* 14(6): 550. https://doi.org/10.3390/jmse14060550 — PDF, §3.1, §4, §6.

**Vendor documentation (not peer-reviewed; fetched 2026-09-14)**

- [V1] Cerulean Sonar, *SonarView — Omniscan 450 display controls*. https://docs.ceruleansonar.com/c/sonarview/device-specific-controls/omniscan-450/display-controls
- [V2] Cerulean Sonar, *SonarView — Omniscan 450 device controls*. https://docs.ceruleansonar.com/c/sonarview/device-specific-controls/omniscan-450/device-controls
- [V3] Cerulean Sonar, *SonarView — Omniscan 450 mounting setup*. https://docs.ceruleansonar.com/c/sonarview/device-specific-controls/omniscan-450/mounting-setup
- [V4] Cerulean Sonar, *SonarView — Multiple Omniscans*. https://docs.ceruleansonar.com/c/sonarview/session-configurations/multiple-omniscans
- [V5] Cerulean Sonar, *Omniscan 450 application programming interface*. https://docs.ceruleansonar.com/c/omniscan-450/application-programming-interface
- [V6] Cerulean Sonar, *SonarView — Session configurations*. https://docs.ceruleansonar.com/c/sonarview/session-configurations
- [V7] Blue Robotics, *Integrating the Omniscan 450 SS on the BlueBoat*. https://bluerobotics.com/learn/omniscan-450-ss-integration/

**Identified, not verified, not cited** (paywalled or unreachable; PDFs were requested and
had not arrived by the end of this pass): Blondel 2009 *Handbook of Sidescan Sonar*
(10.1007/978-3-540-49886-5); Capus et al. 2008 (10.1049/iet-rsn:20070032); Cobra,
Oppenheim & Jaffe 1992 (10.1109/48.153442); Cervenka & de Moustier 1993
(10.1109/48.219531); Johnson & Helferty 1990 (10.1029/RG028i004p00357); Abraham & Lyons
2002 (10.1109/JOE.2002.804324); Reed, Petillot & Bell 2003 (10.1109/JOE.2002.808199);
Al-Rawi et al. 2017 (10.1109/OCEANSE.2017.8084587); Paull et al. 2013 (IEEE/ASME TMech
18(6)); Bore & Folkesson 2021 (10.1109/JOE.2020.2980456); Greene et al. 2018 (ECSS 207);
Zeng et al. 2026 (Ocean Engineering); Chavez 1986 (USGS 70014528, page unreachable); Lurton
2010 *An Introduction to Underwater Acoustics*. Several of these are cited in
`BlueBoat-SSS/blueboat_sss/blueboat_gcs/docs/SCIENTIFIC_BACKGROUND.md`; that document's DOIs
were resolved through Crossref, which confirms existence, not content.

---

## Part 1 — Literature review

### 1.1 Sensing fundamentals: geometry, radiometry, speckle, bottom tracking

**Geometry.** A ping is a time series along slant range; the ground range of a seabed
sample under a flat-floor assumption is `r_g = sqrt(r_s² − h²)` with `h` the transducer
altitude, and the first bottom return sits at `r_g,FBR = h·tan(θ − α/2)` for a beam of
depression `θ` and vertical width `α` [R1]. Burguera & Oliver derive how wrong the flat-floor
assumption is for a 455 kHz Imagenex SportScan at 5 m altitude: an object 1.5 m high is
misplaced by up to 0.7 m at 25 m range, which they report as 1.2 % of the range setting
[R1]. Xu et al. show that the same feature spans 112 and 153 columns in two raw waterfalls
taken at different ranges and 78 and 77 columns after slant-range correction to a fixed
ground pitch, i.e. object size in raw slant-bin imagery depends on where in the swath the
object lies [R2]. Both papers remove the nadir region geometrically (blind-zone removal in
[R1]; projection starting at a 30° incidence angle in [R2]); neither filters it.

**Radiometry.** The one-way transmission loss is `TL = 20 log R + αR` [R11, eq. 2.6], applied
twice for a two-way path; the angular dependence of seabed backscatter is bracketed by the
Lommel–Seeliger and Lambert laws, `BS(θ) = BS₀ + 20 log cos θ` in the incidence-angle form,
with real seafloors between the two and best fitted by `cosⁿθ`, `n ≥ 1` [R11, §2.4.4]. The
guidelines describe the receiver's time-varying gain (TVG) or automatic gain control as a
stage-2 amplification whose purpose is to fit the signal into the sampling hardware, note
that newer systems with enough dynamic range skip the analog TVG, and state that a digital
TVG applied afterwards is done "largely for aesthetic reasons, equalizing the measurements
across the swath" and is completed in post-processing by an angle-varying gain [R11,
§4.2.2]. Zhao et al. write the TVG as `αR + 20 log R`, attribute its residuals to the
empirical `α` and sound speed used in the field, note that the residual cannot be undone
because manufacturers rescale the samples into a fixed 8- or 16-bit range, and estimate the
angle–backscatter curve per sediment class by averaging many pings per incidence angle
[R3, §2.1, §3.2.3]. Xu et al. evaluate beam-pattern plus incidence-angle correction with
`cos`, `cos²` and `cot` laws before slant-range correction and find `cos²` best: patch
correlation across survey lines rises from 0.69 to 0.93 and SIFT matching accuracy reaches
92.7 % [R2]. The GeoHab guidelines also warn that a receiver run near saturation clips
irreversibly and that settings changed while saturated leave artefacts coinciding with the
change [R11, §5.3.1].

**Speckle.** Backscatter from the seafloor is "an inherently random process": an ensemble
of independent measurements of a statistically identical seafloor spans up to 20 dB, a
Rayleigh-law fluctuation that "helps explain the requirement to average over a region of
measurements when generating a crisp-looking seafloor backscatter mosaic" [R11, §2.5.5].
For exponentially distributed intensity (Rayleigh amplitude) the standard deviation of the
decibel value is `(10/ln 10)·π/√6 = 5.57 dB`, a closed-form consequence of that law used
in Part 3.5. Grabek & Cyganek model sonar speckle as multiplicative plus additive noise,
`g = f·u + η`, and note that every despeckling filter is a low-pass operation whose side
effect is "degradation of useful image features such as edges, corners" [R6, §3].

**Bottom tracking.** Threshold trackers, as used in commercial packages, need a preset
minimum altitude and range and fail in the field for identifiable reasons: strong echoes
in the water column (suspended matter, wake bubbles, surface reflections through side
lobes), low water-column-to-seabed contrast in turbid water or over absorbing sediment,
**unknown gain changes** made by the operator and not recorded, and missing pings [R4,
§2.1.2]. Yan et al. list the same factors for single-ping detection and show the classical
"last peak" detector landing behind the true bottom whenever gain is applied, and on a
target instead of the bottom over low-reflectivity sediment; their 1D-UNet fails only at
very low SNR or when a suspended object fills the water column, and they recommend using
port–starboard symmetry and interpolation from neighbouring pings in those cases [R5,
§3.2.1, §4.2]. Zheng et al. reach the same conclusion with a 2-D segmentation of the
waterfall on a 450 kHz Shark-S150D and an EdgeTech 4205 log with two unrecorded gain
changes, where a fixed-threshold tracker drifts at each change [R4, §3.2.1].

### 1.2 Display and processing practice: along-track scale, motion, mosaicking

Along-track resolution of a mosaic "depends on the survey speed and ping rate", and the
along-track resolution at range `D` for a horizontal beam width `θ_h` is `R_x = D·sin θ_h`,
against an across-track resolution `R_y = cτ/(2 cos β)` [R7, §4]. Grządziel's Baltic
comparison of a hull-mounted 100 kHz sonar and a towed 100/500 kHz sonar attributes the
hull-mounted sonar's lower resolving power in shallow water to the transducer–seafloor
distance and pulse geometry, and shows shadows as the decisive interpretation cue for
wrecks [R7, §2.2, §3, §5]. Lei et al. describe the waterfall as a line-scan image "formed by
stacking successive echo profiles along-track" that is therefore sensitive to attitude
oscillation, speed fluctuation and sonar–navigation timing mismatch, which appear as
inter-ping misalignment, along-track stretching and local compression; they refine the
yaw–pitch sequence used in geocoding from stripe-wise distortion patterns, using
port–starboard symmetry to separate pitch (common-mode) from yaw (differential-mode)
[R10, §I, §III]. Kim & Ryou show, for a side-scan sonar towed under a small USV, that
per-ping roll correction from a motion sensor reduces the size error of measured damage
from 21.6 % to 5.8 % at 1250 kHz for roll swings of ±6.5° [R8, §4.2]. Burguera & Oliver
build the mosaic on a metric grid with a per-measurement observation probability and
bilinear interpolation of intensities, achieving 5 cm cells from a 12 cm native pitch by
fusing overlap [R1]; Zhang et al. use a sliding-window seabed line, a mean-amplitude gain
compensation, slant-range correction with linear gap interpolation, and geocoding at 10 Hz
pose rate [R9]. Xu et al.'s slant-range correction resamples each ping to a *chosen*
ground-range pitch by area-weighted averaging of the contributing bins, which they present
as the sensor-independent step that makes images from different sensors and settings
comparable [R2, §III.2].

None of these sources documents a *display* rule for the on-screen waterfall's vertical
scale; the operational standards state the requirement in survey terms instead: NOAA
requires that a 1 m cube be "independently ensonified a minimum of three times per pass",
that the towfish height be 8–20 % of the range scale, that contacts of at least 1 m height
be picked from shadow length in depths ≤ 20 m, and 200 % side-scan coverage for object
detection [R12, §5.2.2.2, §6.1.2, §6.1.3.3]; IHO S-44 Table 1 sets the feature-detection
reference to cubic features > 1 m (Special Order) and > 2 m in depths to 40 m (Order 1a),
with a 100 % or 200 % feature search [R13, §3.3–3.4].

### 1.3 AI on side-scan imagery

The 2022 survey of 62 papers finds CNNs outperforming classical methods for feature
extraction and classification, no comparison with conventional detectors for detection and
segmentation, a domain gap to natural images that defeats naive transfer, and, as the most
challenging problem, the lack of a public benchmark; it names highlight/shadow appearance
changing with viewing angle and seafloor type as the properties a dataset must cover, and
uncertainty estimation and calibration as unexplored [R14, §1, §6.3, §7]. The 2026 review
organises the field into preprocessing (slant-range and geometric-distortion correction,
with bottom tracking as the prerequisite), detection, and survey path planning, and singles
out multi-view "viewpoint optimisation" — including [R17] — as the way past single-view
occlusion and incomplete contours [R15, §2, §4.3.2].

What detectors are actually fed matters here. AI4Shipwrecks exports through EdgeTech
Discover, which "normalizes the sonar image intensity and applies Time Varying Gain", with
**no slant-range correction**, tiles at 1728 px and downsamples to 512 px, normalises around
zero by mean and standard deviation, and has anisotropic pixels (13.6 cm along-track at
2.5 kn versus 1.2 cm across-track) with no speed correction; the best of six segmentation
models reaches 0.445 IoU and performance plateaus after about six training sites [R16].
SCTD 3.0 applies histogram equalisation and crops 800 px around the target with its shadow,
annotates highlight and shadow morphology separately, and reports a "cliff-like" drop across
frequency bands, regions and viewing angles [R21]. The YOLO evaluation on KLSG and SCTD
(447 and 357 images) finds COCO pre-training the dominant factor and explicitly does not
model shadows, speckle or multipath [R27]. WPG-DetNet enforces a target-height/shadow-length
consistency loss and wavelet decoupling of speckle on the 357-image SCTD, reports 97.5 %
mAP, and states that evaluation on a single dataset limits any generalisation claim [R26].
Multi-view active perception with a graph network over six views raises simulated
classification accuracy from 0.628 (single pass) to 0.952 with 1.18 views per target, with
sim-to-real transfer left as future work [R17]. Domain adaptation from optical ship images
to SSS reaches 92 % AP50 unsupervised, with a separate turbid-water set of buried wooden
wrecks as the hard case [R19].

### 1.4 Dataset generation

Public SSS datasets are small: the 2025 survey lists SeabedObjects-KLSG (1 190),
Marine PULSE (627), a mine set (1 170), SWDD (7 904), SubPipe (10 030), SCTD (357) and
AI4Shipwrecks (286) among others, and finds only two datasets with synthetic components
[R20]. Huo et al. built KLSG (385 wrecks, 36 victims, 62 aircraft, 129 mines, 578 seafloor
patches, cut from full images without processing) and raise overall accuracy from 96.1 % to
97.8 % by adding semisynthetic images [R18]. Three simulators take three routes: S3Simulator
renders 3-D models in Gazebo with optical lighting, a linear range gradient and a masked
nadir, and reports +3–6 % accuracy on real data when synthetic images are added to training
[R22]; STARS ray-traces in Blender with a sonar equation `RI = SL − 2TL + TS`, composites
fractured ship meshes onto real terrain, and reaches 0.42 IoU zero-shot on real Thunder Bay
data against 0.35 for the best baseline [R23]; ACOUSIM validates synthetic images against
KLSG-II and SCTD with KL/JS/EMD distances on intensity and LBP histograms (texture KL <
0.07, ship-class intensity KL up to 0.92) but models image formation as illumination ×
reflectance plus Gaussian and multiplicative noise, with no acoustic propagation, TVG or
grazing-angle term [R24, §3]. STARS itself identifies physical degradation and appearance
variance as the gap sources and does not model speckle or TVG [R23].

### 1.5 Surface-vehicle deployment

CORAL is the closest platform precedent: a 1.84 m catamaran with a 450 kHz Starfish 452F
(0.8° beam) on a pole 20–40 cm below the surface and an SBG Ellipse INS, surveying a harbour
of 4–12 m depth with 25–45 m swaths at 10–15 cm/px mosaic resolution, processed in CARIS
with beam-pattern correction and operator-adjusted gain and palette; 1 m concrete cubes and
a mooring chain were resolved; automatic detection and any closed loop are absent [R25].
Kim & Ryou show the wave-induced distortion of a USV-carried side-scan and its correction
[R8]. Grządziel's hull-mounted versus towed comparison explains why a surface-mounted
sonar loses resolving power and shadow length in shallow water [R7]. The standards' towfish
height rule (8–20 % of range scale [R12]) cannot be met by a surface vehicle in shallow
water at the ranges this project uses, which is the regime `project_synthesis.md` §2 builds
on.

### 1.6 Vendor documentation (Cerulean, non-peer-reviewed)

SonarView documents Contrast, Brightness, Heading Up, 3D, Waterfall, Depth Compensation and
a colour picker; it documents no TVG, no speed correction, no scale control and no
port/starboard swap [V1]. Device controls are Gain/Auto Gain (auto recommended), Range,
Pulse Length and Profile Resolution [V2]. The transducer angle is a *mounting* angle,
"+90 starboard, −90 port", and multiple Omniscans need a `config.json`; if a MAVLink
vehicle is connected "the vehicle's heading sensor data will be used", otherwise the
Omniscan's IMU angle must be specified (for the SS model, the electronics module's own
angle) [V3, V4]. The API describes `pwr_results` as "power results scaled from
min_pwr_db to max_pwr_db", in dB "to keep high dynamic range in the u16 sized data
elements", "normally converted back to linear power" [V5]. The BlueBoat guide sets port
`.92` to −90 and starboard `.93` to +90 and says the default Contrast and Brightness "work
well in most situations" [V7].

---

## Part 2 — What the repository currently does

**Acquisition** (`BlueBoat-SSS/blueboat_sss/src/sss_node.py`, VERIFIED). Two Omniscan 450
units are driven over TCP; one `control_os_ping_params` call sets range, rate, pulse
length, filter duration, gain index and bin count (:196-205). Every `OmniscanProfile` field
is a verbatim copy of the device packet (:299-322); `transducer_heading_deg` and
`vehicle_heading_deg` are device fields (:318-319) and the latter is read by nothing
downstream. The raw framed packet is republished unchanged (:324-329).

**Processing** (`BlueBoat-SSS/blueboat_sss/src/sss_processor_node.py`, VERIFIED).
Per ping: `scale_to_db` inverts the device packing as `min + raw/65535·(max − min)` per
ping and side (`BlueBoat-SSS/blueboat_sss/src/_custom_libraries/sss_helper.py:32-43`);
an FBR threshold tracker (noise window 20 samples, +8 dB, persistence 3, ringing search
60 samples, :130-138) fused as the max of locked sides; `project_side` projects to ground
range with the water column removed (`sss_helper.py:142-199`); the pose is the nearest
`/blueboat/odom` sample within 1 s (`sss_processor_node.py:201-255`); rows are assembled on the
offset-normalised ping counter with a counter-restart re-base (`sss_processor_node.py:170-196,
755-874`). **No TVG, gain
normalisation or radiometric correction exists in the processor.** `water_depth` is the FBR
slant altitude plus a 0.0 m submersion placeholder (`sss_processor_node.py:975, 121-124`).

**Side identity** (VERIFIED). `_src_from_packet` reads `channel_number` at frame byte 34
and, when it is not 0/1, the sign of `transducer_heading_deg` at byte 52 if non-zero, else
the arrival topic (`sss_processor_node.py:696-715`); `_channel_of` applies the same rule without the
non-zero guard (`sss_processor_node.py:877-900`); the GCS replay `side_of` matches `_channel_of`
(`BlueBoat-SSS/blueboat_sss/blueboat_gcs/core/svlog.py:206-216`). The `.svlog` `src`
byte is written from that rule (`sss_processor_node.py:717-727`) and never read back.

**`.svlog`** (`BlueBoat-SSS/blueboat_sss/src/_custom_libraries/svlog_helper.py`, VERIFIED).
Session JSON with hard-coded `transducer_deg ±90` per device id (`svlog_helper.py:164, 176`);
id-12 view config is declared (`svlog_helper.py:53`) but never written by us and never parsed; SonarLink writes it (Part 3.2).

**GCS live and replay paths** (VERIFIED). Live rows attach the raw profile bins by device
ping number (`BlueBoat-SSS/blueboat_sss/blueboat_gcs/core/live_native.py:130-174`); replay
decodes the same bins from the file (`core/svlog.py:952-1020`). Both convert with the
per-ping endpoints; neither uses `gain_index` or `analog_gain` anywhere (the comment at
`BlueBoat-SSS/blueboat_sss/blueboat_gcs/models/sonar.py:102-104` describes a gain-break
intent that is not implemented).

**Display model** (`BlueBoat-SSS/blueboat_sss/blueboat_gcs/core/display_model.py`,
VERIFIED). `e = db + TL(r) − A_side(r/h)` with `TL = 40·log10 r + 0.2·r` (:141-145), `A` the
per-bin mode tied to a consensus line (:502-574), `hi` the 95th percentile of seabed `e`
(:576-599), and `u = 10^(γ(e − hi)/10)` with a soft knee at 0.7 and no low handle (:262-275).
Defaults `γ = 0.7`, `hi_pct = 95`, `knee = 0.7`, `warmup_rows = 300`
(`BlueBoat-SSS/blueboat_sss/blueboat_gcs/config/default.yaml:72-81`).

**Waterfall** (VERIFIED). Column pitch is `length_mm/(num_results − 1)`
(`models/sonar.py:164`); the row pitch is the median of the last ≤ 256 consecutive
*pose displacements* (`BlueBoat-SSS/blueboat_sss/blueboat_gcs/core/waterfall_service.py:179,
370-373, 232-237`); the view applies `aspect = clamp(row_pitch/col_pitch, 0.05, 20)` as a
`QTransform` with smooth pixmap transformation, so the vertical stretch is bilinear at
render time (`BlueBoat-SSS/blueboat_sss/blueboat_gcs/gui/waterfall_view.py:79, 149-167,
265`); "True scale" defaults on (:94, :131-132). A stationary boat (median 0) silently
yields aspect 1.0; a NaN median yields 20.0.

**Seabed pictures** (`BlueBoat-SSS/blueboat_sss/blueboat_gcs/core/seabed_imager.py`,
VERIFIED). `row_geometry: square` (`config/default.yaml:106`): one picture row per bin
pitch of along-track distance, nearest ping copied verbatim, so pings are duplicated when
slow and skipped when fast (`seabed_imager.py:534-566`); the along-track distance is the
cumulative sum of pose displacements (`seabed_imager.py:427-434`). Pixels go through the model's own `γ = 0.7` and are rounded
to 8-bit grayscale (`display_model.py:277-283`); no smoothing anywhere.

**A start-up ordering defect (VERIFIED).** `RightPanel` emits its initial display
settings while being constructed (`BlueBoat-SSS/blueboat_sss/blueboat_gcs/gui/right_panel.py:287`),
before the window connects the signal (`gui/main_window.py:152` constructs, `:265`
connects). `DisplaySettings.gamma` defaults to 1.0 (`mapping/renderer.py:88`) and the
waterfall tile renderer uses that value (`core/waterfall_service.py:634-642`). Until a
display control is touched, the on-screen waterfall and mosaic render at **γ = 1.0** while
the Contrast slider reads 0.70 and the seabed PNGs use 0.7.

**Simulator interface** (`BlueBoat-SSS-Sim/blueboat_sss_sim/blueboat_sss_sim/sonar/encoder.py`,
VERIFIED). The simulator encodes `transducer_heading_deg = (vehicle_heading ∓ 90) mod 360`
(:168-169), an absolute bearing in [0, 360), and documents it so
(`BlueBoat-SSS-Sim/blueboat_sss_sim/docs/topics.md:101-102`). The real device writes a
constant ±90 (Part 3.6).

---

## Part 3 — The six field observations

### 3.1 Waterfall vertical scale

**Observation.** Horizontal stretch looks right; vertical scale does not match SonarView.

**Measurement on the screenshot** (MEASURED, `screenshot.py`). Panels: SonarView 552 × 582
px (H/W 1.05), ours 620 × 467 px (H/W 0.75). A RANSAC affine fit on 14 SIFT inliers between
the panels gives `s_x = 1.13, s_y = 0.81`, i.e. **our panel is vertically compressed to
0.71 of SonarView's height at equal horizontal scale**, with negligible shear.

**Measurement on real logs** (MEASURED, `scale_and_tone.py`). On the 7.6 Hz Cerulean
harbour log the estimator behaves: rolling-256 median displacement 135 mm/ping against
130 mm/ping from ground speed, aspect 1.70 versus 1.63 expected. On the 20 Hz
SonarLink-recorded `diffDepthCompensation.svlog` it does not: **18.2 % of consecutive ping
poses are identical** (the replay captures the latest pose at each ping, and at 20 Hz
pings often share a pose sample), the per-ping displacement median is 35 mm against 44–45
mm/ping from both a 10 s pose window and `VFR_HUD` ground speed, and **25.7 % of the
rolling windows have median 0**, which the view turns into aspect 1.0 by the stationary
guard. The reported aspect is p50 0.99 (p10 0, p90 1.50) against 1.31 expected: at the
project's own 20 Hz setting the vertical scale is under-estimated by about a quarter and
jumps between regimes. The live path takes its poses from the processor's odom snap at
ping rate, so the same estimator sees odom jitter instead of repeated samples; the sign of
the bias then depends on odom noise, and it was not measurable here (no live odom
recording). The seabed pictures use a *different* estimator of the same quantity, the
cumulative sum of the same displacements (`seabed_imager.py:427-434`), which zeros do not
bias but rectified noise inflates.

**SonarView side.** No scale or speed-correction control is documented [V1]. The panel's
aspect cannot be attributed to a rule from the evidence here (UNCERTAIN).

**Literature.** Along-track scale in a stacked waterfall depends on speed and ping rate
[R7, R10]; equal ground spacing across-track is the representation that makes features
the same size regardless of range [R2]; standards express the requirement as pings per
target, not pixels [R12]. Nothing read prescribes a display toggle. The literature
therefore supports one geometrically correct behaviour and is silent on offering the
uncorrected one.

**Answer.** The visible mismatch is explained by the row-pitch estimator, not by the
existence of the toggle: at 20 Hz the median-of-displacements estimator is biased low and
intermittently disabled by its own zero guard. Whether SonarView's rule is "true scale" is
UNCERTAIN.

### 3.2 Default contrast

**Ours** (VERIFIED, MEASURED). With the shipped `γ = 0.7`, `hi = p95` and no low handle, the
seabed of two real logs renders at median brightness 0.12–0.20 with 12–20 % of seabed
samples black (u ≤ 0.03) and a coefficient of variation of 0.93–1.16; at the γ = 1.0 the
screen actually uses at start-up (Part 2), median 0.05–0.10, 27–40 % black, CV 1.25–1.58
(`scale_and_tone.py`, table (iv), `fullHarbourCleanExample.svlog` and
`diffDepthCompensation.svlog`).

**SonarView's recorded state** (MEASURED, read-only dump of the id-12 packet SonarLink
writes into its own logs; semantics UNCERTAIN because [V1] documents none):
`{"gamma": 0.2, "signal_range_min": 0.08, "signal_range_max": 0.85, "render_priority":
"closest"}` on the July log and `gamma 0.2, signal_range_min 0.305, signal_range_max
0.85` on a September log. The `signal_range` values lie on the [0, 1] scale of the
per-ping `pwr_results/65535`, which is linear in dB between each ping's own `min_pwr_db`
and `max_pwr_db` [V5]. Applying that window to the same two logs gives, under the plain
linear reading, seabed median 0.43–0.76, 0.4–1.4 % black and CV 0.30–0.57; under `u^0.2`,
median 0.84–0.95 and 12–21 % saturated; under `u^5`, dark. The screenshot's SonarView
panel has median 0.43 (110/255), 3.5 % black and seabed CV 0.20, closest to the
window-only reading; ours has median 0.20, 11.6 % black and CV 0.65. Whatever `gamma
0.2` means, every reading of SonarView's window renders the seabed brighter and with
less relative spread than our default, and the difference is largest at the γ = 1.0
start-up state.

**Gain steps** (MEASURED). On the harbour log the device changed `gain_index` 30 times
and the mean `max_pwr_db` moves from 59.1 (index 4) to 67.8–68.6 (indices 5–7): the
absolute dB scale steps by about 9 dB with the gain ladder, our single mission-wide
`A`/`hi` does not compensate, and SonarView's per-ping window is immune by construction.
Unrecorded gain changes are exactly what [R4] and [R5] report as breaking fixed-threshold
processing.

**Literature.** No source read prescribes a display exponent. Practice is operator-adjusted
gain and palette per track after TVG/beam-pattern correction [R25], or vendor
normalisation plus TVG before export to a detector [R16]; single-look backscatter spans
20 dB and is averaged for "crisp-looking" mosaics [R11]. The literature does not establish a
right default; the comparison with SonarView does establish that ours is markedly darker
and harsher.

### 3.3 Path display

Code evidence only (VERIFIED by reading; no field reproduction available):

- The executed track is drawn from 5 Hz `RobotState`
  (`BlueBoat-SSS/blueboat_sss/blueboat_gcs/ros/telemetry_listener.py:49, 194-196`) into
  an uncapped `QPainterPath` (`gui/map_layers.py:163, 193-202`); it starts a new segment on
  every START (`gui/main_window.py:702`), after 3 s without telemetry (:539-540), and on any
  pose jump > 5 m (`gui/map_layers.py:187-192`), which fires on the odom ⇄ GPS
  dead-reckoning hand-off because the two sources have different origins
  (`telemetry_listener.py:153, 185-192`). Nothing is drawn until the GPS anchor is valid
  (`gui/map_layers.py:90`, `core/geo_service.py:114-116`), and there is no auto-follow
  (`gui/map_view.py:137-141`), so a track that leaves the viewport is simply off-screen.
- The planned path is deduplicated by `(len, first, last)`
  (`ros/path_listener.py:30-41`): a re-planned mission with the same pose count and end
  points is never displayed. `PlannedPathLayer.clear()` does not reset that fingerprint
  (`gui/main_window.py:579-581` versus `ros/path_listener.py:49, 58-62`), so "Clear
  currently displayed data" removes the 1 Hz-resent planned path until the app restarts or
  the path changes shape.
- `boat_trajectory.csv` is written from the ~20 Hz ping poses, not from the on-screen
  track (`core/mosaic_service.py:341, 473-477`); the two legitimately differ.

The literature has nothing to say about this; it is an application-state question.

### 3.4 Performance

**Measured** (`ping_bench`, repo tool, 4000 pings with turns): ingest 0.87 ms/ping; mosaic
render 3.0 ms per pass (max 44); waterfall 18.8 ms per pass (max 49) against the tool's own
≤ 15 ms target (`BlueBoat-SSS/blueboat_sss/blueboat_gcs/analysis/ping_bench.py:14-15`); RSS
509 MB. Micro-benchmarks (`perf.py`, offscreen Qt): re-stroking the uncapped trajectory
path costs only 0.1–3.6 ms per full-viewport antialiased repaint for 1 000–60 000
vertices, so the unbounded track is **not** a material cost; exporting the waterfall
buffer alone takes 2.5 s at 20 000 rows and 7.4 s at 60 000 rows × 1200 bins
(`np.savez_compressed`), before the mosaic planes, PNGs and the CSV loop that run in the
same synchronous `RecordingManager.end()` (`core/recording_session.py:180-183`,
`core/waterfall_service.py:519-524, 563-581`). That matches the reported multi-second
freeze on Record OFF / STOP.

**Where the live load plausibly goes** (VERIFIED code paths; attribution not profiled in
the running app, so UNCERTAIN in proportion): the 4 Hz waterfall pass at 18.8 ms; the 2 Hz
mosaic pass whose "sliver" branch still renders the whole decimated grid before slicing
(`core/mosaic_service.py:426, 428`); an unconditional `detections_updated.emit` on every
waterfall pass that repaints the whole waterfall at 4 Hz with nothing new
(`core/waterfall_service.py:722`); `FullViewportUpdate` with antialiasing on the map view
(`gui/map_view.py:60-62`) with ~15 mutations per second; the display-model histogram
`bincount` on every ping until the model freezes (`core/display_model.py:440-472`); a
`time.sleep(0.5)` on the GUI thread in the leftover sweep (`ros/pipeline_launcher.py:312`);
tile PNG decode and write on the GUI thread while panning (`mapping/tiles.py:104-110,
134`). The mosaic display path has no debounce and its cache key uses `id(settings)`, so a
slider drag re-renders the full raster per tick (`core/mosaic_service.py:373-378, 409`).

### 3.5 Noise character

**Measurement.** On homogeneous seabed patches the screenshot gives CV 0.20 for SonarView
and 0.65 for ours, with a row/column correlation length of about 1 px in both
(`screenshot.py`): ours is **grainier, not smoother**, and the graininess is not a
resolution or smoothing difference. On real logs the seabed residual about the model curve
has a standard deviation of 8.8–10.2 dB (`scale_and_tone.py`), heavier than the 5.57 dB of
pure Rayleigh speckle, as [R11] leads one to expect for a real seafloor with shadows.

**Cause.** Neither product applies a spatial filter: ours is verified (no resize, blur or
row averaging anywhere in the picture path; the vertical stretch is a render-time
transform), SonarView's is undocumented. The difference is the transfer: a power law on
range-normalised level with `γ = 0.7` (or 1.0 at start-up) keeps most of the multiplicative
speckle variance (CV 0.9–1.6 on the real logs), while a window on the dB-linear per-ping
counts, which is what SonarView's recorded state describes, compresses it (CV 0.3–0.6).
The 5.57 dB result says the same thing: in decibels speckle has a bounded spread; in
linear power its CV is 1.

**Literature.** Despeckling is a low-pass trade against edges [R6]; averaging over
independent looks is how crisp mosaics are made [R11]; detectors in the papers read are
trained on unfiltered speckle after TVG/normalisation [R16, R27]. The project's decision
not to despeckle the detector feed is supported; the tone mapping, not the data, is what
makes our picture look noisier.

### 3.6 Port/starboard inversion in SonarView

**Mechanism found** (VERIFIED, MEASURED). The screenshot is from a simulator-recorded
session. The simulator writes `transducer_heading_deg` as an absolute bearing,
`(vehicle_heading ∓ 90) mod 360` (`encoder.py:168-169`), while the real device writes a
constant ±90 on 100 % of packets in every one of the 16 SonarLink logs and all three of
our own recordings that carry the field (`side_identity.py`), and Cerulean defines the
transducer angle as a mounting angle in the vehicle frame [V3, V7]. Simulating the side
rules on the simulator's encoding (`side_identity.py`): a "wrap to ±180 then sign"
mounting-angle reading misroutes **both sides for every compass heading between 90° and
270°**, i.e. one block of pings for each southerly leg — the pattern in the screenshot;
our `channel_number` routing is unaffected, which is why our panel is right. SonarView's
internal rule is undocumented, so the attribution is a strong inference, not a proof
(UNCERTAIN in that one respect). This is also a real-versus-sim interface divergence in a
field SonarView consumes, contrary to the identical-interface rule (CM-2).

**Could it happen to us?** Yes, conditionally. Our fallback uses the *unwrapped* sign,
`heading > 0` (`sss_processor_node.py:713-714, 889`; `core/svlog.py:215`): on the
simulator's [0, 360) encoding that is true for every ping, so a simulator packet with an
invalid `channel_number` would resolve to starboard at every heading but 90°. It is not
exercised today because the simulator always writes a valid channel. On the real device
the fallback is exact, but it was needed: `reflectionEvidenceFullharbour.svlog` carries
`channel_number = 255` on all 13 027 packets (MEASURED). Two further real risks: a
heading of exactly 0.0 sends `_src_from_packet` to the arrival topic but `_channel_of` to
port (`sss_processor_node.py:713-714` versus `sss_processor_node.py:889`), so the `.svlog` `src`
byte and the published row can disagree; and `vehicle_heading_deg` is carried end to end and read by nothing.

**On SonarView's own data.** With a constant ±90 and heading from MAVLink, the
mounting-angle rule cannot invert; the only documented alternative heading source is the
Omniscan IMU when no vehicle is connected [V3], which would affect the mosaic, not the
waterfall. Not testable here (no SonarView; UNCERTAIN). Our three July recordings carry a
wrong `src` byte on 10.6–19.8 % of packets (MEASURED, pre-patch); a viewer routing by
device id would mirror those runs, which is the earlier "banded" symptom, and is
unrelated to the simulator mechanism above.

---

## Part 4 — Gap analysis

| # | Topic | Ours | Literature / standard | Verdict |
|---|---|---|---|---|
| G1 | Along-track scale of the on-screen waterfall | Median of 256 pose displacements; at 20 Hz biased −24 % and zeroed in 26 % of windows (3.1) | Along-track scale is speed × ping period [R7, R10]; equal-spacing representations are the canonical form [R2] | **Gap**: estimator, not principle |
| G2 | Two estimators of along-track distance (median for the view, cumulative sum for the pictures) | Differ in bias direction (3.1) | One geometry per product is implied by [R2, R16] | Gap (consistency) |
| G3 | Default tone mapping | γ 0.7 power law, p95 top, no low handle; 12–20 % seabed black; on screen γ 1.0 at start-up (3.2) | No prescribed exponent; practice is normalisation + TVG then operator gain [R16, R25]; SonarView's recorded window is dB-linear | **Gap** relative to the reference viewer; literature silent on a "right" value |
| G4 | Start-up display settings | Initial emission dropped; screen ≠ config ≠ PNG (Part 2) | — | Gap (defect) |
| G5 | Device gain steps | Uncompensated in a mission-wide model; ~9 dB steps measured (3.2) | Unknown gain changes break fixed references [R4, R5]; settings changes leave artefacts [R11] | Gap |
| G6 | Range/angle normalisation | Physical TL + empirical per-side curve, mode-based, altitude-invariant (Part 2) | Same family as [R3, R2]; `cos²`-type angular term supported [R2]; digital TVG is cosmetic but standard [R11] | No gap in principle |
| G7 | Despeckling of the detector feed | None (Part 2) | Filters trade edges [R6]; detectors trained on unfiltered speckle [R16, R27] | No gap |
| G8 | Bottom tracking | Fixed thresholds in samples, +8 dB, symmetric max fusion; a 60-sample ringing horizon that scales with range (`SONARVIEW_SVLOG_ANALYSIS.md` §4) | Fixed thresholds fail on gain changes, turbidity, water-column echoes [R4, R5]; symmetry and neighbour interpolation recommended [R5] | Gap (robustness), not measured here |
| G9 | Side identity: sim vs device encoding of `transducer_heading_deg` | Absolute bearing vs constant mounting angle (3.6) | Vendor semantics = mounting angle [V3] | **Gap** (CM-2) |
| G10 | Side-identity fallback | Unwrapped sign; heading-0 asymmetry; `vehicle_heading_deg` unused (3.6) | — | Gap (latent) |
| G11 | Pixel anisotropy of AI pictures | Square by nearest-ping copy (Part 2) | AI4Shipwrecks trains on 12:1 anisotropic pixels with no speed correction [R16]; [R2] argues for equal spacing | Literature does not settle it; ours is defensible and reversible |
| G12 | Slant-range vs ground-range domain for the detector | Slant (native bins), water column kept | [R16] trains in slant domain; [R2] and [R1] correct to ground for matching/mapping | Literature split; no gap for detection |
| G13 | Record OFF freeze | Synchronous multi-second exports (3.4) | — | Gap (operational) |
| G14 | Planned-path dedupe and clear | Drops re-plans; clear is permanent (3.3) | — | Gap (defect) |
| G15 | Coverage/along-track requirement | 20 Hz at ≤ 1 m/s gives ≥ 20 pings per metre (Part 2 corpus) | ≥ 3 ensonifications per 1 m target [R12] | No gap |

---

## Part 5 — What should change, and why it matters here

These are recommendations for a planning pass, not an implementation plan.

1. **Derive the waterfall's row pitch from speed and ping period, not from a median of
   raw pose deltas** (G1, G2), and use the same along-track estimate for the seabed
   pictures. Why here: the detector is trained on pictures whose along-track geometry is
   this estimate (CM-10); a 24 % scale bias at the project's standard 20 Hz setting, and
   two products disagreeing on the same quantity, put object aspect ratio — the feature
   the aspect-response experiment (`project_synthesis.md` §7.2) depends on — into the
   pipeline rather than into the measurement. Once the estimate is robust, the "True
   scale" toggle has no remaining justification; the evidence supports one behaviour.

2. **Reconcile the display transfer with the reference viewer before the detector
   dataset is frozen** (G3, G4): fix the start-up ordering so screen, slider and PNG agree,
   then decide the default with SonarView's recorded window and the measured seabed
   statistics on the table rather than by eye. Why here: E1 in the evidence architecture
   calibrates simulator appearance on per-range intensity and speckle statistics of the
   July logs; the tone mapping is what the operator and the labeller see, and a 12–20 %
   black seabed fraction at default hides exactly the weak highlights the shadow-starved
   regime relies on (`project_synthesis.md` §2). The literature offers no exponent to
   copy; the decision needs the project's own measurement.

3. **Account for device gain steps in the display model** (G5). Why here: the harbour logs
   change gain 8–30 times per mission and step the absolute scale by ~9 dB; a
   mission-wide window then renders the same seabed at different brightness before and
   after a step, which a detector will learn as texture.

4. **Make the simulator encode `transducer_heading_deg` as the device does** (G9) and
   **harden the fallback** (G10): wrap before taking the sign, resolve the heading-0
   asymmetry one way, and either use or drop `vehicle_heading_deg`. Why here: CM-2 is the
   premise of the sim-to-real comparison, SonarView is the reference viewer the thesis
   compares against, and the field already produced a whole recording with
   `channel_number = 255` on every packet, so the fallback is not hypothetical.

5. **Move the recording export off the GUI thread or stage it** (G13). Why here: field
   time is the scarcest resource (CM-14); a multi-second freeze at Record OFF during a
   controlled aspect-response pass is where a run gets lost.

6. **Reset the planned-path fingerprint on clear and fingerprint the whole path** (G14).
   Why here: the closed-loop demonstration (E6) replans mid-mission; a re-planned path
   with the same endpoints being silently ignored on the operator's screen defeats the
   supervision the station exists for.

7. **Keep the no-despeckle and native-slant-bin decisions** (G7, G12); they are supported.
   Record in the dataset metadata that pictures are square-pixel by nearest-ping copy so a
   later comparison with anisotropic training (as in [R16]) is possible without
   re-recording.

8. **Before the next field session, record at least one mission with our own stack after
   the side-identity patch.** Why here: every field log on this machine after July was
   written by SonarLink, so the processor's `src` byte, counter-offset handling and
   one-sided-row behaviour have been verified in replay only; `SONARVIEW_SVLOG_ANALYSIS.md`
   §10 still lists this as open.

9. **Obtain the paywalled classics** (Blondel; Capus; Cobra; Johnson & Helferty; Abraham &
   Lyons; Reed) before the thesis text cites them. This review could not verify them and
   does not cite them; `SCIENTIFIC_BACKGROUND.md` cites them from Crossref resolution only.

---

## Appendix — scripts, outputs, reproduction

Scratchpad: `/tmp/claude-1000/-home-kyyrron-ros2-ws-src-BlueBoat-SideScanSonar-BlueBoat-SSS/df991daa-6ae8-4b25-af13-1ca535500b67/scratchpad/review/`

| Script | Inputs (read-only) | Output |
|---|---|---|
| `side_identity.py` | all 19 local `.svlog` | `out/side_identity.md` — recorder census, field statistics, side-rule simulation |
| `screenshot.py` | `~/Desktop/us_vs_sonarview_noise.png` | `out/screenshot.md`, panel and patch crops — scale ratio, tone, texture |
| `scale_and_tone.py` | `fullHarbourCleanExample.svlog`, `diffDepthCompensation.svlog` via `blueboat_gcs.core.svlog.load_svlog` and `DisplayModel.fit` | `out/scale_and_tone.md` — row pitch, residual, tone tables, gain steps |
| `perf.py` | synthetic | `out/perf.md` — path repaint and export timings |
| repo `python3 -m blueboat_gcs.analysis.ping_bench --pings 4000 --turn` | synthetic | ingest/render numbers quoted in 3.4 |
| `pdf/` | downloaded open-access PDFs and text conversions | reading record for Part 1 (`lit_ledger.md`) |

Every measurement re-runs from `BlueBoat-SSS/blueboat_sss/` with `QT_QPA_PLATFORM=offscreen`
and the default GCS configuration; no log was modified (CM-7) and no session folder was
created.

---

## Addendum (2026-09-15) — what was implemented from this review

The update decided on the day after this review (user decisions: add a dB-window transfer
but keep the power law as the default; compensate gain steps by `20·log10(analog_gain /
74.55)`; estimate along-track from ground speed over a ~5 s window × ping period; include
the GCS render-load items and the launch guard; no Aug Studio code change) landed in
`BlueBoat-SSS` and `BlueBoat-SSS-Sim`, each module in its own tree, no commits:

| Gap | Change | Evidence after the change |
|---|---|---|
| G1/G2 (3.1) | `blueboat_gcs/core/along_track.py`, one estimator shared by the waterfall (true-scale rows) and the seabed imager (square rows) | `diffDepthCompensation.svlog`: median pitch / (10 s-chord speed × PRI) = 1.000, 0 % zero windows (previous rule: 19 % zero windows); integrated along-track 100.9 m vs 101.8 m from 1 s chords |
| G3 (3.2/3.5) | `display.transfer: power \| db_window`, `window_db`; the JSON `mapping` documents both inverses | `tests/test_display_model.py`, `test_seabed_pictures.py` (picture == waterfall under both) |
| G4 (Part 2) | services seeded from `display.gamma`; `RightPanel.emit_display()` re-emitted after wiring in both windows | `tests/test_display_startup.py`; `metadata.json.display_settings_at_end` no longer null (`test_sim_session.py`) |
| G5 (3.2) | per-ping, per-side `analog_gain` carried live and on replay; `e = db + TL − A − g`; `row_gain_db` in every npz, `gain_*_db` per row in the JSON | `test_display_model.py` (+5.65 dB row normalises to its twin within 1e-3 dB and inverts), `test_live_native.py`, `test_svlog_replay.py` |
| G9 (3.6) | simulator encodes `transducer_heading_deg = ∓90` (device convention); its reader, bathymetry and contacts consumers updated; smoke gates `[2]`/`[4c]` | `python3 -m test.smoke_test`: ALL CHECKS PASSED (392 backscatter samples: 196 left / 196 right / 0 off-beam) |
| G10 (3.6) | one wrapped-sign side rule (`sss_helper.side_from_fields`, `core/svlog.resolve_side`, `core/live_native.resolve_side_of_profile`, sim `_side_from_packet`); unresolved bearing → arrival topic on both processor paths, counted; GCS counts `unresolved_side` | `test_processor_assembly.py` (255/270/0 cases, raw and message paths agree), `test_svlog_forensics.py`, root `CLAUDE.md` §4.6 |
| G13 (3.4) | `RecordingManager.end()` snapshots and writes `mosaic/` + `waterfall/` on the thread pool; `wait_for_exports()` at close | `test_recording_guards.py::test_end_returns_before_the_exports_finish` (end() < 0.5 s with 0.6 s writers) |
| G14 (3.3) | planned path compared on the full point tuple; `reset()` reachable from "clear overlays" | `test_planned_path_dedupe.py` (changed interior forwarded; < 50 ms per 4 700-pose re-send) |
| 3.4 render load | detections overlay emitted only when it changes; mosaic display debounced (120 ms), cache keyed by value | `test_gcs_throughput.py`; `ping_bench --pings 4000 --turn` same day, same machine: HEAD 1.15 ms ingest / 3.4 mosaic / 25.2 waterfall → 1.18 / 3.5 / 25.8 |
| backlog drift | `SSS_processing_launch.py` nested launch-time groups | launch description evaluated under all four flag combinations: `with_acquisition:=True` → both nodes, `will_use_rosbag` overrides |

Gates after the change: BlueBoat-SSS `pytest` 273 passed / 50 skipped (323 collected, corpus
gates skipped); simulator smoke test ALL CHECKS PASSED (2 m 19 s). Still open, recorded in
`BlueBoat-SSS/.claude/TODO.md`: the default transfer awaits a paired SonarView comparison on
real data; no post-patch recording by our own stack exists yet. The Aug Studio's two items
(G12, and its demo-fixture script) are recorded in its `TODO.md` without a code change.
