from autotagging.standalone.app import TaggingStandaloneCLI


def main(argv: list[str] | None = None) -> int:
    return TaggingStandaloneCLI().execute(argv)


if __name__ == "__main__":
    raise SystemExit(main())
