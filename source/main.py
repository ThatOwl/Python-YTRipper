import sys
import os

#TODO ... a lot 
# implement startup into different modes based on sys.argv
# e.g. "menu" for interactive, otherwise command mode
# possibly add other modes later (e.g. GUI)
# for now, just basic interactive vs command line

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from source.cli.cli_interactive import InteractiveCLI
from source.cli.cli_command import CommandCLI

def main():
    if len(sys.argv) == 1 or sys.argv[1] in ("m", "i","menu", "interactive"):
        InteractiveCLI().run()
    elif sys.argv[1] in ("-h", "--help", "l", "loop"):
        if sys.argv[1] in ("-h", "--help"):
            print("YouTube Downloader CLI (type 'exit' or '(q)uit' to leave)")
            print("Either run in interactive mode (no arguments) or provide a single command.")
            print("- Interactive mode enter with [m]enu or [i]nteractive.")
            print("- Loop mode [l]oop: command menu repeatedly after each command.")
            print("- Command mode: provide all arguments in one line. (limited options)")
            CommandCLI().run("--help")
        
        while True:
            try:
                command = input("yt-ripper> ").strip()
            except EOFError:
                print("\nExiting CLI.")
                return 1
            if command.lower() in ('exit', 'quit', 'q'):
                print("\n Exiting CLI. \n\n")
                return 0
            if not command:
                continue
            
            CommandCLI().run(command)
    else:
        cmdline = " ".join(sys.argv[1:])
        CommandCLI().run(cmdline)

if __name__ == "__main__":
    main()