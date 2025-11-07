import sys
import os

#TODO ... a lot 
# implement startup into different modes based on sys.argv
# e.g. "menu" for interactive, otherwise command mode
# possibly add other modes later (e.g. GUI)
# for now, just basic interactive vs command line

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from source.cli.cli_interactive import InteractiveCLI
from source.cli.cli_command import CommandCLI

def main():
    no_url_provided = len(sys.argv) == 1
    if "menu" in sys.argv or no_url_provided:
        InteractiveCLI().run()
    else:
        CommandCLI().run(sys.argv[1:])
        sys.exit()  # ensure proper exit code propagation
        
if __name__ == "__main__":
    main()