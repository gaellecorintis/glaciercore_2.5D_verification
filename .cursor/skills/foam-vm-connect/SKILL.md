---
name: foam-vm-connect
description: Connect over SSH to the OpenFOAM simulation VM (foam-remote, reached via ProxyJump through the Mac Studio) and transfer files between the local Mac, the VM, and a Windows machine. Use when the user wants to ssh into the foam VM, set up or fix the SSH config/ProxyJump, or copy files (DXF, STEP, meshes, results) with scp between Mac, the VM, and Windows.
---

# Connect to the foam VM and transfer files

The OpenFOAM work runs on a Linux VM ("foam") hosted on a Mac Studio. The VM is
reached from the local Mac by **jumping through the Mac Studio** and a local
port-forward.

## SSH config (on the local Mac: `~/.ssh/config`)

```sshconfig
# The VM, reached by hopping through the Mac Studio
Host foam-remote
    HostName 127.0.0.1
    Port 2222
    User gaelle
    ProxyJump macstudio-gaelle
    StrictHostKeyChecking no
    UserKnownHostsFile /dev/null
```

`macstudio-gaelle` must be defined as its own `Host` block (the jump host).
`127.0.0.1:2222` is a port-forward on the Mac Studio that maps to the VM's SSH.

## Connect

From the Mac:

```bash
ssh foam-remote
```

The VM is Ubuntu 22.04 (arm64), 24 cores, with OpenFOAM 13 already sourced in
`~/.bashrc`. The main case lives under `~/OpenFOAM/`.

## File transfer

### Mac → VM
```bash
scp "/path/on/mac/file.step" foam-remote:~/OpenFOAM/hm27_ne_quarter/
```

### VM → Mac
```bash
scp foam-remote:~/OpenFOAM/hm27_ne_quarter/results/plot.png "/path/on/mac/"
```

### Mac → Windows (direct, same network)
```bash
scp "/path/on/mac/file.step" SolEngLaptop_2@<WINDOWS_IP>:"C:/Users/SolEngLaptop_2/Documents/Gaelle/HM27/mesh/"
```

### Windows → Mac (pull, run in Windows PowerShell)
```powershell
scp gaelle@<MAC_IP>:/Users/gaelle/path/file.dxf .
```

## Gotchas (hit in practice)

- **Find the right IP**: on the Mac use `ipconfig getifaddr en0` (Wi-Fi) or
  `en1` (Ethernet). Don't confuse the Mac IP with the Windows IP — a `ping`
  reply with `TTL=128` is a Windows host, `TTL=64` is macOS/Linux.
- **Typing `@` on a Swiss-French Mac keyboard**: `Alt (⌥) + G`.
- **Password prompt shows nothing while typing** — that's normal, just press Enter.
- **`Permission denied`**: verify the username and that Remote Login / OpenSSH
  Server is enabled on the destination; use `scp -v` to debug.
- **`Connection refused` / firewall (corporate network)**: SSH/HTTP ports are
  often blocked. Fallbacks: USB key, or a cloud drive (OneDrive/Drive).
- Both machines must be on the **same network** for the direct Mac↔Windows scp.
