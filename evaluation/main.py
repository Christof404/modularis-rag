from .cli.evaluation_cli import EvaluationCLI


def main():
    cli = EvaluationCLI()
    try:
        cli.run()
    except KeyboardInterrupt:
        print("\nAborted by user.")

if __name__ == '__main__':
    main()
