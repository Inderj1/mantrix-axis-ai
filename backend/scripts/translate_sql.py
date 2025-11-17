#!/usr/bin/env python3
"""
CLI tool for testing SQL dialect translation.

Usage:
    # Basic translation
    python scripts/translate_sql.py \
        --sql "SELECT DATE_SUB(CURRENT_DATE(), INTERVAL 7 DAY)" \
        --from bigquery \
        --to snowflake

    # With cost estimation
    python scripts/translate_sql.py \
        --sql "SELECT * FROM users WHERE active = true" \
        --from bigquery \
        --to postgresql \
        --show-cost

    # Batch translation from file
    python scripts/translate_sql.py \
        --file queries.sql \
        --from bigquery \
        --to snowflake \
        --output translated.sql

    # Interactive mode
    python scripts/translate_sql.py --interactive
"""
import sys
import os
import argparse
from typing import List

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.core.sql_dialect_translator import SQLDialectTranslator, TranslationError


def print_translation_result(result, verbose=False):
    """Print translation result in a nice format."""
    print("\n" + "="*80)
    print("TRANSLATION RESULT")
    print("="*80)
    print(f"\nSource Dialect: {result.source_dialect}")
    print(f"Target Dialect: {result.target_dialect}")
    print(f"\nTranslated SQL:")
    print("-"*80)
    print(result.translated_sql)
    print("-"*80)

    if result.changes:
        print(f"\nChanges Made ({len(result.changes)}):")
        for i, change in enumerate(result.changes, 1):
            print(f"  {i}. {change}")

    if result.warnings:
        print(f"\nWarnings ({len(result.warnings)}):")
        for i, warning in enumerate(result.warnings, 1):
            print(f"  {i}. {warning}")

    print(f"\nLossless: {'Yes' if result.is_lossless else 'No'}")
    print(f"Confidence Score: {result.confidence_score:.2f}")

    if verbose:
        print(f"\nVerbose Info:")
        print(f"  Original SQL length: {len(result.translated_sql)} chars")
        print(f"  Changes count: {len(result.changes)}")
        print(f"  Warnings count: {len(result.warnings)}")

    print("="*80 + "\n")


def translate_single(args):
    """Translate a single SQL query."""
    translator = SQLDialectTranslator()

    try:
        # Show cost if requested
        if args.show_cost:
            cost = translator.get_translation_cost(
                args.sql,
                args.from_dialect,
                args.to_dialect
            )
            print(f"\nTranslation Cost: {cost:.2f}")
            if cost == 0.0:
                print("  → Trivial (identical syntax or same dialect)")
            elif cost < 0.2:
                print("  → Low cost (minor syntax changes)")
            elif cost < 0.5:
                print("  → Moderate cost (function changes)")
            elif cost < 0.8:
                print("  → High cost (significant differences)")
            else:
                print("  → Very high cost (may require manual review)")
            print()

        # Translate
        result = translator.translate(
            args.sql,
            args.from_dialect,
            args.to_dialect,
            validate=not args.no_validate
        )

        print_translation_result(result, verbose=args.verbose)

        # Copy to clipboard if requested
        if args.copy:
            try:
                import pyperclip
                pyperclip.copy(result.translated_sql)
                print("✓ Translated SQL copied to clipboard")
            except ImportError:
                print("⚠ Install pyperclip to use --copy: pip install pyperclip")

    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except TranslationError as e:
        print(f"Translation failed: {e}", file=sys.stderr)
        sys.exit(1)


def translate_from_file(args):
    """Translate SQL queries from a file."""
    translator = SQLDialectTranslator()

    # Read queries from file
    with open(args.file, 'r') as f:
        content = f.read()

    # Split by semicolons and filter empty
    queries = [q.strip() for q in content.split(';') if q.strip()]

    print(f"\nFound {len(queries)} queries in {args.file}")
    print(f"Translating from {args.from_dialect} to {args.to_dialect}...\n")

    # Batch translate
    results = translator.batch_translate(
        queries,
        args.from_dialect,
        args.to_dialect
    )

    # Print summary
    successful = sum(1 for r in results if r.confidence_score > 0)
    failed = len(results) - successful

    print(f"\nTranslation Complete:")
    print(f"  Total: {len(results)}")
    print(f"  Successful: {successful}")
    print(f"  Failed: {failed}")

    # Save to output file if specified
    if args.output:
        with open(args.output, 'w') as f:
            for i, result in enumerate(results, 1):
                f.write(f"-- Query {i} (confidence: {result.confidence_score:.2f})\n")
                f.write(f"-- Source: {result.source_dialect} → {result.target_dialect}\n")
                if result.warnings:
                    f.write(f"-- Warnings: {', '.join(result.warnings)}\n")
                f.write(result.translated_sql)
                f.write(";\n\n")
        print(f"\n✓ Translated queries saved to {args.output}")
    else:
        # Print all results
        for i, result in enumerate(results, 1):
            print(f"\n--- Query {i}/{len(results)} ---")
            print_translation_result(result, verbose=False)


def interactive_mode():
    """Interactive translation mode."""
    translator = SQLDialectTranslator()
    dialects = ['bigquery', 'snowflake', 'postgresql', 'redshift', 'databricks']

    print("\n" + "="*80)
    print("SQL DIALECT TRANSLATOR - INTERACTIVE MODE")
    print("="*80)
    print("\nSupported dialects:", ", ".join(dialects))
    print("\nCommands:")
    print("  'quit' or 'exit' - Exit interactive mode")
    print("  'dialects' - Show supported dialects")
    print("  'help' - Show this help message")
    print("="*80 + "\n")

    while True:
        try:
            # Get source dialect
            print("\nEnter source dialect (or command):")
            source = input("> ").strip().lower()

            if source in ['quit', 'exit']:
                print("Goodbye!")
                break
            elif source == 'dialects':
                print("\nSupported dialects:", ", ".join(dialects))
                continue
            elif source == 'help':
                print("\nCommands:")
                print("  'quit' or 'exit' - Exit interactive mode")
                print("  'dialects' - Show supported dialects")
                print("  'help' - Show this help message")
                continue
            elif source not in dialects:
                print(f"Invalid dialect. Supported: {', '.join(dialects)}")
                continue

            # Get target dialect
            print("\nEnter target dialect:")
            target = input("> ").strip().lower()

            if target not in dialects:
                print(f"Invalid dialect. Supported: {', '.join(dialects)}")
                continue

            # Get SQL query
            print("\nEnter SQL query (or press Ctrl+D when done):")
            print("(Hint: For multi-line input, type each line and press Ctrl+D when done)")
            lines = []
            try:
                while True:
                    line = input()
                    lines.append(line)
            except EOFError:
                pass

            sql = '\n'.join(lines).strip()

            if not sql:
                print("No SQL provided")
                continue

            # Translate
            try:
                result = translator.translate(sql, source, target)
                print_translation_result(result, verbose=True)
            except Exception as e:
                print(f"Translation error: {e}")

        except KeyboardInterrupt:
            print("\n\nGoodbye!")
            break


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="SQL Dialect Translator CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )

    parser.add_argument(
        '--sql',
        help='SQL query to translate'
    )

    parser.add_argument(
        '--file',
        help='File containing SQL queries (separated by semicolons)'
    )

    parser.add_argument(
        '--from', '--from-dialect',
        dest='from_dialect',
        help='Source dialect (bigquery, snowflake, postgresql, redshift, databricks)'
    )

    parser.add_argument(
        '--to', '--to-dialect',
        dest='to_dialect',
        help='Target dialect'
    )

    parser.add_argument(
        '--output',
        help='Output file for translated queries (only with --file)'
    )

    parser.add_argument(
        '--show-cost',
        action='store_true',
        help='Show translation cost estimate'
    )

    parser.add_argument(
        '--no-validate',
        action='store_true',
        help='Skip validation of translated SQL'
    )

    parser.add_argument(
        '--copy',
        action='store_true',
        help='Copy translated SQL to clipboard (requires pyperclip)'
    )

    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Verbose output'
    )

    parser.add_argument(
        '--interactive', '-i',
        action='store_true',
        help='Interactive mode'
    )

    args = parser.parse_args()

    # Interactive mode
    if args.interactive:
        interactive_mode()
        return

    # Validate arguments
    if args.file:
        if not args.from_dialect or not args.to_dialect:
            parser.error("--from and --to are required with --file")
        translate_from_file(args)
    elif args.sql:
        if not args.from_dialect or not args.to_dialect:
            parser.error("--from and --to are required with --sql")
        translate_single(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == '__main__':
    main()
