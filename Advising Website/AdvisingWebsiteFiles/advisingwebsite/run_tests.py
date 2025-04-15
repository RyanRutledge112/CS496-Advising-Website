import subprocess
import os
import platform

def run_tests():
    # Run Django tests with pytest
    subprocess.run(['pytest', '--maxfail=1', '--disable-warnings', '-q'])
    
    system = platform.system()

    if system == 'Windows':
        # Full path to npm.cmd on Windows
        npm_cmd = r'C:\Program Files\nodejs\npm.cmd'
        subprocess.run([npm_cmd, 'test', '--', '--maxWorkers=2'])
    else:
        # macOS/Linux – just use 'npm' from PATH
        subprocess.run(['npm', 'test', '--', '--maxWorkers=2'])

if __name__ == '__main__':
    run_tests()