import subprocess
import os
import platform

def run_tests():
    # Run Django tests from the general 'tests' folder (using default settings)
    subprocess.run(['pytest', '--maxfail=1', '--disable-warnings', '-q', '-s', 'advisingwebsiteapp/tests'])

    # Now, run only the specific test (test_messaging_system_integration.py) in 'seleniumTests' with 'testSettings.py'
    os.environ['DJANGO_SETTINGS_MODULE'] = 'advisingwebsite.testSettings'
    subprocess.run(['pytest', '--maxfail=1', '--disable-warnings', '-q', '-s', 'advisingwebsiteapp/seleniumTests/test_messaging_system_integration.py'])
    subprocess.run(['pytest', '--maxfail=1', '--disable-warnings', '-q', '-s', 'advisingwebsiteapp/seleniumTests/test_page_load_times.py'])

    # Handle npm tests based on the system type
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