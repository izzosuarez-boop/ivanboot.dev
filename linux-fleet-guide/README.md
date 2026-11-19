# Operating a fleet of headless Linux workers — a field guide

A condensed, sanitized version of the runbook I wrote while building and operating a fleet of
**nine Ubuntu 24.04 VPS instances** running 24/7 desktop-automation workers (computer vision +
OCR on a virtual display), each with its own isolated network egress. Every step in the
original was executed on real machines; every documented failure was caught by hitting it.

The original is ~1,300 lines and names the production systems; this version keeps the
**methodology and the failure catalog**, which is what transfers to any fleet.

---

## 1. The philosophy: clone, don't rebuild

The setup *already lives in scripts inside the machine that works*. A new machine is not
deduced from prose — the scripts are copied, one config file changes (the per-machine proxy
credentials), and they run. Full setup time including transfers: **~45 minutes**.

Two of the earlier versions of the original runbook were wrong **for the same reason**: they
were written by reading other documents instead of looking at the machine. The rule that came
out of that, stated at the top of the runbook:

> **If this document disagrees with the real machine, the machine wins**:
> `ip route`, `apt-mark showmanual`, `systemctl`, `ls`.

### The corollary: the config is not the truth — the process is

A config file edited without restarting its service describes a machine that doesn't exist.
Found in production: a service started at 02:46 with proxy A, config edited at 07:06 to proxy
B — and for days the machine's *file* said B while its *traffic* went through A. Both checks,
always:

```bash
curl -s https://api.ipify.org                                   # where it ACTUALLY exits
ps -eo args --no-headers | grep -- "tun2sock[s]" | grep -o "@[0-9.]*:"   # what the PROCESS dials
```

If they disagree, the process wins, and what you have is an un-restarted edit.

## 2. Architecture (per machine)

| Layer | Implementation |
|---|---|
| Virtual display | Xvfb `:99` at a fixed resolution + openbox |
| Remote access | x11vnc + xrdp, firewalled to a single admin IP |
| Egress isolation | per-machine SOCKS5 proxy via `tun2socks` + `tun0` default route |
| Return-path survival | `iptables` CONNMARK + `ip rule fwmark 0x1 → table 100` so what enters by `eth0` leaves by `eth0` |
| Services | 8–9 systemd units per machine (display, WM, VNC, 3 proxy stages, telemetry, watchdog timer) |
| Watchdog | a supervisor that detects a dead worker process and restores it **in 3–4 s** |
| Firewall | ufw default-DROP, fail2ban, SSH by key only |

Everything exits through the tunnel **by default** — applications need no proxy flags because
they inherit the route table. Exceptions (the machine's own subnet, the proxy's own IP) are
pinned `/32` routes so the tunnel never swallows its own transport.

### Switching a machine's egress is THREE changes, not one

Editing the proxy config file is not enough. The default route goes through `tun0`, so the
connection *to* the new proxy must be pinned out `eth0` or it routes into the tunnel and bites
its own tail:

```
1. the 0x1 iptables mark for the new proxy IP
2. a /32 route to that IP via the physical gateway
3. the config file
```

Without 1 and 2 nothing exits **and the machine looks healthy from outside**, because inbound
SSH is conntrack-marked and still answered via `eth0`. The gateway differs per machine, so the
switch script *derives* it from the existing `/32` route instead of hardcoding it.

## 3. Verification checklist (none skipped, least of all #10)

```bash
# 1. services               systemctl is-active <all units>
# 2. tun0 exists AND has an address
ip -4 addr show tun0 | grep inet
# 3. default route is the tunnel
ip route get 1.1.1.1
# 4. the IP the world sees is the proxy's
curl -s https://api.ipify.org
# 5. the critical upstream endpoint RESPONDS (a 404 is fine; it proves reachability)
# 6. the display            DISPLAY=:99 xdpyinfo | grep dimensions
# 7. the Python stack imports and sees the screen
# 8. the browser actually opens a window (not just "is default")
# 9. every operator script exists (test -f each one)
# 10. REBOOT THE MACHINE and repeat 1–9
```

Step 10 is the one that caught the two worst failures (§4.1, §4.2): the stack **survived until
the first reboot** and the breakage produced no error.

## 4. The failure catalog

Every entry was caught on a real machine. None produced a clear error; several left the
system in a state that *looked* correct.

### 4.1 The setup scripts overwrite the good systemd units

A setup script wrote its own (older) version of a unit, missing the `ExecStartPost=` that
configures `tun0`. The service showed `active`, the interface existed — DOWN and addressless —
and everything downstream failed. **Rule: units are copied AFTER the scripts run.** Check:

```bash
systemctl show <unit> -p ExecStartPost --value    # must NOT be empty
```

### 4.2 The `Type=simple` startup race

Unit B had `After=A.service` and still ran too early: A is `Type=simple`, so systemd considers
it "started" the moment the binary launches — **without waiting for its `ExecStartPost`**. The
dependency was satisfied with `tun0` addressless, and B's route failed with *"Device for
nexthop is not up"*. After a reboot the machine was exiting through **its own IP** — the worst
possible state. Fix: an `ExecStartPre` poll in B:

```ini
ExecStartPre=/bin/bash -c "for i in $(seq 160); do ip -4 addr show tun0 2>/dev/null | grep -q inet && exit 0; sleep 0.25; done; echo 'tun0 has no address after 40 s'; exit 1"
```

### 4.3 `pipefail` + a no-match `grep` aborts the whole script

A firewall script began its cleanup loop with `N=$(ufw status numbered | grep "$PORT" | ...)`.
On a fresh machine there is no rule, `grep` returns 1, `pipefail` propagates it, `set -e`
kills the script — **before the `ufw allow` below ever runs**. The script whose job was to
open remote access left it closed, and if a rule existed it deleted it before dying. Fix on
the assignment (`|| true`), not on the delete — found with `bash -x`, not by rereading prose.

Bonus bug in the same script: its "already allowed" check grepped `IP.*PORT` while `ufw
status` prints `PORT ... IP` — it could never match, so it deleted and re-created the same
rule forever. Harmless alone; fatal next to the first bug.

### 4.4 A patch that isn't in the clone source protects nobody

Months after both fixes above were written and documented, two new machines were born with the
unpatched script: **the machine everyone clones from was the one machine never patched.** An
audit of all nine confirmed it. Lesson: a fix exists only when it is in the *origin* of the
clones; until then every new machine re-inherits the bug.

### 4.5 Checks that pass with the wrong answer

- "Is the port reachable?" (`nc`) is green on the **wrong** proxy port — both ports accept
  TCP; what fails is the protocol handshake. Test proxies with `curl --proxy socks5h://...`,
  never with a port probe.
- `ip route get` says the admin's return traffic goes through the tunnel — scary red flag,
  except it ignores `fwmark`. The conntrack mark is what keeps SSH alive, and the correct
  check is that the marking apparatus exists (`iptables -t mangle -S | grep CONNMARK`,
  `ip rule | grep 0x1`, `ip route show table 100`). The empirical proof is simpler: the SSH
  session you're reading the warning through.
- Grepping the vendor's `.desktop` file for a required flag "fails" forever — correctly,
  because the fix installs its *own* `.desktop` earlier in `XDG_DATA_DIRS`, where no package
  update overwrites it. Check the real resolution chain, not the vendor file.
- `ss -ltn | grep 3389` right after boot is empty because xrdp takes a few seconds longer
  than everything else. Re-check before diagnosing.

### 4.6 A revoked upstream credential looks like a healthy system

When a proxy provider revokes credentials, **established connections keep working** — the
worker keeps running and logging normally. Only *new* connections fail (`rejected
username/password` in the journal). The system is healthy-looking and doomed: it dies at the
next reconnect. Monitoring must therefore test *new* connections, not the process's pulse.

### 4.7 Stray state breaks the managed one

The setup script started Xvfb by hand, leaving `/tmp/.X99-lock`; the systemd unit then
couldn't bind `:99` (`Start request repeated too quickly`). Worse: the stray Xvfb ran at
1280x**984** while the unit uses 1280x**1024** — and all automation coordinates are calibrated
for 1024, so letting it live breaks things *subtly* instead of loudly. The unit is the one
that survives a reboot; the unit wins. Kill the stray, remove the lock, `reset-failed`,
restart, verify `xdpyinfo`.

### 4.8 Cloned state carries the origin machine's identity

The worker payload copied from a working machine included its runtime state files. The new
machine booted believing it was the *old* machine — stale state is bad; someone else's state
is worse. Rule: after deploying, delete all runtime state (`state.json`, identity, caches)
**before** first start, and verify the service logs `identity: None`.

### 4.9 Fleet drift: seven machines, five different inventories

Each machine is supposed to carry the scripts and assets of **every** workload, so moving a
workload is a one-line change. An audit found 127–143 files per machine where the full set was
144 — and the missing files were exactly the two *newest* workloads, each left only on the
machine that used it. One machine spent a day producing nothing because 9 of its 10 route
templates were missing; its own logs looked alive the whole time.

The check that matters is not *counting* files but **comparing the list**:

```bash
for h in m1 m2 m3 ...; do ssh $h 'cd /path && ls | sort' > inv_$h.txt; done
md5sum inv_*.txt | awk '{print $1}' | sort -u | wc -l     # must print 1
```

### 4.10 The timezone trap

All nine machines came from the provider in `Europe/Berlin`, not UTC. A cron line with a
clock time fires an hour (or two, in summer) away from what was intended. Fix: cron says only
"every minute" (timezone-free) and the script compares **epoch** seconds:

```bash
CUTOFF=1793692320                    # the moment, in UTC epoch
[ "$(date -u +%s)" -lt "$CUTOFF" ] && exit 0
```

### 4.11 Assorted traps that cost real time

- **`pkill -f <pattern>` from an SSH command line kills your own session** — the pattern
  matches the remote command itself. Patterns live *inside* scripts, and the script's name
  must not appear on the invoking line either.
- **VNC truncates passwords to 8 characters silently**; a longer one "fails to connect" with
  no reason given.
- **A missing operator script isn't noticed until the day it's needed** — the machine works
  fine without `stop.sh` right up until you need to stop it. Hence check #9 above.
- **Mixed line endings** (one CRLF file, one LF) make patches half-apply. Count bytes:
  `d.count(b"\r\n")` vs `d.count(b"\n")`.
- A long `systemctl enable --now` block can hang the SSH session **while the work completes
  fine**. Don't re-run it (the re-run's cleanup would kill the now-healthy stack) — verify
  from a second session instead.

## 5. The working rules that fall out of all this

1. **Validate the instrument before trusting the conclusion.** Several earlier "conclusions"
   in the original runbook are struck through *in the document itself*, with the explanation
   of why the measurement was broken. Keeping the wrong version visible is deliberate: it's
   the evidence trail.
2. **A verification that passes with the wrong answer verifies nothing.** Every fix is tested
   both ways: it must pass with the right state *and fail* with the wrong one.
3. **When in doubt, build an instrument.** No change ships without a before/after measurement.
4. **Comments say *why*, with the date and the number that motivated the decision.**
