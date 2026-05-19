import sys

from autotagging.standalone.app import TaggingStandaloneCLI
from cli.interactive_prompt import InteractivePrompt, split_prompt_command
import utility.preferences as preferences


def main(argv: list[str] | None = None) -> int:
    cli = TaggingStandaloneCLI()

    if argv is not None:
        return cli.execute(argv)

    args = sys.argv[1:]
    if args and args[0] in ("help", "-h", "--help"):
        print("Standalone autotagger CLI (type 'exit' or '(q)uit' to leave)")
        print("Either run in loop-mode or provide one command directly.")
        print("- Loop mode: no args or -l/--loop")
        print("- Command mode: provide a normal command and flags")
        print("")
        return cli.execute(["--help"])

    if not args or args[0] in ("-l", "--loop", "loop"):
        prompt = InteractivePrompt(
            lambda: cli.parser,
            prompt_label="yt-tagger> ",
            history_path=preferences.CONFIG_DIR / "yt_tagger_history.txt",
        )
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
            cli.execute(split_prompt_command(command))

    return cli.execute(args)


if __name__ == "__main__":
    raise SystemExit(main())
