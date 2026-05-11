import shlex
import sys

from cli.cli_command import CommandCLI


def main():
    args = sys.argv[1:]

    if not args or args[0] in ("-h", "--help", "-l", "--loop"):
        if args and args[0] in ("-h", "--help"):
            print("YouTube Downloader CLI (type 'exit' or '(q)uit' to leave)")
            print("Either run in loop-mode or single by providing a single command.")
            print("- Loop mode [l]oop: command menu repeatedly after each command.")
            print("- Command mode: provide all arguments in one line.")
            print("")
            CommandCLI().run("--help")
            return 0

        cli = CommandCLI()

        while True:
            try:
                command = input("yt-ripper> ").strip()
            except EOFError:
                print("\nExiting CLI.")
                return 1

            if command.lower() in ("exit", "quit", "q"):
                print("\n Exiting CLI. \n\n")
                return 0

            if not command:
                continue

            cli.run(command)

    cmdline = " ".join(shlex.quote(arg) for arg in args)
    return CommandCLI().run(cmdline)


if __name__ == "__main__":
    sys.exit(main())
