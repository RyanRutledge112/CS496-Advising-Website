import subprocess

def run_tests():
    # Run Django tests with pytest
    subprocess.run(['pytest', '--maxfail=1', '--disable-warnings', '-q'])

    # Run Jest tests for JavaScript
    subprocess.run([r'C:\Program Files\nodejs\npm.cmd', 'test', '--', '--maxWorkers=2'])

if __name__ == '__main__':
    run_tests()