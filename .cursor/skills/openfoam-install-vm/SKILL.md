---
name: openfoam-install-vm
description: Install and set up OpenFOAM 13 on an Ubuntu 22.04 (jammy) VM via the official openfoam.org apt repository, source the environment, and verify the install for serial and parallel (MPI) runs. Use when setting up OpenFOAM on a new Ubuntu machine/VM, fixing the environment sourcing (foamMultiRun/blockMesh not found), or preparing to run OpenFOAM in parallel.
---

# Install & set up OpenFOAM 13 on an Ubuntu VM

Target environment (the foam VM): Ubuntu 22.04 LTS, 24 cores, OpenFOAM 13 from
openfoam.org installed under `/opt/openfoam13`, Open MPI 4.1.2.

## Install (apt, openfoam.org)

```bash
# 1. Add the openfoam.org repository + key
sudo sh -c "wget -O - https://dl.openfoam.org/gpg.key | gpg --dearmor > /etc/apt/trusted.gpg.d/openfoam.gpg"
sudo add-apt-repository "deb http://dl.openfoam.org/ubuntu jammy main"

# 2. Install OpenFOAM 13
sudo apt update
sudo apt install -y openfoam13
```

This installs into `/opt/openfoam13`. (Works on amd64 and arm64.)

## Source the environment

Add this to `~/.bashrc` so every shell has the OpenFOAM tools:

```bash
source /opt/openfoam13/etc/bashrc
```

Then `source ~/.bashrc` (or open a new shell). If commands like `blockMesh`,
`foamMultiRun`, `checkMesh`, or `reconstructPar` are "not found", the env is not
sourced — this single line is the fix.

## Verify

```bash
# version + paths
foamVersion 2>/dev/null || echo $WM_PROJECT_VERSION   # -> 13
which blockMesh checkMesh foamMultiRun
# parallel stack
mpirun --version | head -1                            # Open MPI 4.1.x
nproc                                                 # available cores (24)
```

## Running solvers in parallel

```bash
source /opt/openfoam13/etc/bashrc
decomposePar -allRegions            # split mesh across N subdomains (system/decomposeParDict)
mpirun -np 24 foamMultiRun -parallel
reconstructPar -allRegions -latestTime
```

For post-processing on a decomposed (not reconstructed) case, run the function
in parallel too, e.g.:

```bash
mpirun -np 24 foamPostProcess -parallel -region fluid -time 5000 -func "patchAverage(patch=outlet, p)"
```

## Notes

- `controlDict` with `runTimeModifiable true` lets you change settings (schemes,
  relaxation, write interval) on a running job — picked up at the next time step.
- Heavy reconstructs (large meshes) need free disk; check `df -h .` first.
