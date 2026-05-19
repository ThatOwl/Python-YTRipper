import shlex
import sys

from autotagging.standalone.app import TaggingStandaloneCLI
from cli.interactive_prompt import InteractivePrompt


def main(argv: list[str] | None = None) -> int:
    if argv is not None:
        return TaggingStandaloneCLI().execute(argv)

    args = sys.argv[1:]
    if args and args[0] in ("help", "-h", "--help"):
        print("Standalone autotagger CLI (type 'exit' or '(q)uit' to leave)")
        print("Either run in loop-mode or provide one command directly.")
        print("- Loop mode: no args or -l/--loop")
        print("- Command mode: provide a normal command and flags")
        print("")
        return TaggingStandaloneCLI().execute(["--help"])

    if not args or args[0] in ("-l", "--loop", "loop"):
        cli = TaggingStandaloneCLI()
        prompt = InteractivePrompt(lambda: cli.build_parser(), prompt_label="yt-tagger> ")
        while True:
            try:
                command = prompt.prompt().strip()
            except KeyboardInterrupt:
                print("")
                continue
            except EOFError:
                print("\nExiting CLI.")
                return 1

            if command.lower() in ("exit", "quit", "q"):
                print("\n Exiting CLI. \n")
                return 0
            if not command:
                continue
            cli.execute(shlex.split(command))

    return TaggingStandaloneCLI().execute(args)


if __name__ == "__main__":
    raise SystemExit(main())
