#!/usr/bin/env python3
"""Main executable entry point for doq CLI."""

import sys

def main():
    """Main entry point for module execution."""
    # Import and run the main function with command line arguments
    from doq.main import main as doq_main
    return doq_main(sys.argv[1:])

if __name__ == "__main__":
    sys.exit(main())
