import shutil
import subprocess
import os
from backend.kite_passport import KitePassport

k = KitePassport.__new__(KitePassport)

wsl = shutil.which('wsl')
print('wsl executable:', repr(wsl))

if not wsl:
    raise SystemExit('wsl not found')

result = subprocess.run([wsl, '-l', '-q'], capture_output=True, timeout=10)
print('distro raw bytes:', repr(result.stdout[:200]))
print('rc', result.returncode)
distro_stdout = k._decode_wsl_output(result.stdout)
print('decoded distros:', repr(distro_stdout))
distros = [line.strip() for line in distro_stdout.splitlines() if line.strip() and not line.strip().startswith('docker-')]
print('parsed distros:', repr(distros))

candidate_users = []
env_user = os.getenv('KITE_PASSPORT_WSL_USER')
if env_user:
    candidate_users.append(env_user)
for user_var in (os.getenv('USER'), os.getenv('USERNAME')):
    if user_var and user_var not in candidate_users:
        candidate_users.append(user_var)
print('candidate_users:', repr(candidate_users))

for distro in distros:
    for user in candidate_users:
        if not user:
            continue
        try:
            args = [wsl, '-d', distro, '-u', user, 'bash', '-ic', 'command -v kpass']
            print('trying args:', repr(args))
            print('has null?', any('\x00' in a for a in args))
            r = subprocess.run(args, capture_output=True, timeout=10)
            decoded = k._decode_wsl_output(r.stdout)
            print('  rc', r.returncode, 'out', repr(decoded), 'err', repr(k._decode_wsl_output(r.stderr)))
        except Exception as e:
            print('  exception', type(e).__name__, e)

    try:
        cmd = "awk -F: '$3>=1000 && $1 != \"nobody\" {print $1}' /etc/passwd"
        args = [wsl, '-d', distro, 'bash', '-lc', cmd]
        print('trying passwd args:', repr(args))
        r = subprocess.run(args, capture_output=True, timeout=10)
        decoded = k._decode_wsl_output(r.stdout)
        print('passwd rc', r.returncode, 'out', repr(decoded), 'err', repr(k._decode_wsl_output(r.stderr)))
        distro_users = [line.strip() for line in decoded.splitlines() if line.strip()]
        print('distro_users', repr(distro_users))
    except Exception as e:
        print('passwd exception', type(e).__name__, e)
        distro_users = []

    for user in distro_users:
        if user in candidate_users:
            continue
        try:
            args = [wsl, '-d', distro, '-u', user, 'bash', '-ic', 'command -v kpass']
            print('trying distro user args:', repr(args))
            r = subprocess.run(args, capture_output=True, timeout=10)
            decoded = k._decode_wsl_output(r.stdout)
            print('  rc', r.returncode, 'out', repr(decoded), 'err', repr(k._decode_wsl_output(r.stderr)))
        except Exception as e:
            print('  exception', type(e).__name__, e)
