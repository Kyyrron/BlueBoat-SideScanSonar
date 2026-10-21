# Simulator review — `BlueBoat-SSS-Sim` against the real Omniscan 450 pipeline

> **Superseded in part since 2026-10-20** (dated review, not rewritten): where it assumes a detector trained on real beach imagery, 30 m coverage / 15 m revisit passes, a "MAVLink mission swap", or a publication plan, the owner's decisions of 2026-10-20 apply — see the revision note of `project_synthesis.md`.

*Review only, 2026-09-17 (finished 2026-09-18). No simulator or GCS code was changed. The only edits
outside this file are the three `CLAUDE.md` notes recording the `v1.0` freeze of
`BlueBoat-Control` and `BlueBoat-MCS` (Part 3.2). Every repository claim carries a `path:line`
(paths relative to the superproject root, line numbers harvested on 2026-09-17 by
`scripts/cite.sh` → `out/citations.txt`); every literature claim carries a numbered reference
from the list below; every measured number names the script and the output file that produced
it. The evidence root is `~/ros2_ws/sim_review_work/` (scripts, outputs, reading extracts).*

**Markers.** VERIFIED = read in the named file or paper. MEASURED = computed by a named script
on a named log, world folder or render, reproducible from the evidence root. UNCERTAIN =
contested, undocumented, or not establishable on this machine.

**Reading and evidence discipline.** Every source in list A was read in full for this pass
(PDF text with equations checked on rendered page images; the two long books chapter-wise,
with the chapters read named per entry; open-access articles section by section through
their HTML or XML full text). Nothing from list B is cited in Parts 1–5. Field recordings,
world folders and GCS sessions were read only; all outputs went to the evidence root. The
session scratchpad was wiped twice between sessions, so the evidence root is a persistent
mirror rather than the scratchpad named in the approved plan.

**Evidence base on this machine.**

| Item | What it is |
|---|---|
| `~/ros2_ws/data/SSS_data/beach_sept/bath1..3.svlog` | Real beach survey, 2026-09-07, 20 m / 600 bins, SonarLink-written; `bath3` is the twin of the simulated mission |
| `beach_sept/object_boiteVsDistance.svlog`, `object_boiteEncore.svlog` | Real passes over the NAFCO container (Part 3.6), 15–40 m / 1200 bins, range changed live |
| `sessions/full_beach_sim/2026-09-17-11-50-46.svlog` (+ `waterfall/`, `metadata.json`) | Simulator run of the same mission (`.deployed/plage_bathymetry2.yaml`, 1317.6 s, loop) over world `~/worlds/plage_bathymetry2/plage_test`; source of `see_throught_walls.png` |
| `sessions/2026_09_17-11_27_57/2026-09-17-11-27-57.svlog` | Simulator run with three hand-placed `mesh_crate` objects, ranges 36 / 20 / 15 m; source of `mesh_container_sim_perfect_shadow.png` |
| `~/worlds/plage_bathymetry2/plage_test/` | World built from `bath1_2_3.svlog` (recording mode, relief `synthetic`, 33 quay chords, 3 `mesh_crate`) |
| `~/Desktop/*.png` (4 screenshots) | The user's field/sim comparison pictures |
| `~/Downloads/research_paper/*.pdf` (12 PDFs) | Sources for list A read from PDF |

---

## References

### A. Read in full for this review (cited in Parts 1–5)

Format: authors (year). Title. Venue vol(issue):pages. DOI — access route; sections read.

- [R1] Jackson, D. R., Richardson, M. D. (2007). *High-Frequency Seafloor Acoustics*. Springer, New York. https://doi.org/10.1007/978-0-387-36945-7 — local PDF (618 pp.); read in full: §2.3, §5.1.3 + Tables 5.1–5.2, §8.4–8.5, ch. 12, §13.1–13.7 (head), ch. 16, App. G.2.2, App. L; other chapters by table of contents only. DOI verified through Crossref (the book prints none).
- [R2] Mackenzie, K. V. (1961). Bottom reverberation for 530- and 1030-cps sound in deep water. *J. Acoust. Soc. Am.* 33(11):1498–1504. https://doi.org/10.1121/1.1908482 — local PDF, read in full. (The DOI first assumed for this paper, 10.1121/1.1908588, resolves to a different article; the DOI above is the Crossref record for this title.)
- [R3] Abraham, D. A., Lyons, A. P. (2002). Novel physical interpretations of K-distributed reverberation. *IEEE J. Ocean. Eng.* 27(4):800–813. https://doi.org/10.1109/JOE.2002.804324 — local PDF, read in full; DOI printed on p. 800.
- [R4] Selfridge, A. R. (1985). Approximate material properties in isotropic materials. *IEEE Trans. Sonics Ultrason.* SU-32(3):381–394. https://doi.org/10.1109/T-SU.1985.31608 — local PDF, read in full (tables from page images).
- [R5] Blondel, P. (2009). *The Handbook of Sidescan Sonar*. Springer-Praxis, Berlin. https://doi.org/10.1007/978-3-540-49886-5 — local PDF (344 pp., text layer unusable, read from page images); read in full: ch. 2, §3.1–3.2, §4.4–4.9, ch. 8, §9.2.2–9.2.4, §9.3.3, §9.4, ch. 10. Page numbers are the printed ones.
- [R6] Coiras, E., Petillot, Y., Lane, D. M. (2007). Multiresolution 3-D reconstruction from side-scan sonar images. *IEEE Trans. Image Process.* 16(2):382–390. https://doi.org/10.1109/TIP.2006.888337 — local PDF, read in full.
- [R7] Bell, J. M., Linnett, L. M. (1997). Simulation and analysis of synthetic sidescan sonar images. *IEE Proc. Radar Sonar Navig.* 144(4):219–226. https://doi.org/10.1049/ip-rsn:19971311 — local PDF, read in full.
- [R8] Bore, N., Folkesson, J. (2021). Modeling and simulation of sidescan using conditional generative adversarial network. *IEEE J. Ocean. Eng.* 46(1):195–205. https://doi.org/10.1109/JOE.2020.2980456 — local PDF (early-access pagination 1–11), read in full.
- [R9] Sung, M., Kim, J., Lee, M., Kim, B., Kim, T., Kim, J., Yu, S.-C. (2020). Realistic sonar image simulation using deep learning for underwater object detection. *Int. J. Control Autom. Syst.* 18(3):523–534. https://doi.org/10.1007/s12555-019-0691-3 — local PDF, read in full. Forward-looking sonar, not side-scan.
- [R10] Cobra, D. T., Oppenheim, A. V., Jaffe, J. S. (1992). Geometric distortions in side-scan sonar images: a procedure for their estimation and correction. *IEEE J. Ocean. Eng.* 17(3):252–268. https://doi.org/10.1109/48.153442 — local PDF, read in full.
- [R11] Cuschieri, J. M., Hebert, M. (1990). Three-dimensional map generation from side-scan sonar images. *J. Energy Resour. Technol.* 112(2):96–102. https://doi.org/10.1115/1.2905729 — local PDF, read in full. (The candidate DOI 10.1115/1.2905717 resolves to another paper.)
- [R12] Potokar, E., Lay, K., Norman, K., Benham, D., Neilsen, T. B., Kaess, M., Mangelson, J. G. (2022). HoloOcean: realistic sonar simulation. *IEEE/RSJ IROS 2022*, pp. 8450–8456. https://doi.org/10.1109/IROS47612.2022.9981119 — author PDF, read in full.
- [R13] Xie, Y., Bore, N., Folkesson, J. (2023). Neural network normal estimation and bathymetry reconstruction from sidescan sonar. *IEEE J. Ocean. Eng.* 48(1):218–232. https://doi.org/10.1109/JOE.2022.3194899 — read in full from arXiv:2206.07819v2.
- [R14] Choi, W.-S., Olson, D. R., Davis, D., Zhang, M., Racson, A., Bingham, B., McCarrin, M., Vogt, C., Herman, J. (2021). Physics-based modelling and simulation of multibeam echosounder perception for autonomous underwater manipulation. *Front. Robot. AI* 8:706646. https://doi.org/10.3389/frobt.2021.706646 — open-access full text, read in full.
- [R15] Choi, W.-S. (2025). Ray-based physical modeling and simulation of multibeam sonar for underwater robotics in ROS-Gazebo framework. *Sensors* 25(5):1516. https://doi.org/10.3390/s25051516 — Europe PMC full text (PMC11902455), read in full.
- [R16] Cerqueira, R., Trocoli, T., Albiez, J., Oliveira, L. (2020). A rasterized ray-tracer pipeline for real-time, multi-device sonar simulation. *Graphical Models* 111:101086. https://doi.org/10.1016/j.gmod.2020.101086 — read in full from arXiv:2001.03539v1.
- [R17] Sethuraman, A. V., Skinner, K. A. (2023). STARS: zero-shot sim-to-real transfer for segmentation of shipwrecks in sonar imagery. arXiv:2310.01667. https://doi.org/10.48550/arXiv.2310.01667 — read in full (main text; supplementary not read).
- [R18] Basha, S. K., Nambiar, A. (2026). Physics-informed simulation framework for realistic sonar image generation and statistical validation (ACOUSIM). arXiv:2605.19712. https://doi.org/10.48550/arXiv.2605.19712 — read in full.
- [R19] Basha, S. K., Nambiar, A. (2024). S3Simulator: a benchmarking side scan sonar simulator dataset for underwater image analysis. arXiv:2408.12833v1. https://doi.org/10.48550/arXiv.2408.12833 — arXiv HTML, read in full. (Its ICPR 2024 proceedings DOI was not verified and is not cited.)
- [R20] Attia, Y., Costa, D., Wanderlingh, F., Campagnaro, F., Simetti, E. (2026). Towards realistic 3D sonar simulation. arXiv:2606.06130v1. https://doi.org/10.48550/arXiv.2606.06130 — arXiv HTML, read in full.
- [R21] Steiniger, Y., Kraus, D., Meisen, T. (2022). Survey on deep learning based computer vision for sonar imagery. *Eng. Appl. Artif. Intell.* 114:105157. https://doi.org/10.1016/j.engappai.2022.105157 — author-deposited PDF, read in full.
- [R22] NOAA Office of Coast Survey (2021). *Hydrographic Surveys Specifications and Deliverables*, April 2021. https://nauticalcharts.noaa.gov/publications/standards-and-requirements.html — PDF (159 pp.); read: §5.2.2 and §6.1 in full, rest grepped. No DOI.
- [R23] Grządziel, A. (2023). The impact of side-scan sonar resolution and acoustic shadow phenomenon on the quality of sonar imagery and data interpretation capabilities. *Remote Sens.* 15(23):5599. https://doi.org/10.3390/rs15235599 — publisher PDF, read in full.
- [R24] Kim, Y., Ryou, J. (2020). A study of sonar image stabilization of unmanned surface vehicle based on motion sensor for inspection of underwater infrastructure. *Remote Sens.* 12(21):3481. https://doi.org/10.3390/rs12213481 — publisher PDF, read in full.
- [R25] Cocchi, L., Muccini, F., Locritani, M., Spinelli, L., Cocco, M. (2024). CORAL — Catamaran for Underwater Exploration: development of a multipurpose unmanned surface vessel for environmental studies. *Sensors* 24(14):4544. https://doi.org/10.3390/s24144544 — Europe PMC full text XML (PMC11280589), main text read in full; supplementary not read.
- [R26] Lurton, X., Lamarche, G. (eds.) (2015). *Backscatter measurements by seafloor-mapping sonars — Guidelines and Recommendations*. GeoHab Backscatter Working Group, 200 pp. https://doi.org/10.5281/zenodo.10089261 — Zenodo web-quality PDF; read: §2.4.4, §2.5.5, §4.2.2 (stage 2), §5.3.1. Cited only for those sections.
- [R27] Fonseca, L., Lurton, X., Fezzani, R., Roche, M. (2025). A simplified semi-empirical model for multifrequency seafloor backscattering angular response (ESAB). *Front. Remote Sens.* https://doi.org/10.3389/frsen.2025.1619218 — open-access HTML, main text read in full; supplementary not read.

**Vendor documentation (not peer-reviewed; fetched 2026-09-17).**

- [V1] Cerulean Sonar, *Omniscan 450 — Specifications*. https://docs.ceruleansonar.com/c/omniscan-450/specifications
- [V2] Cerulean Sonar, *Omniscan 450 — Application programming interface*. https://docs.ceruleansonar.com/c/omniscan-450/application-programming-interface
- [V3] Blue Robotics, *Integrating the Omniscan 450 SS on the BlueBoat*. https://bluerobotics.com/learn/omniscan-450-ss-integration/

### B. Identified, not verified, not cited

Lurton 2010 *An Introduction to Underwater Acoustics* (unavailable); Urick 1983 *Principles of Underwater Sound* (unavailable); Eckart 1953 (JASA); Wagner 1967 (shadowing function, via [R1]); Langer & Hebert 1991 (via [R8]); APL-UW TR 9407 (via [R1]); Fish & Carr 1990 (via [R5]); Johnson & Hebert 1996; Gueriot et al. 2007; Pailhas et al. 2010; Hamilton 1980; Cerqueira et al. 2017 (*Comput. Graph.*); Coiras & Groen 2009, DeMarco et al. 2015, Gwon et al. 2017 (via [R16]); Reed, Petillot & Bell 2003 and Quinn et al. (via [R23]); Zhu et al. 2018, Karjalainen et al. 2019, Li et al. 2021 (via [R21]); the ICPR 2024 proceedings version of [R19]. Where one of these is named in Parts 1–5 it is as "cited by [Rn]", never as a source of its own.

---
## Part 1 — Literature review

### 1.1 Image formation and the backscatter law

**What the physics says.** The seafloor backscattering cross section per unit area, σ, is
dimensionless and its bound is geometric: "the backscattering cross section must approach zero
at least as rapidly as sin² θi" at small grazing angles, and "any measured backscattering
strength that does not fall off rapidly as the grazing angle becomes small should be viewed
with suspicion" [R1, p. 27]. Lambert's rule in the acoustics literature is `σ = μ sin θs sin θi`,
which for backscatter "reduces to the form most common in the ocean acoustics literature,
σ = μ sin² θi" [R1, p. 26, Eq. 2.22]; energy conservation bounds μ < 1/π [R1, Eq. 2.23; R2,
footnote 15]. In incidence-angle form the same law reads `BS = BS0L + 20 log cos θ`, while the
first-power law `BS = BS0LS + 10 log cos θ` is the Lommel–Seeliger law, "a good description
for e.g. coarse-grain seafloors at high frequencies", and the guidelines recommend fitting
`cosⁿ` with n ≥ 1 because "any interface backscatter strength decreases at least by this value"
[R26, §2.4.4, Eqs. 31–32]. Blondel states the same thing for side-scan practice: "The simplest
model is Lambert's law … approximating backscatter as a linear function of the square cosine
of the incidence angle" [R5, p. 18]. VERIFIED in all three.

**Values.** Fitted over grazing angles below 60°, 10 log10 μ is −19.7 dB for mud, −20.2 dB for
sand, −11.7 dB for gravel and −5.6 dB for rock, with a within-class spread of "about ±5–8 dB",
so that "sediment name is not a good predictor of scattering strength" [R1, pp. 323–326].
Frequency trends are roughly +3 dB/decade for mud and +6–8 dB/decade for sand, sparse for
gravel and rock [R1, p. 327]. Mackenzie's original deep-water fit was 10 log μ = −27 dB with a
sin² dependence valid from 90° to about 30° grazing, and "no significant frequency trend …
over the range of more than 7 octaves for these fine grained bottoms" [R2, pp. 1498, 1502,
1504]. The multifrequency ESAB model fitted at 35–440 kHz gives volume parameters of about
−7 dB for sandy mud and medium sand and +0.4 to +4 dB for gravelly mud, maërl and bedrock,
and reports no shadowing treatment [R27, §3, Fig. 8]. Two caveats bind directly on this
project: the data behind the fits "have been edited to remove data at smaller grazing angles,
which may be contaminated by multipath reverberation and therefore biased upward" [R1,
p. 323], and "it is unlikely that the overall accuracy of the most careful measurement of
scattering strength will be better than about 2 dB" [R1, p. 326].

**Near-nadir return.** Roughness scattering "shows a peak near vertical incidence. This is the
remnant of the vertical reflection that would occur if the seafloor were flat" [R1, p. 331]; in
the high-frequency Kirchhoff limit the peak is Gaussian in the angle from vertical with a
width parameter that "should be considered to be a measure of the angular width of the
backscattering cross section peak at vertical incidence" [R1, p. 504, Eq. G.36], and "at high
frequencies, the coherent component … is likely to be negligible" [R1, p. 504]. The guidelines
describe the same echo: amplitude "ramps up quickly after the leading edge of the pulse reaches
the seafloor", then decays "governed by the beam pattern … and by the angular response of the
seabed" [R26, §2.5.5]. Blondel's practical statement is that "the irregular band of
high-backscatter points nearest to the ship's track … is explained by a contribution from
near-normal incidence specular and sub-bottom returns, which will only occur within the first
few degrees from nadir" [R5, p. 236].

**How the simulation literature uses "Lambert".** The word carries three different laws.
Coiras uses `I = K Φ R |cos θ|`, first power with an absolute value, and calls it Lambertian
[R6, p. 383, Eq. 1]; Bore & Folkesson feed their network cos²θ because it "better approximates
scattering at low-grazing seafloor angles" while their baseline labelled "Lambertian" is a
first-power cosine plus a specular term [R8, pp. 4–5]; Sung uses cos²α citing a
computer-graphics report [R9, p. 3, Eq. 5]; Choi's point-scattering simulators use
`μ cos²(α)` and say so is "often provides a good fit to seafloor reverberation measurements"
[R14, §2.2, Eq. 6; R15, Eq. 4]; Bell & Linnett use no cosine law at all but Jackson's
bistatic roughness-plus-volume model [R7, p. 221, Eq. 12]. The consequence for this review:
a simulator that writes `ρ · cos(θ)^1.0` and calls it Lambert's law is using the
Lommel–Seeliger form; the two differ by 10 log cos θ, which is −7.6 dB at 10° grazing and
−10.6 dB at 5° (VERIFIED arithmetic on [R26, Eqs. 31–32]).

### 1.2 Highlight, shadow and the geometry of small objects

Shadow height recovery is the classic side-scan measurement: `H_t = L_s · H_f / (L_s + R_s)`
with L_s the shadow length, H_f the transducer altitude and R_s the range to the object [R11,
p. 99, unnumbered; Fig. 3]. Cuschieri & Hebert treat the shadow as a region where "there is a
period of time for which no signal is received" [R11, p. 99]; NOAA requires that a 1 m cube be
detectable "from shadow length measurements" and that contacts in ≤ 20 m of water have
"computed target heights (based on side scan sonar shadow lengths) of at least 1 m" [R22,
§6.1.2.1, §6.1.3.3]. The shadow is the more stable cue: Grządziel reports the literature view
that "the appearance of the shadow region is more constant than the highlight area" and that
"at low resolution, information about the target is contained mainly in its shadow" [R23,
§1], and Steiniger's survey names "the variable nature of highlight and shadow appearance
when the angle from which the object is viewed changes" as a major classification challenge
[R21, §6.3]. Blondel's shallow-water examples show rock outcrops "imaged at far range, [with]
long shadows", an outcrop shaded "very bright (on the side facing toward the sonar) to medium
… and dark (on the side facing away)" [R5, pp. 190, 192], and a 1.5 m metal container as "a
bright rectangular highlight … with a compact black shadow" [R5, p. 218, Fig. 9.16]; a plastic
ground mine "is mainly detected from its long shadow" and images as "one or two very bright
pixels at most" [R5, p. 220].

**Are shadows ever black?** None of the simulation papers read models a partially filled
shadow: Sung's forward model puts exactly zero in occluded bins [R9, Eq. 7]; HoloOcean's
shadows hold only additive Rayleigh noise plus any second-bounce energy [R12, §III-A, §III-D];
Cerqueira's hold only the additive Gaussian term [R16, §3.3]; Coiras's forward model has no
occlusion test at all [R6, p. 383]; Xie et al. mask shadows out because neither their CNN
nor the Lambertian renderer can model them [R13, §V-A]. The real-data side is different.
Blondel's own TOBI histogram example has shadow pixels at a minimum of 54 on an 8-bit scale,
not zero [R5, p. 70]; the multipath section explains that in shallow water "the acoustic
radiation from the sonar (main lobe and sidelobes) will bounce several times on the seabed and
the water surface before being scattered back to the receiver" [R5, p. 230]; and the
reverberation literature notes that multipath "would be to make the reverberation at any given
time more Rayleigh-like, owing to scatterers arriving from different parts of the sea-floor
through alternative acoustic propagation paths" [R3, p. 804]. VERIFIED: the literature read
here documents shadow fill as a real-data phenomenon and does not model it in any simulator.

### 1.3 Shallow-water propagation: multipath, surface, near field

Blondel distinguishes the direct path, the "single-surface reflection" (target → surface →
sonar) and the "double-surface reflection", after which "the imagery will display two or three
recordings of the same target" [R5, p. 228]; surface multiples appear "as bright lines parallel
to the sonar track, at a distance from the sonar track roughly equivalent to the water depth"
[R5, p. 74], and "very reflective targets just out of range will still manage to be recorded …
generally observed in shallow waters with man-made reflectors such as walls and caissons" [R5,
p. 234]. The Lloyd's mirror interference "requires … a transducer depth which does not exceed
a few tens of wavelengths … This usually means a hull-mounted or shallow-towed sonar" [R5,
p. 232]; NOAA lists "surface mirroring (Lloyd Mirror Effect), passing vessel prop wash,
sediment, fish" among the environmental degraders [R22, §6.1.3.2]. Bubbles "would also be
present in the surf zone, for surveys in very shallow water" and can produce "parasite
backscattering observed at very close range" [R5, p. 225].

**Altitude rules.** NOAA requires a towfish height of "8 percent to 20 percent of the range
scale in use" and, below 8 %, defines "the effective scanning range … to equal 12.5 times the
towfish height" [R22, §6.1.2.3]; Grządziel gives "towfish altitude … less than one quarter of
the maximum slant range" as the undistorted-image rule and notes that hull-mounted sonars have
"lower resolving power due to the transducer–seafloor distance and the geometry of the
propagating acoustic pulse" [R23, §1, §2.2]; his hull-mounted 100 kHz example "actually shows
a black echo with a barely visible acoustic shadow" [R23, §3]. Cocchi's catamaran survey kept
the sonar 20–40 cm below the surface, used 25 m swaths in 6–13 m of water and excluded areas
shallower than 1.5 m [R25, §2.2.2, §3.2]. The vendor gives the Omniscan 450 SS a 0.5° (2-way,
3 dB) beam width, 50° beam height, a **far-field distance of 9 m**, a 150 m maximum range and a
20 Hz maximum ping rate [V1]; inside the far-field distance "the effective beam width gets
wider, and sidelobes get larger" [V1]. At 1 m altitude and a 20 m range every rule above is
violated: the altitude is 5 % of the range, the claimable range would be 12.5 m, and half of
the swath lies inside the transducer's near field. VERIFIED.

**Grazing angle and detectability.** With `σ ∝ sin²θ` the seabed return at 5° grazing is
21 dB below its value at 45° [R1, Eq. 2.22]; Blondel's roughness-model curve for a sandy
bottom plateaus at about −31 dB from ~10° grazing while the volume model keeps rising [R5,
p. 17, Fig. 2.7]. Below ~10° grazing the guidelines' fitted data are the ones "contaminated by
multipath reverberation" [R1, p. 323]. The literature therefore predicts that at altitudes
around 1 m the seabed beyond a few metres is both dark and multipath-filled, that shadows
lose their background contrast, and that a hull-mounted platform loses the shadow first
[R23, §3].

### 1.4 Speckle and reverberation statistics

For Gaussian scattered pressure "the envelope obeys Rayleigh statistics"; the squared
envelope is exponential with a scintillation index of unity and the log-intensity standard
deviation is π/√6 in nepers, "which gives a standard deviation of 5.57 dB" [R1, pp. 421–427,
Eqs. 16.11–16.17]. Samples "should be spaced by at least the pulse time resolution in order to
be independent" and the reverberation covariance follows the transmit autocorrelation [R1,
p. 429, Eq. 16.22]. Non-Rayleigh tails arise "when the conditions of the CLT are violated. For
example, there may be too few scatterers in the resolution cell" [R3, p. 800]; for
K-distributed reverberation the shape parameter equals the number of Gaussian patches (or half
the number of exponentially sized scatterers) in the cell and is therefore proportional to the
resolution-cell area, verified at 450–700 Hz as α ∝ beamwidth [R3, pp. 803–809]. Bell & Linnett
validate their deterministic renderer's grey-level histograms against a Rayleigh fit (χ² of
0.012–0.041) but have no speckle model [R7, pp. 223–224]; Bore & Folkesson use multiplicative
Gaussian noise with σ = 0.3 "to match the real signal" and observe that synthesised artifacts
"would not be correlated between subsequent pings, while in reality they clearly are" [R8,
pp. 4–5]; Sung finds that adding speckle lowered cross-correlation and SSIM against a tank
frame and concludes that "speckle noise is not sufficient to simulate highly realistic images"
[R9, p. 7]. Choi's simulators obtain speckle from circular complex Gaussian scatterer
amplitudes, "the summation of complex Gaussian noise and a coherent field would result in
Rician statistics" [R14, §2.3]. None of the papers read validates second-order speckle
structure (range or along-track correlation) against real data. VERIFIED.

### 1.5 Radiometry: TVG, AGC, saturation and what a raw stream looks like

Receivers amplify "using a static gain" and "optionally … either a time-varying gain (TVG) or
an automatic gain control (AGC)"; "TVG is based on a predictive estimate of the signal decrease
with time; while AGC automatically adapts to the fluctuations of the received level" [R26,
§4.2.2 stage 2]. Newer systems skip the analog TVG and "apply a digital TVG or AGC to their
amplitude measurements after sampling, largely for aesthetic reasons" [R26, §4.2.2]; "when the
received signal exceeds the dynamic range of the system, the signal is clipped or otherwise
distorted in a non-linear fashion, leading to an irrevocable loss of some backscatter
information", and "many systems can obtain satisfactory bottom detections from clipped or
otherwise disordered signals", so the operator may not notice [R26, §5.3.1]. TOBI's hardware
TVG is "40 log R + 2αR" [R5, p. 37]; "identical targets placed at different positions
across-track will therefore have increasingly lower backscatter", and "a fixed correction is
usually built in the sonar hardware" [R5, p. 63]. Blondel also notes that recorded pulses "are
not always exact replicas of the signals input into the transducer (e.g., short pulses might
exhibit some 'ringing')" [R5, p. 20]. The Cerulean API defines `pwr_results` as "power results
scaled from min_pwr_db to max_pwr_db", `gain_index` as "0-7", and `msec_per_ping` as "normally
set to 0 for best ping rate" [V2]. VERIFIED. Nothing in the vendor documentation states whether
`max_pwr_db` is pre- or post-gain-regulation, or what the receiver does near saturation
(UNCERTAIN).

### 1.6 Platform motion and the waterfall

Pitch and yaw "cause geometric distortions", while "rolling may result in intensity
distortions in the area immediately below the towfish and at the maximum range due to the
rotation of vertical sidelobes" [R10, p. 253]; the first-order along-track displacement is
`Δn y'_s ≈ Δy'_o + m (cTs/2) Δθ` [R10, p. 256, Eq. 3b]. For a small USV "the change amount of
the roll more greatly affects the distortion … than the change of the pitch", with roll
excursions of ±6.5° at 1.25 MHz and 9.5–13.8° at 2 MHz, and a roll-induced displacement of
range × tan(roll) [R24, §3.2–3.3, §4.2]. Along-track resolution is "Δx = R × sin θh" and range
resolution "Δy = (cτ/2) × 1/cos β" [R5, p. 31, Eqs. 2.10–2.11; R23, §4, Eqs. 3–4]; the
waterfall's along-track spacing "is determined by either the width of the horizontal beam on
the ground or the distance travelled by the transducer during the reception interval, whichever
is smallest", and anamorphosis "aims at producing an image with a 1:1 aspect ratio" [R5, p. 66,
§4.5.2]; an assumed speed higher than the true one stretches the image along-track, a lower
one compresses it [R5, p. 237]. NOAA's coverage rule is that a 1 m object be "independently
ensonified a minimum of three times per pass" [R22, §6.1.2.2]. VERIFIED.

### 1.7 Sonar simulators, Gazebo/ROS integration and sim-to-real claims

| Source | Engine / scene | Backscatter | Shadows | Noise | Validation against real data | Sim-to-real claim |
|---|---|---|---|---|---|---|
| Bell & Linnett 1997 [R7] | own ray tracer, fractal terrain | Jackson bistatic | ray occlusion | none (deterministic) | Rayleigh χ² on grey-level histograms | "identical images cannot be synthesised" (p. 222) |
| Coiras 2007 [R6] | Lambertian inversion | |cos θ| | none in forward model | none | pipe radius 0.51 ± 0.19 m vs 0.381 m | augmented-reality embedding "realistic" by inspection |
| Bore & Folkesson 2021 [R8] | cGAN on bathymetry | cos² input | not discussed | Gaussian σ 0.3 (baseline) | expert preference study | GAN preferred to ground truth 59 % of the time (p. 10) |
| Sung 2020 [R9] (FLS) | ray tracer + pix2pix | cos² | exactly zero | "modeled speckle" | cross-corr / SSIM vs tank | YOLO 86.6 % TPR at sea after synthetic-only training; speckle alone < 10 % (p. 9) |
| HoloOcean 2022 [R12] | UE4 octree | impedance R² × cosine | occlusion, noise-filled | Rayleigh additive + Gaussian multiplicative, second-bounce multipath | one qualitative side-by-side | none measured |
| Choi 2021/2025 [R14, R15] | Gazebo Classic (DAVE), point scattering | μ cos²α | first hit only | complex Gaussian → Rayleigh/Rician | 2025: source level and two μ fitted on tank peaks at 2.1 MHz, validated at 1.2 MHz | none measured |
| Cerqueira 2020 [R16] | Rock-Gazebo, rasterised + selective ray tracing | cosine × per-object reflectivity, normal-map roughness | occlusion, Gaussian-filled | Gaussian mult. + add.; Ainslie–McColm absorption; no surface | MSE/PSNR/SSIM vs one Gemini frame | none measured |
| STARS 2023 [R17] | Blender, ships composited on **real terrain** | dB sonar equation, random TS | ray-cast | none (real terrain carries it) | zero-shot IoU 0.42 on 549 real images at 14 sites | real terrain essential: without it IoU 0.24; UDA methods 0.19–0.28 |
| S3Simulator 2024 [R19] | Gazebo, optical rendering | none (visual) | optical | Gaussian | none | +4 % classification on KLSG with synthetic added |
| ACOUSIM 2026 [R18] | Gazebo, illumination × reflectance | none | optical | Gaussian + speckle (law unstated) | KL/JS/EMD on intensity and LBP histograms vs KLSG-II/SCTD | texture KL < 0.07; ship-class intensity KL up to 0.92 |
| Attia 2026 [R20] | Isaac Sim, 3D sonar | incidence × material | ray-cast | phase-aware roadmap | qualitative sheet-pile comparison | "returns are sparser and less uniform" than sim (V-B) |

What the papers say closes the gap, as opposed to looking realistic: (i) **real background
statistics** — STARS' only ablated ingredient that mattered was compositing onto real terrain
(IoU 0.42 → 0.24 without it), while two domain-adaptation methods under-performed the naive
baseline [R17, Table 2, §5]; (ii) **learning the degradation** — Sung's detector transferred only
after a GAN learned the residual between ray-traced and real frames, and added speckle alone
did nothing [R9, Table 4, §4.4]; (iii) **calibrating the few level constants on the real device**
— Choi 2025's protocol fixes source level and two reflectivities on measured peaks and then
validates at another frequency and tilt [R15, §3.2–3.3]; (iv) **distribution-level validation
rather than downstream accuracy**, because "mixing real and synthetic data during training
further obscures the intrinsic domain gap" [R18, §1]. What the papers themselves call
insufficient: independent per-pixel noise ("would not be correlated between subsequent pings,
while in reality they clearly are" [R8, p. 4]); geometry-only rendering that "fails to account
for fundamental acoustic phenomena such as refraction, multi-path interference, and
phase-dependent signal formation" [R20, §I]; GAN images that "show artifacts which make them
easy to distinguish from real sonar images" [R21, §4.2]. Every Gazebo/ROS simulator read
(Choi 2021/2025, Cerqueira, S3Simulator, ACOUSIM) uses hand-modelled meshes or planar textured
seabeds; none ingests measured bathymetry or generates terrain procedurally with a stated
roughness model, and none reports a side-scan sim-to-real detector result. The only measured
zero-shot side-scan transfer in this set (STARS) achieves it with real terrain, not with a
better acoustic model. VERIFIED.

### 1.8 Procedural seabed for sonar simulation

Bell & Linnett generate the seafloor as a fractal height field with `S(f) ∝ 1/f^β` and note
that "fractals with dimensions 0.2 to 0.3 greater than the Euclidean dimension tend to produce
the most realistic natural scenes" [R7, p. 221, Eqs. 10–11]; Cerqueira's "corrugated seabed"
is a normal-map texture, not geometry [R16, §4.2]; ACOUSIM's seabed is planar with texture
[R18, §3.1]; Bore & Folkesson's cGAN synthesises ripples on flat ground and warn that it
hallucinates them where the ground truth is flat [R8, p. 8]. The physical literature ties
roughness to scattering through spectra: composite-roughness splits the spectrum at a cutoff
wavenumber, "the small-scale … roughness causes scattering, while the large-scale … roughness
simply tilts the seafloor, altering the grazing angle and causing acoustic shadowing" [R1,
p. 362], with a Wagner shadowing factor [R1, Eqs. 13.81–13.83]; the small-slope model "does not
incorporate the effects of large-scale tilting and shadowing" [R1, p. 368]. No paper read
here reports a procedural terrain generator whose statistics were matched to a side-scan
survey, so the simulator's authored-bathymetry route (a spline through measured first-bottom
returns plus synthetic or shading relief) has no direct precedent in this set and is judged on
its own evidence in Part 3.9. VERIFIED.

### 1.9 What the beach regime needs, in the literature's terms

The project's regime — a 450 kHz hull-mounted transducer at 0.15 m depth, 1–2 m of water,
20 m range, objects 0.3 m tall — sits outside every rule read: altitude/range 5 % against
NOAA's 8–20 % [R22]; half the swath inside the vendor's 9 m far-field distance [V1]; grazing
angles of 3–10° over most of the swath where the guidelines' own data were multipath-edited
[R1, p. 323]; a surface only 0.15 m above the transducer, i.e. a few tens of wavelengths, the
Lloyd's-mirror condition [R5, p. 232]; and a hull-mounted geometry that Grządziel's example
shows losing the shadow first [R23, §3]. A simulator for this regime must therefore be judged on
(a) the angular law at 3–10° grazing, (b) the fill of shadows by surface and bottom multiples,
(c) the near-field beam, (d) the device's gain regulation and dynamic range, and (e) the
acoustic transparency of thin-walled plastic targets — a polypropylene wall has an impedance of
2.36–2.40 MRayl against 1.48–1.53 for water [R4, Table I, pp. 387, 390], so a plane interface
reflects only `((2.4 − 1.5)/(2.4 + 1.5))² ≈ 5 %` of the incident power [R4, p. 383, Eq. 1;
R1, Eq. 8.49]. Part 2 checks which of these the simulator carries.

---
## Part 2 — What the repository currently does

All line numbers below were harvested on 2026-09-17 (`scripts/cite.sh` → `out/citations.txt`)
from the working trees; the simulator tree is uncommitted ahead of `a3730b5`, so they are
working-tree lines. Paths are relative to the superproject root.

### 2.1 Pipeline map

One ping runs `sss_sim_node._tick` → `GeometricRenderer.render` → `apply_ping_noise` →
`PingEncoder.encode` → `/side_scan_sonar/{port,starboard}/{profile,raw}`; both sides are
rendered in the same tick from the same pose (`BlueBoat-SSS-Sim/blueboat_sss_sim/blueboat_sss_sim/ros/sss_sim_node.py:241`), and a dropped
ping still advances the counter (`sss_sim_node.py:246`). Downstream, the unmodified
`sss_processor_node` converts `pwr_results` per ping with `scale_to_db`
(`BlueBoat-SSS/blueboat_sss/src/_custom_libraries/sss_helper.py:66`), resolves the side from
the packet (`sss_helper.py:32`), assembles rows and writes the `.svlog`, whose navigation
envelopes carry `vx = vy = 0` (`BlueBoat-SSS/blueboat_sss/src/sss_processor_node.py:631`) —
a processor property, so a real recording made by our own stack would also carry zero
velocities (VERIFIED). The GCS then applies its display model and along-track estimator
(Part 2.6). VERIFIED.

### 2.2 Renderer physics: modelled, simplified, placeholder

| Effect | Where | What the code does | Class |
|---|---|---|---|
| Backscatter law | `sonar/acoustics.py:25-28` | `reflectivity · clip(cos θ_inc, 0, 1) ** lambert_exponent`, exponent 1.0 (`sonar/config.py:189`) | **Simplified and misnamed**: this is the Lommel–Seeliger first-power law [R26, Eq. 31]; the docs call it "Lambert's law proper" (`docs/sonar_model.md:234`) |
| Per-material angular response | `worldgen/materials.py:44` | `Material.lambert_exp` is declared and loadable but read by nothing; the renderer uses only the global exponent | **Dead code** |
| Vertical beam | `sonar/acoustics.py:32` | Gaussian in depression angle, FWHM 50°, tilt 20°, floor 0.004 | Simplified; no near field (the vendor's far-field distance is 9 m [V1]) |
| Near-nadir lobe | `sonar/acoustics.py:51` | `S · (0.5 + 0.5ρ) · exp(−θn²/2σ²)`, S = 30, σ = 8° | Placeholder constants (docs §6: "not determined") |
| Spreading, absorption, TVG | `sonar/acoustics.py:69-86` | `r^−4 · 10^(−0.2 r/10)`, TVG fraction 0 | Modelled; pre-TVG stream by fit on a 6–9 m altitude corpus |
| Shadows | `sonar/renderer.py:452-458` | one `np.maximum.accumulate` horizon cull on the merged terrain + object heightfield; a culled ground sample contributes exactly 0 (`renderer.py:527`) | Modelled geometrically; **no fill path is on by default** |
| Noise floor / water column | `sonar/noise.py:84`, `config.py:345` | additive Exp(1) at 8.3e-11 (−3.6 dB reported), applied to every bin | Measured on the harbour corpus; white (uncorrelated) |
| Speckle | `sonar/noise.py:73` | multiplicative coherent-scatterer texture, correlated along range and track | Modelled |
| Ringing | `renderer.py` (§3 of the docs) | 55 dB at 0 m, −22 dB/m, coherent channel | Measured |
| Second-bottom echo | `sonar/renderer.py:736`, `config.py:268` | copy of the direct response shifted by the altitude, gain 0.12 | **Off by default** |
| Surface mirror | `sonar/multipath.py:85`, `config.py:282` | image source across z = 0, evaluated at −depression | **Off by default** |
| Wall face echo | `sonar/renderer.py:640-697` | coherent line at the face range; loop `break`s at the first wet hit (`:697`); a dry-foot wall is skipped (`:654`) | Simplified; see 2.3 |
| Wall occlusion | `sonar/renderer.py:464-474` | direct path only; dry-foot walls skipped (`:466`) | Simplified |
| Wall ghosts and corner band | `sonar/multipath.py:85,162,195`; `renderer.py:545,758-795` | mirror sources per wall, crossing test against the ghost's own wall only; corner band from `_direct_sensor` | **No occlusion by nearer walls** |
| Gain ladder, per-ping normalisation | `sonar/encoder.py:55-60,161` | `20·log10` amplitude ladder, indices 4–7 measured; one bin at 65535, span clamped at 90 dB | Measured; AGC absent |
| Side identity | `sonar/encoder.py:176,189` | `channel_number` 0/1, `transducer_heading_deg` ∓90 | VERIFIED device convention |
| Objects | `worldgen/objects.py:963,925` | one height stamp per cell (`h_eff · prof`), reflectivity blend `(1 − 0.8·burial)`; z-buffer keeps one top surface (`worldgen/solids.py:254`) | Simplified: opaque, no cavity, no transmission |
| Materials | `worldgen/materials.py:3,58-59,21` | scalar reflectivities described in the module docstring as "relative acoustic parameters … not a physical scattering theory"; `plastic` 0.40, `pvc` 0.50; ceiling 4.0 under a gain map | **Judgement values** |
| Terrain micro-relief | `worldgen/terrain.py:367` | per-material fBm added to the 0.1 m heightfield; no sub-raster roughness reaches the renderer | Simplified |

VERIFIED for every row (code read this pass).

### 2.3 Walls

Walls are analytic vertical segments, never in the raster. Seven properties of the code
(VERIFIED):

- W0 `wall_echo_enabled = False` also disables occlusion, because `_wall_hits` returns an
  empty list (`sonar/renderer.py:264-268`).
- W1 all five azimuth lines intersect the walls from the un-offset sensor.
- W2 `_face_echo_into` renders the first hit whose face band is wet and then `break`s
  (`renderer.py:697`), so a pontoon or low sill hides the face of any wall behind it.
- W3 the face echo never consults the terrain visibility mask.
- W4 `mirror_sources` has no mutual occlusion (`sonar/multipath.py:85`); `crossing_mask`
  tests only the ghost's own wall (`multipath.py:162`).
- W5 ghost passes run with `direct=False`, so the wall-occlusion block is skipped for them
  (`renderer.py:464`).
- W6 the single-bounce corner band uses the real transducer's leg with no occlusion check
  (`renderer.py:545`).
- W7 `wall_echo_strength` 30 is admitted non-corpus (`config.py:294`).

Part 3.3 shows which of these produced the see-through line.

### 2.4 Objects and materials: the judgement calls, one by one

`CATALOG` holds 27 classes; `crate_plastic` is a solid box 0.45–0.55 × 0.30–0.40 × 0.18–0.25 m
in `plastic` (`worldgen/objects.py:233`) and `mesh_crate` a lattice-thinned box 0.50–0.56 ×
0.34–0.39 × 0.28–0.34 m, fill 0.30–0.50, sized from a solid-wall 50 L container
(`objects.py:289`, `target_families_and_surrogates.md:179`). No class declares a
`params_schema` (`objects.py:191`), so exact length, width and height can be set only in a
world YAML `explicit:` entry (`objects.py:976-998`) or in the Screen-5 per-object editor;
Screen 4 exposes an isotropic size scale. VERIFIED.

The material table (`worldgen/materials.py`) and the `TODO.md` items that flag it, evaluated
against the literature read:

| Item | Repository value | Literature | Evaluation |
|---|---|---|---|
| Seabed spread sand 0.55 / mud 0.30 / gravel 0.70 / rocks 0.85 (≈ 3.7 dB) | judgement (`TODO.md` "Reflectivity from a recording") | J&R fits: mud −19.7, sand −20.2, gravel −11.7, rock −5.6 dB, i.e. gravel +8.5 and rock +14.6 dB over sand, with ±5–8 dB within-class spread [R1, pp. 323–326] | The table compresses a 15 dB range into 3.7 dB; the survey layer's own thresholds (−3.5 / +2.5 / +5.5 dB) are closer to the literature than the table. The 2026-09-16 decision to keep the table and open the ceiling under a gain map is a reasonable interim, but the material contrast a synthetic world can express is a third of the literature's. |
| `eps` 0.80 (`TODO.md` "EPS reflectivity is a judgement call") | air-backed foam ≈ total reflection | air/water impedance step is near-total [R1, Eq. 8.49 with aρ·ap ≪ 1] | Consistent with the physics; only the value 0.80 versus 0.95 is unmeasured. Keep. |
| `plastic` 0.40 < `pvc` 0.50 | judgement, no comment | PP impedance 2.36–2.40 MRayl, PVC 3.27, LDPE 1.79, water 1.5 [R4, Table I]: plane-interface power reflection 5 % (PP), 14 % (PVC), 0.8 % (LDPE) | The ordering PP < PVC is right in sign; the magnitudes are not: a water-filled thin PP shell reflects an order of magnitude less than the 0.40 scalar implies relative to `metal` 0.95 (steel 46 MRayl: 96 %). More important, a scalar reflectivity cannot express that 95 % of the energy passes through the wall (Part 3.6). |
| Pontoon face `wall_pontoon_specular` 0.15, `wall_face_diffuse` 0.5 (`TODO.md`) | judgement | Blondel: docks and jetties "will generally appear as distinct, linear barriers" [R5, p. 206]; mooring chains visible "for a range of 30 m" [R5, p. 207] | No pontoon-specific data read; the literature says structures of this kind are conspicuous, which argues against a faint default. UNCERTAIN until a pontoon is recorded. |
| `lambert_exponent` 1.0 "held at Lambert's law proper" (`docs/sonar_model.md:234`) | corpus-undetermined | Lambert is cos² / sin²θg [R1, Eq. 2.22; R26, Eq. 32]; cos¹ is Lommel–Seeliger [R26, Eq. 31] | The doc statement is wrong; the value may still be the better fit at low grazing over a rough bottom [R26, §2.4.4], which Part 3.9 tests. |
| Material reflectivities are single scalars; `lambert_exp` per material is dead | — | scattering depends on roughness spectra and impedance [R1, ch. 13]; HoloOcean and Choi use impedance-derived coefficients [R12, Eq. 4; R15, §3.2] | A physics gap rather than a calibration one: no roughness or impedance enters the object or seabed model. |

### 2.5 Noise, encoding and the calibration anchor

The level constant `calibration_db_offset` 97.2 (`config.py:256`) was fitted on the
Shiraishi-jima harbour corpus flown at 6–9 m altitude with the device's auto-gain walking
indices 4–7 (`docs/sonar_model.md` §6); the same section still lists the retired joint noise
value 6.79e-7 in its table (`docs/sonar_model.md:157,232`) while the shipped YAML carries
8.3e-11 and 1.15e-7 (`config/default_sonar.yaml:159`). The encoder's gain step is
`20·log10(analog_gain/74.55)` (`sonar/encoder.py:60`), the auto-gain sentinel resolves to
index 4 (`config.py:106`), and no AGC exists: a run reports index 4 whatever the seabed
returns. `dropped_ping_prob` is 0 in every shipped profile (`config.py:360`). VERIFIED.

### 2.6 The GCS display path

The "scaling button" is the `True scale` checkbox (`BlueBoat-SSS/blueboat_sss/blueboat_gcs/gui/waterfall_view.py:133`);
the row stretch is a `QTransform` scale by `aspect = clamp(row_pitch / col_pitch, 0.05, 20)`
(`waterfall_view.py:165,175`), with `aspect = 1.0` whenever the estimated row pitch is not a
finite positive number (`waterfall_view.py:161`); the row pitch is ground speed × ping period
from `core/along_track.py:25,123`. The seabed pictures resample rows through their own
estimator instance instead of stretching (`core/seabed_imager.py:563`), and their PNGs are
written with the configuration γ, not the slider's (`core/seabed_imager.py:184`,
`core/display_model.py:369`). Defaults: `display.gamma` 0.7 (`config/default.yaml:79`),
`display.transfer: power` (`default.yaml:83`), `seabed.row_geometry: square`
(`default.yaml:116`). The planned path comes from `/set_path` (`ros/path_listener.py:79`,
`gui/map_layers.py:476`) with no truncation of its own. VERIFIED.

### 2.7 CM-1/CM-2: what the identical interface guarantees, and what it does not

The interface contract guarantees names, types, QoS and the three per-ping normalisation
invariants (one bin at full scale `65535`, minimum `0`, span ≤ `90` dB), all of which the simulator satisfies
(MEASURED · `analysis.calibration_cli` → `out/g_calib/base/calibration.md`: 0.9975 / 1.0000 /
1.0000 on 400 simulated pings against 1.0000 / 1.0000 / 1.0000 on 60 468 real). It does not
guarantee that the *values* behave like the device's, and four downstream mechanisms are never
exercised by the simulator as shipped (VERIFIED by code reading, MEASURED on the two simulator
logs with `analysis.svlog_compare` → `out/c_compare/compare.md`):

| Downstream mechanism | Depends on | Simulator as shipped | Exercised? |
|---|---|---|---|
| GCS gain compensation `20·log10(analog_gain/74.55)` | `analog_gain` walking with the device's AGC (4→7 inside every real recording) | constant index 4 → correction exactly 0 dB | no |
| Side-identity fallback (channel 255, wrapped heading sign, arrival topic) | `channel_number` outside {0,1} | always 0/1 | no |
| Counter-restart re-base (`COUNTER_RESTART_PINGS`, `sss_processor_node.py:192`) and per-device counter offsets | a key ≥ 128 behind, offsets 0/−1/+60 in the field | monotonic lockstep counters, 0 resets | no |
| One-sided rows, torn-row alarm | a missing side | both sides every tick; 100 % of port stamps also on starboard against 0 % in the real logs | no |
| Along-track estimator from GPS velocity | `vx, vy` | processor writes 0 (`sss_processor_node.py:631`); estimator uses positions, so unaffected — but any consumer of `vx/vy` is blind | partly |

A regression in any of the first four would pass every simulator-based check. The
structural blindness is the point the user asked about: the simulator validates the happy
path of the pipeline and nothing else. VERIFIED.

---
## Part 3 — Field and comparison observations, one by one

Each point: the user's observation, the evidence on disk, what the code does, what was
measured, what the literature says, a verdict (confirmed · partly · not reproduced; severity
for the thesis: threatening · material · cosmetic), and a pointer into Part 6. Correlations
between points are stated where they exist. Measured numbers cite `scripts/<name>.py →
out/<step>/<file>` under the evidence root.

### 3.1 Pontoon walls — what they are, and whether they are useless

**Observation.** "What are pontoon walls? Aren't they useless to us as they don't even appear
in the sonar?"

**What the code does (VERIFIED).** A wall of `kind: pontoon` is a face spanning only
`[−draft_m, 0]`; a ground ray is occluded only where it crosses that band, so the seabed
beneath and beyond stays lit (`BlueBoat-SSS-Sim/blueboat_sss_sim/blueboat_sss_sim/sonar/renderer.py:464-474`);
its face echo keeps only `wall_pontoon_specular` = 0.15 of the specular lobe plus the diffuse
term (`renderer.py:674`); it is an ordinary mirror source for ghosts. The kind exists because a
crossed wall rendered as a quay under the hull produced a bright slab in the water column and
a full shadow (`BlueBoat-SSS-Sim/.claude/CLAUDE.md` §11, 2026-09-03). The harbour world on
this machine carries three pontoons and eight quays; the beach world none (VERIFIED in
`metadata.yaml` of `~/worlds/testGPS/harbour` and `plage_test`).

**Literature.** Docks and jetties "will generally appear as distinct, linear barriers (a bit
like fault scarps)" and a mooring chain is "visible for a range of 30 m" [R5, pp. 206–207];
Kim & Ryou image a quay wall as a block-layer line from a USV [R24, §4.1]. Nothing read here
describes a floating pontoon's signature, and no field recording of one exists in the corpus.

**Verdict.** Not useless, but misjudged in two ways. (i) The kind is the only representation
of a structure the boat can cross, and it is what keeps the sonar from painting a quay slab
under the hull; removing it would reintroduce that artefact. (ii) Its faintness is a judgement
value with no anchor (`TODO.md` "Pontoon face level"), and the literature's description of
harbour structures argues for a stronger signature: real pontoons have vertical float faces
and mooring piles, neither of which the model carries. A pontoon also hides the face echo of
any quay behind it (W2), which is a bug rather than a design choice. Severity: cosmetic for the
beach thesis, material for any harbour scene. → P6-6, P6-7.

### 3.2 `BlueBoat-Control` and `BlueBoat-MCS` are frozen at `v1.0`

**Evidence (VERIFIED).** Tag `v1.0` = `65b15bb` "Dev V1.0 (#1)" in Control and `790934f`
"V1.0 (#1)" in MCS, both on `origin/main`; the superproject gitlinks point at the `dev`
HEADs `d64ac71` / `3cfb58c`, whose trees are byte-identical to the tags (`git rev-parse
v1.0^{tree}` = `HEAD^{tree}` in both). No `CLAUDE.md` in the tree said so before this pass
(grep for `v1.0`, `frozen`, `do not modify`: no hits in the four files). The three notes are
now in the superproject `.claude/CLAUDE.md` (§1 table and §3), `BlueBoat-SSS-Sim/.claude/CLAUDE.md`
§8 and `BlueBoat-SSS/.claude/CLAUDE.md` (the `blueboat_interfaces` paragraph).

**Consequences carried through this review.** The planned-path fix (3.4) cannot touch
`path_publisher`; the RViz half is deferred; the `vx = vy = 0` envelope (2.7) is in
`BlueBoat-SSS`, not frozen; nothing in Part 6 edits Control or MCS.

### 3.3 See-through walls

**Observation and evidence.** `see_throught_walls.png`, from the `full_beach_sim` session over
`plage_test`: a thin bright line inside the black zone behind the shoreline wall, at the place
of a second wall further inland.

**What the code does (VERIFIED).** Part 2.3, W2–W6.

**Measured.** Over the 56 806 posed profiles of the session log, 4 100 rays meet a wall and
517 meet two wet faces in succession, all on the beach walls (`wall_6` → `wall_7_s05`: 261,
`wall_8_s10` → `wall_7_s05`: 84, …); no ray meets a dry-foot wall first. At the second face's
range the recorded contrast is 33.0 dB median with 97 % of those pings above 6 dB, while the
zone between the two faces lies 63 dB below the seabed reference; the longest run is 277
consecutive port pings at 20 m (MEASURED · `scripts/e_walls_find.py` →
`out/e_walls/wall_hits_summary.json`, `wall_hits.csv`, `wall_cluster_crop.png`,
`wall_candidates_map.png`). Rendering the scene offline at one of those poses (ping 54 704)
reproduces the line at the second face with 26.1 dB contrast in the noiseless power; setting
`wall_corner_gain = 0` removes it (1.1 dB), setting `wall_echo_strength = 0` leaves it
untouched (26.1 dB), and disabling `wall_multipath_enabled` empties the whole occluded zone
(MEASURED · `scripts/e_walls_render.py` → `out/e_walls/render_variants.json`,
`render_variants.png`).

**Attribution.** The line is the single-bounce corner band of the far wall — energy that
leaves the transducer, scatters off the seabed in front of the far wall and returns off its
face — accumulated at the mean of the direct and folded path lengths (`renderer.py:545`)
without any check that the near wall blocks the direct leg (W6) or the mirror geometry
(W4/W5). The far wall's *face* echo is correctly suppressed by the `break` (W2), which is why
the line is thin and dotted rather than a full face. The "small reflection line that
corresponds to a placed wall behind another one" is therefore real energy in the model, routed
through a path the geometry forbids.

**Literature.** Out-of-range and behind-structure returns exist in real harbours, but as
late echoes of *very reflective* targets [R5, p. 234]; nothing supports a corner band of a
fully occluded wall.

**Verdict.** Confirmed; software gap (a missing occlusion test), independent of the
acoustic constants. Severity: material for harbour worlds (a ghost line labels as ground
truth `via: wall:<name>`), cosmetic for the beach. Correlated with 3.1 (W2 hides real faces in
the opposite direction). → P6-5.

### 3.4 The full planned path in the GCS and RViz

**Observation.** The MCS map shows the whole path; the GCS and RViz show only its beginning.

**What the code does (VERIFIED).** `path_publisher` requests `linspace(0, total_time,
total_time/dt + 1)` with the parameter default `total_time = 1000.0`
(`BlueBoat-Control/blueboat_control/src/_custom_libraries/path_publisher.py:31,48`);
`Sim_launch.py` starts it without parameters (`BlueBoat-Control/blueboat_control/launch/Sim_launch.py:35`);
the `from_yaml` trajectory clamps to its last pose unless `loop: true`
(`yaml_trajectory.py:42,51`); the mission on this machine has `duration_s: 1317.569` and
`loop: true` (`.deployed/plage_bathymetry2.yaml`), so the published path stops at 1000 s of a
1318 s loop. The GCS forwards every pose it receives (`blueboat_gcs/ros/path_listener.py:79`,
`gui/map_layers.py:476`); RViz displays the same `/set_path`. The MCS does not use `/set_path`:
it reads `duration_s` from the YAML and calls `/path_request` itself with that horizon
(`BlueBoat-MCS/mcs/gui/main_window.py:417,428`, `mcs/ros/bridge_node.py:12,49,108`). The
simulator's own `full_mission_launch.py` already sets `total_time` from `duration_s`
(`BlueBoat-SSS-Sim/blueboat_sss_sim/launch/full_mission_launch.py:183`), so a mission launched
from it is complete; one launched by the MCS through `Sim_launch.py` is not.

**Verdict.** Confirmed; software gap; cosmetic for the thesis, operational for supervision.
Doing "what MCS does" in the GCS is a small change with no ROS contract impact: read
`duration_s` (and, simpler still, the dense `points`) from the deployed YAML, or issue one
`/path_request` with `[0, duration_s]`. The RViz half needs a `total_time` parameter passed
from the launch that starts `path_publisher`, which is Control/MCS territory and frozen. →
P6-11.

### 3.5 A `plastic_box` item with exact height, length and depth

**Evidence (VERIFIED).** The product placed on 2026-09-07 is NAFCO NA Container Clear #75:
polypropylene body and lid, solid transparent walls, 716 × 425 × 323 mm outside, 609 × 354 ×
300 mm inside, 68 L (vendor page, fetched 2026-09-17); it was sunk flooded with the lid on
(user, 2026-09-17). The catalog has no such class: `crate_plastic` is a solid box whose random
draw tops out at 0.25 m, `mesh_crate` a lattice (Part 2.4). Exact dimensions can already be
pinned per instance in a world YAML (`objects.explicit`, `objects.py:976-998`) or in the
Screen-5 editor, and `mesh_crate` with `fill_fraction: 1.0` is a solid box to within one cell
in 65 536 (`objects.py:133`); what is missing is a class whose *defaults* are the product and
whose form exposes length, width and height, which the `params_schema` seam supports with no
GUI code (`objects.py:191`, every class currently leaves it empty).

**What the acoustics says the class must carry.** Polypropylene: longitudinal speed
2.66–2.74 mm/µs, density 0.88–0.89 g/ml, impedance 2.36–2.40 MRayl against 1.48–1.53 for water
[R4, Table I pp. 387, 390]. A plane water/PP interface reflects `((Z − Zw)/(Z + Zw))²` = 5 %
of the incident power at normal incidence [R4, p. 383, Eq. 1; R1, Eq. 8.49]; two walls and a
water-filled interior transmit most of the energy to the seabed behind. A scalar `reflectivity`
cannot express that; the model needs a per-object *transmission* (opacity) that attenuates the
horizon cull instead of zeroing it, and a highlight that comes from the near wall's specular
face rather than from a bright top. Severity: material (it is the object the field detected).
→ P6-2, P6-3.

### 3.6 Real box versus simulated mesh container: shadows too perfect and too long

**Observation and evidence.** `plastic_box_real_shadow_noise.png` (real: shadow only, speckle
inside), `mesh_container_sim_perfect_shadow.png` (sim: hard black slab, thin bright leading
edge), `left_realBox_right_simMeshContainer.png` (real: faint highlight and noisy shadow over
ripples; sim: black shadows). Logs: `object_boiteVsDistance.svlog`, `object_boiteEncore.svlog`
(real), `2026-09-17-11-27-57.svlog` (sim, three `mesh_crate` 0.795 × 0.547 × 0.465 m, fill
0.40–0.475, burial 0.21–0.30, `plastic`).

**Measured, same definitions on both sides** (highlight = maximum over the 0.6 m before the
object relative to a per-range reference built from neighbouring pings without the object;
shadow window = the flat-bottom length `h·r/alt` behind the object; fill = share of shadow bins
within 6 dB of the reference):

| Quantity | Real NAFCO box (port, 19.7 m, rows 935–964, 6.03–7.82 m slant, altitude 1.17 m) | Sim `mesh_crate` ids 1–2 (per-pass, 102 + 78 passes, 10.8–11.0 m across, altitude 1.1–1.2 m) |
|---|---|---|
| Highlight above local seabed | +9.4 dB (row median; max +15.2) | +17.8 / +20.4 dB |
| Shadow mean relative to local seabed | −9.6 dB (p50 −8.8, p10 −17.2, p90 −3.1) | −26.4 / −32.7 dB (p10 −35.8 / −36.5) |
| Shadow bins within 6 dB of seabed | 0.28 | 0.00 |
| Shadow absolute level above the receiver noise floor (−3.6 dB) | +36.7 dB | +3.9 dB |
| Linear-intensity CV inside the shadow / on the seabed rows outside | 1.42 / 1.34 | (sim shadow is floor noise) |
| Measured shadow length / flat-bottom `h·r/alt` | 1.8 m patch extent / 1.67 m | 6.45 m / 3.38 m and 6.78 m / 3.67 m |
| Along-track extent | 29 pings ≈ 1.0 m at 0.7 m/s | — |

(MEASURED · `scripts/d_box_measure.py` → `out/d_shadow/box_measure.json`, `real_box_zoom.png`;
`scripts/d_shadow_local.py` → `out/d_shadow/shadow_local.json`; `scripts/d_shadow_sim.py` →
`out/d_shadow/shadow_sim_rows.csv`, `sim_crate_*_crop.png`; cross-check with an identical blob
detector on both logs: `scripts/d_blob_detect.py` → `out/d_shadow/blobs.json`, sim blobs −17 to
−27 dB mean with fill 0.03–0.07, real box-like blobs −7 to −10 dB with fill 0.27–0.48.)

**Why the sim shadow is longer.** The world's seabed rises 0.42 m between nadir and the
crates at 10.8 m across (altitude 1.2 m at nadir), so the ray over the crate top grazes the
bottom beyond it at about 1.5°, and the geometric shadow is far longer than the flat-bottom
formula, bounded only by the synthetic relief (MEASURED · `scripts/d_sim_slope.py` →
`out/d_shadow/sim_slope.json`). This is geometry the real box faces too, at 7 m across; the
real shadow shows no long tail because it is filled, not because it is shorter.

**Why the sim shadow is perfect.** A culled sample contributes exactly nothing
(`renderer.py:527`); the only additions are the white receiver floor and, if enabled, the
two multipath terms (Part 2.2). The synthetic sweep with the NAFCO box on flat sand shows the
consequence: at 0.6–1.0 m altitude the baseline shadow lies 68–69 dB below the seabed at 6 m
across, `multipath_enabled` raises it only to 62–46 dB below (the ghost is displaced by one
altitude, less than the shadow length), `surface_mirror_enabled` changes nothing, and fill
appears only at 1.5–3.0 m altitude (MEASURED · `scripts/f_altitude_sweep.py` →
`out/f_altitude/sweep.csv`, `contrast_vs_altitude.png`).

**What fills the real shadow.** Its absolute level is 37 dB above the receiver floor and its
speckle statistic matches the seabed's (CV 1.42 vs 1.34), so it is scattered energy, not noise.
Candidates, in the order the physics read supports: (i) transmission through the water-filled
PP shell — 5 % reflection per interface [R4], so the seabed behind the box is insonified
through it; (ii) surface and bottom multiples, which in 1.2 m of water arrive within
centimetres of the direct return [R5, pp. 74, 228–230] and make reverberation "more
Rayleigh-like" [R3, p. 804]; (iii) the near-field beam and sidelobes inside the 9 m far-field
distance [V1]. Which dominates is UNCERTAIN; (i) is specific to this object and testable with a
steel box of the same size, (ii) is generic to the site.

**Verdict.** Confirmed on both counts, and they are different gaps: the length is geometry
(correct in the model, misread as a fault), the darkness is physics (no transmission, no fill
path on, white floor). The detector the thesis trains keys on shadows; a simulator whose
shadows are 30 dB deeper than the field's is a threatening gap for any synthetic-to-real
statement about shadow cues. → P6-3, P6-4, P6-2.

### 3.7 Relief shadows look right, object shadows look perfect — are they treated separately?

**What the code does (VERIFIED).** No. One horizon cull on one heightfield produces both
(`renderer.py:452`); no code path distinguishes an object stamp from terrain, and no
post-noise mask exists (`sss_sim_node.py` assigns the noisy vector straight to the encoder).

**Why they look different.** On a 0.1 m raster with slopes of a few degrees, relief seldom
produces a true geometric shadow: back slopes are dimmed by the angular law but keep a
non-zero, speckled return, and the five-line azimuth integration adds a small along-track
penumbra (±6.5 cm at 15 m). A 0.37 m slab at 1.2 m altitude produces a true cull over metres,
and a culled bin carries only the floor. The user's reading is therefore correct as an
observation and wrong as a diagnosis: the difference is geometric, and the fix is the same fill
physics as 3.6, applied to everything. Severity: follows 3.6. → P6-4.

### 3.8 Objects invisible at less than 1 m of water

**Observation.** In the field, objects in less than about 1 m of water could not be seen at
all. Which recording documents this is UNCERTAIN (the user's answer named the world and
session for 3.3 only); `object_checkDepthVisibility.svlog` is the candidate by name and was not
analysed for this point.

**Literature (Part 1.3).** Every operational rule read is violated at 1 m altitude and 20 m
range: NOAA's 8–20 % altitude/range band, with an effective range of 12.5 × altitude below 8 %
[R22, §6.1.2.3]; Grządziel's altitude < range/4 and the hull-mounted example that "shows a
black echo with a barely visible acoustic shadow" [R23, §1, §3]; the transducer's 9 m far-field
distance [V1]; the sin² fall-off that puts the seabed at 5° grazing 21 dB below its 45° value
[R1, Eq. 2.22]; multipath contamination below ~10° grazing [R1, p. 323]; surface multiples "at
a distance … roughly equivalent to the water depth" [R5, p. 74]; the surf-zone bubble layer
[R5, p. 225]. The expected picture is a swath that is dark and multipath-filled beyond a few
metres, in which small targets lose both highlight and shadow contrast. Is it expected: yes.

**Does it emerge from the model.** No. The synthetic sweep predicts the opposite: at 0.6 m
altitude the NAFCO box at 6 m across shows a +14 dB highlight and a 68 dB shadow, stronger than
at 3 m altitude (+11 dB, 54 dB), and the ground-truth label reports it visible at every
altitude (MEASURED · `scripts/f_altitude_sweep.py` → `out/f_altitude/sweep.csv`). The reasons
are the same three physics items as 3.6 plus one more: the first-power angular law keeps the
seabed 10 dB brighter than Lambert at 5° grazing; no multipath fills; no near-field beam; and
the receiver floor is white at −3.6 dB where the real far-range floor sits at 18 dB in the
same geometry (MEASURED · `analysis.svlog_compare` → `out/c_compare/compare.md`, far-decile
floor bath3 18.1–19.0 dB vs sim 21.9–23.1 dB at 20 m — close in level, but the real floor is
reverberation, the sim's is noise; and `scripts/a_level_match.py` → `out/a_level/level_match.json`,
first-metre level real 39.5 dB vs sim 44.2 dB).

**Verdict.** Expected by the literature; not reproduced by the model as shipped; a physics
gap (angular law, multipath, near field, reverberation floor). Severity: material — it decides
where in the swath the aspect-response experiment can see anything. The model should not be
tuned to it; it should be given the missing physics and then checked against
`object_checkDepthVisibility.svlog`. → P6-1, P6-4, P6-8.

### 3.9 `bath3.svlog` versus `full_beach_sim`: same place, same path, same controller

**Path identity (MEASURED · `scripts/b_fbr_align.py` → `out/b_fbr/fbr_align.json`).** 97.8 % of
the real soundings lie within 3 m of the deployed `plage_bathymetry2` polyline (100 % of the
simulated ones), so the real recording was flown on the same 658.8 m path.

**Depth over the path.** Along 1 m arc-length bins the real and simulated first-bottom-return
depths agree with a bias of +0.11 m (real deeper), a median |Δ| of 0.17 m, a 90th-percentile
|Δ| of 0.33 m and a correlation of 0.83 over 638 bins; the simulated soundings follow the
world's authored surface with correlation 0.998 and a constant −0.15 m offset (the detector
fires on the specular ramp before the nadir; whether the sensor depth is double-counted in the
sounding is UNCERTAIN); medians are 1.59 m real, 1.52 m sim, 1.67 m authored (MEASURED ·
same script → `fbr_vs_s.csv`, `fbr_vs_s.png`). The world was built from `bath1_2_3.svlog`, so
the real-versus-authored agreement (0.83) is partly circular; the sim-versus-real agreement is
the honest number: the authored-bathymetry route reproduces the recorded depth profile to a
few decimetres, which is what the user expected.

**Level and range law (MEASURED · `scripts/a_level_match.py` → `out/a_level/level_match.json`,
`level_curves.csv`, `level_match.png`; same subset 20 m / 600 bins / gain 4, altitude band
0.97–1.63 m, 16 661 real vs 22 473 simulated port pings).**

| Statistic | Real bath3 | Sim full_beach_sim |
|---|---|---|
| `max_pwr_db` median (port / starboard) | 66.8 / 66.5 dB | 84.2 / 84.0 dB |
| First-bottom-return peak, median | 63.9 / 63.2 dB | 83.3 / 83.1 dB |
| Mean level slope over 2–16 m slant | −44.0 / −44.3 dB per decade | −55.9 / −54.9 dB per decade |
| Sim − real fitted as `a + b·log10(r)` over 2–16 m | a = +17.8 / +17.7 dB, b = −11.9 / −10.6 dB per decade, residual 0.5 dB RMS | |
| Sim − real at 2 / 5 / 8 / 16 m | +16.3 / +9.2 / +6.5 / +4.8 dB (port) | |
| `max_pwr_db` versus altitude, 0.6–2.2 m | −5.8 / −6.3 dB per decade of altitude | −33.3 / −32.8 |
| First-bottom-return misses (detector) | 4.5 % / 4.0 % | 0 / 0 |
| Far-decile floor at 20 m | 18.2 / 18.6 dB | 22.0 / 23.3 dB |

The calibration report scores the shape referenced to each ping's own peak at 24.8–26.4 dB RMS
over 6–14.5 m against a 3.1 dB site floor (MEASURED · `analysis.calibration_cli` →
`out/g_calib/base/calibration.md`). Three separable defects: (i) the absolute anchor, fitted at
6–9 m altitude on a harbour with an r⁻⁴ law, lands 18 dB hot at 1.2 m; (ii) the simulated
range law is 11–12 dB per decade steeper than the device's at this altitude, and the extra
steepness equals the first-power angular term (sin θg ≈ alt/r, −10 dB per decade) — with true
Lambert it would be 20 dB per decade steeper still, so at 3–10° grazing the device's stream
falls *less* steeply than any cosⁿ law with n ≥ 1 on a flat floor, which the physics explains
either by multipath filling the far range [R1, p. 323; R5, p. 230] or by a partial receiver
TVG/AGC [R26, §4.2.2] (UNCERTAIN which; a pass at ≥ 3 m altitude on the same site separates
them); (iii) the device's peak level barely moves with altitude (−6 dB per decade against the
model's −33), the fingerprint of gain regulation or compression that the model does not have
[R26, §4.2.2, §5.3.1].

**Texture (MEASURED · `analysis.svlog_compare` → `out/c_compare/compare.md`).** High-pass
speckle standard deviation 6.0–6.1 dB real vs 5.7 dB sim; range correlation at lag 1 0.55 vs
0.54–0.62; along-track correlation at lags 1/3/10 0.38/0.30/0.23 vs 0.44/0.37/0.32; 2–98 %
per-ping span 52–53 dB real vs 64–65 dB sim; ping period 50 ms in both, 0 counter resets in
both. The single-look statistics match; the dynamic range does not, because the sim's floor is
noise and the real floor is reverberation. The world used `relief: synthetic`
(`metadata.yaml`); the ripple field visible in every real crop is therefore not in the world,
which the along-track lag-10 correlation reflects.

**Verdict.** Geometry reproduced; radiometry not. The level anchor is a calibration gap, the
slope and the altitude dependence are physics gaps (angular law at low grazing, multipath,
gain regulation). Severity: threatening for any per-range intensity claim of E1 at this site.
→ P6-1, P6-4, P6-9.

### 3.10 The GCS scaling option

**Observation.** Horizontal scaling is right; vertical is still wrong; remove the button and
make the waterfall and the AI pictures share one scale.

**What the code does (VERIFIED, Part 2.6).** The toggle stretches rows with a `QTransform`
by `row_pitch/col_pitch` clamped to [0.05, 20]; a non-finite or zero pitch silently draws
square pixels; the stretch is re-applied only when the aspect moves by more than 5 %; on a
range change the whole history is redrawn at the newest column pitch. The seabed pictures
resample rows from their own estimator instance. In the simulator session that motivated the
observation the range changed 36 → 20 → 15 m inside one recording (MEASURED ·
`analysis.svlog_compare` → `out/c_compare/compare.md`), so rows acquired at 36 m were
re-stretched to the 15 m pitch — a mechanism for "horizontal right, vertical wrong" that needs
no estimator error at all (UNCERTAIN whether it is the one the user saw; it is the one the code
guarantees).

**Literature.** One geometrically correct behaviour exists — the along-track spacing is the
smaller of beam footprint and distance travelled per ping, and anamorphosis targets 1:1 [R5,
p. 66]; a wrong assumed speed stretches or compresses [R5, p. 237] — and nothing prescribes an
uncorrected option.

**Verdict.** Confirmed; software gap; cosmetic for the physics, material for labelling
consistency. Remove the toggle, render the on-screen waterfall by row resampling through the
same `_emit_square` path the pictures use so both are the same pixels by construction, keep a
visible "no speed" state instead of a silent 1.0, and give each acquisition segment its own
pitch. → P6-12.

### 3.11 Default contrast

**Evidence (VERIFIED).** `display.gamma` ships at 0.7 (`config/default.yaml:79`);
the user's own mesh-container session ended at γ = 0.48 while the two beach sessions kept 0.7
(VERIFIED in `metadata.json`, `display_settings_at_end`, of the three sessions); the slider
does not reach the saved PNGs, which use the configuration value (`seabed_imager.py:184`).
Blondel represents images "with highest backscatter values as white and lowest … as black"
and stretches by histogram, with no exponent prescribed [R5, pp. 63, 72]; the one measured
reference viewer comparison in this project (`project_review.md` §3.2) found ours darker and
harsher than SonarView's window.

**Verdict.** Confirmed; software; lower the default toward the value the operator chose
(0.5), make the exported pictures follow the same transfer the operator sees or state in the
metadata that they do not, and keep the `db_window` transfer as the candidate default pending
a paired SonarView comparison. → P6-13.

---
## Part 4 — Gap analysis

Classes: **physics** = an unmodelled effect; **calibration** = the right model with wrong or
unvalidated parameters; **software** = a defect independent of the acoustic model. Severity:
**threatening** = undermines the sim-to-real argument of `project_synthesis.md` (E1
calibration, the aspect-response and transfer-gap experiments); **material** = changes what
the simulator can be used for; **cosmetic** = visible, not evidential.

| # | Gap | Evidence | Class | Severity |
|---|---|---|---|---|
| G1 | No shadow fill: a culled bin holds only white receiver noise; the two multipath terms are off and, when on, fill nothing at < 1.5 m altitude | 3.6, 3.7; sweep | physics | threatening (shadow cue) |
| G2 | Opaque objects: no acoustic transmission through thin-walled targets; the field's object was a water-filled PP shell | 3.5, 3.6; [R4] | physics | threatening for that object family |
| G3 | Angular law is first-power cosine labelled Lambert; per-material exponent dead; no roughness or impedance model for seabed or objects | 2.2, 2.4; [R1, R26] | physics + documentation | material (calibration of E1 depends on it) |
| G4 | Absolute level anchored at 6–9 m altitude: +18 dB at 1.2 m; no gain regulation, device peak level flat versus altitude | 3.9 | calibration (anchor) + physics (AGC/saturation) | threatening for per-range intensity claims |
| G5 | Range-law slope 11–12 dB per decade steeper than the device at 1.2 m altitude | 3.9 | physics (multipath / TVG) — attribution UNCERTAIN | threatening at this site |
| G6 | Near-field beam: half the 20 m swath lies inside the 9 m far-field distance; the model uses a fixed 0.5° Gaussian | [V1]; 2.2 | physics | material |
| G7 | Reverberation floor: the real far range is reverberation-limited (18 dB) with seabed-like speckle; the sim floor is white noise | 3.6, 3.9 | physics | material |
| G8 | Wall corner band and ghosts unoccluded by nearer walls; face echo ignores terrain; a pontoon hides the quay behind it | 3.3, 2.3 | software | material (harbour), cosmetic (beach) |
| G9 | Material table compresses the literature's 15 dB seabed range into 3.7 dB; object values are judgement | 2.4 | calibration | material |
| G10 | Simulator never exercises gain compensation, side fallback, counter re-base, one-sided rows; GPS envelope velocities are zero | 2.7 | software (test coverage) | material (CM-2 promise untestable) |
| G11 | Planned path cut at 1000 s | 3.4 | software | cosmetic |
| G12 | Waterfall stretch versus picture resampling; silent fallback; range-change redraw | 3.10 | software | cosmetic (physics), material (labelling) |
| G13 | Contrast default and PNG/slider divergence | 3.11 | software | cosmetic |
| G14 | Ground-truth `shadow_bins` uses `h·r/alt` while the picture uses the terrain profile; the lattice crate's `visible` label reads False at 3 m across in the sweep while the picture shows it | 2.2, 3.6, 3.8 | software (labels) | material for training labels |
| G15 | Documentation drift: stale noise-floor row, duplicated tilt row, "Lambert's law proper" | 2.5 | documentation | cosmetic |
| G16 | Pontoon signature is a judgement value; no field anchor | 3.1 | calibration | cosmetic |

What threatens the thesis is not the pixel look but the *cue physics*: the detector is trained
on shadows and highlights, and in the beach regime the simulator produces shadows 30 dB deeper
and highlights 8–10 dB brighter than the device does for the same object, with a level 18 dB
off and a range slope 11 dB per decade off. STARS' evidence that background statistics decide
transfer [R17] and Sung's that added noise without the right degradation does nothing [R9]
point the same way: fix the fill physics and the level regulation before any more texture
work.

---

## Part 5 — Recommendations, prioritised

1. **Give shadows their physics before anything else (G1, G7).** Enable and re-derive the
   two fill paths for the shallow profile: the second-bottom ghost with a displacement and
   gain derived from the geometry (surface reflection ≈ −1 dB, bottom loss from the seabed
   material, extra spreading), and the surface mirror evaluated with the main lobe rather than
   the sidelobe floor at the altitudes where it matters; replace the white receiver floor with
   a reverberation floor whose level follows the seabed return. Gate: the NAFCO box measurement
   of 3.6 (shadow −9.6 dB mean, fill 0.28, +37 dB above the floor) reproduced within 3 dB and
   0.1 in fill by the synthetic sweep at 1.2 m.
2. **Model transmission through thin-walled objects (G2).** A per-object `transmission`
   (or impedance-derived opacity) that attenuates the horizon cull instead of zeroing it, and
   a `plastic_box` class with the NAFCO defaults and an exact-size form. Gate: the same
   measurement, with the class in place of `mesh_crate`.
3. **Re-anchor the level at the field altitude and add gain regulation (G4).** Fit
   `calibration_db_offset` on the beach corpus at 1.2 m as well as the harbour corpus at
   6–9 m and model the device's regulation (a compression or AGC term) so that the peak level
   moves −6 dB per decade of altitude as measured, not −33. Gate: `a` within ±3 dB and the
   altitude slope within ±5 dB per decade in `scripts/a_level_match.py`.
4. **Settle the angular law with the two-altitude lever the project now has (G3, G5).**
   The harbour (6–9 m) and beach (1.2 m) corpora together separate `lambert_exponent`,
   `tvg_compensation` and a multipath term that the single-altitude fit could not; fix the
   documentation to call the current law Lommel–Seeliger; wire or delete
   `Material.lambert_exp`. Gate: real-minus-sim slope within ±3 dB per decade at both
   altitudes.
5. **Occlude walls properly (G8).** Cull the corner band and every mirror source against
   nearer walls, let terrain occlude a face, and let the face loop skip a pontoon whose band
   the ray passes under. Gate: `scripts/e_walls_render.py` default equals the
   `wall_corner_gain = 0` variant at the far face for the 517 census pings.
6. **Make the simulator exercise the downstream paths (G10).** Add a gain walk (4→7), a
   per-side `dropped_ping_prob`, a counter reset/offset option and a `channel_number: 255`
   option to the sonar profile, off by default; publish GPS velocities in the processor
   envelope (BlueBoat-SSS). Gate: `sss_svlog_compare` reports counter resets > 0 and shared
   stamps < 100 % on a fault-injection run.
7. **Near-field beam (G6).** Widen the along-track beam and raise the sidelobe floor inside
   the far-field distance, per the vendor statement, with the 0.5° value beyond 9 m. Gate: a
   point target's along-track extent at 3 m versus 12 m matches the vendor's near-field
   description qualitatively; a field capture of a point target settles the numbers.
8. **Re-anchor the material table (G9)** to the literature contrasts and to an impedance
   argument for objects, keeping existing worlds bit-identical through a versioned table.
9. **GCS: one scale, one transfer (G12, G13).** Remove the toggle, resample the on-screen
   waterfall, show the no-speed state, per-segment pitch; default γ 0.5 and PNGs that follow
   the slider or say they do not.
10. **GCS: read the deployed trajectory (G11).** The MCS route, without touching Control.
11. **Fix the labels (G14)** so `shadow_bins` and `visible` come from the rendered mask, not
    the flat-bottom formula.
12. **Documentation hygiene (G15).**

Field captures that no offline work replaces: a steel box and the PP box side by side at
1–1.5 m (transmission); the same site at ≥ 3 m altitude (slope attribution); a fixed-gain pass
(regulation); a point target at 3 and 12 m (near field); a pontoon with known geometry.

---
## Part 6 — Update plan

> **Status: implemented on 2026-09-18, the same day.** Read **Part 7** for what was
> actually done, what gates it, and the two numbers in this plan that did not survive
> being measured properly (the −6 dB per decade altitude law and the AGC mechanism
> behind it). This part is kept as written — it is the plan the work was done against,
> not a record of the work.

Effort: S ≤ 2 h, M ≤ 1 day, L > 1 day. Every item is confined to `BlueBoat-SSS-Sim` unless the
module column says otherwise; none touches `BlueBoat-Control` or `BlueBoat-MCS` (v1.0 frozen).
Verification gates name the review script whose number must move.

| # | Item | Module / files | Effort | Verification gate | Field capture needed? | Depends on |
|---|---|---|---|---|---|---|
| P6-1 | Level re-anchor + gain regulation: fit `calibration_db_offset` on both corpora; add a compression/AGC term so the peak level follows the measured −6 dB per decade of altitude | sim `sonar/config.py`, `sonar/encoder.py`, `docs/sonar_model.md` §6 | M | `scripts/a_level_match.py`: `a_offset_db` within ±3 dB, altitude slope within ±5 dB/decade; `calibration_cli` shape residual ≤ 6 dB RMS | a fixed-gain pass on the beach helps; not required for the first fit | — |
| P6-2 | `plastic_box` class: NAFCO defaults, `params_schema` for length/width/height, lidded solid shell; material `pp_shell` with impedance-derived reflection | sim `worldgen/objects.py`, `worldgen/materials.py`, `docs/configuration_guide.md` | S | catalog smoke section; Screen-4 form shows the three fields; `explicit:` round-trip bit-identical | no | — |
| P6-3 | Object transmission: per-object opacity attenuating the horizon cull; highlight from the near face | sim `worldgen/objects.py` (raster channel), `sonar/renderer.py` (`_ping_geometry` cull) | M | `scripts/f_altitude_sweep.py` with the NAFCO class: shadow mean −9.6 ± 3 dB, fill 0.28 ± 0.1 at 1.2 m | steel vs PP box side by side confirms the mechanism | P6-2, P6-4 |
| P6-4 | Shadow fill physics: geometry-derived second-bottom ghost, main-lobe surface mirror where the altitude warrants it, reverberation floor; a `shallow_beach_sonar.yaml` profile with them on | sim `sonar/renderer.py`, `sonar/multipath.py`, `sonar/noise.py`, `config/` | L | `scripts/d_blob_detect.py` on a re-run of the crate session: sim blob fill ≥ 0.2 and mean ≥ −15 dB; smoke `[2b]` FBR lock kept | the ≥ 3 m altitude pass separates fill from TVG | P6-1 |
| P6-5 | Wall occlusion: cull corner band and mirror sources against nearer walls; terrain occludes faces; pontoon-aware face loop | sim `sonar/renderer.py:535-549,640-697`, `sonar/multipath.py:85-192` | M | `scripts/e_walls_render.py`: default equals `corner_gain_0` at the far face; census `B_c1` share > 6 dB drops from 0.97 to < 0.05 | no | — |
| P6-6 | Pontoon signature: float faces and mooring piles (upright cylinders) as scene furniture; raise `wall_pontoon_specular` only with an anchor | sim `worldgen/sdf_writer.py`, `worldgen/objects.py`, `config/default_sonar.yaml` | S–M | smoke `[4d]` pontoon case unchanged for the seabed beneath | a pontoon recording with known geometry | — |
| P6-7 | Face loop bug: do not `break` on a pontoon whose band the ray passes under | sim `sonar/renderer.py:653-697` | S | smoke `[4d]`: quay behind a pontoon renders its face | no | — |
| P6-8 | Near-field beam: along-track width and sidelobe floor as functions of range inside 9 m | sim `sonar/acoustics.py`, `sonar/renderer.py` (line offsets) | M | point-target extent at 3 m vs 12 m; smoke `[2d]` | a point target at two ranges | — |
| P6-9 | Angular law: two-altitude fit of `lambert_exponent` / `tvg_compensation` / multipath; rename the law in the docs; wire or delete `Material.lambert_exp` | sim `sonar/config.py`, `analysis/calibration.py`, `docs/sonar_model.md`, `worldgen/materials.py` | M | `scripts/a_level_match.py` slope difference within ±3 dB/decade on both corpora | the ≥ 3 m altitude pass | P6-1 |
| P6-10 | Fault-injection knobs: gain walk, per-side drops, counter reset/offset, `channel_number: 255`; processor GPS velocities | sim `sonar/config.py`, `ros/sss_sim_node.py`, `sonar/encoder.py`; **BlueBoat-SSS** `src/sss_processor_node.py:631` | M | `sss_svlog_compare`: resets > 0, shared stamps < 100 %; GCS tests `test_processor_assembly.py` pass on a fault run | no | — |
| P6-11 | GCS planned path from the deployed YAML (`points`, `duration_s`) with `/set_path` as fallback | **BlueBoat-SSS** `blueboat_gcs/ros/path_listener.py`, `gui/map_layers.py` | S | GCS shows all 2 631 points of `plage_bathymetry2`; `test_planned_path_dedupe.py` | no | — |
| P6-12 | GCS waterfall: remove the toggle, resample rows through the seabed imager's path, visible no-speed state, per-segment pitch | **BlueBoat-SSS** `blueboat_gcs/gui/waterfall_view.py`, `core/waterfall_service.py`, `core/along_track.py` | M | `test_seabed_pictures.py`: screen tile == picture rows; a replay of the 36→20→15 m session shows consistent aspect per segment | no | — |
| P6-13 | GCS contrast: default γ 0.5; PNG export follows the slider or records that it does not; `db_window` evaluation | **BlueBoat-SSS** `blueboat_gcs/config/default.yaml`, `core/seabed_imager.py`, `core/display_model.py` | S | `test_display_startup.py`, `test_display_model.py` | paired SonarView comparison for the transfer decision | — |
| P6-14 | Labels from the rendered mask: `shadow_bins` and `visible` from the cull, per object | sim `sonar/renderer.py:816-873` | S | smoke `[4c]`: label shadow length equals the rendered run within one bin on flat sand | no | — |
| P6-15 | Documentation: stale noise-floor row, duplicated tilt row, law naming; record the pontoon and material judgement values with their status | sim `docs/sonar_model.md`, `.claude/CLAUDE.md`, `TODO.md` | S | none | no | — |
| P6-16 | Material table re-anchor (versioned; existing worlds bit-identical) | sim `worldgen/materials.py`, survey layer thresholds | M | smoke `[8]`/`[12]` bit-identity on legacy worlds; new-table worlds show the literature contrasts | a capture over a known bottom | P6-9 |

Suggested order: P6-5 and P6-7 (small, pure software) → P6-2 → P6-1 → P6-4 → P6-3 → P6-9 →
P6-8 → P6-14 → P6-10 → GCS items P6-11/12/13 (independent, any time) → P6-16, P6-6, P6-15.

---

## Appendix A — Measurement index

| Number in the text | Script | Output |
|---|---|---|
| Level offset, slopes, altitude dependence, FBR peaks, misses (3.9, 4) | `scripts/a_level_match.py` | `out/a_level/level_match.json`, `level_curves.csv`, `level_match.png` |
| Depth alignment real / sim / authored (3.9) | `analysis.bathymetry` ×2, `scripts/b_fbr_align.py` | `out/b_fbr/*_soundings.csv`, `fbr_align.json`, `fbr_vs_s.csv`, `fbr_vs_s.png` |
| Ping law, levels, texture, counter and stamp statistics (2.7, 3.8, 3.9, 3.10) | `analysis.svlog_compare` | `out/c_compare/compare.md`, `compare.json` |
| Real box patch, sim crate blobs with outside reference, box-like scan (3.6) | `scripts/d_box_measure.py` | `out/d_shadow/box_measure.json`, `real_box_zoom.png`, `scan_*.png` |
| Sim crate per-pass measurement, local reference (3.6) | `scripts/d_shadow_sim.py`, `scripts/d_shadow_local.py` | `out/d_shadow/shadow_sim_rows.csv`, `shadow_local.json`, `sim_crate_*_crop.png` |
| Blob detector on both logs (3.6) | `scripts/d_blob_detect.py` | `out/d_shadow/blobs.json`, `blob_*.png` |
| Seabed rise nadir → crate (3.6) | `scripts/d_sim_slope.py` | `out/d_shadow/sim_slope.json` |
| Wall census and cluster (3.3) | `scripts/e_walls_find.py` | `out/e_walls/wall_hits_summary.json`, `wall_hits.csv`, `wall_cluster_crop.png`, `wall_candidates_map.png` |
| Wall render variants (3.3) | `scripts/e_walls_render.py` | `out/e_walls/render_variants.json`, `render_variants.png` |
| Synthetic altitude sweep (3.6, 3.7, 3.8) | `scripts/f_altitude_sweep.py` | `out/f_altitude/sweep.csv`, `sweep.json`, `contrast_vs_altitude.png` |
| Calibration report, invariants, nadir column (2.7, 3.9) | `analysis.calibration_cli` | `out/g_calib/base/calibration.md`, `calibration.json` |
| Code line anchors (Part 2) | `scripts/cite.sh` | `out/citations.txt` |

Shared reduction: `scripts/common.py` (per-ping dB inversion through the package's own
`scale_to_db`, first-bottom-return index through its `fbr_bin`, GPS → world through
`core.geo`). Sonar profiles used for the offline renders are `cfg/sonar_20m_600.yaml`,
`cfg/sonar_36m_600.yaml`, `cfg/sonar_15m_1200.yaml` (copies of the shipped default with one
key changed). All scripts run from the package source root with `PYTHONPATH=<root>/pypath`
(which exposes only `lark`).

## Appendix B — Run log and environment notes

- Tool CLIs are not installed as console scripts in the workspace venv; every tool ran as
  `python3 -m blueboat_sss_sim.analysis.<module>`.
- `svlog_reader.read_svlog` must be called with `with_power=True`; without it every profile
  reads `length_mm = 0`, `num_results = 0`, `gain_index = −1`.
- `calibration_cli` compares curve shape referenced to each ping's own first-bottom-return
  peak and refuses a 15 m-versus-20 m pairing; a 20 m sonar profile was supplied.
- The smoke test writes to a fixed `/tmp` path outside the evidence root and was not run in
  this pass (no code changed).
- The session scratchpad was wiped twice between sessions; the evidence root is the
  persistent mirror. `runs.log` in the root records start/end times and return codes.
- Reading assistants were interrupted by session limits three times; their extracts are the
  five files under `lit/`, each persisted incrementally; the remaining sources were read
  directly (GeoHab PDF, ESAB, S3Simulator, Attia 2026, Cocchi 2024, vendor pages).

## Appendix C — Verification of this document

Filled by `scripts/verify_all.sh` after the text was final; see the block appended at the end
of this file.

### Appendix C results (run 2026-09-18, `scripts/verify_measured.py`, `scripts/verify_cites.py`, `scripts/verify_dois.sh`; outputs under `verify/`)

| Check | Result |
|---|---|
| DOIs cited (`https://doi.org/…`) resolved through Crossref or DataCite to the cited title | 26 of 26 resolved, 0 unresolved (`verify/doi_check.txt`) |
| List-B sources named as a citation in Parts 1–5 | none (they appear only as "cited by [Rn]") |
| `path:line` citations resolved by basename against the 2026-09-17 anchor harvest, cited range within ±2 lines of a harvested anchor | citations: 87 matched, 0 problems (`verify/cites_check.txt`) |
| MEASURED blocks with an existing output reference in their section, and every plain number in them found in those outputs within its printed precision | MEASURED blocks: 12; sections lacking an output reference: 0; unmatched numbers: 0 (`verify/measured_trace.txt`) |
| Marker counts | VERIFIED 30, MEASURED 16, UNCERTAIN 9 |
| Git status, before → after this pass | superproject gains only `?? sim_review.md`; the working-tree diffstats of `BlueBoat-SSS` and `BlueBoat-SSS-Sim` move by the `CLAUDE.md` freeze notes only (+4/−1 and +6/−0 lines); `BlueBoat-Control` and `BlueBoat-MCS` status empty before and after (`verify/git_status_{before,after}.txt`) |
| Reflogs of the six repositories | no new entries — no commit, checkout or push happened (`verify/reflog_{before,after}.txt`) |
| Field data, sessions, world folders | 860 files, sizes and modification times identical before and after (`verify/protected_mtimes_{before,after}.txt`) |

---

## Part 7 — Implementation record (2026-09-18, same day)

Part 6 was implemented in the session that followed this review. This part records
**what was done, what it is gated by, and where the review turned out to be wrong** —
the third of those matters most, because two of the review's own numbers did not
survive being measured properly.

Markers as in the rest of the document. Every number below is MEASURED unless marked
otherwise, and every gate named is in a suite that runs offline.

### 7.1 What the implementation changed about the review's conclusions

**The −6 dB per decade altitude law (par. 3.9, P6-1) was wrong, and so was the
mechanism.** The review estimated the device's level-versus-altitude behaviour from
two recordings and attributed the flatness to AGC. Measured over **every gain-4 ping
of all 19 corpus recordings** (0.92–12.19 m altitude), the reported peak follows

    max_pwr_db = 66.60 − 11.28 · log₁₀(altitude_m),  rms 1.57 dB

and the FBR bin itself follows `59.44 − 15.38 · log₁₀ alt` (rms 2.06). That is a law,
not a regulator. What made the simulator fall 20–27 dB per decade instead was giving
the **coherent** component the diffuse field's spreading: a specular reflection is the
field of an image source and spreads once over the folded path, not twice. No
compression term was needed, and none was added.

**"18 dB hot" was a slope, not an offset (par. 3.9, 4.2, G4).** Fitting
`lambert_exponent`, `tvg_compensation` and `calibration_db_offset` on *two* altitudes
at once — `bath3` at 1.40 m (12 371 pings) and `reflectionEvidenceFullharbour` at
7.33 m (1 445 pings) — lands at (1.0, 0.30, 81.1 dB) with **0.92 dB rms** on both
curves. The old (1.0, 0.0, 97.2) is the same fit done at one altitude. This also
settles G3's first half: the angular exponent **is** determined once two altitudes are
in play (0.75 and 1.25 both score worse), and it is 1.0 over sand — which is why the
dead per-material `lambert_exp`, claiming 1.6 for exactly that sand, was deleted
rather than wired.

**The near-field beam (G6, P6-8) is ruled out by the corpus, not confirmed by it.**
An unfocused 0.38 m array — what a 0.5° beam at 450 kHz implies — would floor the
along-track footprint across the whole swath, and would put the lag-1 along-track
texture correlation at 0.76 where the corpus measures **0.36–0.66** at 1 m/s. The
device focuses its near field. The knob exists (`array_length_m`) and ships at **0**;
what happens inside ~3 m remains undetermined, and the point-target capture the review
asks for is still the thing that would settle it.

### 7.2 The changes, and what gates each

| # | What was implemented | Gate (all offline) |
|---|---|---|
| P6-1, P6-9 | Two-altitude re-fit: `tvg_compensation` 0 → 0.30, `calibration_db_offset` 97.2 → 81.1, `specular_spreading_exponent` → 2.0, `specular_strength` 30 → 12; noise floor and water column re-expressed at the new offset; `lambert_exponent` confirmed 1.0 and `Material.lambert_exp` deleted | smoke `[2c]` altitude law (sim 71.9 − 10.8 vs device 66.60 − 11.28), `[2c]` level anchor 66.10 ± 0.5 dB, `[2e]` identifiability pair re-derived (tvg 0.20 ≡ lambert 1.45), `[2f]` the corpus sections |
| P6-2 | `plastic_box` class (the NAFCO box's exact dimensions as class knobs) on a new `pp_shell` material (ρ 0.18 from the polypropylene slab formula) | smoke `[8]` "the field target is a class of its own" |
| P6-3 | Per-material two-way `transmission` attenuating the horizon cull instead of zeroing it; a transmission raster on the scene, absent from `scene.npz` when nothing transmits | smoke `[8]`: the shell's shadow reads **−9.6 dB** under the open seabed — the field measurement, reproduced — while an opaque twin still blacks it out |
| P6-4 | `reverberation_db` (18): a shadow's floor follows the ping's own unoccluded level with the seabed's speckle; `config/shallow_beach_sonar.yaml` | smoke `[8]`: −18.9 dB with the floor on, −49.6 with it off; `[4b]` the profile differs in the range and the two paths alone |
| P6-5, P6-7 | Wall faces occluded by nearer faces and by the terrain horizon (so a quay behind a **pontoon** is imaged and a quay behind a quay is not); ghosts and the corner band culled on both real legs of the folded path | smoke `[4d]`: a second quay adds **±0.00 dB** past the first's foot; a quay behind a pontoon returns **+78 dB** over the same scene without it |
| P6-6 | `mooring_pile` class — the furniture a pontoon line is actually held by. `wall_pontoon_specular` **unchanged**: still no field anchor | smoke `[8]` catalog |
| P6-8 | `array_length_m` knob, shipped at 0 (see 7.1) | smoke `[4b]` |
| P6-10 | Four `fault_*` knobs + `config/fault_injection_sonar.yaml` (gain walk, counter restart, per-device offset, `channel_number: 255`, per-side drops); **BlueBoat-SSS**: `GLOBAL_POSITION_INT` velocities from `velocity_local` instead of zeros | smoke `[4b]` (all on the wire, byte 34 included); `BlueBoat-SSS` pytest |
| P6-11 | GCS reads the station's own deployed trajectory (`core/deployed_path.py`), `/set_path` as fallback | `tests/test_deployed_path.py` (7 tests) |
| P6-12 | Waterfall: toggle removed, aspect from the rows on screen, scale state on screen (including "unavailable" and "mixed") | `tests/test_waterfall_pick.py` |
| P6-13 | Contrast slider reaches `DisplayModel.gamma` (hence the saved AI pictures); shipped γ 0.7 → 0.5 | `tests/test_display_startup.py` |
| P6-14 | `shadow_bins` / `visible` read off the rendered mask | smoke `[8]`: a 0.35 m block 22 bins, a 0.05 m can 2, a brick in the block's shadow **0** and not visible |
| P6-15 | `docs/sonar_model.md` §2, §3, §5, §6, §7, §11; `seabed_model.md` §5, §7.1; `configuration_guide.md`; `topics.md`; `architecture.md`; `developer_guide.md`; `svlog_depth_survey.md`; three `CLAUDE.md`s and two `TODO.md`s | — |
| P6-16 | `config/materials_literature.yaml`: the J&R contrasts as an override (5.9 → **14.5 dB** span) with the level offset its anchoring implies | smoke `[8]` |

Also implemented in the same session, from the operator's own reports rather than from
this review: the World Builder's OOM death (the `.svlog` shading inversion is now cached
and chunked — 1.6 GB on a 129 MB file, 0.04 ms on a cache hit), the half-built world
folder it left behind (builds are assembled in a hidden sibling and renamed into place,
so a folder under `~/worlds` is either whole or absent) and the wizard autosave that
survives a kill; the relief striping (*"the path of the boat is printed"* — a
coverage-weighted blend plus an across-track debias, keeping 0.89 of a 10 m bedform);
the blocky reflectivity (bilinear with normalised convolution instead of
nearest-neighbour); and dry land as a first-class layer with a rounded shoreline.

### 7.3 What Part 6 asked for and did **not** get

* **A compression / AGC term** (P6-1's wording). Not implemented, because the
  measurement says the effect is a spreading law, not a regulator. If a fixed-gain
  capture ever shows a regulator, the place for it is the encoder.
* **A raised `wall_pontoon_specular`** (P6-6). Explicitly conditional on a field anchor
  in the plan; there is still none.
* **Row-by-row resampling of the on-screen waterfall** (P6-12's second clause). The
  view still draws one transform; what changed is that the transform is taken from the
  rows on screen and the picture says so when they disagree. Per-row resampling would
  be a rework of the tile pipeline, and the labelling error it would fix is now
  visible rather than silent.
* **A `db_window` evaluation** (P6-13's third clause). The transfer remains `power`
  with the default moved to γ 0.5; comparing the two against SonarView's recorded view
  state needs the paired recording listed under "field captures".

### 7.4 Residuals, stated so they are not rediscovered

1. The reported **peak** is 4–7 dB hot with the right slope (the seabed itself matches
   within 0.6 dB). It is the near-nadir return, which the tail fit excludes.
2. The **fill** statistic of a shadow (0.28 measured on the field box) is not
   reproduced exactly: the transmitted mean is, the tail statistics are speckle.
3. Everything in 7.1's last paragraph: the near field inside 3 m is unmeasured.
4. The field captures this review listed are all still outstanding, and three of them
   (fixed gain, ≥ 3 m altitude at the same site, a point target at two ranges) are now
   the *only* way to move constants that are currently held rather than fitted.

*End of document.*
