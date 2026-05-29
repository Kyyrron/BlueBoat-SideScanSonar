import numpy as np
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors


# ----------------------------------------------------------
# Load NPZ
# ----------------------------------------------------------

data = np.load("sonar_mosaic.npz")

x = data["x"]
y = data["y"]
intensity = data["intensity"]

# ----------------------------------------------------------
# Normalize intensity
# ----------------------------------------------------------

normalizer = mcolors.Normalize(
    vmin=np.min(intensity),
    vmax=np.max(intensity)
)

normalized_intensity = normalizer(intensity)

# ----------------------------------------------------------
# Colormap
# ----------------------------------------------------------

cmap = mcolors.LinearSegmentedColormap.from_list(
    "sonar_orange",
    [
        (0.0, 0.0, 0.0),
        (1.0, 0.5, 0.0),
    ]
)

# ----------------------------------------------------------
# Plot
# ----------------------------------------------------------

fig, ax = plt.subplots(figsize=(10, 10))

scatter = ax.scatter(
    x,
    y,
    c=normalized_intensity,
    cmap=cmap,
    s=1
)

ax.set_xlabel("X world (m)")
ax.set_ylabel("Y world (m)")
ax.set_title("Side-scan sonar mosaic")

ax.axis("equal")
ax.grid(True)

cbar = plt.colorbar(scatter)
cbar.set_label("Normalized intensity")

plt.show()