---
name: openfoam-launch-vm
description: Launch (boot) and stop the OpenFOAM QEMU VM ("foam") on the Mac Studio host, set its RAM/CPU allocation, and recover from a stuck boot. Use when the VM is off and needs starting, when SSH to foam/foam-remote times out because the VM is not running, when changing how much RAM the VM reserves, or when QEMU is stuck/stopped at boot. This is the host-side launch step that must happen BEFORE foam-vm-connect can connect.
---

# Launch the foam QEMU VM (host side, Mac Studio)

The OpenFOAM VM ("foam") runs as a QEMU `aarch64` guest on the Mac Studio. This
skill covers **starting/stopping the VM on the host**. Connecting to it once it
is up is covered by the `foam-vm-connect` skill.

VM files live in `~/vmware-foam-setup/`:

- `run-qemu-foam.sh` — original launcher (`-serial mon:stdio`, interactive console)
- `ubuntu-cloud-qemu.img` — the persistent disk (your `~/OpenFOAM/` data lives here; powering off never erases it)
- `edk2-vars.fd`, `seed.iso` — UEFI vars + cloud-init seed

## Recommended: daemonized launch (robust)

The original `run-qemu-foam.sh` uses `-serial mon:stdio`, which breaks when
started in the background (see Gotchas). Launch QEMU **daemonized** instead — it
detaches itself from the shell, survives terminal/agent interrupts, and writes
the boot console to a file:

```bash
cd ~/vmware-foam-setup
qemu-system-aarch64 \
  -name foam-qemu \
  -accel hvf \
  -machine virt,highmem=on,gic-version=3 \
  -cpu host \
  -smp cores=24 \
  -m 32G \
  -drive if=pflash,format=raw,readonly=on,file=/opt/homebrew/share/qemu/edk2-aarch64-code.fd \
  -drive if=pflash,format=raw,file=edk2-vars.fd \
  -drive if=virtio,format=qcow2,file=ubuntu-cloud-qemu.img \
  -drive if=virtio,format=raw,readonly=on,file=seed.iso \
  -nic user,model=virtio-net-pci,hostfwd=tcp:127.0.0.1:2222-:22 \
  -display none \
  -serial file:serial.log \
  -monitor none \
  -daemonize
```

Adjust two knobs for the workload:

- `-m 32G` — RAM the VM reserves on the host. **Reserved for the whole VM
  lifetime**, even when idle, so keep it low when sharing the Studio (Fusion,
  glaciercore). Rule of thumb: `host RAM − 32 GB − what glaciercore/Fusion need`.
  - SSH / scripts / post-pro: `32G`–`64G`
  - mesh < 50 M cells: `128G`
  - HM27 production mesh (50–150 M cells): `128G`–`256G`
- `-smp cores=24` — vCPUs (cap at ~half the host's physical cores when sharing).

## Verify the boot

QEMU's `hostfwd` accepts the TCP on `127.0.0.1:2222` **before** the guest sshd
is up, so a bare port check is not enough — test a real SSH:

```bash
# process alive + busy (R / high %CPU = booting)
ps -o pid,stat,%cpu,etime -p "$(pgrep -f qemu-system)" | cat

# real SSH check (retry for ~1–2 min while it boots)
ssh -o ConnectTimeout=5 -o BatchMode=yes foam 'echo VM_OK; hostname; nproc; free -g | head -2'
```

`free -g` should report ~the RAM you passed to `-m`. The boot console is in
`~/vmware-foam-setup/serial.log` if you need to debug.

Then connect / transfer files per the `foam-vm-connect` skill (`ssh foam` on the
Studio, `ssh foam-remote` from a laptop via ProxyJump).

## Stop the VM

```bash
ssh foam 'sudo poweroff'        # clean shutdown (preferred)
pkill -f foam-qemu              # hard stop only if SSH is gone
```

Stopping frees the reserved RAM (~the `-m` value) for Fusion / glaciercore.

## Gotchas (hit in practice)

- **VM "running" but SSH times out, 0% CPU, tiny RSS, `STAT = T`**: QEMU is
  **stopped** (SIGTTIN) because `-serial mon:stdio` tried to read the terminal
  while backgrounded. The daemonized launch above avoids this. To unstick an
  existing one: `kill -9 <pid>` then relaunch daemonized.
- **`qemu.log` empty + boot never progresses**: same stdio/background problem.
- **`setsid` not found**: macOS has no `setsid`; use `-daemonize` (above) instead.
- **`< /dev/null` + `-serial mon:stdio`**: QEMU can quit on monitor EOF — another
  reason to prefer `-serial file:` + `-monitor none`.
- **Powering off loses nothing**: the qcow2 disk is persistent; only RAM, running
  processes and the SSH session are lost. Never delete `ubuntu-cloud-qemu.img`.
- **RAM is reserved, not just used**: a 256 GB VM holds 256 GB away from the host
  even when idle inside — the usual cause of Fusion RAM pressure on the Studio.
